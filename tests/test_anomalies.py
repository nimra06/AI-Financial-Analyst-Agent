"""Tests for anomaly detection."""

from pathlib import Path

import pandas as pd
import pytest

from analytics.anomalies import (
    chart_anomaly_months,
    detect_all_anomalies,
    detect_iqr_anomalies,
    detect_isolation_forest_anomalies,
    detect_mom_opex_spikes,
    detect_zscore_anomalies,
)
from analytics.ingest import load_and_clean
from schemas.anomaly import AnomalyFlag
from schemas.financial import ValidationResult

pytest.importorskip("sklearn")

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"


@pytest.fixture
def retail_monthly() -> pd.DataFrame:
    path = SAMPLE / "retail_monthly_pl.csv"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult)
    return result.monthly


def test_detect_all_returns_report(retail_monthly: pd.DataFrame) -> None:
    report = detect_all_anomalies(retail_monthly)
    assert report.summary["count"] >= 0
    assert isinstance(report.flags, list)


def test_zscore_flags_retail(retail_monthly: pd.DataFrame) -> None:
    flags = detect_zscore_anomalies(retail_monthly)
    assert all(isinstance(f, AnomalyFlag) for f in flags)
    if flags:
        assert flags[0].method == "z_score"


def test_isolation_forest_runs_on_retail(retail_monthly: pd.DataFrame) -> None:
    flags = detect_isolation_forest_anomalies(retail_monthly)
    assert isinstance(flags, list)


def test_chart_anomaly_months(retail_monthly: pd.DataFrame) -> None:
    report = detect_all_anomalies(retail_monthly)
    months = chart_anomaly_months(report, "revenue")
    assert isinstance(months, set)


def test_iqr_and_mom(retail_monthly: pd.DataFrame) -> None:
    assert isinstance(detect_iqr_anomalies(retail_monthly), list)
    assert isinstance(detect_mom_opex_spikes(retail_monthly), list)


def test_too_few_rows() -> None:
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
    report = detect_all_anomalies(df)
    assert report.summary["count"] == 0
    assert report.warnings
