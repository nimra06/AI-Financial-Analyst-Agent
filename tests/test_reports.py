"""Tests for executive report generation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from analytics.ingest import load_and_clean
from analytics.kpis import compute_kpis
from analytics.snapshot import build_metrics_snapshot
from reports.builder import build_executive_report
from reports.explainability import build_why_panel
from schemas.financial import ValidationResult
from schemas.summary import ExecutiveSummary

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"


@pytest.fixture
def retail_bundle():
    path = SAMPLE / "retail_monthly_pl.csv"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult)
    from analytics.anomalies import detect_all_anomalies

    kpis = compute_kpis(result.monthly, result.categories)
    snapshot = build_metrics_snapshot(kpis, source_file=path.name)
    anomalies = detect_all_anomalies(result.monthly, result.categories)
    return result, kpis, snapshot, anomalies, path.name


def test_why_panel_has_kpi_rows(retail_bundle) -> None:
    _, kpis, _, anomalies, _ = retail_bundle
    panel = build_why_panel(kpis, anomaly_report=anomalies)
    assert len(panel) >= 10
    assert panel[0].formula_hint
    assert any(p.category == "kpi" for p in panel)


def test_build_report_html_and_markdown(retail_bundle) -> None:
    ingest, kpis, snapshot, anomalies, name = retail_bundle
    fake_png = b"\x89PNG\r\n\x1a\n"

    with (
        patch("reports.builder._chart_png_base64", return_value="abc123"),
        patch("reports.builder._html_to_pdf", return_value=(b"%PDF-1.4 fake", None)),
    ):
        artifacts = build_executive_report(
            ingest=ingest,
            kpis=kpis,
            snapshot=snapshot,
            source_file=name,
            anomaly_report=anomalies,
            executive_summary=ExecutiveSummary(
                summary="Revenue trend is stable.",
                trends=["MoM growth noted."],
                risks=["Margin pressure."],
                opportunities=["Scale best month."],
                recommendations=["Review opex."],
            ),
        )

    assert "Executive Financial Report" in artifacts.html
    assert "Latest revenue" in artifacts.html
    assert len(artifacts.why_panel) >= 10
    assert "# Executive Financial Report" in artifacts.markdown
    assert "Revenue trend" in artifacts.markdown


def test_report_without_ai_summary_warns(retail_bundle) -> None:
    ingest, kpis, snapshot, anomalies, name = retail_bundle
    with (
        patch("reports.builder._chart_png_base64", return_value="abc"),
        patch("reports.builder._html_to_pdf", return_value=(b"%PDF-fake", None)),
    ):
        artifacts = build_executive_report(
            ingest=ingest,
            kpis=kpis,
            snapshot=snapshot,
            source_file=name,
            anomaly_report=anomalies,
            executive_summary=None,
            generate_pdf=True,
        )
    assert any("No AI executive summary" in w for w in artifacts.warnings)
    assert artifacts.pdf_available
