"""Tier 3 analytics tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from analytics.alerts import generate_alert_rules
from analytics.benchmarks import score_against_benchmark
from analytics.compare import compare_session_payloads
from analytics.scenarios import run_scenario
from api.main import app

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"
client = TestClient(app)


def test_benchmark_scoring() -> None:
    kpis = {
        "latest_gross_margin_pct": 72,
        "latest_opex_ratio_pct": 55,
        "mom_revenue_growth_pct": 5,
    }
    result = score_against_benchmark(kpis, "saas")
    assert result["industry"] == "saas"
    assert len(result["scores"]) >= 2


def test_scenario_opex_reduction() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    from analytics.ingest import load_and_clean
    from schemas.financial import ValidationResult

    ing = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(ing, ValidationResult)
    from analytics.kpis import compute_kpis

    kpis = compute_kpis(ing.monthly, ing.categories)
    result = run_scenario(kpis.monthly_records, opex_delta_pct=-10)
    assert result["projected_net_profit"] >= result["baseline_net_profit"]


def test_alert_rules_mom_drop() -> None:
    kpis = {"latest_month": "Jan 2024", "mom_revenue_growth_pct": -20}
    alerts = generate_alert_rules(kpis, {"summary": {}})
    assert any(a["rule_id"] == "mom_revenue_drop" for a in alerts)


def test_compare_sessions_api() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    with path.open("rb") as f:
        a = client.post("/api/v1/upload", files={"file": (path.name, f, "text/csv")})
    with path.open("rb") as f:
        b = client.post(
            "/api/v1/upload",
            files={"file": ("other_" + path.name, f, "text/csv")},
        )
    id_a = a.json()["dashboard"]["session_id"]
    id_b = b.json()["dashboard"]["session_id"]
    r = client.post(
        "/api/v1/sessions/compare",
        json={"session_id_a": id_a, "session_id_b": id_b},
    )
    assert r.status_code == 200
    assert "deltas" in r.json()


def test_scenarios_api() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    with path.open("rb") as f:
        up = client.post("/api/v1/upload", files={"file": (path.name, f, "text/csv")})
    records = up.json()["dashboard"]["monthly_records"]
    r = client.post(
        "/api/v1/scenarios",
        json={"monthly_records": records, "opex_delta_pct": -5},
    )
    assert r.status_code == 200
    assert "impact" in r.json()


def test_alerts_after_upload() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    with path.open("rb") as f:
        up = client.post("/api/v1/upload", files={"file": (path.name, f, "text/csv")})
    sid = up.json()["dashboard"]["session_id"]
    r = client.get(f"/api/v1/alerts?session_id={sid}")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
