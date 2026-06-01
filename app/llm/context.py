"""Shared financial context for tools and chat."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd

from analytics.kpis import KpiSummary


@dataclass
class FinancialContext:
    """In-memory dataset for tool execution."""

    monthly: pd.DataFrame
    kpis: KpiSummary
    snapshot: dict[str, Any]
    categories: Optional[pd.DataFrame] = None
    source_file: str = "upload"
    sources_log: list[str] = field(default_factory=list)
    pending_chart: Optional[str] = None

    def log_source(self, label: str) -> None:
        if label not in self.sources_log:
            self.sources_log.append(label)

    def clear_sources(self) -> None:
        self.sources_log.clear()
