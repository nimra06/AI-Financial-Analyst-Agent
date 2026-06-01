"""Detect upload shape and analyze non-P&L files (e.g. Upwork lifetime billed)."""

from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd

DATE_ALIASES = ["date", "period", "month", "transaction_date", "reporting_period"]
PL_METRIC_ALIASES = [
    "revenue",
    "sales",
    "income",
    "cogs",
    "opex",
    "operating_expenses",
    "budget_revenue",
]
FREELANCE_CLIENT_ALIASES = [
    "client",
    "customer",
    "company",
    "employer",
    "account",
    "buyer",
]
FREELANCE_AMOUNT_ALIASES = [
    "total_billed",
    "total_billed_amount",
    "billed",
    "lifetime_billed",
    "lifetime",
    "earnings",
    "total_earnings",
    "amount",
    "revenue",
    "income",
    "total",
    "gross",
]


def _column_map(df: pd.DataFrame) -> dict[str, str]:
    return {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}


def _find_column(lower_map: dict[str, str], aliases: list[str]) -> Optional[str]:
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    return None


def _parse_numeric_series(series: pd.Series) -> pd.Series:
    def clean_cell(val: object) -> object:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        s = str(val).strip()
        if not s or s.lower() in {"nan", "none", "-"}:
            return None
        negative = s.startswith("(") and s.endswith(")")
        s = s.strip("()")
        s = re.sub(r"[$€£,\s]", "", s)
        if not s:
            return None
        try:
            num = float(s)
            return -num if negative else num
        except ValueError:
            return None

    return pd.Series([clean_cell(v) for v in series], index=series.index, dtype=float)


def _has_alias(lower: dict[str, str], aliases: list[str]) -> bool:
    return any(a in lower for a in aliases)


def detect_upload_format(df: pd.DataFrame) -> str:
    """
    Returns: monthly_pl | freelance_client_billing | unknown
    """
    lower = _column_map(df)

    if _has_alias(lower, DATE_ALIASES) and _has_alias(lower, PL_METRIC_ALIASES):
        return "monthly_pl"

    client_col = _find_column(lower, FREELANCE_CLIENT_ALIASES)
    amount_col = _find_column(lower, FREELANCE_AMOUNT_ALIASES)
    if client_col and amount_col and not _has_alias(lower, DATE_ALIASES):
        return "freelance_client_billing"

    if client_col and amount_col:
        return "freelance_client_billing"

    return "unknown"


def analyze_freelance_client_billing(df: pd.DataFrame) -> dict[str, Any]:
    """Summarize client + lifetime billing exports (Upwork-style)."""
    lower = _column_map(df)
    client_key = _find_column(lower, FREELANCE_CLIENT_ALIASES)
    amount_key = _find_column(lower, FREELANCE_AMOUNT_ALIASES)
    if not client_key or not amount_key:
        return {"insights": [], "clients": []}

    work = df[[client_key, amount_key]].copy()
    work.columns = ["client", "amount"]
    work["client"] = work["client"].astype(str).str.strip()
    work["amount"] = _parse_numeric_series(work["amount"])
    work = work.dropna(subset=["client"])
    work = work[work["client"].str.lower().isin({"", "nan", "none"}) == False]  # noqa: E712
    work = work.dropna(subset=["amount"])
    work = work[work["amount"] > 0]

    if work.empty:
        return {
            "insights": ["No billable client rows found after parsing amounts."],
            "clients": [],
            "total_lifetime": 0,
            "client_count": 0,
        }

    work = work.sort_values("amount", ascending=False).reset_index(drop=True)
    total = float(work["amount"].sum())
    n = len(work)
    top = work.head(5)
    top3_share = float(work.head(3)["amount"].sum() / total * 100) if total > 0 else 0
    median = float(work["amount"].median())
    good = work[work["amount"] >= median].head(8)

    insights: list[str] = [
        f"This file looks like lifetime client billing ({n} clients), not monthly P&L.",
        f"Lifetime total in this export: ${total:,.2f}.",
        f"Top client: {top.iloc[0]['client']} (${float(top.iloc[0]['amount']):,.2f}, "
        f"{float(top.iloc[0]['amount']) / total * 100:.1f}% of total).",
    ]

    if n >= 3:
        insights.append(
            f"Your top 3 clients are {top3_share:.0f}% of lifetime billing — "
            + (
                "high concentration; diversifying clients reduces risk."
                if top3_share >= 60
                else "a reasonably balanced mix."
            )
        )

    good_names = ", ".join(good["client"].tolist()[:5])
    insights.append(f"Strong clients to prioritize: {good_names}.")

    insights.append(
        "Month-over-month trends (e.g. earned more this month) need a dated export "
        "(monthly P&L or transactions). Use Data → template_monthly_pl.csv for the full dashboard."
    )

    clients = [
        {
            "client": row["client"],
            "amount": round(float(row["amount"]), 2),
            "share_pct": round(float(row["amount"]) / total * 100, 1) if total else 0,
        }
        for _, row in work.iterrows()
    ]

    return {
        "insights": insights,
        "clients": clients,
        "total_lifetime": round(total, 2),
        "client_count": n,
        "top_clients": clients[:5],
    }


def build_wrong_format_validation(
    df: pd.DataFrame,
    *,
    filename: str = "",
) -> tuple[list[str], list[str], str, Optional[dict[str, Any]]]:
    """
    User-facing errors, warnings, detected_format, optional freelance_summary.
    """
    fmt = detect_upload_format(df)
    headers = ", ".join(str(c) for c in df.columns[:8])
    if len(df.columns) > 8:
        headers += ", …"

    if fmt == "freelance_client_billing":
        summary = analyze_freelance_client_billing(df)
        errors = [
            "This file doesn't look like monthly financial P&L data.",
            "It appears to be a per-client billing list (e.g. Upwork lifetime billed).",
            "The full dashboard needs columns like: date, revenue, cogs, opex.",
        ]
        warnings = [
            f"Detected columns: {headers}",
            "See insights below from your client billing data.",
        ]
        if filename:
            warnings.append(f"File: {filename}")
        return errors, warnings, fmt, summary

    errors = [
        "This doesn't look like financial P&L data we can analyze in the dashboard.",
        "Expected a monthly file with at least: date and revenue (or category + amount).",
    ]
    warnings = [
        f"Detected columns: {headers}",
        "Download template_monthly_pl.csv under Data and match that layout.",
    ]
    if fmt == "unknown" and re.search(r"client|billed|upwork|freelance", filename, re.I):
        warnings.append(
            "Tip: platform earnings exports often need to be pivoted or joined with dates "
            "before upload."
        )
    return errors, warnings, fmt, None
