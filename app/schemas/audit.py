"""Audit and policy API models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditEventRecord(BaseModel):
    id: int
    event_type: str
    actor: str
    session_id: Optional[str] = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class RetentionPolicy(BaseModel):
    retention_days: int
    expiring_soon: list[dict[str, Any]] = Field(default_factory=list)
    last_purge_count: int = 0
