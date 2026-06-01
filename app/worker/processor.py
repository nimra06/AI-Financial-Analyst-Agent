"""Background job processor."""

from __future__ import annotations

from typing import Any

from api.services import build_report_from_dashboard, report_to_api_response, run_forecast_api
from db.tier3_store import get_scheduled_report, mark_scheduled_report_run
from schemas.dashboard import DashboardPayload


def process_job(job: dict[str, Any]) -> dict[str, Any]:
    job_type = job["job_type"]
    payload = job["payload"]

    if job_type == "forecast":
        data = run_forecast_api(
            payload["monthly_records"],
            payload.get("metric", "revenue"),
            payload.get("horizon_months", 3),
        )
        return {"forecast": data}

    if job_type == "report":
        dashboard = DashboardPayload(
            session_id=payload.get("session_id", ""),
            source_file=payload.get("source_file", ""),
            period_count=len(payload.get("monthly_records", [])),
            kpis=payload.get("snapshot", {}).get("metrics", {}),
            snapshot=payload.get("snapshot", {}),
            monthly_records=payload.get("monthly_records", []),
            chart_series=[],
            top_expense_categories=payload.get("top_expense_categories", []),
            anomalies=payload.get("anomalies", {}),
            warnings=payload.get("warnings", []),
        )
        artifacts = build_report_from_dashboard(
            dashboard,
            executive_summary=payload.get("summary"),
        )
        return report_to_api_response(artifacts)

    if job_type == "scheduled_report":
        report_id = payload["report_id"]
        row = get_scheduled_report(report_id)
        if row is None:
            raise ValueError(f"Scheduled report {report_id} not found")
        session_payload = payload.get("session_payload")
        if not session_payload:
            raise ValueError("Session payload missing for scheduled report")
        dashboard = DashboardPayload(
            session_id=row["session_id"],
            source_file=session_payload.get("source_file", ""),
            period_count=len(session_payload.get("monthly_records", [])),
            kpis=session_payload.get("kpis", {}),
            snapshot=session_payload.get("snapshot", {}),
            monthly_records=session_payload.get("monthly_records", []),
            chart_series=session_payload.get("chart_series", []),
            top_expense_categories=session_payload.get("top_expense_categories", []),
            anomalies=session_payload.get("anomalies", {}),
            warnings=session_payload.get("warnings", []),
        )
        artifacts = build_report_from_dashboard(dashboard)
        mark_scheduled_report_run(report_id)
        result = report_to_api_response(artifacts)
        result["recipients"] = row["recipients"]
        result["label"] = row["label"]
        return result

    raise ValueError(f"Unknown job type: {job_type}")
