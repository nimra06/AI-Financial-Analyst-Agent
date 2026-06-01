"""Anomaly detection: z-score, IQR, MoM spikes, and Isolation Forest."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from schemas.anomaly import AnomalyFlag, AnomalyReport, AnomalySeverity

Z_THRESHOLD = 2.0
IQR_MULTIPLIER = 1.5
MOM_OPEX_THRESHOLD_PCT = 30.0
MIN_ROWS_STATS = 3
MIN_ROWS_IFOREST = 8

_SERIES_METRICS = [
    ("revenue", "revenue"),
    ("net_profit", "net profit"),
    ("gross_profit", "gross profit"),
    ("opex", "operating expenses"),
    ("gross_margin_pct", "gross margin %"),
]

_IQR_METRICS = [
    ("revenue", "revenue"),
    ("opex", "operating expenses"),
    ("net_profit", "net profit"),
]


def _month_label(ts: pd.Timestamp) -> str:
    return ts.strftime("%b %Y")


def _dedupe_key(flag: AnomalyFlag) -> tuple[str, str, str]:
    return (flag.month, flag.metric, flag.method)


def _severity_from_score(score: float, *, high_at: float = 3.0) -> AnomalySeverity:
    return "high" if abs(score) >= high_at else "medium"


def detect_zscore_anomalies(monthly: pd.DataFrame) -> list[AnomalyFlag]:
    if len(monthly) < MIN_ROWS_STATS:
        return []

    df = monthly.sort_values("month").copy()
    flags: list[AnomalyFlag] = []

    for column, label in _SERIES_METRICS:
        if column not in df.columns:
            continue
        series = df[column].astype(float)
        std = float(series.std())
        if std == 0 or np.isnan(std):
            continue
        mean = float(series.mean())
        for idx, val in series.items():
            z = (float(val) - mean) / std
            if abs(z) < Z_THRESHOLD:
                continue
            direction = "high" if z > 0 else "low"
            flags.append(
                AnomalyFlag(
                    month=_month_label(df.loc[idx, "month"]),
                    metric=label,
                    value=round(float(val), 2),
                    method="z_score",
                    severity=_severity_from_score(z),
                    score=round(float(z), 2),
                    direction=direction,
                    description=f"Z-score {z:.2f}: unusually {direction} {label} vs period mean",
                )
            )
    return flags


def detect_iqr_anomalies(monthly: pd.DataFrame) -> list[AnomalyFlag]:
    if len(monthly) < MIN_ROWS_STATS:
        return []

    df = monthly.sort_values("month").copy()
    flags: list[AnomalyFlag] = []

    for column, label in _IQR_METRICS:
        series = df[column].astype(float)
        q1, q3 = float(series.quantile(0.25)), float(series.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - IQR_MULTIPLIER * iqr, q3 + IQR_MULTIPLIER * iqr
        for idx, val in series.items():
            v = float(val)
            if lower <= v <= upper:
                continue
            direction = "high" if v > upper else "low"
            bound = upper if v > upper else lower
            distance = abs(v - bound) / iqr if iqr else 0
            flags.append(
                AnomalyFlag(
                    month=_month_label(df.loc[idx, "month"]),
                    metric=label,
                    value=round(v, 2),
                    method="iqr",
                    severity="high" if distance > 1 else "medium",
                    score=round(distance, 2),
                    direction=direction,
                    description=f"IQR outlier: {label} outside typical range [{lower:,.0f}, {upper:,.0f}]",
                )
            )
    return flags


def detect_mom_opex_spikes(monthly: pd.DataFrame) -> list[AnomalyFlag]:
    if len(monthly) < 2:
        return []

    df = monthly.sort_values("month").copy()
    opex = df["opex"].astype(float)
    mom_pct = opex.pct_change() * 100
    flags: list[AnomalyFlag] = []

    changes = mom_pct.dropna()
    if changes.empty:
        return flags

    std_chg = float(changes.std()) if len(changes) > 1 else 0.0
    for idx, pct in mom_pct.items():
        if pd.isna(pct) or pct < MOM_OPEX_THRESHOLD_PCT:
            continue
        if std_chg > 0 and pct < std_chg * 2:
            continue
        row = df.loc[idx]
        flags.append(
            AnomalyFlag(
                month=_month_label(row["month"]),
                metric="operating expenses",
                value=round(float(row["opex"]), 2),
                method="mom_change",
                severity="high" if pct >= MOM_OPEX_THRESHOLD_PCT * 1.5 else "medium",
                score=round(float(pct), 2),
                direction="high",
                description=f"Opex jumped {pct:.1f}% month-over-month",
            )
        )
    return flags


def detect_isolation_forest_anomalies(monthly: pd.DataFrame) -> list[AnomalyFlag]:
    if len(monthly) < MIN_ROWS_IFOREST:
        return []

    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return []

    df = monthly.sort_values("month").copy()
    features = df[
        ["revenue", "gross_profit", "net_profit", "opex", "gross_margin_pct"]
    ].astype(float)
    model = IsolationForest(
        n_estimators=100,
        contamination=min(0.2, max(0.05, 2 / len(df))),
        random_state=42,
    )
    preds = model.fit_predict(features)
    scores = model.decision_function(features)

    flags: list[AnomalyFlag] = []
    for i, (idx, pred) in enumerate(zip(df.index, preds, strict=True)):
        if pred != -1:
            continue
        row = df.loc[idx]
        score = float(scores[i])
        flags.append(
            AnomalyFlag(
                month=_month_label(row["month"]),
                metric="multivariate pattern",
                value=round(float(row["revenue"]), 2),
                method="isolation_forest",
                severity="high" if score < -0.2 else "medium",
                score=round(score, 3),
                direction="low",
                description=(
                    "Multivariate outlier: combined revenue, profit, and opex pattern "
                    "differs from typical months"
                ),
            )
        )
    return flags


def _merge_flags(*groups: list[AnomalyFlag]) -> list[AnomalyFlag]:
    seen: set[tuple[str, str, str]] = set()
    merged: list[AnomalyFlag] = []
    for group in groups:
        for flag in group:
            key = _dedupe_key(flag)
            if key in seen:
                continue
            seen.add(key)
            merged.append(flag)
    return sorted(merged, key=lambda f: (f.month, f.metric))


def detect_all_anomalies(
    monthly: pd.DataFrame,
    categories: Optional[pd.DataFrame] = None,
) -> AnomalyReport:
    """
    Run all detectors and return a unified report for UI and chat tools.
    """
    warnings: list[str] = []
    if len(monthly) < MIN_ROWS_STATS:
        return AnomalyReport(
            flags=[],
            summary={"count": 0},
            warnings=["Need at least 3 months of data for anomaly detection."],
        )

    z_flags = detect_zscore_anomalies(monthly)
    iqr_flags = detect_iqr_anomalies(monthly)
    mom_flags = detect_mom_opex_spikes(monthly)
    if_flags = detect_isolation_forest_anomalies(monthly)

    if len(monthly) < MIN_ROWS_IFOREST:
        warnings.append(
            f"Isolation Forest skipped — need {MIN_ROWS_IFOREST}+ months (have {len(monthly)})."
        )

    flags = _merge_flags(z_flags, iqr_flags, mom_flags, if_flags)

    by_method: dict[str, int] = {}
    for f in flags:
        by_method[f.method] = by_method.get(f.method, 0) + 1

    summary = {
        "count": len(flags),
        "by_method": by_method,
        "high_severity": sum(1 for f in flags if f.severity == "high"),
        "months_flagged": len({f.month for f in flags}),
    }

    return AnomalyReport(flags=flags, summary=summary, warnings=warnings)


def detect_monthly_anomalies(monthly: pd.DataFrame) -> list[dict[str, Any]]:
    """Backward-compatible API for chat tools (Step 3)."""
    report = detect_all_anomalies(monthly)
    return [f.model_dump() for f in report.flags]


def report_to_context_dict(report: AnomalyReport) -> dict[str, Any]:
    return report.model_dump()


def chart_anomaly_months(report: AnomalyReport, chart: str) -> set[str]:
    """Months to mark on a given dashboard chart."""
    mapping = {
        "revenue": {"revenue"},
        "profit": {"net profit", "gross profit", "multivariate pattern"},
        "opex": {"operating expenses"},
        "trends": {"revenue", "gross margin %", "multivariate pattern"},
    }
    metrics = mapping.get(chart, set())
    return {f.month for f in report.flags if f.metric in metrics or f.method == "isolation_forest"}
