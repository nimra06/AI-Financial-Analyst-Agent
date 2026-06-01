"""Tier 4 API schemas."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class AuthLoginRequest(BaseModel):
    name: str
    email: str
    role: Literal["Viewer", "Analyst", "Admin"] = "Analyst"


class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, str]


class ApiKeyCreateRequest(BaseModel):
    label: str
    owner_email: str
    role: Literal["Viewer", "Analyst", "Admin"] = "Analyst"


class ApiKeyRecord(BaseModel):
    id: int
    key_prefix: str
    label: str
    owner_email: str
    role: str
    created_at: str
    last_used_at: Optional[str] = None


class ApiKeyCreateResponse(BaseModel):
    raw_key: str
    key: ApiKeyRecord


class JobRecord(BaseModel):
    job_id: str
    job_type: str
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    actor: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class JobEnqueueResponse(BaseModel):
    job_id: str
    status: str = "pending"


class HealthReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]
