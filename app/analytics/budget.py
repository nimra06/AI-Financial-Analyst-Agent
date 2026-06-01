"""Budget vs actual variance from monthly aggregates."""

from __future__ import annotations

from typing import Any

import pandas as pd


def compute_budget_variance(monthly: pd.DataFrame) -> dict[str, Any]:
    """
    Compare actuals to budget columns when present on monthly frame.
    Expected columns: budget_revenue, budget_opex (optional budget_net_profit).
    """
    if monthly.empty:
        return {"available": False, "reason": "No monthly data"}

    has_rev = "budget_revenue" in monthly.columns and monthly["budget_revenue"].sum() > 0
    has_opex = "budget_opex" in monthly.columns and monthly["budget_opex"].sum() > 0
    if not has_rev and not has_opex:
        return {
            "available": False,
            "reason": "Add budget_revenue and/or budget_opex columns to your CSV for variance analysis.",
        }

    latest = monthly.sort_values("month").iloc[-1]
    rows: list[dict[str, Any]] = []

    if has_rev:
        actual = float(latest["revenue"])
        budget = float(latest["budget_revenue"])
        var = actual - budget
        var_pct = (var / budget * 100) if budget else None
        rows.append(
            {
                "metric": "revenue",
                "actual": round(actual, 2),
                "budget": round(budget, 2),
                "variance": round(var, 2),
                "variance_pct": round(var_pct, 2) if var_pct is not None else None,
                "favorable": var >= 0,
            }
        )

    if has_opex:
        actual = float(latest["opex"])
        budget = float(latest["budget_opex"])
        var = budget - actual  # lower opex is favorable
        var_pct = (var / budget * 100) if budget else None
        rows.append(
            {
                "metric": "opex",
                "actual": round(actual, 2),
                "budget": round(budget, 2),
                "variance": round(var, 2),
                "variance_pct": round(var_pct, 2) if var_pct is not None else None,
                "favorable": var >= 0,
            }
        )

    ytd_actual_rev = float(monthly["revenue"].sum())
    ytd_budget_rev = float(monthly["budget_revenue"].sum()) if has_rev else 0
    return {
        "available": True,
        "latest_month": latest["month"].strftime("%b %Y") if hasattr(latest["month"], "strftime") else str(latest["month"]),
        "lines": rows,
        "ytd_revenue_actual": round(ytd_actual_rev, 2),
        "ytd_revenue_budget": round(ytd_budget_rev, 2) if has_rev else None,
        "ytd_revenue_variance_pct": (
            round((ytd_actual_rev - ytd_budget_rev) / ytd_budget_rev * 100, 2)
            if has_rev and ytd_budget_rev
            else None
        ),
    }
