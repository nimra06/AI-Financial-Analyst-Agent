"""Tool-based financial analyst chat agent."""

from __future__ import annotations

import os
from typing import Any, Optional

import pandas as pd
from openai import OpenAI
from schemas.chat import ChatResult, ChatTurn

from analytics.kpis import KpiSummary
from analytics.snapshot import build_metrics_snapshot
from llm.agent_tools import OPENAI_TOOLS, context_from_monthly_records, run_tool_call
from llm.context import FinancialContext
from llm.summarize import SummaryError, _resolve_api_key  # noqa: F401 — re-export pattern

DEFAULT_MODEL = "gpt-4o-mini"
MAX_TOOL_ROUNDS = 8

CHAT_SYSTEM_PROMPT = """You are an AI financial analyst with access to tools over pre-computed data.

The user's financial dataset is ALREADY LOADED in this session. Never ask them to upload a file or document.
If they greet you or ask a general question, answer using tools on the loaded data (start with get_kpi).

RULES:
1. ALWAYS use tools to look up numbers before stating facts. Do not guess.
2. Only cite figures returned by tools or present in tool JSON.
3. Keep answers concise (2-6 sentences) unless the user asks for detail.
4. When comparing periods, call compare_months or get_kpi.
5. For "why did X drop" questions: compare relevant months, check anomalies, check expenses.
6. End with a line: Sources: <comma-separated list of metrics/periods you used>
7. Call suggest_chart when a visual would help (revenue|profit|expenses|trends|none).
8. No investment advice. Analysis/demo only.

Dataset source: {source_file}
Latest period in data: {latest_month}
Periods in dataset: {period_count}
"""


class ChatError(Exception):
    """Raised when chat fails."""


def build_context(
    monthly: pd.DataFrame,
    kpis: KpiSummary,
    snapshot: dict[str, Any],
    *,
    categories: Optional[pd.DataFrame] = None,
    source_file: str = "upload",
) -> FinancialContext:
    return FinancialContext(
        monthly=monthly,
        categories=categories,
        kpis=kpis,
        snapshot=snapshot,
        source_file=source_file,
    )


def _parse_sources_from_answer(answer: str, ctx: FinancialContext) -> tuple[str, list[str]]:
    """Extract Sources: line; merge with tool log."""
    sources = list(ctx.sources_log)
    lines = answer.strip().split("\n")
    body_lines: list[str] = []
    for line in lines:
        lower = line.strip().lower()
        if lower.startswith("sources:"):
            inline = line.split(":", 1)[-1].strip()
            if inline:
                for part in inline.split(","):
                    label = part.strip()
                    if label and label not in sources:
                        sources.append(label)
        else:
            body_lines.append(line)
    return "\n".join(body_lines).strip(), sources


def run_chat(
    user_message: str,
    ctx: FinancialContext,
    *,
    history: Optional[list[ChatTurn]] = None,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> ChatResult:
    """Run agent loop with OpenAI tool calling."""
    try:
        key = _resolve_api_key(api_key)
    except SummaryError as exc:
        raise ChatError(str(exc)) from exc
    ctx.clear_sources()
    ctx.pending_chart = None

    metrics = ctx.kpis.to_snapshot_dict()
    system = CHAT_SYSTEM_PROMPT.format(
        source_file=ctx.source_file,
        latest_month=metrics.get("latest_month", "unknown"),
        period_count=len(ctx.monthly),
    )

    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for turn in history or []:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=key)

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
            )
        except Exception as exc:  # noqa: BLE001
            raise ChatError(f"OpenAI request failed: {exc}") from exc

        msg = response.choices[0].message
        if msg.tool_calls:
            messages.append(msg.model_dump(exclude_none=True))
            for call in msg.tool_calls:
                tool_output = run_tool_call(ctx, call.function.name, call.function.arguments or "{}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": tool_output,
                    }
                )
            continue

        answer = msg.content or ""
        answer, sources = _parse_sources_from_answer(answer, ctx)
        chart = ctx.pending_chart if ctx.pending_chart and ctx.pending_chart != "none" else None
        return ChatResult(answer=answer, sources=sources, chart=chart)  # type: ignore[arg-type]

    raise ChatError("Too many tool call rounds; try a simpler question.")


def run_chat_from_snapshot_payload(
    message: str,
    monthly_records: list[dict[str, Any]],
    *,
    top_expense_categories: Optional[list[dict[str, Any]]] = None,
    source_file: str = "upload",
    history: Optional[list[ChatTurn]] = None,
    api_key: str | None = None,
) -> ChatResult:
    """Entry point for FastAPI — rebuild context from serialized records."""
    ctx = context_from_monthly_records(
        monthly_records,
        top_expense_categories=top_expense_categories or [],
        source_file=source_file,
    )
    return run_chat(message, ctx, history=history, api_key=api_key)
