"""Tests for chat agent (mocked OpenAI)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from analytics.ingest import load_and_clean
from analytics.kpis import compute_kpis
from analytics.snapshot import build_metrics_snapshot
from llm.chat import ChatError, build_context, run_chat
from schemas.financial import ValidationResult

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"


@pytest.fixture
def retail_ctx():
    path = SAMPLE / "retail_monthly_pl.csv"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult)
    kpis = compute_kpis(result.monthly, result.categories)
    snapshot = build_metrics_snapshot(kpis, source_file=path.name)
    return build_context(
        result.monthly,
        kpis,
        snapshot,
        categories=result.categories,
        source_file=path.name,
    )


def _tool_call_response(tool_name: str, args: dict, call_id: str = "call_1"):
    fn = MagicMock()
    fn.name = tool_name
    fn.arguments = json.dumps(args)
    tc = MagicMock()
    tc.id = call_id
    tc.function = fn
    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = None
    msg.model_dump.return_value = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": tool_name, "arguments": json.dumps(args)},
            }
        ],
    }
    choice = MagicMock()
    choice.message = msg
    comp = MagicMock()
    comp.choices = [choice]
    return comp


def _text_response(text: str):
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    comp = MagicMock()
    comp.choices = [choice]
    return comp


def test_run_chat_with_tool_then_answer(retail_ctx) -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _tool_call_response("get_kpi", {"metric_name": "latest_revenue"}),
        _text_response(
            "Latest revenue is strong. Sources: KPI: latest_revenue = 120000"
        ),
    ]

    with patch("llm.chat.OpenAI", return_value=mock_client):
        result = run_chat("What is latest revenue?", retail_ctx, api_key="sk-test")

    assert "revenue" in result.answer.lower() or "Latest" in result.answer
    assert len(result.sources) >= 1
    assert mock_client.chat.completions.create.call_count == 2


def test_missing_api_key(retail_ctx) -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ChatError):
            run_chat("hello", retail_ctx, api_key="")
