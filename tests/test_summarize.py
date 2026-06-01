"""Tests for LLM summarization (mocked — no API key required)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from analytics.ingest import load_and_clean
from analytics.kpis import compute_kpis
from analytics.snapshot import build_metrics_snapshot
from llm.summarize import SummaryError, generate_executive_summary
from schemas.financial import ValidationResult
from schemas.summary import ExecutiveSummary

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"


@pytest.fixture
def retail_snapshot() -> dict:
    path = SAMPLE / "retail_monthly_pl.csv"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult)
    kpis = compute_kpis(result.monthly, result.categories)
    return build_metrics_snapshot(kpis, source_file=path.name)


def test_missing_api_key_raises(retail_snapshot: dict) -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SummaryError, match="API key"):
            generate_executive_summary(retail_snapshot, api_key="")


def test_generate_summary_parsed_response(retail_snapshot: dict) -> None:
    fake_summary = ExecutiveSummary(
        summary="Revenue grew in the latest period per CONTEXT.",
        trends=["Latest revenue per metrics snapshot."],
        risks=["Opex ratio may pressure margins."],
        opportunities=["Best month shows revenue upside."],
        recommendations=["Review top expense categories."],
    )
    mock_message = MagicMock()
    mock_message.parsed = fake_summary
    mock_message.refusal = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.parse.return_value = mock_completion

    with patch("llm.summarize.OpenAI", return_value=mock_client):
        out = generate_executive_summary(retail_snapshot, api_key="sk-test")

    assert "Revenue" in out.summary
    assert len(out.trends) >= 1
    mock_client.chat.completions.parse.assert_called_once()
    call_kwargs = mock_client.chat.completions.parse.call_args.kwargs
    user_msg = call_kwargs["messages"][1]["content"]
    assert "metrics" in user_msg
    assert retail_snapshot["metrics"]["latest_month"] in user_msg
