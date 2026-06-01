"""Generate metric-backed executive summaries via OpenAI."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from schemas.summary import ExecutiveSummary

from llm.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

DEFAULT_MODEL = "gpt-4o-mini"


class SummaryError(Exception):
    """Raised when summary generation fails."""


def _resolve_api_key(api_key: str | None) -> str:
    key = api_key or os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise SummaryError(
            "OpenAI API key not found. Set OPENAI_API_KEY in .env or enter it in the sidebar."
        )
    return key


def generate_executive_summary(
    snapshot: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> ExecutiveSummary:
    """
    Call OpenAI with structured output. `snapshot` is from build_metrics_snapshot().
    """
    key = _resolve_api_key(api_key)
    context_json = json.dumps(snapshot, indent=2, default=str)
    user_content = USER_PROMPT_TEMPLATE.format(context_json=context_json)

    client = OpenAI(api_key=key)
    try:
        completion = client.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=ExecutiveSummary,
        )
    except Exception as exc:  # noqa: BLE001
        raise SummaryError(f"OpenAI request failed: {exc}") from exc

    message = completion.choices[0].message
    if message.parsed is not None:
        return message.parsed

    if message.refusal:
        raise SummaryError(f"Model refused: {message.refusal}")

    raise SummaryError("No structured summary returned from the model.")
