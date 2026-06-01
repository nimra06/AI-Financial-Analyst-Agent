"""Tier 3 API models: scenarios, compare, alerts, scheduled reports."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    monthly_records: list[dict[str, Any]]
    revenue_delta_pct: float = 0.0
    opex_delta_pct: float = 0.0
    cogs_delta_pct: float = 0.0
    apply_to: str = "latest"


class CompareRequest(BaseModel):
    session_id_a: str
    session_id_b: str


class AlertRecord(BaseModel):
    id: int
    session_id: str
    rule_id: str
    severity: str
    title: str
    message: str
    metric: Optional[str] = None
    value: Optional[float] = None
    read_at: Optional[str] = None
    created_at: str


class ScheduledReportCreate(BaseModel):
    session_id: str
    label: str
    cadence: str = "weekly"
    format: str = "pdf"
    recipients: list[str] = Field(default_factory=list)


class ScheduledReportRecord(BaseModel):
    id: int
    session_id: str
    label: str
    cadence: str
    format: str
    recipients: list[str]
    enabled: bool
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    created_at: str
