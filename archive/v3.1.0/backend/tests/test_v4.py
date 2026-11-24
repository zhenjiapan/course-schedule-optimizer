from datetime import date, timedelta
from fractions import Fraction
from itertools import product

import pytest
from pydantic import ValidationError

from app.optimization.model import Catalog, Meeting, Section
from app.optimization.v4.policy import Policy
from app.optimization.v4.solve import solve, validate

MON = date(2026,9,7)


def section(course, code, day, start, end, teacher, component="LEC", actual=None):
    return Section(course,code,component,
                   (Meeting(day,start,end,MON,MON+timedelta(days=6),(),(teacher,),actual),),(teacher,))


@pytest.fixture
def catalog():
    return Catalog(
        {c: {"credits":3,"name":c} for c in "AB"},
        {"A":[section("A","A1",1,540,600,"A"), section("A","A2",2,540,600,"B")],
         "B":[section("B","B1",1,570,630,"A"), section("B","B2",2,600,660,"C"), section("B","B3",3,600,660,"B")]},
        {c:{"LEC"} for c in "AB"}, [])


def test_report_worked_example(catalog):
    p = Policy(credit_min=6,credit_max=6,weekdays={2:5,3:1},teachers={"A":5,"C":1})
    answer = solve(catalog,list("AB"),p)
    assert answer["status"] == "optimal"
    assert answer["certified_prefix"] == 3
    assert answer["proof_scope"] == "reference"
    assert [r["loss"] for r in answer["solutions"]] == ["7/24","3/8","5/12"]
    assert [r["selections"] for r in answer["solutions"]] == [
        (("A","A2"),("B","B1")),(("A","A2"),("B","B2")),(("A","A1"),("B","B2"))]


@pytest.mark.parametrize("gap",["compact","balanced","spacious"])
def test_joint_categories_against_enumeration(catalog,gap):
    p = Policy(credit_min=6,credit_max=6,weekdays={2:5,3:1}, teachers={"A":5,"C":1},
               gaps=gap, distribution="distributed", teaching_weeks=[MON],
               counts={"morning":{"target":2,"comparison":"exactly"}},
               latest={"minute":645,"mode":"soft"}, early=1)
    rows = []
    for pair in product(*catalog.sections.values()):
        picks = tuple((s.course,s.code) for s in pair)
        row = validate(catalog,list("AB"),p,picks)
        if row["passed"]:
            rows.append((picks, {k:Fraction(v) for k,v in row["raw_factors"].items()}))
    keys = ["T","W","latest","gaps","count:morning","B"]
    series = {key:[v.get(key,Fraction(0)) for _,v in rows] for key in keys}
    active = {k for k,column in series.items() if len(set(column))>1}
    assert "early" not in active
    expected = []
    for signature, metrics in rows:
        value = {k:metrics.get(k,Fraction(0)) for k in active}
        lo, hi = min(series["W"]),max(series["W"])
        value["W"] = (hi-value["W"])/max(1,hi-lo)
        ds = [value.pop(k) for k in ("gaps","count:morning") if k in value]
        if ds:
            value["D"] = sum(ds)/len(ds)
        expected.append((sum(value.values())/len(value),signature))
    outcome = solve(catalog,list("AB"),p)
    assert outcome["status"] == "optimal", outcome
    assert [(Fraction(r["loss"]),r["selections"]) for r in outcome["solutions"]] == sorted(expected)[:3]


def test_calendar_rules_bindings_and_no_signal(catalog):
    catalog.sections["A"].append(section("A","T1",1,580,610,"C","TUT",(MON+timedelta(days=7),)))
    catalog.required["A"].add("TUT")
    catalog.bindings["A","A1"] = {"T1"}
    p = Policy(credit_min=6,credit_max=6,required=[("A","A1")])
    r = solve(catalog,list("AB"),p)
    assert r["status"] == "optimal"
    assert r["certified_prefix"] == 2
    assert r["proof_scope"] == "feasibility_only"
    assert all(s["score"] is None for s in r["solutions"])
    assert not validate(catalog,list("AB"),p,[("A","A2"),("A","T1"),("B","B2")])["passed"]
    hard = p.model_copy(update={"free_days":Policy(free_days={"minimum":5,"mode":"hard"}).free_days})
    assert solve(catalog,list("AB"),hard)["status"] == "insufficient_data"
    assert solve(catalog,list("AB"),hard.model_copy(update={"teaching_weeks":{MON}}))["status"] == "infeasible_proven"


def test_input_and_timeout(catalog):
    with pytest.raises(ValidationError):
        Policy(early=0)
    assert solve(catalog,list("AB"),Policy(credit_min=6),timeout=0)["status"] == "timeout_no_feasible"


def test_api_uses_v4_worker_and_display(catalog,monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    monkeypatch.setattr(main,"catalog",lambda _:catalog)
    body = {"codes":["A","B"],"preferences":{"credit_min":6,"credit_max":6,"early":1}}
    with TestClient(main.app) as client:
        assert client.get("/api/v4/preferences/schema").status_code == 200
        response = client.post("/api/v4/optimize",json=body)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "optimal"
        first = data["solutions"][0]
        assert len(first["validation"]["meetings"]) == 2
        report = client.post("/api/v4/validate",json={**body, "selections":first["selections"]})
        assert report.json()["passed"]
