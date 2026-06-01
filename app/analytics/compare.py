"""Compare two saved dataset sessions side by side."""

from __future__ import annotations

from typing import Any


def compare_session_payloads(
    payload_a: dict[str, Any],
    payload_b: dict[str, Any],
) -> dict[str, Any]:
    kpis_a = payload_a.get("kpis", {})
    kpis_b = payload_b.get("kpis", {})

    metrics = [
        "latest_revenue",
        "latest_net_profit",
        "latest_gross_margin_pct",
        "latest_opex_ratio_pct",
        "mom_revenue_growth_pct",
        "total_revenue",
    ]

    deltas: list[dict[str, Any]] = []
    for key in metrics:
        a = kpis_a.get(key)
        b = kpis_b.get(key)
        if a is None or b is None:
            continue
        a_f, b_f = float(a), float(b)
        deltas.append(
            {
                "metric": key,
                "session_a": round(a_f, 2),
                "session_b": round(b_f, 2),
                "delta": round(b_f - a_f, 2),
                "delta_pct": round((b_f - a_f) / abs(a_f) * 100, 2) if a_f else None,
            }
        )

    rev_a = float(kpis_a.get("latest_revenue", 0))
    rev_b = float(kpis_b.get("latest_revenue", 0))
    profit_a = float(kpis_a.get("latest_net_profit", 0))
    profit_b = float(kpis_b.get("latest_net_profit", 0))

    return {
        "session_a": {
            "session_id": payload_a.get("session_id"),
            "source_file": payload_a.get("source_file"),
            "period_count": payload_a.get("period_count"),
            "latest_month": kpis_a.get("latest_month"),
        },
        "session_b": {
            "session_id": payload_b.get("session_id"),
            "source_file": payload_b.get("source_file"),
            "period_count": payload_b.get("period_count"),
            "latest_month": kpis_b.get("latest_month"),
        },
        "deltas": deltas,
        "summary": {
            "higher_latest_revenue": "b" if rev_b > rev_a else "a",
            "higher_latest_profit": "b" if profit_b > profit_a else "a",
            "revenue_gap": round(rev_b - rev_a, 2),
            "profit_gap": round(profit_b - profit_a, 2),
        },
    }
