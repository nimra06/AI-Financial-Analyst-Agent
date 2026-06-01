"""Unit tests for ingest and KPI analytics."""

from pathlib import Path

import pandas as pd
import pytest

from analytics.ingest import load_and_clean
from analytics.kpis import compute_kpis
from schemas.financial import ValidationResult

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "datasets" / "sample"


@pytest.fixture
def retail_bytes() -> tuple[bytes, str]:
    path = SAMPLE / "retail_monthly_pl.csv"
    return path.read_bytes(), path.name


def test_load_retail_monthly_pl(retail_bytes: tuple[bytes, str]) -> None:
    data, name = retail_bytes
    result = load_and_clean(data, name)
    assert not isinstance(result, ValidationResult)
    assert len(result.monthly) == 24
    assert "net_profit" in result.monthly.columns


def test_kpis_have_ten_plus_fields(retail_bytes: tuple[bytes, str]) -> None:
    data, name = retail_bytes
    result = load_and_clean(data, name)
    assert not isinstance(result, ValidationResult)
    kpis = compute_kpis(result.monthly, result.categories)
    snapshot = kpis.to_snapshot_dict()
    assert kpis.latest_revenue > 0
    assert kpis.total_net_profit != 0
    assert len(kpis.monthly_records) == 24
    assert "mom_revenue_growth_pct" in snapshot
    assert "avg_revenue_3m" in snapshot


def test_mom_growth_second_month(retail_bytes: tuple[bytes, str]) -> None:
    data, name = retail_bytes
    result = load_and_clean(data, name)
    assert not isinstance(result, ValidationResult)
    kpis = compute_kpis(result.monthly, result.categories)
    assert kpis.mom_revenue_growth_pct is not None


def test_invalid_file_missing_date() -> None:
    csv = b"revenue,cogs\n100,40\n"
    result = load_and_clean(csv, "bad.csv")
    assert isinstance(result, ValidationResult)
    assert not result.ok


def test_categories_sample() -> None:
    path = SAMPLE / "retail_with_categories.csv"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult)
    assert result.categories is not None
    assert len(result.categories) > 0
    kpis = compute_kpis(result.monthly, result.categories)
    assert len(kpis.top_expense_categories) >= 1


def test_currency_parsing() -> None:
    csv = b"date,revenue,cogs,opex\n2024-01-01,\"$120,000.00\",48000,\"(2,500)\"\n2024-02-01,125000,50000,30000\n"
    result = load_and_clean(csv, "curr.csv")
    assert not isinstance(result, ValidationResult)
    jan = result.monthly.iloc[0]
    assert jan["revenue"] == 120000
    assert jan["opex"] == 2500
