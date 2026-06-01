"""Pydantic models for financial upload validation."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FinancialRow(BaseModel):
    """One row after column normalization (monthly P&L or category line)."""

    date: date
    revenue: float = Field(default=0.0, ge=0)
    cogs: Optional[float] = Field(default=None, ge=0)
    opex: Optional[float] = Field(default=None, ge=0)
    category: Optional[str] = None
    amount: Optional[float] = Field(
        default=None,
        description="Expense amount when row is category-level detail",
    )
    budget_revenue: Optional[float] = Field(default=None, ge=0)
    budget_opex: Optional[float] = Field(default=None, ge=0)

    @field_validator("category", mode="before")
    @classmethod
    def strip_category(cls, v: object) -> Optional[str]:
        if v is None or (isinstance(v, float) and str(v) == "nan"):
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("revenue", "cogs", "opex", "amount", mode="before")
    @classmethod
    def coerce_numeric(cls, v: object) -> object:
        if v is None or v == "":
            return None
        return v


class ValidationResult(BaseModel):
    """Outcome of validating an upload."""

    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    row_count: int = 0
