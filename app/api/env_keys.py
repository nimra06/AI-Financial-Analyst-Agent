"""Environment variable helpers for deployment (Railway, local .env)."""

from __future__ import annotations

import os


def resolve_openai_api_key() -> str:
    direct = os.environ.get("OPENAI_API_KEY", "").strip()
    if direct:
        return direct
    for name, val in os.environ.items():
        if name.strip().upper() == "OPENAI_API_KEY" and val and val.strip():
            return val.strip()
    return ""
