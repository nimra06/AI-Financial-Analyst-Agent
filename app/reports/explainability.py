"""Deterministic 'Why' panel — every figure traceable to a formula."""

from __future__ import annotations

from typing import Any, Optional

from analytics.kpis import KpiSummary
from schemas.anomaly import AnomalyReport
from schemas.report import WhyInsight


def _fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def _fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def build_why_panel(
    kpis: KpiSummary,
    *,
    anomaly_report: Optional[AnomalyReport] = None,
) -> list[WhyInsight]:
    """Build explainability rows from computed KPIs and anomaly flags."""
    m = kpis.to_snapshot_dict()
    period = m["latest_month"]
    insights: list[WhyInsight] = [
        WhyInsight(
            metric="Latest revenue",
            value=_fmt_money(m["latest_revenue"]),
            period=period,
            formula_hint="Sum of `revenue` for the latest month in uploaded data",
            category="kpi",
        ),
        WhyInsight(
            metric="Latest net profit",
            value=_fmt_money(m["latest_net_profit"]),
            period=period,
            formula_hint="revenue − cogs − opex (or revenue − cogs if opex missing) for latest month",
            category="kpi",
        ),
        WhyInsight(
            metric="Gross margin %",
            value=_fmt_pct(m["latest_gross_margin_pct"]),
            period=period,
            formula_hint="(gross_profit / revenue) × 100, latest month",
            category="derived",
        ),
        WhyInsight(
            metric="Operating expense ratio %",
            value=_fmt_pct(m["latest_opex_ratio_pct"]),
            period=period,
            formula_hint="(opex / revenue) × 100, latest month",
            category="derived",
        ),
        WhyInsight(
            metric="MoM revenue growth",
            value=_fmt_pct(m.get("mom_revenue_growth_pct")),
            period=f"vs prior month to {period}",
            formula_hint="(latest_revenue − prior_revenue) / |prior_revenue| × 100",
            category="derived",
        ),
        WhyInsight(
            metric="MoM net profit growth",
            value=_fmt_pct(m.get("mom_profit_growth_pct")),
            period=f"vs prior month to {period}",
            formula_hint="(latest_net_profit − prior_net_profit) / |prior_net_profit| × 100",
            category="derived",
        ),
        WhyInsight(
            metric="3-month average revenue",
            value=_fmt_money(m["avg_revenue_3m"]),
            period="Trailing 3 months",
            formula_hint="Mean of `revenue` over the last 3 months",
            category="derived",
        ),
        WhyInsight(
            metric="3-month average net profit",
            value=_fmt_money(m["avg_profit_3m"]),
            period="Trailing 3 months",
            formula_hint="Mean of `net_profit` over the last 3 months",
            category="derived",
        ),
        WhyInsight(
            metric="Total revenue (all periods)",
            value=_fmt_money(m["total_revenue"]),
            period="Full dataset",
            formula_hint="Sum of `revenue` across all months",
            category="kpi",
        ),
        WhyInsight(
            metric="Total net profit (all periods)",
            value=_fmt_money(m["total_net_profit"]),
            period="Full dataset",
            formula_hint="Sum of `net_profit` across all months",
            category="kpi",
        ),
        WhyInsight(
            metric="Best month by revenue",
            value=f"{m['best_month_by_revenue']} ({_fmt_money(m['best_month_revenue'])})",
            period="Full dataset",
            formula_hint="Month with maximum `revenue`",
            category="derived",
        ),
    ]

    for item in m.get("top_expense_categories", [])[:5]:
        insights.append(
            WhyInsight(
                metric=f"Top expense: {item['category']}",
                value=_fmt_money(float(item["amount"])),
                period=period,
                formula_hint="Sum of category `amount` (or opex) for latest/detailed rows",
                category="kpi",
            )
        )

    if anomaly_report:
        for flag in anomaly_report.flags[:8]:
            insights.append(
                WhyInsight(
                    metric=f"Anomaly: {flag.metric}",
                    value=f"{_fmt_money(flag.value)} (score {flag.score})",
                    period=flag.month,
                    formula_hint=f"{flag.method}: {flag.description}",
                    category="anomaly",
                )
            )

    return insights
