"""API models for dashboard session payloads."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from schemas.chat import ChatResult
from schemas.summary import ExecutiveSummary


class MonthlyPoint(BaseModel):
    month: str
    revenue: float
    gross_profit: float
    net_profit: float
    opex: float
    gross_margin_pct: float
    opex_ratio_pct: float


class DashboardPayload(BaseModel):
    session_id: str
    source_file: str
    period_count: int
    kpis: dict[str, Any]
    snapshot: dict[str, Any]
    monthly_records: list[dict[str, Any]]
    chart_series: list[MonthlyPoint]
    top_expense_categories: list[dict[str, Any]] = Field(default_factory=list)
    raw_preview: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    industry: str = "saas"
    budget_variance: dict[str, Any] = Field(default_factory=dict)
    benchmarks: dict[str, Any] = Field(default_factory=dict)


class SessionMeta(BaseModel):
    session_id: str
    source_file: str
    period_count: int
    latest_month: str
    created_at: str


class UploadResponse(BaseModel):
    dashboard: DashboardPayload


class SummarizeRequest(BaseModel):
    snapshot: dict[str, Any]
    session_id: Optional[str] = None


class SummarizeResponse(BaseModel):
    summary: ExecutiveSummary


class ForecastRequest(BaseModel):
    monthly_records: list[dict[str, Any]]
    metric: str = "revenue"
    horizon_months: int = 3


class ForecastResponse(BaseModel):
    forecast: dict[str, Any]


class ChatApiResponse(BaseModel):
    result: ChatResult


class ReportRequest(BaseModel):
    session_id: str
    source_file: str
    snapshot: dict[str, Any]
    monthly_records: list[dict[str, Any]]
    top_expense_categories: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    summary: Optional[ExecutiveSummary] = None


class ReportResponse(BaseModel):
    html: str
    markdown: str
    pdf_available: bool = False
    pdf_base64: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
