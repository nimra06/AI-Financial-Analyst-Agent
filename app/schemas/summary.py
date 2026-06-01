"""Structured executive summary returned by the LLM."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExecutiveSummary(BaseModel):
    """Metric-backed executive analysis — all numbers must come from CONTEXT."""

    summary: str = Field(description="2-4 sentence executive overview")
    trends: list[str] = Field(description="3-5 trend bullets citing specific metrics")
    risks: list[str] = Field(description="2-4 risk bullets tied to data")
    opportunities: list[str] = Field(description="2-4 opportunity bullets tied to data")
    recommendations: list[str] = Field(
        description="3-5 actionable recommendations referencing metrics"
    )
