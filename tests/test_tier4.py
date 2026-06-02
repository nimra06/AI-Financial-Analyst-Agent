"""Tier 4 tests: auth, API keys, jobs, health."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from api.auth import create_access_token
from db.api_keys_store import create_api_key, verify_api_key
from db.jobs_store import enqueue_job, get_job
from worker.processor import process_job
from worker.runner import run_once

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"


@pytest.fixture()
def client() -> TestClient:
    from api.main import app

    return TestClient(app)


def test_jwt_login_and_auth(client: TestClient) -> None:
    r = client.post(
        "/api/v1/auth/login",
        json={"name": "Test User", "email": "test@example.com", "role": "Analyst"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    up = client.post(
        "/api/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("t.csv", SAMPLE.joinpath("retail_monthly_pl.csv").read_bytes(), "text/csv")},
    )
    assert up.status_code == 200


def test_api_key_auth(client: TestClient) -> None:
    raw, _ = create_api_key("ci-key", "bot@example.com", "Analyst")
    assert verify_api_key(raw) is not None
    r = client.get("/api/v1/sessions", headers={"X-API-Key": raw})
    assert r.status_code == 200


def test_api_keys_admin_only(client: TestClient) -> None:
    analyst_token = create_access_token(name="U", email="u@x.com", role="Analyst")
    r = client.get(
        "/api/v1/admin/api-keys",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert r.status_code == 403

    admin_token = create_access_token(name="A", email="a@x.com", role="Admin")
    r = client.post(
        "/api/v1/admin/api-keys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"label": "test", "owner_email": "a@x.com", "role": "Analyst"},
    )
    assert r.status_code == 200
    assert r.json()["raw_key"].startswith("fa_")


def test_health_endpoints(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/health/ready").json()
    assert ready["checks"]["database"] == "ok"
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "finanalyst_requests_total" in metrics.text


def test_background_forecast_job(client: TestClient) -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    token = create_access_token(name="A", email="a@x.com", role="Analyst")
    with path.open("rb") as f:
        up = client.post(
            "/api/v1/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (path.name, f, "text/csv")},
        )
    records = up.json()["dashboard"]["monthly_records"]
    job_id = enqueue_job(
        "forecast",
        {"monthly_records": records, "metric": "revenue", "horizon_months": 3},
        actor="test",
    )
    assert run_once() is True
    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert "forecast" in job["result"]


def test_job_processor_forecast_direct() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    from analytics.ingest import load_and_clean
    from schemas.financial import ValidationResult

    ing = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(ing, ValidationResult)
    from analytics.kpis import compute_kpis

    kpis = compute_kpis(ing.monthly, ing.categories)
    job = {
        "job_type": "forecast",
        "payload": {
            "monthly_records": kpis.monthly_records,
            "metric": "revenue",
            "horizon_months": 3,
        },
    }
    result = process_job(job)
    assert "forecast" in result
