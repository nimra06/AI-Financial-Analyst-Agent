"""Plain-language explanation of detected anomalies."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from llm.summarize import SummaryError, _resolve_api_key

DEFAULT_MODEL = "gpt-4o-mini"


class AnomalyExplanation(BaseModel):
    summary: str = Field(description="2-3 sentence overview for executives")
    highlights: list[str] = Field(description="Bullets citing specific months and metrics")
    suggested_actions: list[str] = Field(description="Practical follow-ups, not investment advice")


class AnomalyExplainError(Exception):
    pass


SYSTEM_PROMPT = """You explain financial anomaly alerts to business users.

RULES:
1. Use ONLY facts from the JSON (flags, summary, methods).
2. Reference month, metric, method, and values from flags.
3. Explain what z_score, iqr, mom_change, and isolation_forest mean in plain language when cited.
4. No investment advice. Analysis/demo only.
5. If no flags, say the period looks statistically typical."""

USER_TEMPLATE = """Explain these anomaly detection results.

{context_json}
"""


def explain_anomalies(
    report_context: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> AnomalyExplanation:
    try:
        key = _resolve_api_key(api_key)
    except SummaryError as exc:
        raise AnomalyExplainError(str(exc)) from exc

    client = OpenAI(api_key=key)
    try:
        completion = client.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_TEMPLATE.format(
                        context_json=json.dumps(report_context, indent=2, default=str)
                    ),
                },
            ],
            response_format=AnomalyExplanation,
        )
    except Exception as exc:  # noqa: BLE001
        raise AnomalyExplainError(f"OpenAI request failed: {exc}") from exc

    message = completion.choices[0].message
    if message.parsed is not None:
        return message.parsed
    if message.refusal:
        raise AnomalyExplainError(f"Model refused: {message.refusal}")
    raise AnomalyExplainError("No explanation returned.")
