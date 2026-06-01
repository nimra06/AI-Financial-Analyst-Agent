"""Executive report and explainability models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class WhyInsight(BaseModel):
    """Traceable metric line for the 'Why' panel."""

    metric: str
    value: str
    period: str
    formula_hint: str
    category: str = Field(
        default="kpi",
        description="kpi | derived | anomaly",
    )


class ReportArtifacts(BaseModel):
    """Generated report outputs."""

    html: str
    markdown: str
    why_panel: list[WhyInsight]
    pdf_available: bool = False
    pdf_bytes: Optional[bytes] = None
    warnings: list[str] = Field(default_factory=list)
