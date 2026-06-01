"""Rule-based financial alerts from KPIs and anomalies."""

from __future__ import annotations

from typing import Any


def generate_alert_rules(
    kpis: dict[str, Any],
    anomalies: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return alert dicts ready for DB insert (no id)."""
    alerts: list[dict[str, Any]] = []
    latest = kpis.get("latest_month", "latest period")

    mom_rev = kpis.get("mom_revenue_growth_pct")
    if mom_rev is not None and float(mom_rev) <= -15:
        alerts.append(
            {
                "rule_id": "mom_revenue_drop",
                "severity": "high",
                "title": "Revenue dropped sharply MoM",
                "message": f"Revenue fell {abs(float(mom_rev)):.1f}% month-over-month ({latest}).",
                "metric": "mom_revenue_growth_pct",
                "value": float(mom_rev),
            }
        )

    mom_profit = kpis.get("mom_profit_growth_pct")
    if mom_profit is not None and float(mom_profit) <= -20:
        alerts.append(
            {
                "rule_id": "mom_profit_drop",
                "severity": "high",
                "title": "Net profit declined MoM",
                "message": f"Net profit changed {float(mom_profit):+.1f}% vs prior month ({latest}).",
                "metric": "mom_profit_growth_pct",
                "value": float(mom_profit),
            }
        )

    margin = kpis.get("latest_gross_margin_pct")
    if margin is not None and float(margin) < 20:
        alerts.append(
            {
                "rule_id": "low_gross_margin",
                "severity": "medium",
                "title": "Low gross margin",
                "message": f"Gross margin is {float(margin):.1f}% in {latest} — review COGS and pricing.",
                "metric": "latest_gross_margin_pct",
                "value": float(margin),
            }
        )

    opex_ratio = kpis.get("latest_opex_ratio_pct")
    if opex_ratio is not None and float(opex_ratio) > 50:
        alerts.append(
            {
                "rule_id": "high_opex_ratio",
                "severity": "medium",
                "title": "Elevated operating expense ratio",
                "message": f"Opex ratio is {float(opex_ratio):.1f}% of revenue ({latest}).",
                "metric": "latest_opex_ratio_pct",
                "value": float(opex_ratio),
            }
        )

    summary = anomalies.get("summary", {}) or {}
    high_sev = int(summary.get("high_severity", 0) or 0)
    if high_sev > 0:
        alerts.append(
            {
                "rule_id": "anomaly_high",
                "severity": "high",
                "title": "High-severity anomalies detected",
                "message": f"{high_sev} high-severity anomaly flag(s) in the dataset.",
                "metric": "anomalies",
                "value": high_sev,
            }
        )

    count = int(summary.get("count", 0) or 0)
    if count >= 3 and high_sev == 0:
        alerts.append(
            {
                "rule_id": "anomaly_multiple",
                "severity": "low",
                "title": "Multiple anomalies flagged",
                "message": f"{count} statistical anomalies detected — review Anomalies tab.",
                "metric": "anomalies",
                "value": count,
            }
        )

    return alerts
