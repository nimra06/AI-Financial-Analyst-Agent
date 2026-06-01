"""Tests for metrics snapshot and all sample datasets."""

import json
from pathlib import Path

import pytest

from analytics.ingest import load_and_clean
from analytics.kpis import compute_kpis
from analytics.snapshot import SNAPSHOT_VERSION, build_metrics_snapshot, snapshot_to_json
from schemas.financial import ValidationResult

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"

SAMPLE_FILES = [
    "template_monthly_pl.csv",
    "retail_monthly_pl.csv",
    "saas_monthly_pl.csv",
    "retail_with_categories.csv",
]


@pytest.mark.parametrize("filename", SAMPLE_FILES)
def test_all_samples_load_and_snapshot(filename: str) -> None:
    path = SAMPLE / filename
    assert path.exists(), f"Missing sample: {filename}"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult), result.errors

    kpis = compute_kpis(result.monthly, result.categories)
    snapshot = build_metrics_snapshot(
        kpis,
        source_file=filename,
        period_count=len(result.monthly),
    )

    assert snapshot["snapshot_version"] == SNAPSHOT_VERSION
    assert snapshot["source_file"] == filename
    assert snapshot["period_count"] == len(result.monthly)
    assert "generated_at" in snapshot
    assert snapshot["metrics"]["latest_revenue"] > 0

    parsed = json.loads(snapshot_to_json(snapshot))
    assert len(parsed["metrics"]["monthly_records"]) == len(result.monthly)


def test_retail_snapshot_has_mom_growth() -> None:
    path = SAMPLE / "retail_monthly_pl.csv"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult)
    kpis = compute_kpis(result.monthly, result.categories)
    snapshot = build_metrics_snapshot(kpis, source_file=path.name)
    assert snapshot["metrics"]["mom_revenue_growth_pct"] is not None
