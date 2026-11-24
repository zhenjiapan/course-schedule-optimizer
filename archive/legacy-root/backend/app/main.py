from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import asdict
from threading import BoundedSemaphore
from time import monotonic
from typing import Annotated, Literal

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
    with ProcessPoolExecutor(max_workers=2) as executor:
        app.state.executor = executor
        app.state.slots = BoundedSemaphore(2)
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
