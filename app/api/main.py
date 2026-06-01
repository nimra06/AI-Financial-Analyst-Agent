"""FastAPI backend for AI Financial Analyst (Steps 3–7)."""

from __future__ import annotations

import sys
from pathlib import Path

# Local dev uses PYTHONPATH=app; Vercel loads app.api.main:app from repo root.
_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

import os
from typing import Annotated, Any

# Required for POST /api/v1/upload (File uploads) — fail fast with a clear message
try:
    import multipart  # noqa: F401
except ImportError:
    print(
        'ERROR: python-multipart is required. Run: pip install python-multipart',
        file=sys.stderr,
    )
    raise

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from api.auth import AuthError, create_access_token, verify_google_id_token
from api.deps import get_current_user, require_admin, require_write_access
from api.observability import (
    RequestMetricsMiddleware,
    get_metrics_text,
    readiness_status,
    setup_observability,
)
from api.rate_limit import RateLimiter
from analytics.benchmarks import list_industries
from analytics.compare import compare_session_payloads
from analytics.scenarios import run_scenario
from api.services import (
    build_report_from_dashboard,
    enrich_dashboard_tier3,
    process_upload,
    report_to_api_response,
    restore_dashboard_from_records,
    run_forecast_api,
)
from db.audit import (
    log_audit_event,
    list_audit_events,
    purge_expired_sessions,
    sessions_expiring_within,
)
from db.connection import init_db
from db.store import (
    clear_chat_messages,
    get_chat_messages,
    get_session,
    list_sessions,
    save_chat_message,
)
from db.api_keys_store import create_api_key, list_api_keys, revoke_api_key
from db.jobs_store import enqueue_job, get_job, list_jobs
from db.tier3_store import (
    create_scheduled_report,
    delete_scheduled_report,
    list_alerts,
    list_scheduled_reports,
    mark_alerts_read,
)
from schemas.tier4 import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyRecord,
    AuthLoginRequest,
    AuthResponse,
    GoogleAuthRequest,
    HealthReadyResponse,
    JobEnqueueResponse,
    JobRecord,
)
from schemas.tier3 import (
    AlertRecord,
    CompareRequest,
    ScenarioRequest,
    ScheduledReportCreate,
    ScheduledReportRecord,
)
from llm.chat import ChatError, run_chat_from_snapshot_payload
from llm.chat_advisory import run_advisory_chat
from llm.summarize import SummaryError, generate_executive_summary
from llm.agent_tools import context_from_monthly_records
from reports.explainability import build_why_panel
from schemas.anomaly import AnomalyReport
from schemas.audit import AuditEventRecord, RetentionPolicy
from schemas.chat import ChatHistoryResponse, ChatMessageRecord, ChatRequest, ChatResponse, ChatTurn
from schemas.dashboard import (
    DashboardPayload,
    ForecastRequest,
    ForecastResponse,
    ReportRequest,
    ReportResponse,
    SessionMeta,
    SummarizeRequest,
    SummarizeResponse,
    UploadResponse,
)
from schemas.financial import ValidationResult
from analytics.forecasting import ForecastError

load_dotenv()

RETENTION_DAYS = int(os.environ.get("DATA_RETENTION_DAYS", "90"))
CHAT_RATE_LIMIT = int(os.environ.get("CHAT_RATE_LIMIT_PER_MIN", "20"))
SUMMARIZE_RATE_LIMIT = int(os.environ.get("SUMMARIZE_RATE_LIMIT_PER_MIN", "10"))

_chat_limiter = RateLimiter(CHAT_RATE_LIMIT, 60)
_summarize_limiter = RateLimiter(SUMMARIZE_RATE_LIMIT, 60)
_last_purge_count = 0

import logging

app = FastAPI(
    title="AI Financial Analyst API",
    description="Enterprise financial analytics API",
    version="0.9.0",
)

setup_observability()
app.add_middleware(RequestMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    global _last_purge_count
    init_db()
    deleted = purge_expired_sessions(RETENTION_DAYS)
    _last_purge_count = len(deleted)
    if deleted:
        log_audit_event(
            "retention_purge",
            "system",
            detail={"deleted_sessions": deleted, "retention_days": RETENTION_DAYS},
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", response_model=HealthReadyResponse)
def health_ready() -> HealthReadyResponse:
    data = readiness_status()
    return HealthReadyResponse(**data)


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(get_metrics_text(), media_type="text/plain; version=0.0.4")


@app.post("/api/v1/auth/login", response_model=AuthResponse)
def auth_login(body: AuthLoginRequest) -> AuthResponse:
    token = create_access_token(
        name=body.name.strip(),
        email=body.email.strip(),
        role=body.role,
        provider="demo",
    )
    return AuthResponse(
        access_token=token,
        user={"name": body.name, "email": body.email, "role": body.role},
    )


@app.post("/api/v1/auth/google", response_model=AuthResponse)
def auth_google(body: GoogleAuthRequest) -> AuthResponse:
    try:
        profile = verify_google_id_token(body.id_token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    token = create_access_token(**profile)
    return AuthResponse(
        access_token=token,
        user={
            "name": profile["name"],
            "email": profile["email"],
            "role": profile["role"],
        },
    )


@app.get("/api/v1/auth/config")
def auth_config() -> dict[str, Any]:
    return {
        "google_sso_enabled": bool(os.environ.get("GOOGLE_CLIENT_ID", "").strip()),
        "jwt_enabled": True,
        "demo_login_enabled": True,
    }


@app.get("/api/v1/admin/api-keys", response_model=list[ApiKeyRecord])
def api_keys_list(
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> list[ApiKeyRecord]:
    require_admin(user)
    return [ApiKeyRecord(**row) for row in list_api_keys()]


@app.post("/api/v1/admin/api-keys", response_model=ApiKeyCreateResponse)
def api_keys_create(
    body: ApiKeyCreateRequest,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> ApiKeyCreateResponse:
    require_admin(user)
    raw, record = create_api_key(body.label, body.owner_email, body.role)
    log_audit_event(
        "api_key_created",
        user["actor"],
        detail={"label": body.label, "owner_email": body.owner_email},
    )
    return ApiKeyCreateResponse(raw_key=raw, key=ApiKeyRecord(**record))


@app.delete("/api/v1/admin/api-keys/{key_id}")
def api_keys_revoke(
    key_id: int,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> dict[str, str]:
    require_admin(user)
    if not revoke_api_key(key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    log_audit_event("api_key_revoked", user["actor"], detail={"key_id": key_id})
    return {"status": "revoked"}


@app.get("/api/v1/jobs/{job_id}", response_model=JobRecord)
def jobs_get(job_id: str) -> JobRecord:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRecord(**job)


@app.get("/api/v1/jobs", response_model=list[JobRecord])
def jobs_list(
    user: Annotated[dict[str, str], Depends(get_current_user)],
    limit: int = 20,
) -> list[JobRecord]:
    rows = list_jobs(limit=min(limit, 50), actor=user["actor"])
    return [JobRecord(**row) for row in rows]


@app.post("/api/v1/jobs/forecast", response_model=JobEnqueueResponse)
def jobs_forecast_async(
    body: ForecastRequest,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> JobEnqueueResponse:
    require_write_access(user)
    job_id = enqueue_job(
        "forecast",
        body.model_dump(),
        actor=user["actor"],
    )
    return JobEnqueueResponse(job_id=job_id)


@app.post("/api/v1/jobs/report", response_model=JobEnqueueResponse)
def jobs_report_async(
    body: ReportRequest,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> JobEnqueueResponse:
    require_write_access(user)
    job_id = enqueue_job(
        "report",
        body.model_dump(),
        actor=user["actor"],
    )
    return JobEnqueueResponse(job_id=job_id)


@app.get("/api/v1/policy/retention", response_model=RetentionPolicy)
def retention_policy() -> RetentionPolicy:
    expiring = sessions_expiring_within(days=14, retention_days=RETENTION_DAYS)
    return RetentionPolicy(
        retention_days=RETENTION_DAYS,
        expiring_soon=expiring,
        last_purge_count=_last_purge_count,
    )


@app.get("/api/v1/audit", response_model=list[AuditEventRecord])
def audit_log(limit: int = 50) -> list[AuditEventRecord]:
    rows = list_audit_events(limit=min(limit, 200))
    return [AuditEventRecord(**row) for row in rows]


@app.get("/api/v1/sessions", response_model=list[SessionMeta])
def sessions_list() -> list[SessionMeta]:
    rows = list_sessions()
    return [SessionMeta(**row) for row in rows]


@app.get("/api/v1/sessions/{session_id}", response_model=DashboardPayload)
def sessions_get(
    session_id: str,
    user: Annotated[dict[str, str], Depends(get_current_user)],
    x_skip_audit: Annotated[str | None, Header(alias="X-Skip-Audit")] = None,
) -> DashboardPayload:
    payload = get_session(session_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if x_skip_audit != "1":
        log_audit_event(
            "session_open",
            user["actor"],
            session_id=session_id,
            detail={"source_file": payload.get("source_file"), "role": user["role"]},
        )
    dash = restore_dashboard_from_records(payload)
    return enrich_dashboard_tier3(dash)


@app.post("/api/v1/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: Annotated[dict[str, str], Depends(get_current_user)] = ...,
) -> UploadResponse:
    require_write_access(user)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    result = process_upload(content, file.filename)
    if isinstance(result, ValidationResult):
        log_audit_event(
            "upload_failed",
            user["actor"],
            detail={"filename": file.filename, "errors": result.errors[:5]},
        )
        raise HTTPException(
            status_code=422,
            detail={
                "errors": result.errors,
                "warnings": result.warnings,
                "row_count": result.row_count,
                "detected_format": result.detected_format,
                "freelance_insights": result.freelance_insights,
                "freelance_summary": result.freelance_summary,
            },
        )

    log_audit_event(
        "upload",
        user["actor"],
        session_id=result.session_id,
        detail={
            "source_file": result.source_file,
            "period_count": result.period_count,
            "role": user["role"],
        },
    )
    return UploadResponse(dashboard=result)


@app.post("/api/v1/summarize", response_model=SummarizeResponse)
def summarize(
    body: SummarizeRequest,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> SummarizeResponse:
    require_write_access(user)
    _summarize_limiter.check(user["actor"])

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")
    try:
        summary = generate_executive_summary(body.snapshot, api_key=api_key)
    except SummaryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    session_id = body.snapshot.get("source_file", "unknown")
    log_audit_event(
        "summarize",
        user["actor"],
        session_id=body.session_id,
        detail={"source_file": session_id, "role": user["role"]},
    )
    return SummarizeResponse(summary=summary)


@app.post("/api/v1/forecast", response_model=ForecastResponse)
def forecast(body: ForecastRequest) -> ForecastResponse:
    try:
        data = run_forecast_api(body.monthly_records, body.metric, body.horizon_months)
    except ForecastError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ForecastResponse(forecast=data)


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_endpoint(
    body: ChatRequest,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> ChatResponse:
    require_write_access(user)
    _chat_limiter.check(user["actor"])

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    session_id = body.session_id or "advisory"
    use_dataset = bool(body.monthly_records) and body.mode == "dataset"
    freelance_ctx = body.freelance_summary if body.mode in ("freelance", "advisory") else None

    stored = get_chat_messages(session_id) if session_id else []
    history: list[ChatTurn] = [
        ChatTurn(role=m["role"], content=m["content"]) for m in stored
    ]
    if not history and body.history:
        history = body.history

    save_chat_message(session_id, "user", body.message)

    try:
        if use_dataset:
            result = run_chat_from_snapshot_payload(
                body.message,
                body.monthly_records,
                top_expense_categories=body.top_expense_categories,
                source_file=body.source_file,
                history=history,
                api_key=api_key,
            )
        else:
            result = run_advisory_chat(
                body.message,
                history=history,
                freelance_summary=freelance_ctx or body.freelance_summary,
                api_key=api_key,
            )
    except ChatError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    save_chat_message(
        session_id,
        "assistant",
        result.answer,
        sources=result.sources,
    )

    log_audit_event(
        "chat",
        user["actor"],
        session_id=session_id if use_dataset else None,
        detail={
            "question_preview": body.message[:120],
            "mode": "dataset" if use_dataset else ("freelance" if freelance_ctx else "advisory"),
            "role": user["role"],
        },
    )

    return ChatResponse(result=result)


@app.get("/api/v1/sessions/{session_id}/chat", response_model=ChatHistoryResponse)
def chat_history(session_id: str) -> ChatHistoryResponse:
    payload = get_session(session_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = get_chat_messages(session_id)
    return ChatHistoryResponse(
        messages=[ChatMessageRecord(**m) for m in rows]
    )


@app.delete("/api/v1/sessions/{session_id}/chat")
def chat_clear(
    session_id: str,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> dict[str, str]:
    require_write_access(user)
    payload = get_session(session_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Session not found")
    clear_chat_messages(session_id)
    log_audit_event("chat_clear", user["actor"], session_id=session_id)
    return {"status": "cleared"}


@app.post("/api/v1/reports/executive", response_model=ReportResponse)
def executive_report(
    body: ReportRequest,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> ReportResponse:
    require_write_access(user)
    dashboard = DashboardPayload(
        session_id=body.session_id,
        source_file=body.source_file,
        period_count=len(body.monthly_records),
        kpis=body.snapshot.get("metrics", {}),
        snapshot=body.snapshot,
        monthly_records=body.monthly_records,
        chart_series=[],
        top_expense_categories=body.top_expense_categories,
        anomalies=body.anomalies,
        warnings=body.warnings,
    )
    try:
        artifacts = build_report_from_dashboard(dashboard, executive_summary=body.summary)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    log_audit_event(
        "report_export",
        user["actor"],
        session_id=body.session_id,
        detail={"source_file": body.source_file, "has_summary": body.summary is not None},
    )
    data = report_to_api_response(artifacts)
    return ReportResponse(**data)


@app.get("/api/v1/benchmarks/industries")
def benchmarks_industries() -> list[dict[str, str]]:
    return list_industries()


@app.get("/api/v1/alerts", response_model=list[AlertRecord])
def alerts_list(
    session_id: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[AlertRecord]:
    rows = list_alerts(session_id=session_id, unread_only=unread_only, limit=limit)
    return [AlertRecord(**row) for row in rows]


@app.post("/api/v1/alerts/mark-read")
def alerts_mark_read(session_id: str | None = None) -> dict[str, int]:
    count = mark_alerts_read(session_id=session_id)
    return {"marked": count}


@app.post("/api/v1/scenarios")
def scenarios_run(body: ScenarioRequest) -> dict[str, Any]:
    return run_scenario(
        body.monthly_records,
        revenue_delta_pct=body.revenue_delta_pct,
        opex_delta_pct=body.opex_delta_pct,
        cogs_delta_pct=body.cogs_delta_pct,
        apply_to=body.apply_to,
    )


@app.post("/api/v1/sessions/compare")
def sessions_compare(body: CompareRequest) -> dict[str, Any]:
    a = get_session(body.session_id_a)
    b = get_session(body.session_id_b)
    if a is None or b is None:
        raise HTTPException(status_code=404, detail="One or both sessions not found")
    return compare_session_payloads(a, b)


@app.get("/api/v1/scheduled-reports", response_model=list[ScheduledReportRecord])
def scheduled_reports_list(session_id: str | None = None) -> list[ScheduledReportRecord]:
    return [ScheduledReportRecord(**row) for row in list_scheduled_reports(session_id)]


@app.post("/api/v1/scheduled-reports", response_model=ScheduledReportRecord)
def scheduled_reports_create(
    body: ScheduledReportCreate,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> ScheduledReportRecord:
    require_write_access(user)
    rid = create_scheduled_report(
        body.session_id,
        body.label,
        body.cadence,
        body.format,
        body.recipients,
    )
    rows = list_scheduled_reports(body.session_id)
    row = next((r for r in rows if r["id"] == rid), rows[0] if rows else None)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create schedule")
    log_audit_event(
        "scheduled_report_created",
        user["actor"],
        session_id=body.session_id,
        detail={"label": body.label, "cadence": body.cadence},
    )
    return ScheduledReportRecord(**row)


@app.post("/api/v1/scheduled-reports/{report_id}/run", response_model=JobEnqueueResponse)
def scheduled_reports_run(
    report_id: int,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> JobEnqueueResponse:
    """Enqueue background job to generate scheduled report."""
    require_write_access(user)
    from db.tier3_store import get_scheduled_report

    row = get_scheduled_report(report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    session_payload = get_session(row["session_id"])
    if session_payload is None:
        raise HTTPException(status_code=404, detail="Session not found for schedule")
    job_id = enqueue_job(
        "scheduled_report",
        {"report_id": report_id, "session_payload": session_payload},
        actor=user["actor"],
    )
    log_audit_event(
        "scheduled_report_queued",
        user["actor"],
        session_id=row["session_id"],
        detail={"report_id": report_id, "job_id": job_id},
    )
    return JobEnqueueResponse(job_id=job_id)


@app.delete("/api/v1/scheduled-reports/{report_id}")
def scheduled_reports_delete(
    report_id: int,
    user: Annotated[dict[str, str], Depends(get_current_user)],
) -> dict[str, str]:
    require_write_access(user)
    if not delete_scheduled_report(report_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "deleted"}


@app.post("/api/v1/why-panel")
def why_panel(body: dict[str, Any]) -> dict[str, Any]:
    records = body.get("monthly_records", [])
    ctx = context_from_monthly_records(
        records,
        top_expense_categories=body.get("top_expense_categories", []),
    )
    from schemas.anomaly import AnomalyFlag

    raw_flags = body.get("anomalies", {}).get("flags", [])
    flags = [AnomalyFlag(**f) for f in raw_flags]
    report = AnomalyReport(
        flags=flags,
        summary=body.get("anomalies", {}).get("summary", {}),
    )
    panel = build_why_panel(ctx.kpis, anomaly_report=report if flags else None)
    return {"insights": [p.model_dump() for p in panel]}
