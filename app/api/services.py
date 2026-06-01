"""Business logic for API dashboard assembly."""

from __future__ import annotations

import base64
import uuid
from typing import Any, Optional

import pandas as pd

from analytics.alerts import generate_alert_rules
from analytics.anomalies import detect_all_anomalies, report_to_context_dict
from analytics.benchmarks import score_against_benchmark
from analytics.budget import compute_budget_variance
from db.tier3_store import replace_session_alerts
from analytics.forecasting import ForecastError, forecast_series, forecast_to_context_dict
from analytics.ingest import IngestResult, load_and_clean
from analytics.kpis import KpiSummary, compute_kpis
from analytics.snapshot import build_metrics_snapshot
from db.store import save_session
from llm.agent_tools import context_from_monthly_records
from reports.builder import build_executive_report
from schemas.anomaly import AnomalyFlag, AnomalyReport
from schemas.dashboard import DashboardPayload, MonthlyPoint
from schemas.financial import ValidationResult
from schemas.report import ReportArtifacts
from schemas.summary import ExecutiveSummary


def _monthly_to_chart_series(monthly: pd.DataFrame) -> list[MonthlyPoint]:
    series: list[MonthlyPoint] = []
    for _, row in monthly.sort_values("month").iterrows():
        series.append(
            MonthlyPoint(
                month=row["month"].strftime("%b %Y"),
                revenue=round(float(row["revenue"]), 2),
                gross_profit=round(float(row["gross_profit"]), 2),
                net_profit=round(float(row["net_profit"]), 2),
                opex=round(float(row["opex"]), 2),
                gross_margin_pct=round(float(row["gross_margin_pct"]), 2),
                opex_ratio_pct=round(float(row["opex_ratio_pct"]), 2),
            )
        )
    return series


def _detect_industry(source_file: str) -> str:
    name = source_file.lower()
    if "saas" in name:
        return "saas"
    if "retail" in name:
        return "retail"
    if "service" in name:
        return "services"
    return "saas"


def _ingest_to_dashboard(
    result: IngestResult,
    source_file: str,
    *,
    session_id: Optional[str] = None,
    industry: Optional[str] = None,
) -> DashboardPayload:
    kpis = compute_kpis(result.monthly, result.categories)
    snapshot = build_metrics_snapshot(
        kpis, source_file=source_file, period_count=len(result.monthly)
    )
    anomaly_report = detect_all_anomalies(result.monthly, result.categories)
    metrics = kpis.to_snapshot_dict()
    industry_key = industry or _detect_industry(source_file)
    anomalies_dict = report_to_context_dict(anomaly_report)
    budget_var = compute_budget_variance(result.monthly)
    bench = score_against_benchmark(metrics, industry_key)

    sid = session_id or ""
    if sid:
        replace_session_alerts(sid, generate_alert_rules(metrics, anomalies_dict))

    payload = DashboardPayload(
        session_id=sid,
        source_file=source_file,
        period_count=len(result.monthly),
        kpis=metrics,
        snapshot=snapshot,
        monthly_records=metrics["monthly_records"],
        chart_series=_monthly_to_chart_series(result.monthly),
        top_expense_categories=metrics.get("top_expense_categories", []),
        raw_preview=result.raw_preview.fillna("").astype(str).to_dict(orient="records"),
        anomalies=anomalies_dict,
        warnings=list(result.validation.warnings),
        industry=industry_key,
        budget_variance=budget_var,
        benchmarks=bench,
    )
    return payload


def enrich_dashboard_tier3(payload: DashboardPayload) -> DashboardPayload:
    """Recompute Tier 3 fields when restoring a session from DB."""
    metrics = payload.kpis
    budget_var = compute_budget_variance_from_records(payload.monthly_records)
    bench = score_against_benchmark(metrics, payload.industry or "saas")
    if payload.session_id:
        replace_session_alerts(
            payload.session_id,
            generate_alert_rules(metrics, payload.anomalies),
        )
    return payload.model_copy(
        update={
            "budget_variance": budget_var,
            "benchmarks": bench,
        }
    )


def compute_budget_variance_from_records(monthly_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Rebuild monthly frame for budget variance when only records are stored."""
    import pandas as pd

    if not monthly_records:
        return {"available": False, "reason": "No monthly data"}
    rows = []
    for rec in monthly_records:
        parsed = pd.to_datetime(rec["month"], format="%b %Y", errors="coerce")
        if pd.isna(parsed):
            parsed = pd.to_datetime(rec["month"], errors="coerce")
        row: dict[str, Any] = {
            "month": parsed.to_period("M").to_timestamp(),
            "revenue": float(rec.get("revenue", 0)),
            "cogs": float(rec.get("cogs", rec.get("revenue", 0) - rec.get("gross_profit", 0))),
            "opex": float(rec.get("opex", 0)),
        }
        if "budget_revenue" in rec:
            row["budget_revenue"] = float(rec["budget_revenue"])
        if "budget_opex" in rec:
            row["budget_opex"] = float(rec["budget_opex"])
        rows.append(row)
    monthly = pd.DataFrame(rows)
    return compute_budget_variance(monthly)


def process_upload(file_bytes: bytes, filename: str) -> DashboardPayload | ValidationResult:
    result = load_and_clean(file_bytes, filename)
    if isinstance(result, ValidationResult):
        return result

    kpis = compute_kpis(result.monthly, result.categories)
    session_id = str(uuid.uuid4())
    dashboard = _ingest_to_dashboard(result, filename, session_id=session_id)
    save_session(
        filename,
        len(result.monthly),
        kpis.latest_month,
        dashboard.model_dump(),
    )
    return dashboard


def process_upload_no_persist(file_bytes: bytes, filename: str) -> DashboardPayload | ValidationResult:
    """Upload without DB write (for tests)."""
    result = load_and_clean(file_bytes, filename)
    if isinstance(result, ValidationResult):
        return result
    return _ingest_to_dashboard(result, filename, session_id="local")


def run_forecast_api(
    monthly_records: list[dict[str, Any]],
    metric: str,
    horizon_months: int,
) -> dict[str, Any]:
    from analytics.kpis import compute_kpis
    from llm.agent_tools import context_from_monthly_records

    ctx = context_from_monthly_records(monthly_records)
    payload = forecast_series(ctx.monthly, metric, horizon_months)  # type: ignore[arg-type]
    return forecast_to_context_dict(payload)


def restore_dashboard_from_records(payload: dict[str, Any]) -> DashboardPayload:
    return DashboardPayload.model_validate(payload)


def _anomaly_markers(anomalies: dict[str, Any]) -> tuple[set[str], set[str], set[str], set[str]]:
    rev: set[str] = set()
    profit: set[str] = set()
    opex: set[str] = set()
    trend: set[str] = set()
    for flag in anomalies.get("flags", []):
        month = flag.get("month", "")
        metric = flag.get("metric", "")
        if metric == "revenue":
            rev.add(month)
        elif metric in ("net_profit", "gross_profit"):
            profit.add(month)
        elif metric in ("opex", "operating_expenses"):
            opex.add(month)
        else:
            trend.add(month)
    return rev, profit, opex, trend


def build_report_from_dashboard(
    dashboard: DashboardPayload,
    executive_summary: Optional[ExecutiveSummary] = None,
) -> ReportArtifacts:
    ctx = context_from_monthly_records(
        dashboard.monthly_records,
        top_expense_categories=dashboard.top_expense_categories,
        source_file=dashboard.source_file,
    )
    raw_preview = (
        pd.DataFrame(dashboard.raw_preview) if dashboard.raw_preview else pd.DataFrame()
    )
    ingest = IngestResult(
        monthly=ctx.monthly,
        categories=ctx.categories,
        raw_preview=raw_preview,
        validation=ValidationResult(ok=True, errors=[], warnings=dashboard.warnings),
    )
    flags = [AnomalyFlag(**f) for f in dashboard.anomalies.get("flags", [])]
    anomaly_report = AnomalyReport(
        flags=flags,
        summary=dashboard.anomalies.get("summary", {}),
        warnings=dashboard.anomalies.get("warnings", []),
    )
    rev_m, profit_m, opex_m, trend_m = _anomaly_markers(dashboard.anomalies)
    return build_executive_report(
        ingest=ingest,
        kpis=ctx.kpis,
        snapshot=dashboard.snapshot,
        source_file=dashboard.source_file,
        anomaly_report=anomaly_report,
        executive_summary=executive_summary,
        rev_markers=rev_m,
        profit_markers=profit_m,
        opex_markers=opex_m,
        trend_markers=trend_m,
    )


def report_to_api_response(artifacts: ReportArtifacts) -> dict[str, Any]:
    pdf_b64: Optional[str] = None
    if artifacts.pdf_available and artifacts.pdf_bytes:
        pdf_b64 = base64.b64encode(artifacts.pdf_bytes).decode("ascii")
    return {
        "html": artifacts.html,
        "markdown": artifacts.markdown,
        "pdf_available": artifacts.pdf_available,
        "pdf_base64": pdf_b64,
        "warnings": artifacts.warnings,
    }
