"""Anomaly detection result models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

AnomalyMethod = Literal["z_score", "iqr", "isolation_forest", "mom_change"]
AnomalySeverity = Literal["medium", "high"]


class AnomalyFlag(BaseModel):
    month: str
    metric: str
    value: float
    method: AnomalyMethod
    severity: AnomalySeverity
    score: float = Field(description="Method-specific score (z, IQR distance, IF score, MoM %)")
    direction: Literal["high", "low"]
    description: str


class AnomalyReport(BaseModel):
    flags: list[AnomalyFlag] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
