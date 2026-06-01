"""Forecast models for Prophet output and LLM explanations."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ForecastMetric = Literal["revenue", "opex"]


class ForecastPoint(BaseModel):
    month: str
    value: float
    lower: float
    upper: float


class ForecastPayload(BaseModel):
    """Serializable Prophet forecast for charts, export, and LLM context."""

    metric: ForecastMetric
    horizon_months: int
    history: list[ForecastPoint]
    forecast: list[ForecastPoint]
    summary: dict = Field(
        description="Aggregates: last_actual, forecast_total, forecast_avg, etc."
    )
    warnings: list[str] = Field(default_factory=list)


class ForecastExplanation(BaseModel):
    """LLM narrative tied to forecast JSON only."""

    outlook: str = Field(description="2-3 sentences on forward view")
    key_figures: list[str] = Field(description="Bullets citing numbers from CONTEXT")
    risks_and_caveats: list[str] = Field(description="Uncertainty and data limitations")
