"""Requires an initialized development PostgreSQL loaded with the SIS snapshot."""
import json
import os
from pathlib import Path

import pytest

if os.environ.get("RUN_POSTGRES_TESTS") != "1":
    pytest.skip("Set RUN_POSTGRES_TESTS=1 after importing the local snapshot", allow_module_level=True)

from fastapi.testclient import TestClient
from app.main import app

CODES = ["AIE1001", "AIE1901", "MAT1001", "ENG1001", "CHI1000", "PED1113"]
PAYLOAD = {"codes": CODES, "preferences": {"early": 0, "weekdays": {"5": 0}}}

def test_catalog_optimize_validate():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/openapi.json").status_code == 200
        codes = {c["code"] for c in client.get("/api/courses").json()}
        assert codes.issuperset(CODES)
        chi = client.get("/api/courses/CHI1000").json()
        assert chi["required"] == ["LEC"]
        assert client.get("/api/courses/UNKNOWN").status_code == 404
        assert client.post("/api/optimize", json={**PAYLOAD, "timeout": 0}).status_code == 422
        assert client.post("/api/optimize", json={**PAYLOAD, "codes": ["UNKNOWN"]}).status_code == 422
        result = client.post("/api/optimize", json=PAYLOAD)
        assert result.status_code == 200, result.text
        data = result.json()
        assert data["status"] == "optimal"
        assert len(data["solutions"]) == 3
        expected = Path(__file__).resolve().parents[2] / "private" / "legacy_baseline.json"
        if expected.exists():
            baseline = json.loads(expected.read_text())
            assert data["status"] == baseline["status"]
            assert [p["score"] for p in data["solutions"]] == pytest.approx([p["score"] for p in baseline["solutions"]])
        for solution in data["solutions"]:
            report = client.post("/api/validate", json={**PAYLOAD, "selections": solution["selections"]}).json()
            assert report["passed"]
            assert report["meetings"]
        invalid = client.post("/api/validate", json={**PAYLOAD, "selections": [[CODES[0], "UNKNOWN"]]}).json()
        assert not invalid["passed"]


def test_v4_real_snapshot_top_three():
    options = {
        "codes": ["ACT3141","ACT3311","AIE1101","ENG1001K"],
        "preferences": {
            "early": 1, "weekdays": {"2":5,"5":1}, "gaps": "compact",
            "evaluation_days": [f"2026-09-{day:02d}" for day in range(7,12)],
        },
    }
    with TestClient(app) as client:
        response = client.post("/api/v4/optimize",json=options)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "optimal", result
        assert result["certified_prefix"] == 3
        assert [s["loss"] for s in result["solutions"]] == ["53/287"]*3
        for row in result["solutions"]:
            report = client.post("/api/v4/validate",json={**options,"selections":row["selections"]}).json()
            assert report["passed"] and report["meetings"]


def test_v4_refreshed_term_two_bindings():
    options = {"term":"2026-27 Term 2","codes":["MAT1002","STA2001","CSC3001","CSC3200"],
               "preferences":{"early":1,"weekdays":{"5":1}}}
    with TestClient(app) as client:
        detail = client.get("/api/courses/GFN1000",params={"term":options["term"]}).json()
        assert "T27" in detail["bindings"]["L03"]
        assert "T27" not in detail["bindings"]["L10"]
        result = client.post("/api/v4/optimize",json=options).json()
        assert result["status"] == "optimal", result
        assert result["certified_prefix"] == 3
        assert all(s["validation"]["passed"] for s in result["solutions"])


def test_postgres_occurrence_override_replaces_weekly_pattern():
    from datetime import date
    from sqlalchemy import text
    from app.db import engine
    from app.repository import load_catalog
    from app.optimization.model import dates

    with engine.connect() as conn:
        tx = conn.begin()
        try:
            code, section, meeting, first = conn.execute(text("""
                SELECT s.course_code,s.section_code,m.id,m.start_date
                FROM sections s JOIN meetings m ON m.section_id=s.id
                WHERE s.term='2026-27 Term 1' AND s.course_code='CHI1000'
                    AND m.start_date IS NOT NULL AND m.start_time IS NOT NULL
                ORDER BY m.id LIMIT 1
            """)).one()
            updated = date(2026,9,20)
            assert updated != first
            conn.execute(text("""
                INSERT INTO meeting_occurrence_overrides(meeting_id, occurrences)
                VALUES (:id, ARRAY[CAST(:day AS date)])
            """),{"id":meeting,"day":updated})
            catalog = load_catalog(conn,"2026-27 Term 1",code)
            found = next(s for s in catalog.sections[code] if s.code==section)
            override = [m for m in found.meetings if m.occurrences]
            assert [list(dates(m)) for m in override] == [[updated]]
        finally:
            tx.rollback()
