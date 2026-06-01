"""General-purpose chat when no monthly P&L dataset is loaded."""

from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI
from schemas.chat import ChatResult, ChatTurn

from llm.summarize import SummaryError, _resolve_api_key

DEFAULT_MODEL = "gpt-4o-mini"

ADVISORY_BASE = """You are FinAnalyst AI — a friendly financial analyst assistant in a demo FP&A app.

{context}

RULES:
- Be warm, clear, and concise (short paragraphs, not walls of text).
- No investment, tax, or legal advice. Say this is demo analysis only.
- Do not invent dollar amounts unless they appear in the context below.
- If the user asks about monthly trends but only has lifetime client data, explain they need a dated export.
- Suggest uploading template_monthly_pl.csv (date + revenue columns) for full dashboards and charts.
"""


def _freelance_context_block(summary: dict[str, Any]) -> str:
    top = summary.get("top_clients") or summary.get("clients", [])[:8]
    lines = [
        "The user uploaded a CLIENT BILLING file (e.g. Upwork lifetime billed), NOT monthly P&L.",
        f"Lifetime total: ${summary.get('total_lifetime', 0):,.2f} across {summary.get('client_count', 0)} clients.",
    ]
    if top:
        lines.append("Top clients by lifetime billing:")
        for row in top[:8]:
            lines.append(
                f"  - {row.get('client')}: ${row.get('amount', 0):,.2f} ({row.get('share_pct', 0)}% of total)"
            )
    insights = summary.get("insights") or []
    if insights:
        lines.append("Key points: " + " ".join(insights[:4]))
    return "\n".join(lines)


def run_advisory_chat(
    user_message: str,
    *,
    history: Optional[list[ChatTurn]] = None,
    freelance_summary: Optional[dict[str, Any]] = None,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> ChatResult:
    """Chat without tool access — general help or freelance billing context."""
    try:
        key = _resolve_api_key(api_key)
    except SummaryError as exc:
        from llm.chat import ChatError

        raise ChatError(str(exc)) from exc

    if freelance_summary:
        context = _freelance_context_block(freelance_summary)
    else:
        context = (
            "No monthly P&L dataset is loaded yet. "
            "Help the user understand what to upload, how the app works, and general freelance/FP&A concepts. "
            "Do not claim to see their numbers."
        )

    system = ADVISORY_BASE.format(context=context)
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for turn in history or []:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except Exception as exc:  # noqa: BLE001
        from llm.chat import ChatError

        raise ChatError(f"OpenAI request failed: {exc}") from exc

    answer = (response.choices[0].message.content or "").strip()
    sources = []
    if freelance_summary:
        sources = ["freelance_billing_export"]
    return ChatResult(answer=answer, sources=sources, chart=None)
