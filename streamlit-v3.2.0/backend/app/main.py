import os
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from collections import deque
from dataclasses import asdict
from multiprocessing import Manager
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import engine
from .repository import load_catalog
from .optimization.model import Preferences, validate_request
from .optimization.optimizer import solve
from .optimization.checker import check
from .optimization.v4.policy import Policy
from .optimization.v4.solve import solve as solve_v4, validate as validate_v4

Term = Literal["2026-27 Term 1", "2026-27 Term 2"]
DEFAULT_TERM = "2026-27 Term 1"
Day = Annotated[int, Field(ge=1, le=7)]
Minute = Annotated[int, Field(ge=0, le=1440)]
Rating = Annotated[float, Field(ge=0, le=5)]

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

class PreferenceInput(Input):
    early: Rating | None = None
    weekdays: dict[Day, Rating] = Field(default_factory=dict, max_length=7)
    teachers: dict[str, dict[str, Rating]] = Field(default_factory=dict, max_length=500)
    ban_early: bool = False
    banned_days: tuple[Day, ...] = Field(default=(), max_length=7)
    blocked: tuple[tuple[Day, Minute, Minute], ...] = Field(default=(), max_length=100)
    allow_missing_components: bool = False

    @model_validator(mode="after")
    def check_ranges(self):
        if any(start >= end for _, start, end in self.blocked):
            raise ValueError("Blocked periods must end after they start")
        return self

class PlanInput(Input):
    term: Term = DEFAULT_TERM
    codes: list[str] = Field(min_length=1, max_length=500)
    preferences: PreferenceInput = Field(default_factory=PreferenceInput)

class OptimizeInput(PlanInput):
    timeout: int = Field(default=15, ge=1, le=120)

class ValidateInput(PlanInput):
    selections: list[tuple[str, str]] = Field(max_length=1500)

@asynccontextmanager
async def lifespan(app):
    with Manager() as manager:
        with ProcessPoolExecutor(max_workers=2) as executor:
            app.state.executor = executor
            app.state.slots = BoundedSemaphore(2)
            app.state.progress_store = manager.dict()
            app.state.progress_order = deque()
            app.state.progress_lock = Lock()
            yield

app = FastAPI(title="Course Schedule Optimizer", lifespan=lifespan)

def failure(status, code, detail):
    return JSONResponse(status_code=status, content=jsonable_encoder({"error": {"code": code, "detail": detail}}))

@app.exception_handler(StarletteHTTPException)
def http_error(request, exc):
    return failure(exc.status_code, f"http_{exc.status_code}", exc.detail)

@app.exception_handler(RequestValidationError)
def input_error(request, exc):
    errors = [{"location": e["loc"], "message": e["msg"]} for e in exc.errors()]
    return failure(422, "invalid_input", errors)

@app.exception_handler(SQLAlchemyError)
def db_error(request, exc):
    return failure(503, "database_unavailable", "The course database is unavailable.")

def catalog(term):
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        return load_catalog(connection, term)

@app.get("/api/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.get("/api/courses")
def courses(term: Term = DEFAULT_TERM):
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT c.code,c.name,c.credits FROM courses c WHERE EXISTS "
            "(SELECT 1 FROM sections s WHERE s.term=:term AND s.course_code=c.code) ORDER BY c.code"
        ), {"term": term}).mappings()
        return [dict(row) for row in rows]

@app.get("/api/courses/{code}")
def course(code: str, term: Term = DEFAULT_TERM):
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        cat = load_catalog(connection, term, code)
    if code not in cat.courses:
        raise HTTPException(404, "Course is unavailable in this term")
    bindings = {lecture: sorted(tutorials) for (course_code, lecture), tutorials in cat.bindings.items() if course_code == code}
    return {**cat.courses[code], "sections": [asdict(s) for s in cat.sections[code]],
            "required": sorted(cat.required[code]), "bindings": bindings, "warnings": cat.warnings}

@app.get("/api/preferences/schema")
def preference_schema():
    return OptimizeInput.model_json_schema()

def verified(cat, codes, selections, preferences):
    report = check(cat, codes, selections, preferences)
    meetings = []
    if report["passed"]:
        for code, section in selections:
            item = next(s for s in cat.sections[code] if s.code == section)
            meetings.extend({**asdict(m), "course": code, "section": section, "component": item.component,
                             "name": cat.courses[code]["name"]} for m in item.meetings)
    return {**report, "meetings": meetings}

def optimize_job(cat, codes, preferences, timeout):
    result = solve(cat, codes, preferences, timeout=timeout)
    payload = asdict(result)
    for solution in payload["solutions"]:
        solution["validation"] = verified(cat, codes, solution["selections"], preferences)
    return payload

@app.post("/api/optimize")
def optimize(body: OptimizeInput, request: Request):
    if not request.app.state.slots.acquire(blocking=False):
        raise HTTPException(503, "Both search workers are busy. Try again shortly.")
    try:
        cat = catalog(body.term)
        prefs = Preferences(**body.preferences.model_dump())
        errors = validate_request(cat, body.codes, prefs)
        if errors:
            raise HTTPException(422, errors)
        future = request.app.state.executor.submit(optimize_job, cat, body.codes, prefs, body.timeout)
    except BaseException:
        request.app.state.slots.release()
        raise
    future.add_done_callback(lambda _: request.app.state.slots.release())
    try:
        return future.result(timeout=body.timeout + 10)
    except TimeoutError:
        raise HTTPException(504, "Search exceeded the server deadline")

@app.post("/api/validate")
def validate(body: ValidateInput):
    return verified(catalog(body.term), body.codes, body.selections, Preferences(**body.preferences.model_dump()))


class V4Plan(Input):
    term: Term = DEFAULT_TERM
    codes: list[str] = Field(min_length=1, max_length=80)
    preferences: Policy = Field(default_factory=Policy)


class V4Optimize(V4Plan):
    timeout: Annotated[int, Field(strict=True, ge=1)] = 30


class V4Validate(V4Plan):
    selections: list[tuple[str, str]] = Field(max_length=500)


def v4_display(cat, choices, report, warnings):
    report["warnings"] = warnings
    report["meetings"] = []
    if report["passed"]:
        for code, sec in choices:
            section = next(s for s in cat.sections[code] if s.code == sec)
            report["meetings"].extend({**asdict(m), "course": code, "section": sec,
                "component": section.component, "name": cat.courses[code]["name"]} for m in section.meetings)
    return report


def run_v4_job(cat, codes, preferences, timeout, deadline, progress_store=None, progress_job_id=None):
    class DisplayProgress:
        def get(self, *args):
            return progress_store.get(*args)

        def __setitem__(self, key, value):
            for row in value.get("preview", []):
                v4_display(cat, row["selections"], row["validation"], [])
            progress_store[key] = value

    answer = solve_v4(cat, codes, preferences, timeout, deadline,
                      progress_store=DisplayProgress() if progress_store is not None else None,
                      progress_job_id=progress_job_id)
    for row in answer["solutions"]:
        v4_display(cat, row["selections"], row["validation"], answer["warnings"])
    return answer


@app.get("/api/v4/preferences/schema")
def v4_schema():
    return V4Optimize.model_json_schema()


def v4_timeout_limit():
    return max(30, int(os.environ.get("V4_MAX_TIMEOUT_SECONDS", "180")))


@app.get("/api/v4/settings")
def v4_settings(term: Term = DEFAULT_TERM):
    with engine.connect() as connection:
        updated = connection.execute(text("""
            SELECT MAX(verified_at) FROM collection_runs WHERE term=:term
        """), {"term": term}).scalar()
    return {"timeout_default": 30, "timeout_limit": v4_timeout_limit(),
            "top_k": 3, "data_source": "学校 SIS 课程快照", "last_verified": updated}


def update_progress(request, job_id, **updates):
    store = request.app.state.progress_store
    snapshot = dict(store.get(job_id, {}))
    snapshot.update(updates)
    snapshot["updated_at"] = monotonic()
    store[job_id] = snapshot


@app.get("/api/v4/progress/{job_id}")
def v4_progress(job_id: str, request: Request):
    try:
        canonical_id = str(UUID(job_id))
    except ValueError:
        raise HTTPException(404, "Optimization job was not found")
    snapshot = request.app.state.progress_store.get(canonical_id)
    if snapshot is None:
        raise HTTPException(404, "Optimization job was not found")
    return JSONResponse(jsonable_encoder(dict(snapshot)), headers={"Cache-Control": "no-store"})


@app.post("/api/v4/optimize")
def optimize_v4(body: V4Optimize, request: Request):
    limit = v4_timeout_limit()
    continuous = request.headers.get("X-Search-Mode") == "complete"
    if not continuous and body.timeout > limit:
        raise HTTPException(422, f"服务器本次允许最多 {limit} 秒，请调整搜索时间。")
    deadline = None if continuous else monotonic() + body.timeout
    supplied_job_id = request.headers.get("X-Progress-Id")
    try:
        job_id = str(UUID(supplied_job_id)) if supplied_job_id else str(uuid4())
    except ValueError:
        raise HTTPException(422, "X-Progress-Id must be a UUID.")
    if not request.app.state.slots.acquire(blocking=False):
        raise HTTPException(503, "Both search workers are busy. Try again shortly.")
    registered = False
    try:
        cat = catalog(body.term)
        with request.app.state.progress_lock:
            if job_id in request.app.state.progress_store:
                raise HTTPException(409, "Optimization job ID already exists.")
            request.app.state.progress_store[job_id] = {
                "job_id": job_id, "state": "queued", "phase": "queued",
                "branches": 0, "current_branches": 0, "conflicts": 0,
                "solver_run": 0, "updated_at": monotonic(),
            }
            registered = True
            request.app.state.progress_order.append(job_id)
            for expired in tuple(request.app.state.progress_order):
                if len(request.app.state.progress_order) <= 128:
                    break
                old = request.app.state.progress_store.get(expired)
                if old is None or old["state"] in {"completed", "failed", "timed_out"}:
                    request.app.state.progress_order.remove(expired)
                    request.app.state.progress_store.pop(expired, None)
        future = request.app.state.executor.submit(
            run_v4_job, cat, body.codes, body.preferences, None if continuous else body.timeout, deadline,
            request.app.state.progress_store, job_id)
    except BaseException:
        request.app.state.slots.release()
        if registered:
            request.app.state.progress_store.pop(job_id, None)
        raise
    if continuous:
        def finish(job):
            try:
                answer = job.result()
                update_progress(request, job_id, state="completed", phase="completed", result=answer,
                                preview=[], branches=answer["search_summary"]["branches"])
            except Exception:
                update_progress(request, job_id, state="failed", phase="failed")
            finally:
                request.app.state.slots.release()
        future.add_done_callback(finish)
        return JSONResponse({"job_id": job_id}, status_code=202)
    future.add_done_callback(lambda _: request.app.state.slots.release())
    try:
        answer = future.result(timeout=max(0.001, deadline-monotonic()+1))
        update_progress(request, job_id, state="completed", phase="completed",
                        result_status=answer["status"],
                        branches=answer.get("search_summary", {}).get("branches", 0),
                        current_branches=0)
        return answer
    except TimeoutError:
        future.cancel()
        update_progress(request, job_id, state="timed_out", phase="timed_out")
        raise HTTPException(504, "The optimization response exceeded its deadline.")
    except BaseException:
        update_progress(request, job_id, state="failed", phase="failed")
        raise


@app.post("/api/v4/validate")
def check_v4(body: V4Validate):
    cat = catalog(body.term)
    result = validate_v4(cat,body.codes,body.preferences,body.selections)
    return v4_display(cat,body.selections,result,result.get("warnings",[]))
