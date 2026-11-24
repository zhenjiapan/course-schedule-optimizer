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
