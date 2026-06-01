"""Tier 2 tests: audit, retention, rate limits, RBAC."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from api.main import _chat_limiter, app
from db.audit import log_audit_event, list_audit_events, purge_expired_sessions
from db.store import init_db

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"
client = TestClient(app)


def test_audit_log_endpoint() -> None:
    init_db()
    log_audit_event("test_event", "test@example.com", detail={"foo": "bar"})
    r = client.get("/api/v1/audit?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["event_type"] == "test_event"


def test_retention_policy_endpoint() -> None:
    r = client.get("/api/v1/policy/retention")
    assert r.status_code == 200
    body = r.json()
    assert "retention_days" in body
    assert body["retention_days"] >= 0


def test_viewer_cannot_upload() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    with path.open("rb") as f:
        r = client.post(
            "/api/v1/upload",
            files={"file": (path.name, f, "text/csv")},
            headers={"X-Demo-Role": "Viewer", "X-Demo-User": "viewer@test.com"},
        )
    assert r.status_code == 403


def test_rate_limiter_blocks() -> None:
    limiter = _chat_limiter.__class__(max_calls=2, window_seconds=60)
    limiter.check("user-a")
    limiter.check("user-a")
    with pytest.raises(Exception) as exc:
        limiter.check("user-a")
    assert exc.value.status_code == 429  # type: ignore[attr-defined]


def test_purge_expired_empty() -> None:
    init_db()
    assert purge_expired_sessions(36500) == []
