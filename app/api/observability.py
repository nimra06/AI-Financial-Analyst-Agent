"""Structured logging, request metrics, and health probes."""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections import defaultdict
from threading import Lock
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from db.connection import is_postgres, ping_db

_metrics_lock = Lock()
_request_counts: dict[str, int] = defaultdict(int)
_request_latency_ms: dict[str, float] = defaultdict(float)


def setup_observability() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    )
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(dsn=dsn, integrations=[FastApiIntegration()], traces_sample_rate=0.1)
            logging.getLogger(__name__).info("Sentry initialized")
        except ImportError:
            logging.getLogger(__name__).warning("SENTRY_DSN set but sentry-sdk not installed")


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        route = request.url.path
        status = str(response.status_code)

        with _metrics_lock:
            key = f"{request.method}:{route}:{status}"
            _request_counts[key] += 1
            _request_latency_ms[key] = (
                _request_latency_ms.get(key, 0) * (_request_counts[key] - 1) + elapsed_ms
            ) / _request_counts[key]

        logging.getLogger("api.request").info(
            "request %s %s -> %s (%.1fms) rid=%s",
            request.method,
            route,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response


def get_metrics_text() -> str:
    lines = [
        "# HELP finanalyst_requests_total Total HTTP requests",
        "# TYPE finanalyst_requests_total counter",
    ]
    with _metrics_lock:
        for key, count in sorted(_request_counts.items()):
            method, route, status = key.split(":", 2)
            lines.append(
                f'finanalyst_requests_total{{method="{method}",route="{route}",status="{status}"}} {count}'
            )
        lines.append("# HELP finanalyst_request_latency_ms Average request latency")
        lines.append("# TYPE finanalyst_request_latency_ms gauge")
        for key, avg in sorted(_request_latency_ms.items()):
            method, route, status = key.split(":", 2)
            lines.append(
                f'finanalyst_request_latency_ms{{method="{method}",route="{route}",status="{status}"}} {avg:.2f}'
            )
    return "\n".join(lines) + "\n"


def readiness_status() -> dict[str, Any]:
    db_ok = ping_db()
    openai_ok = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    ready = db_ok and openai_ok
    return {
        "status": "ready" if ready else "degraded",
        "checks": {
            "database": "ok" if db_ok else "fail",
            "database_backend": "postgresql" if is_postgres() else "sqlite",
            "openai_api_key": "ok" if openai_ok else "missing",
        },
    }
