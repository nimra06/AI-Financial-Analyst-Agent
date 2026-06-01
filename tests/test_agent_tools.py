"""Tests for agent tools (no OpenAI)."""

from pathlib import Path

import pytest

from analytics.ingest import load_and_clean
from analytics.kpis import compute_kpis
from analytics.snapshot import build_metrics_snapshot
from llm.agent_tools import (
    execute_tool,
    tool_compare_months,
    tool_get_kpi,
    tool_list_anomalies,
)
from llm.chat import build_context
from llm.context import FinancialContext
from schemas.financial import ValidationResult

SAMPLE = Path(__file__).resolve().parent.parent / "datasets" / "sample"


@pytest.fixture
def retail_ctx() -> FinancialContext:
    path = SAMPLE / "retail_monthly_pl.csv"
    result = load_and_clean(path.read_bytes(), path.name)
    assert not isinstance(result, ValidationResult)
    kpis = compute_kpis(result.monthly, result.categories)
    snapshot = build_metrics_snapshot(kpis, source_file=path.name)
    return build_context(
        result.monthly,
        kpis,
        snapshot,
        categories=result.categories,
        source_file=path.name,
    )


def test_get_kpi_latest_revenue(retail_ctx: FinancialContext) -> None:
    out = tool_get_kpi(retail_ctx, "latest_revenue")
    assert out["metric"] == "latest_revenue"
    assert out["value"] > 0
    assert "latest_revenue" in retail_ctx.sources_log[0]


def test_compare_months(retail_ctx: FinancialContext) -> None:
    months = retail_ctx.kpis.monthly_records
    a, b = months[0]["month"], months[-1]["month"]
    out = tool_compare_months(retail_ctx, a, b)
    assert "month_a" in out
    assert "revenue_change_pct" in out


def test_list_anomalies(retail_ctx: FinancialContext) -> None:
    out = tool_list_anomalies(retail_ctx)
    assert "flags" in out
    assert "summary" in out
    assert isinstance(out["flags"], list)


def test_execute_unknown_tool(retail_ctx: FinancialContext) -> None:
    out = execute_tool(retail_ctx, "unknown_tool", {})
    assert "error" in out


def test_suggest_chart_sets_pending(retail_ctx: FinancialContext) -> None:
    execute_tool(retail_ctx, "suggest_chart", {"chart_type": "revenue"})
    assert retail_ctx.pending_chart == "revenue"
