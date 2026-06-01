"""Build versioned metrics snapshots for LLM context and export."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from analytics.kpis import KpiSummary

SNAPSHOT_VERSION = "1.0"


def build_metrics_snapshot(
    kpis: KpiSummary,
    *,
    source_file: str = "upload",
    period_count: int | None = None,
) -> dict[str, Any]:
    """Full metrics payload for JSON export and Step 2 LLM CONTEXT."""
    metrics = kpis.to_snapshot_dict()
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": source_file,
        "period_count": period_count or len(metrics.get("monthly_records", [])),
        "metrics": metrics,
    }


def snapshot_to_json(snapshot: dict[str, Any], *, indent: int = 2) -> str:
    return json.dumps(snapshot, indent=indent, default=str)
