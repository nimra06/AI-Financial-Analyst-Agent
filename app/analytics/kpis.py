"""Deterministic KPI and metric computations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class KpiSummary:
    """Headline metrics for dashboard cards and future LLM context."""

    latest_month: str
    total_revenue: float
    total_net_profit: float
    latest_revenue: float
    latest_net_profit: float
    latest_gross_margin_pct: float
    latest_opex_ratio_pct: float
    mom_revenue_growth_pct: Optional[float]
    mom_profit_growth_pct: Optional[float]
    avg_revenue_3m: float
    avg_profit_3m: float
    best_month_by_revenue: str
    best_month_revenue: float
    top_expense_categories: list[dict[str, Any]] = field(default_factory=list)
    monthly_records: list[dict[str, Any]] = field(default_factory=list)

    def to_snapshot_dict(self) -> dict[str, Any]:
        """JSON-serializable metrics for Step 2 LLM context."""
        return {
            "latest_month": self.latest_month,
            "total_revenue": round(self.total_revenue, 2),
            "total_net_profit": round(self.total_net_profit, 2),
            "latest_revenue": round(self.latest_revenue, 2),
            "latest_net_profit": round(self.latest_net_profit, 2),
            "latest_gross_margin_pct": round(self.latest_gross_margin_pct, 2),
            "latest_opex_ratio_pct": round(self.latest_opex_ratio_pct, 2),
            "mom_revenue_growth_pct": (
                round(self.mom_revenue_growth_pct, 2)
                if self.mom_revenue_growth_pct is not None
                else None
            ),
            "mom_profit_growth_pct": (
                round(self.mom_profit_growth_pct, 2)
                if self.mom_profit_growth_pct is not None
                else None
            ),
            "avg_revenue_3m": round(self.avg_revenue_3m, 2),
            "avg_profit_3m": round(self.avg_profit_3m, 2),
            "best_month_by_revenue": self.best_month_by_revenue,
            "best_month_revenue": round(self.best_month_revenue, 2),
            "top_expense_categories": self.top_expense_categories,
            "monthly_records": self.monthly_records,
        }


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None if current == 0 else 100.0
    return ((current - previous) / abs(previous)) * 100


def _month_label(ts: pd.Timestamp) -> str:
    return ts.strftime("%b %Y")


def compute_kpis(
    monthly: pd.DataFrame,
    categories: Optional[pd.DataFrame] = None,
) -> KpiSummary:
    """Compute dashboard KPIs from monthly aggregates and optional category breakdown."""
    df = monthly.sort_values("month").copy()
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    mom_rev = (
        _pct_change(float(latest["revenue"]), float(prev["revenue"]))
        if prev is not None
        else None
    )
    mom_profit = (
        _pct_change(float(latest["net_profit"]), float(prev["net_profit"]))
        if prev is not None
        else None
    )

    tail = df.tail(3)
    best_idx = df["revenue"].idxmax()
    best_row = df.loc[best_idx]

    top_expenses: list[dict[str, Any]] = []
    if categories is not None and not categories.empty:
        latest_month = latest["month"]
        cat_latest = categories[categories["month"] == latest_month]
        if cat_latest.empty:
            cat_latest = categories
        grouped = (
            cat_latest.groupby("category", as_index=False)["expense"]
            .sum()
            .sort_values("expense", ascending=False)
            .head(8)
        )
        top_expenses = [
            {"category": row["category"], "amount": round(float(row["expense"]), 2)}
            for _, row in grouped.iterrows()
        ]
    elif float(latest["opex"]) > 0:
        top_expenses = [{"category": "Total operating expenses", "amount": round(float(latest["opex"]), 2)}]

    monthly_records = []
    for _, row in df.iterrows():
        rec: dict[str, Any] = {
            "month": _month_label(row["month"]),
            "revenue": round(float(row["revenue"]), 2),
            "gross_profit": round(float(row["gross_profit"]), 2),
            "net_profit": round(float(row["net_profit"]), 2),
            "gross_margin_pct": round(float(row["gross_margin_pct"]), 2),
            "opex_ratio_pct": round(float(row["opex_ratio_pct"]), 2),
            "cogs": round(float(row.get("cogs", 0)), 2),
            "opex": round(float(row.get("opex", 0)), 2),
        }
        if "budget_revenue" in df.columns:
            rec["budget_revenue"] = round(float(row.get("budget_revenue", 0)), 2)
        if "budget_opex" in df.columns:
            rec["budget_opex"] = round(float(row.get("budget_opex", 0)), 2)
        monthly_records.append(rec)

    return KpiSummary(
        latest_month=_month_label(latest["month"]),
        total_revenue=float(df["revenue"].sum()),
        total_net_profit=float(df["net_profit"].sum()),
        latest_revenue=float(latest["revenue"]),
        latest_net_profit=float(latest["net_profit"]),
        latest_gross_margin_pct=float(latest["gross_margin_pct"]),
        latest_opex_ratio_pct=float(latest["opex_ratio_pct"]),
        mom_revenue_growth_pct=mom_rev,
        mom_profit_growth_pct=mom_profit,
        avg_revenue_3m=float(tail["revenue"].mean()),
        avg_profit_3m=float(tail["net_profit"].mean()),
        best_month_by_revenue=_month_label(best_row["month"]),
        best_month_revenue=float(best_row["revenue"]),
        top_expense_categories=top_expenses,
        monthly_records=monthly_records,
    )
