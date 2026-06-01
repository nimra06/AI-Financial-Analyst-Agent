"""Static industry benchmark bands for demo comparisons."""

from __future__ import annotations

from typing import Any

# (low, typical, high) ranges for key ratios
INDUSTRY_BENCHMARKS: dict[str, dict[str, tuple[float, float, float]]] = {
    "saas": {
        "gross_margin_pct": (55.0, 70.0, 85.0),
        "opex_ratio_pct": (45.0, 60.0, 75.0),
        "mom_revenue_growth_pct": (-5.0, 8.0, 25.0),
    },
    "retail": {
        "gross_margin_pct": (25.0, 35.0, 45.0),
        "opex_ratio_pct": (20.0, 28.0, 38.0),
        "mom_revenue_growth_pct": (-8.0, 3.0, 12.0),
    },
    "services": {
        "gross_margin_pct": (40.0, 55.0, 65.0),
        "opex_ratio_pct": (30.0, 42.0, 55.0),
        "mom_revenue_growth_pct": (-5.0, 5.0, 15.0),
    },
}


def list_industries() -> list[dict[str, str]]:
    return [{"id": k, "label": k.replace("_", " ").title()} for k in INDUSTRY_BENCHMARKS]


def score_against_benchmark(kpis: dict[str, Any], industry: str = "saas") -> dict[str, Any]:
    bands = INDUSTRY_BENCHMARKS.get(industry.lower(), INDUSTRY_BENCHMARKS["saas"])
    scores: list[dict[str, Any]] = []

    aliases = {
        "gross_margin_pct": "latest_gross_margin_pct",
        "opex_ratio_pct": "latest_opex_ratio_pct",
    }

    for metric, (low, mid, high) in bands.items():
        value = kpis.get(metric)
        if value is None and metric in aliases:
            value = kpis.get(aliases[metric])
        if value is None:
            continue
        val = float(value)
        if val < low:
            status = "below"
        elif val > high:
            status = "above"
        else:
            status = "in_range"
        scores.append(
            {
                "metric": metric,
                "value": round(val, 2),
                "benchmark_low": low,
                "benchmark_mid": mid,
                "benchmark_high": high,
                "status": status,
                "vs_typical": round(val - mid, 2),
            }
        )

    return {
        "industry": industry,
        "scores": scores,
        "disclaimer": "Static demo benchmarks — not company-specific guidance.",
    }
