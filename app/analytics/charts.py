"""Plotly chart builders with a consistent theme."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from schemas.forecast import ForecastPayload

ANOMALY_MARKER = dict(size=14, color="#ef4444", symbol="diamond", line=dict(width=1, color="#fca5a5"))

CHART_COLORS = {
    "revenue": "#3b82f6",
    "profit": "#10b981",
    "gross": "#8b5cf6",
    "opex": "#f59e0b",
    "grid": "rgba(148, 163, 184, 0.15)",
    "paper": "#0f172a",
    "plot": "#1e293b",
    "text": "#e2e8f0",
}


def _apply_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CHART_COLORS["paper"],
        plot_bgcolor=CHART_COLORS["plot"],
        font=dict(color=CHART_COLORS["text"], family="Inter, system-ui, sans-serif"),
        margin=dict(l=40, r=24, t=48, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor=CHART_COLORS["grid"], zerolinecolor=CHART_COLORS["grid"])
    fig.update_yaxes(gridcolor=CHART_COLORS["grid"], zerolinecolor=CHART_COLORS["grid"])
    return fig


def _month_labels(monthly: pd.DataFrame) -> list[str]:
    return [ts.strftime("%b %Y") for ts in monthly["month"]]


def _add_anomaly_markers(
    fig: go.Figure,
    labels: list[str],
    monthly: pd.DataFrame,
    anomaly_months: Optional[set[str]],
    value_col: str,
    *,
    legend: bool = True,
) -> None:
    if not anomaly_months:
        return
    xs, ys = [], []
    for i, label in enumerate(labels):
        if label in anomaly_months:
            xs.append(label)
            ys.append(float(monthly.iloc[i][value_col]))
    if not xs:
        return
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            name="Anomaly",
            marker=ANOMALY_MARKER,
            showlegend=legend,
        )
    )


def revenue_chart(
    monthly: pd.DataFrame,
    anomaly_months: Optional[set[str]] = None,
) -> go.Figure:
    labels = _month_labels(monthly)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=monthly["revenue"],
            name="Revenue",
            marker_color=CHART_COLORS["revenue"],
        )
    )
    _add_anomaly_markers(fig, labels, monthly, anomaly_months, "revenue")
    title = "Monthly revenue"
    if anomaly_months:
        title += " (◆ = anomaly)"
    fig.update_layout(title=title, yaxis_title="USD")
    return _apply_theme(fig)


def profit_chart(
    monthly: pd.DataFrame,
    anomaly_months: Optional[set[str]] = None,
) -> go.Figure:
    labels = _month_labels(monthly)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=monthly["gross_profit"],
            name="Gross profit",
            mode="lines+markers",
            line=dict(color=CHART_COLORS["gross"], width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=monthly["net_profit"],
            name="Net profit",
            mode="lines+markers",
            line=dict(color=CHART_COLORS["profit"], width=2),
        )
    )
    _add_anomaly_markers(
        fig, labels, monthly, anomaly_months, "net_profit", legend=not anomaly_months
    )
    title = "Gross & net profit"
    if anomaly_months:
        title += " (◆ = anomaly)"
    fig.update_layout(title=title, yaxis_title="USD")
    return _apply_theme(fig)


def top_expenses_chart(
    categories: Optional[pd.DataFrame],
    monthly: pd.DataFrame,
    anomaly_months: Optional[set[str]] = None,
) -> go.Figure:
    fig = go.Figure()
    if categories is not None and not categories.empty:
        grouped = (
            categories.groupby("category", as_index=False)["expense"]
            .sum()
            .sort_values("expense", ascending=True)
            .tail(10)
        )
        fig.add_trace(
            go.Bar(
                x=grouped["expense"],
                y=grouped["category"],
                orientation="h",
                marker_color=CHART_COLORS["opex"],
                name="Expense",
            )
        )
        fig.update_layout(title="Top expense categories (all periods)", xaxis_title="USD")
    else:
        labels = _month_labels(monthly)
        fig.add_trace(
            go.Bar(
                x=labels,
                y=monthly["opex"],
                name="Operating expenses",
                marker_color=CHART_COLORS["opex"],
            )
        )
        _add_anomaly_markers(fig, labels, monthly, anomaly_months, "opex")
        title = "Monthly operating expenses"
        if anomaly_months:
            title += " (◆ = anomaly)"
        fig.update_layout(title=title, yaxis_title="USD")
    return _apply_theme(fig)


def trends_chart(
    monthly: pd.DataFrame,
    anomaly_months: Optional[set[str]] = None,
) -> go.Figure:
    labels = _month_labels(monthly)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=monthly["revenue"],
            name="Revenue",
            mode="lines+markers",
            line=dict(color=CHART_COLORS["revenue"], width=2),
        ),
        secondary_y=False,
    )
    margin = monthly["gross_margin_pct"]
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=margin,
            name="Gross margin %",
            mode="lines+markers",
            line=dict(color=CHART_COLORS["gross"], width=2, dash="dot"),
        ),
        secondary_y=True,
    )
    _add_anomaly_markers(
        fig, labels, monthly, anomaly_months, "revenue", legend=not anomaly_months
    )
    title = "Revenue vs gross margin %"
    if anomaly_months:
        title += " (◆ = anomaly)"
    fig.update_layout(title=title)
    fig.update_yaxes(title_text="Revenue (USD)", secondary_y=False)
    fig.update_yaxes(title_text="Margin %", secondary_y=True)
    return _apply_theme(fig)


def forecast_chart(payload: ForecastPayload) -> go.Figure:
    """Historical actuals + Prophet forecast with confidence band."""
    metric = payload.metric
    color = CHART_COLORS.get(metric, CHART_COLORS["revenue"])
    hist_months = [p.month for p in payload.history]
    hist_vals = [p.value for p in payload.history]
    fc_months = [p.month for p in payload.forecast]
    fc_vals = [p.value for p in payload.forecast]
    fc_lower = [p.lower for p in payload.forecast]
    fc_upper = [p.upper for p in payload.forecast]

    # Connect last actual to first forecast for a continuous line
    bridge_x = [hist_months[-1], fc_months[0]] if hist_months and fc_months else fc_months
    bridge_y = [hist_vals[-1], fc_vals[0]] if hist_vals and fc_vals else fc_vals

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hist_months,
            y=hist_vals,
            name="Actual",
            mode="lines+markers",
            line=dict(color=color, width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=bridge_x + fc_months[1:],
            y=bridge_y + fc_vals[1:],
            name="Forecast",
            mode="lines+markers",
            line=dict(color=color, width=2, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=fc_months + fc_months[::-1],
            y=fc_upper + fc_lower[::-1],
            fill="toself",
            fillcolor="rgba(59, 130, 246, 0.2)",
            line=dict(color="rgba(0,0,0,0)"),
            name="80% interval",
            showlegend=True,
        )
    )
    title_metric = "Revenue" if metric == "revenue" else "Operating expenses"
    fig.update_layout(
        title=f"{title_metric} forecast ({payload.horizon_months} months ahead)",
        yaxis_title="USD",
        xaxis_title="Month",
    )
    return _apply_theme(fig)
