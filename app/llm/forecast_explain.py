"""Explain Prophet forecasts using structured OpenAI output."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from schemas.forecast import ForecastExplanation

from llm.summarize import SummaryError, _resolve_api_key

DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You explain financial forecasts to executives.

RULES:
1. Use ONLY numbers from the user JSON (summary and forecast points).
2. Do NOT invent figures or months.
3. Mention uncertainty — these are model projections with confidence intervals.
4. Note warnings in the payload if present.
5. No investment advice. Demo/analysis only.

Output: outlook (short paragraph), key_figures (bullets with numbers), risks_and_caveats (bullets)."""

USER_TEMPLATE = """Explain this Prophet forecast for business readers.

{context_json}
"""


class ForecastExplainError(Exception):
    pass


def explain_forecast(
    forecast_context: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> ForecastExplanation:
    try:
        key = _resolve_api_key(api_key)
    except SummaryError as exc:
        raise ForecastExplainError(str(exc)) from exc

    client = OpenAI(api_key=key)
    user_content = USER_TEMPLATE.format(
        context_json=json.dumps(forecast_context, indent=2, default=str)
    )

    try:
        completion = client.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=ForecastExplanation,
        )
    except Exception as exc:  # noqa: BLE001
        raise ForecastExplainError(f"OpenAI request failed: {exc}") from exc

    message = completion.choices[0].message
    if message.parsed is not None:
        return message.parsed
    if message.refusal:
        raise ForecastExplainError(f"Model refused: {message.refusal}")
    raise ForecastExplainError("No explanation returned from the model.")
