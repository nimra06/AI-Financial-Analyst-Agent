"""Executive report generation (lazy imports — avoids loading plotly at API startup)."""

from reports.explainability import build_why_panel

__all__ = ["build_why_panel", "build_executive_report"]


def build_executive_report(*args, **kwargs):
    """Lazy import so FastAPI can start without plotly/kaleido unless reports are used."""
    from reports.builder import build_executive_report as _build

    return _build(*args, **kwargs)
