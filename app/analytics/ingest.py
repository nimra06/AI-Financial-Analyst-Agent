"""Load, normalize, clean, and validate financial uploads."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import BinaryIO, Optional, Union

import pandas as pd
from pydantic import ValidationError

from analytics.format_detect import build_wrong_format_validation
from schemas.financial import FinancialRow, ValidationResult

COLUMN_ALIASES: dict[str, list[str]] = {
    "date": ["date", "period", "month", "transaction_date", "reporting_period"],
    "revenue": ["revenue", "sales", "income", "total_revenue", "net_sales"],
    "cogs": ["cogs", "cost_of_goods", "cost_of_goods_sold", "cost_of_sales", "cos"],
    "opex": ["opex", "operating_expenses", "expenses", "operating_expense", "total_opex"],
    "category": ["category", "expense_category", "cost_center", "department"],
    "amount": ["amount", "value", "expense_amount", "spend"],
    "budget_revenue": [
        "budget_revenue",
        "budget",
        "planned_revenue",
        "forecast_revenue",
        "revenue_budget",
    ],
    "budget_opex": ["budget_opex", "planned_opex", "opex_budget", "budget_expenses"],
}

REQUIRED_CANONICAL = {"date"}


@dataclass
class IngestResult:
    """Successful ingest payload."""

    monthly: pd.DataFrame
    categories: Optional[pd.DataFrame]
    raw_preview: pd.DataFrame
    validation: ValidationResult


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed: dict[str, str] = {}
    lower_map = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                renamed[lower_map[alias]] = canonical
                break

    out = df.rename(columns=renamed)
    return out


def _parse_numeric_series(series: pd.Series) -> pd.Series:
    if series.dtype.kind in "biufc":
        return pd.to_numeric(series, errors="coerce")

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


def _parse_dates(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.isna().all():
        for fmt in ("%Y-%m", "%m/%Y", "%Y/%m", "%b-%Y", "%Y-%m-%d"):
            try:
                parsed = pd.to_datetime(series, format=fmt, errors="coerce")
                if not parsed.isna().all():
                    break
            except (ValueError, TypeError):
                continue
    return parsed.dt.to_period("M").dt.to_timestamp()


def load_file(upload: Union[BinaryIO, bytes], filename: str) -> pd.DataFrame:
    """Read CSV or XLSX into a DataFrame."""
    name = (filename or "").lower()
    if isinstance(upload, bytes):
        buffer: BinaryIO = io.BytesIO(upload)
    else:
        buffer = upload

    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(buffer, engine="openpyxl")
    return pd.read_csv(buffer)


def validate_rows(df: pd.DataFrame) -> tuple[list[FinancialRow], ValidationResult]:
    errors: list[str] = []
    warnings: list[str] = []
    rows: list[FinancialRow] = []

    if "date" not in df.columns:
        errors, warnings, fmt, summary = build_wrong_format_validation(df)
        return [], ValidationResult(
            ok=False,
            errors=errors,
            warnings=warnings,
            row_count=len(df),
            detected_format=fmt,
            freelance_insights=summary.get("insights", []) if summary else [],
            freelance_summary=summary,
        )

    has_revenue = "revenue" in df.columns
    has_amount = "amount" in df.columns
    has_opex = "opex" in df.columns

    if not has_revenue and not (has_amount and "category" in df.columns):
        return [], ValidationResult(
            ok=False,
            errors=[
                "Need column 'revenue' (monthly P&L) OR 'category' + 'amount' (expense detail)"
            ],
            row_count=len(df),
        )

    def _optional_float(val: object) -> Optional[float]:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        num = float(val)
        return abs(num)

    for idx, record in df.iterrows():
        row_num = int(idx) + 2  # header is row 1
        payload = {
            "date": record.get("date"),
            "revenue": record.get("revenue", 0) if has_revenue else 0,
            "cogs": _optional_float(record.get("cogs")),
            "opex": _optional_float(record.get("opex")),
            "category": record.get("category"),
            "amount": _optional_float(record.get("amount")),
            "budget_revenue": _optional_float(record.get("budget_revenue")),
            "budget_opex": _optional_float(record.get("budget_opex")),
        }
        if pd.isna(payload["revenue"]):
            payload["revenue"] = 0
        else:
            payload["revenue"] = max(0.0, float(payload["revenue"]))
        if pd.isna(payload["date"]):
            errors.append(f"Row {row_num}: invalid or missing date")
            continue
        try:
            rows.append(FinancialRow.model_validate(payload))
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(x) for x in err["loc"])
                errors.append(f"Row {row_num} ({loc}): {err['msg']}")

    if not rows and not errors:
        errors.append("No valid rows found after parsing.")

    if rows and not has_revenue and has_amount:
        warnings.append("Using category + amount rows; monthly revenue may be zero unless merged.")

    ok = len(rows) > 0 and len(errors) == 0
    return rows, ValidationResult(
        ok=ok,
        errors=errors,
        warnings=warnings,
        row_count=len(df),
    )


def _rows_to_frames(rows: list[FinancialRow]) -> tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    records = [r.model_dump() for r in rows]
    detail = pd.DataFrame(records)
    detail["month"] = pd.to_datetime(detail["date"]).dt.to_period("M").dt.to_timestamp()

    category_mask = detail["category"].notna() & (
        detail["amount"].notna() | detail["opex"].notna()
    )
    cat_df: Optional[pd.DataFrame] = None
    if category_mask.any():
        cat_rows = detail.loc[category_mask].copy()
        cat_rows["expense"] = cat_rows["amount"].fillna(cat_rows["opex"]).fillna(0)
        cat_df = (
            cat_rows.groupby(["month", "category"], as_index=False)["expense"]
            .sum()
            .sort_values("expense", ascending=False)
        )

    agg_map: dict[str, tuple[str, str]] = {
        "revenue": ("revenue", "sum"),
        "cogs": ("cogs", "sum"),
        "opex": ("opex", "sum"),
    }
    if "budget_revenue" in detail.columns:
        agg_map["budget_revenue"] = ("budget_revenue", "sum")
    if "budget_opex" in detail.columns:
        agg_map["budget_opex"] = ("budget_opex", "sum")

    monthly = detail.groupby("month", as_index=False).agg(**agg_map).sort_values("month")

    monthly["cogs"] = monthly["cogs"].fillna(0)
    monthly["opex"] = monthly["opex"].fillna(0)
    if "budget_revenue" in monthly.columns:
        monthly["budget_revenue"] = monthly["budget_revenue"].fillna(0)
    if "budget_opex" in monthly.columns:
        monthly["budget_opex"] = monthly["budget_opex"].fillna(0)

    if cat_df is not None and monthly["revenue"].sum() == 0 and cat_df["expense"].sum() > 0:
        opex_by_month = cat_df.groupby("month", as_index=False)["expense"].sum()
        opex_by_month = opex_by_month.rename(columns={"expense": "opex"})
        monthly = monthly.drop(columns=["opex"]).merge(opex_by_month, on="month", how="outer")
        monthly["opex"] = monthly["opex"].fillna(0)
        monthly["revenue"] = monthly["revenue"].fillna(0)
        monthly["cogs"] = monthly["cogs"].fillna(0)

    monthly["gross_profit"] = monthly["revenue"] - monthly["cogs"]
    monthly["net_profit"] = monthly["gross_profit"] - monthly["opex"]
    monthly["gross_margin_pct"] = (
        (monthly["gross_profit"] / monthly["revenue"].replace(0, pd.NA)) * 100
    ).fillna(0)
    monthly["opex_ratio_pct"] = (
        (monthly["opex"] / monthly["revenue"].replace(0, pd.NA)) * 100
    ).fillna(0)

    return monthly, cat_df


def load_and_clean(upload: Union[BinaryIO, bytes], filename: str) -> IngestResult | ValidationResult:
    """
    Full pipeline: read file → normalize → clean → validate → monthly aggregates.

    Returns IngestResult on success, or ValidationResult with ok=False on failure.
    """
    try:
        raw = load_file(upload, filename)
    except Exception as exc:  # noqa: BLE001 — surface parse errors to UI
        return ValidationResult(ok=False, errors=[f"Could not read file: {exc}"])

    if raw.empty:
        return ValidationResult(ok=False, errors=["File is empty."])

    df = _normalize_columns(raw)
    preview = df.head(10).copy()

    if "date" not in df.columns:
        errors, warnings, fmt, summary = build_wrong_format_validation(
            raw, filename=filename
        )
        return ValidationResult(
            ok=False,
            errors=errors,
            warnings=warnings,
            row_count=len(raw),
            detected_format=fmt,
            freelance_insights=summary.get("insights", []) if summary else [],
            freelance_summary=summary,
        )

    df["date"] = _parse_dates(df["date"])
    for col in ("revenue", "cogs", "opex", "amount", "budget_revenue", "budget_opex"):
        if col in df.columns:
            df[col] = _parse_numeric_series(df[col])

    if "category" in df.columns:
        df["category"] = df["category"].astype(str).replace("nan", None)

    df = df.dropna(subset=["date"])
    rows, validation = validate_rows(df)
    if not validation.ok:
        validation.row_count = len(raw)
        return validation

    monthly, categories = _rows_to_frames(rows)
    if monthly.empty:
        return ValidationResult(ok=False, errors=["No monthly periods could be derived."])

    validation.ok = True
    return IngestResult(
        monthly=monthly,
        categories=categories,
        raw_preview=preview,
        validation=validation,
    )
