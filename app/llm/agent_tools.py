"""Tool definitions and handlers for the financial analyst agent."""

from __future__ import annotations

import json
from typing import Any, Optional

import pandas as pd

from analytics.anomalies import detect_all_anomalies, report_to_context_dict
from analytics.forecasting import ForecastError, forecast_series, forecast_to_context_dict
from analytics.kpis import KpiSummary, compute_kpis
from llm.context import FinancialContext

KPI_FIELDS = {
    "latest_revenue",
    "latest_net_profit",
    "latest_gross_margin_pct",
    "latest_opex_ratio_pct",
    "mom_revenue_growth_pct",
    "mom_profit_growth_pct",
    "avg_revenue_3m",
    "avg_profit_3m",
    "total_revenue",
    "total_net_profit",
    "best_month_by_revenue",
    "best_month_revenue",
    "latest_month",
}

OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_kpi",
            "description": "Get a headline KPI or the full KPI bundle from computed metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "description": (
                            "KPI key e.g. latest_revenue, mom_revenue_growth_pct, "
                            "best_month_by_revenue. Use 'all' for the full snapshot metrics."
                        ),
                    }
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_months",
            "description": (
                "Compare two months for revenue, profit, margins, and period-over-period change."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month_a": {"type": "string", "description": "First month label or YYYY-MM"},
                    "month_b": {"type": "string", "description": "Second month label or YYYY-MM"},
                },
                "required": ["month_a", "month_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_expenses",
            "description": "List top expense categories or monthly opex totals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max categories to return (default 5)",
                        "default": 5,
                    },
                    "month": {
                        "type": "string",
                        "description": "Optional month filter (label or YYYY-MM)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_anomalies",
            "description": (
                "List unusual months/spend using z-score, IQR, MoM opex spikes, "
                "and Isolation Forest (when enough data)."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_months",
            "description": "List all available months in the dataset with key figures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 12},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": (
                "Prophet forecast for revenue or opex with 80% confidence intervals. "
                "horizon_months: 3 (one quarter) or 12 (one year)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": ["revenue", "opex"],
                        "default": "revenue",
                    },
                    "horizon_months": {
                        "type": "integer",
                        "enum": [3, 12],
                        "default": 3,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_chart",
            "description": "Request a dashboard chart to show alongside your answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["revenue", "profit", "expenses", "trends", "none"],
                    }
                },
                "required": ["chart_type"],
            },
        },
    },
]


def _resolve_month(monthly: pd.DataFrame, label: str) -> Optional[pd.Series]:
    """Match 'Mar 2024', '2024-03', 'March 2024' to a monthly row."""
    label_clean = label.strip().lower()
    df = monthly.copy()
    df["month_label"] = df["month"].dt.strftime("%b %Y")
    df["month_ym"] = df["month"].dt.strftime("%Y-%m")

    for _, row in df.iterrows():
        if label_clean in (
            row["month_label"].lower(),
            row["month_ym"].lower(),
            row["month"].strftime("%B %Y").lower(),
        ):
            return row
        if label_clean.replace("-", "") in row["month_ym"].replace("-", ""):
            return row

    parsed = pd.to_datetime(label, errors="coerce")
    if pd.notna(parsed):
        target = parsed.to_period("M").to_timestamp()
        match = df[df["month"] == target]
        if not match.empty:
            return match.iloc[0]
    return None


def tool_get_kpi(ctx: FinancialContext, metric_name: str) -> dict[str, Any]:
    metrics = ctx.kpis.to_snapshot_dict()
    key = metric_name.strip().lower().replace(" ", "_")

    if key in ("all", "full", "snapshot"):
        ctx.log_source("KPI snapshot (all metrics)")
        return {"metrics": metrics}

    if key not in KPI_FIELDS:
        return {
            "error": f"Unknown metric '{metric_name}'",
            "available_metrics": sorted(KPI_FIELDS),
        }

    value = metrics.get(key)
    ctx.log_source(f"KPI: {key} = {value}")
    return {"metric": key, "value": value, "latest_month": metrics.get("latest_month")}


def tool_compare_months(
    ctx: FinancialContext, month_a: str, month_b: str
) -> dict[str, Any]:
    row_a = _resolve_month(ctx.monthly, month_a)
    row_b = _resolve_month(ctx.monthly, month_b)
    if row_a is None or row_b is None:
        labels = ctx.monthly["month"].dt.strftime("%b %Y").tolist()
        return {
            "error": "Could not resolve one or both months",
            "available_months": labels,
        }

    def _row_payload(row: pd.Series) -> dict[str, Any]:
        return {
            "month": row["month"].strftime("%b %Y"),
            "revenue": round(float(row["revenue"]), 2),
            "gross_profit": round(float(row["gross_profit"]), 2),
            "net_profit": round(float(row["net_profit"]), 2),
            "gross_margin_pct": round(float(row["gross_margin_pct"]), 2),
            "opex": round(float(row["opex"]), 2),
        }

    a = _row_payload(row_a)
    b = _row_payload(row_b)
    rev_chg = ((b["revenue"] - a["revenue"]) / a["revenue"] * 100) if a["revenue"] else None
    profit_chg = (
        ((b["net_profit"] - a["net_profit"]) / abs(a["net_profit"]) * 100)
        if a["net_profit"]
        else None
    )

    ctx.log_source(f"Compare: {a['month']} vs {b['month']}")
    return {
        "month_a": a,
        "month_b": b,
        "revenue_change_pct": round(rev_chg, 2) if rev_chg is not None else None,
        "net_profit_change_pct": round(profit_chg, 2) if profit_chg is not None else None,
    }


def tool_top_expenses(
    ctx: FinancialContext,
    limit: int = 5,
    month: Optional[str] = None,
) -> dict[str, Any]:
    limit = max(1, min(limit, 20))
    items: list[dict[str, Any]] = []

    if ctx.categories is not None and not ctx.categories.empty:
        cat = ctx.categories.copy()
        if month:
            row = _resolve_month(ctx.monthly, month)
            if row is not None:
                cat = cat[cat["month"] == row["month"]]
        grouped = (
            cat.groupby("category", as_index=False)["expense"]
            .sum()
            .sort_values("expense", ascending=False)
            .head(limit)
        )
        items = [
            {"category": r["category"], "amount": round(float(r["expense"]), 2)}
            for _, r in grouped.iterrows()
        ]
        ctx.log_source(f"Top {len(items)} expense categories")
    else:
        df = ctx.monthly.sort_values("month")
        if month:
            row = _resolve_month(ctx.monthly, month)
            if row is not None:
                df = df[df["month"] == row["month"]]
        for _, row in df.tail(limit).iterrows():
            items.append(
                {
                    "month": row["month"].strftime("%b %Y"),
                    "opex": round(float(row["opex"]), 2),
                }
            )
        ctx.log_source("Monthly operating expenses")

    return {"expenses": items}


def tool_list_anomalies(ctx: FinancialContext) -> dict[str, Any]:
    report = detect_all_anomalies(ctx.monthly, ctx.categories)
    ctx.log_source(f"Anomaly scan ({report.summary.get('count', 0)} flags)")
    return report_to_context_dict(report)


def tool_list_months(ctx: FinancialContext, limit: int = 12) -> dict[str, Any]:
    records = ctx.kpis.monthly_records[-limit:]
    ctx.log_source(f"Monthly series ({len(records)} periods)")
    return {"months": records}


def tool_get_forecast(
    ctx: FinancialContext,
    metric: str = "revenue",
    horizon_months: int = 3,
) -> dict[str, Any]:
    horizon = 12 if int(horizon_months) == 12 else 3
    m = metric if metric in ("revenue", "opex") else "revenue"
    try:
        payload = forecast_series(ctx.monthly, m, horizon)  # type: ignore[arg-type]
    except ForecastError as exc:
        return {"error": str(exc)}
    ctx.log_source(f"Forecast: {m} +{horizon}m")
    return forecast_to_context_dict(payload)


def execute_tool(
    ctx: FinancialContext,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch a tool call by name."""
    if name == "get_kpi":
        return tool_get_kpi(ctx, arguments.get("metric_name", "all"))
    if name == "compare_months":
        return tool_compare_months(
            ctx, arguments.get("month_a", ""), arguments.get("month_b", "")
        )
    if name == "top_expenses":
        return tool_top_expenses(
            ctx,
            limit=int(arguments.get("limit", 5)),
            month=arguments.get("month"),
        )
    if name == "list_anomalies":
        return tool_list_anomalies(ctx)
    if name == "list_months":
        return tool_list_months(ctx, limit=int(arguments.get("limit", 12)))
    if name == "get_forecast":
        return tool_get_forecast(
            ctx,
            metric=str(arguments.get("metric", "revenue")),
            horizon_months=int(arguments.get("horizon_months", 3)),
        )
    if name == "suggest_chart":
        chart = str(arguments.get("chart_type", "none"))
        if chart != "none":
            ctx.pending_chart = chart
        ctx.log_source(f"Chart: {chart}")
        return {"chart_type": chart}
    return {"error": f"Unknown tool: {name}"}


def context_from_monthly_records(
    monthly_records: list[dict[str, Any]],
    *,
    top_expense_categories: Optional[list[dict[str, Any]]] = None,
    source_file: str = "upload",
    categories: Optional[pd.DataFrame] = None,
) -> FinancialContext:
    """Rebuild FinancialContext from API payload (monthly_records from snapshot)."""
    rows = []
    for rec in monthly_records:
        parsed = pd.to_datetime(rec["month"], format="%b %Y", errors="coerce")
        if pd.isna(parsed):
            parsed = pd.to_datetime(rec["month"], errors="coerce")
        revenue = float(rec["revenue"])
        gross = float(rec["gross_profit"])
        net = float(rec["net_profit"])
        rows.append(
            {
                "month": parsed.to_period("M").to_timestamp(),
                "revenue": revenue,
                "gross_profit": gross,
                "net_profit": net,
                "gross_margin_pct": float(rec["gross_margin_pct"]),
                "opex_ratio_pct": float(rec["opex_ratio_pct"]),
                "cogs": float(rec.get("cogs", revenue - gross)),
                "opex": float(rec.get("opex", gross - net)),
            }
        )
    monthly = pd.DataFrame(rows).sort_values("month")
    kpis = compute_kpis(monthly, categories)
    if top_expense_categories:
        kpis.top_expense_categories = top_expense_categories

    from analytics.snapshot import build_metrics_snapshot

    snapshot = build_metrics_snapshot(kpis, source_file=source_file, period_count=len(monthly))
    return FinancialContext(
        monthly=monthly,
        categories=categories,
        kpis=kpis,
        snapshot=snapshot,
        source_file=source_file,
    )


def run_tool_call(
    ctx: FinancialContext,
    tool_name: str,
    arguments_json: str,
) -> str:
    """Execute tool and return JSON string for OpenAI tool message."""
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError:
        args = {}
    result = execute_tool(ctx, tool_name, args)
    return json.dumps(result, default=str)
