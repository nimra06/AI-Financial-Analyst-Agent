"""Simple in-memory rate limiter for LLM endpoints."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException


class RateLimiter:
    """Fixed-window rate limit keyed by client identifier."""

    def __init__(self, max_calls: int, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        if self.max_calls <= 0:
            return
        now = time.time()
        window_start = now - self.window_seconds
        recent = [t for t in self._hits[key] if t >= window_start]
        if len(recent) >= self.max_calls:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded ({self.max_calls} requests per "
                    f"{self.window_seconds}s). Try again shortly."
                ),
            )
        recent.append(now)
        self._hits[key] = recent
