"""API integration tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fastapi")

from api.main import app

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"
client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_retail() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    with path.open("rb") as f:
        r = client.post("/api/v1/upload", files={"file": (path.name, f, "text/csv")})
    assert r.status_code == 200, r.text
    data = r.json()["dashboard"]
    assert data["period_count"] == 24
    assert "latest_revenue" in data["kpis"]


def test_sessions_list_after_upload() -> None:
    r = client.get("/api/v1/sessions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_upload_validation_422() -> None:
    r = client.post(
        "/api/v1/upload",
        files={"file": ("bad.csv", b"revenue,cogs\n100,40\n", "text/csv")},
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "errors" in detail
    assert "row_count" in detail


def test_chat_persistence() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    with path.open("rb") as f:
        up = client.post("/api/v1/upload", files={"file": (path.name, f, "text/csv")})
    assert up.status_code == 200
    session_id = up.json()["dashboard"]["session_id"]

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with patch("llm.chat.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            msg = MagicMock()
            msg.tool_calls = None
            msg.content = "Revenue is stable. Sources: KPI: latest_revenue"
            choice = MagicMock()
            choice.message = msg
            comp = MagicMock()
            comp.choices = [choice]
            mock_client.chat.completions.create.return_value = comp

            chat = client.post(
                "/api/v1/chat",
                json={
                    "message": "How is revenue?",
                    "session_id": session_id,
                    "monthly_records": up.json()["dashboard"]["monthly_records"],
                    "source_file": path.name,
                    "mode": "dataset",
                },
            )
    assert chat.status_code == 200

    hist = client.get(f"/api/v1/sessions/{session_id}/chat")
    assert hist.status_code == 200
    messages = hist.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    clear = client.delete(f"/api/v1/sessions/{session_id}/chat")
    assert clear.status_code == 200
    assert client.get(f"/api/v1/sessions/{session_id}/chat").json()["messages"] == []


def test_executive_report_endpoint() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    with path.open("rb") as f:
        up = client.post("/api/v1/upload", files={"file": (path.name, f, "text/csv")})
    dash = up.json()["dashboard"]
    r = client.post(
        "/api/v1/reports/executive",
        json={
            "session_id": dash["session_id"],
            "source_file": dash["source_file"],
            "snapshot": dash["snapshot"],
            "monthly_records": dash["monthly_records"],
            "top_expense_categories": dash.get("top_expense_categories", []),
            "anomalies": dash.get("anomalies", {}),
            "warnings": dash.get("warnings", []),
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "html" in data
    assert "markdown" in data
    assert len(data["html"]) > 100
