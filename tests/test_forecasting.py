"""Tests for Prophet forecasting."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analytics.forecasting import ForecastError, forecast_series, forecast_to_context_dict
from analytics.ingest import load_and_clean
from llm.forecast_explain import ForecastExplainError, explain_forecast
from schemas.financial import ValidationResult
from schemas.forecast import ForecastExplanation

pytest.importorskip("prophet")

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"


@pytest.fixture
def retail_monthly():
    path = SAMPLE / "retail_monthly_pl.csv"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult)
    return result.monthly


def test_forecast_revenue_quarter(retail_monthly: pd.DataFrame) -> None:
    payload = forecast_series(retail_monthly, "revenue", 3)
    assert payload.metric == "revenue"
    assert len(payload.forecast) == 3
    assert payload.summary["forecast_total"] > 0
    for point in payload.forecast:
        assert point.lower <= point.upper


def test_forecast_revenue_year(retail_monthly: pd.DataFrame) -> None:
    payload = forecast_series(retail_monthly, "revenue", 12)
    assert len(payload.forecast) == 12


def test_forecast_opex(retail_monthly: pd.DataFrame) -> None:
    payload = forecast_series(retail_monthly, "opex", 3)
    assert payload.metric == "opex"


def test_forecast_insufficient_data() -> None:
    df = pd.DataFrame(
        {
            "month": pd.date_range("2024-01-01", periods=2, freq="MS"),
            "revenue": [100.0, 110.0],
            "cogs": [40.0, 44.0],
            "opex": [30.0, 33.0],
            "gross_profit": [60.0, 66.0],
            "net_profit": [30.0, 33.0],
            "gross_margin_pct": [60.0, 60.0],
            "opex_ratio_pct": [30.0, 30.0],
        }
    )
    with pytest.raises(ForecastError, match="at least"):
        forecast_series(df, "revenue", 3)


def test_forecast_invalid_horizon(retail_monthly: pd.DataFrame) -> None:
    with pytest.raises(ForecastError, match="horizon"):
        forecast_series(retail_monthly, "revenue", 6)


def test_forecast_json_roundtrip(retail_monthly: pd.DataFrame) -> None:
    payload = forecast_series(retail_monthly, "revenue", 3)
    data = forecast_to_context_dict(payload)
    parsed = json.loads(json.dumps(data))
    assert parsed["summary"]["horizon_months"] == 3


def test_explain_forecast_mock(retail_monthly: pd.DataFrame) -> None:
    payload = forecast_series(retail_monthly, "revenue", 3)
    context = forecast_to_context_dict(payload)
    fake = ForecastExplanation(
        outlook="Revenue is projected to grow per forecast totals.",
        key_figures=[f"Forecast total: ${context['summary']['forecast_total']}"],
        risks_and_caveats=["Short history increases uncertainty."],
    )
    mock_message = MagicMock()
    mock_message.parsed = fake
    mock_message.refusal = None
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=mock_message)]
    mock_client = MagicMock()
    mock_client.chat.completions.parse.return_value = mock_completion

    with patch("llm.forecast_explain.OpenAI", return_value=mock_client):
        out = explain_forecast(context, api_key="sk-test")
    assert "Revenue" in out.outlook
