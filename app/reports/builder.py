"""Build HTML, Markdown, and PDF executive reports."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader, select_autoescape

from analytics.charts import (
    profit_chart,
    revenue_chart,
    top_expenses_chart,
    trends_chart,
)
from analytics.ingest import IngestResult
from analytics.kpis import KpiSummary
from reports.explainability import build_why_panel
from schemas.anomaly import AnomalyReport
from schemas.report import ReportArtifacts, WhyInsight
from schemas.summary import ExecutiveSummary

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _chart_png_base64(fig: go.Figure) -> str:
    try:
        png_bytes = fig.to_image(format="png", width=960, height=480, scale=2)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Chart export failed. Install kaleido: pip install kaleido"
        ) from exc
    return base64.b64encode(png_bytes).decode("ascii")


def _charts_as_images(
    ingest: IngestResult,
    rev_markers: Optional[set[str]] = None,
    profit_markers: Optional[set[str]] = None,
    opex_markers: Optional[set[str]] = None,
    trend_markers: Optional[set[str]] = None,
) -> dict[str, str]:
    monthly = ingest.monthly
    return {
        "revenue": _chart_png_base64(revenue_chart(monthly, rev_markers)),
        "profit": _chart_png_base64(profit_chart(monthly, profit_markers)),
        "expenses": _chart_png_base64(
            top_expenses_chart(ingest.categories, monthly, opex_markers)
        ),
        "trends": _chart_png_base64(trends_chart(monthly, trend_markers)),
    }


def _html_to_pdf(html: str) -> tuple[Optional[bytes], Optional[str]]:
    """Convert HTML to PDF via xhtml2pdf (pure Python, no system libs)."""
    try:
        from io import BytesIO

        from xhtml2pdf import pisa
    except ImportError:
        return None, "PDF engine not installed. Run: pip install xhtml2pdf"

    buffer = BytesIO()
    status = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if status.err:
        return None, "PDF generation failed — try downloading HTML instead."
    return buffer.getvalue(), None


def build_executive_report(
    *,
    ingest: IngestResult,
    kpis: KpiSummary,
    snapshot: dict[str, Any],
    source_file: str,
    anomaly_report: AnomalyReport,
    executive_summary: Optional[ExecutiveSummary] = None,
    rev_markers: Optional[set[str]] = None,
    profit_markers: Optional[set[str]] = None,
    opex_markers: Optional[set[str]] = None,
    trend_markers: Optional[set[str]] = None,
    generate_pdf: bool = True,
) -> ReportArtifacts:
    """Render full executive report package."""
    warnings: list[str] = []
    why_panel = build_why_panel(kpis, anomaly_report=anomaly_report)

    try:
        charts = _charts_as_images(
            ingest, rev_markers, profit_markers, opex_markers, trend_markers
        )
    except RuntimeError as exc:
        warnings.append(str(exc))
        charts = {}

    ai_sections: dict[str, Any] | None = None
    if executive_summary:
        ai_sections = executive_summary.model_dump()
    else:
        warnings.append(
            "No AI executive summary included — generate one in the Executive summary tab first."
        )

    context = {
        "title": "Executive Financial Report",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source_file": source_file,
        "period_count": len(ingest.monthly),
        "latest_month": kpis.latest_month,
        "metrics": snapshot.get("metrics", kpis.to_snapshot_dict()),
        "anomaly_summary": anomaly_report.summary,
        "anomaly_flags": [f.model_dump() for f in anomaly_report.flags[:12]],
        "ai": ai_sections,
        "charts": charts,
        "why_panel": [w.model_dump() for w in why_panel],
        "disclaimer": (
            "This report is for analysis and demonstration only. It is not financial, "
            "tax, or investment advice. Verify all figures against your source systems."
        ),
        "watermark": "DEMO ONLY — NOT FINANCIAL ADVICE",
    }

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template("executive_report.html.j2").render(**context)
    markdown = env.get_template("executive_report.md.j2").render(**context)

    pdf_bytes: Optional[bytes] = None
    if generate_pdf:
        pdf_bytes, pdf_err = _html_to_pdf(html)
        if pdf_err:
            warnings.append(pdf_err)

    return ReportArtifacts(
        html=html,
        markdown=markdown,
        why_panel=why_panel,
        pdf_available=pdf_bytes is not None,
        pdf_bytes=pdf_bytes,
        warnings=warnings,
    )
