"""Prophet-based monthly forecasting for revenue and opex."""

from __future__ import annotations

import logging
from typing import Any, Literal

import pandas as pd

from schemas.forecast import ForecastPayload, ForecastPoint

ForecastMetric = Literal["revenue", "opex"]

MIN_MONTHS = 3
RECOMMENDED_MONTHS = 6

logger = logging.getLogger(__name__)


class ForecastError(Exception):
    """Raised when forecasting cannot run."""


def _suppress_prophet_logs() -> None:
    for name in ("cmdstanpy", "prophet", "matplotlib"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _month_label(ts: pd.Timestamp) -> str:
    return ts.strftime("%b %Y")


def _build_prophet_frame(monthly: pd.DataFrame, column: str) -> pd.DataFrame:
    frame = monthly.sort_values("month")[["month", column]].copy()
    frame = frame.rename(columns={"month": "ds", column: "y"})
    frame["ds"] = pd.to_datetime(frame["ds"])
    frame["y"] = frame["y"].astype(float)
    return frame.dropna()


def forecast_series(
    monthly: pd.DataFrame,
    metric: ForecastMetric,
    horizon_months: int,
) -> ForecastPayload:
    """
    Fit Prophet on monthly series and project forward with confidence intervals.
    """
    if metric not in ("revenue", "opex"):
        raise ForecastError(f"Unsupported metric: {metric}")

    if horizon_months not in (3, 12):
        raise ForecastError("horizon_months must be 3 (quarter) or 12 (year)")

    if metric == "opex" and float(monthly["opex"].sum()) <= 0:
        raise ForecastError("No operating expense data to forecast.")

    train = _build_prophet_frame(monthly, metric)
    if len(train) < MIN_MONTHS:
        raise ForecastError(
            f"Need at least {MIN_MONTHS} months of data to forecast; got {len(train)}."
        )

    warnings: list[str] = []
    if len(train) < RECOMMENDED_MONTHS:
        warnings.append(
            f"Only {len(train)} months of history — forecast uncertainty is high. "
            f"{RECOMMENDED_MONTHS}+ months recommended."
        )

    try:
        from prophet import Prophet
    except ImportError as exc:
        raise ForecastError(
            "Prophet is not installed. Run: pip install prophet"
        ) from exc

    _suppress_prophet_logs()

    use_yearly = len(train) >= 18
    model = Prophet(
        yearly_seasonality=use_yearly,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.8,
    )
    model.fit(train)

    future = model.make_future_dataframe(periods=horizon_months, freq="MS")
    pred = model.predict(future)

    last_hist = pd.to_datetime(train["ds"].max())
    hist_rows = pred[pred["ds"] <= last_hist]
    future_rows = pred[pred["ds"] > last_hist].head(horizon_months)

    history: list[ForecastPoint] = []
    for _, row in hist_rows.iterrows():
        actual = train.loc[train["ds"] == row["ds"], "y"]
        val = float(actual.iloc[0]) if len(actual) else float(row["yhat"])
        history.append(
            ForecastPoint(
                month=_month_label(row["ds"]),
                value=round(val, 2),
                lower=round(float(row["yhat_lower"]), 2),
                upper=round(float(row["yhat_upper"]), 2),
            )
        )

    forecast: list[ForecastPoint] = []
    for _, row in future_rows.iterrows():
        forecast.append(
            ForecastPoint(
                month=_month_label(row["ds"]),
                value=round(max(0.0, float(row["yhat"])), 2),
                lower=round(max(0.0, float(row["yhat_lower"])), 2),
                upper=round(max(0.0, float(row["yhat_upper"])), 2),
            )
        )

    if not forecast:
        raise ForecastError("Model produced no future periods.")

    values = [p.value for p in forecast]
    summary: dict[str, Any] = {
        "metric": metric,
        "horizon_months": horizon_months,
        "last_actual_month": history[-1].month if history else None,
        "last_actual_value": history[-1].value if history else None,
        "first_forecast_month": forecast[0].month,
        "last_forecast_month": forecast[-1].month,
        "forecast_total": round(sum(values), 2),
        "forecast_avg_monthly": round(sum(values) / len(values), 2),
        "forecast_end_value": forecast[-1].value,
        "confidence_level": "80%",
    }

    return ForecastPayload(
        metric=metric,
        horizon_months=horizon_months,
        history=history,
        forecast=forecast,
        summary=summary,
        warnings=warnings,
    )


def forecast_to_context_dict(payload: ForecastPayload) -> dict[str, Any]:
    """JSON-safe dict for LLM and export."""
    return payload.model_dump()
