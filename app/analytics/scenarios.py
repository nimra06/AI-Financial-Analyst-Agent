"""Deterministic what-if scenario modeling."""

from __future__ import annotations

from typing import Any

import pandas as pd

from llm.agent_tools import context_from_monthly_records


def run_scenario(
    monthly_records: list[dict[str, Any]],
    *,
    revenue_delta_pct: float = 0.0,
    opex_delta_pct: float = 0.0,
    cogs_delta_pct: float = 0.0,
    apply_to: str = "latest",
) -> dict[str, Any]:
    """
    Apply percentage deltas to revenue, opex, or cogs and recompute profit.

    apply_to: 'latest' (single month) or 'all' (full series).
    """
    ctx = context_from_monthly_records(monthly_records)
    df = ctx.monthly.sort_values("month").copy()

    if df.empty:
        return {"error": "No data"}

    rev_mult = 1 + revenue_delta_pct / 100
    opex_mult = 1 + opex_delta_pct / 100
    cogs_mult = 1 + cogs_delta_pct / 100

    baseline = df.copy()
    projected = df.copy()

    if apply_to == "latest":
        idx = projected.index[-1]
        projected.loc[idx, "revenue"] = float(projected.loc[idx, "revenue"]) * rev_mult
        projected.loc[idx, "cogs"] = float(projected.loc[idx, "cogs"]) * cogs_mult
        projected.loc[idx, "opex"] = float(projected.loc[idx, "opex"]) * opex_mult
    else:
        projected["revenue"] = projected["revenue"] * rev_mult
        projected["cogs"] = projected["cogs"] * cogs_mult
        projected["opex"] = projected["opex"] * opex_mult

    for frame in (baseline, projected):
        frame["gross_profit"] = frame["revenue"] - frame["cogs"]
        frame["net_profit"] = frame["gross_profit"] - frame["opex"]

    b_latest = baseline.iloc[-1]
    p_latest = projected.iloc[-1]

    def _row(label: str, b: float, p: float) -> dict[str, Any]:
        return {
            "metric": label,
            "baseline": round(float(b), 2),
            "projected": round(float(p), 2),
            "delta": round(float(p - b), 2),
            "delta_pct": round((p - b) / b * 100, 2) if b else None,
        }

    return {
        "assumptions": {
            "revenue_delta_pct": revenue_delta_pct,
            "opex_delta_pct": opex_delta_pct,
            "cogs_delta_pct": cogs_delta_pct,
            "apply_to": apply_to,
        },
        "latest_month": p_latest["month"].strftime("%b %Y"),
        "impact": [
            _row("revenue", b_latest["revenue"], p_latest["revenue"]),
            _row("gross_profit", b_latest["gross_profit"], p_latest["gross_profit"]),
            _row("net_profit", b_latest["net_profit"], p_latest["net_profit"]),
        ],
        "projected_net_profit": round(float(p_latest["net_profit"]), 2),
        "baseline_net_profit": round(float(b_latest["net_profit"]), 2),
    }
