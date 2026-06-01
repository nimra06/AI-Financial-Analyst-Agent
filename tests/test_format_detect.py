"""Upload format detection and freelance billing insights."""

from analytics.format_detect import (
    analyze_freelance_client_billing,
    build_wrong_format_validation,
    detect_upload_format,
)
from analytics.ingest import load_and_clean
import pandas as pd


def test_detect_freelance_upwork_shape() -> None:
    df = pd.DataFrame(
        {
            "Client": ["Acme Corp", "Beta LLC", "Gamma Inc"],
            "Total billed": ["$10,000.00", "$5,500", "1200"],
        }
    )
    assert detect_upload_format(df) == "freelance_client_billing"


def test_freelance_insights() -> None:
    df = pd.DataFrame(
        {
            "Client": ["Big Co", "Small Co", "Mid Co"],
            "Total billed": [80000, 2000, 15000],
        }
    )
    out = analyze_freelance_client_billing(df)
    assert out["client_count"] == 3
    assert out["total_lifetime"] == 97000
    assert len(out["insights"]) >= 4
    assert out["top_clients"][0]["client"] == "Big Co"


def test_load_and_clean_freelance_returns_insights() -> None:
    csv = b"Client,Total billed\nHelona,4200\nGetro,8900\n"
    result = load_and_clean(csv, "lifetime_billed.csv")
    assert result.ok is False
    assert result.detected_format == "freelance_client_billing"
    assert len(result.freelance_insights) > 0
    assert result.freelance_summary is not None


def test_unknown_format_message() -> None:
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    errors, _, fmt, summary = build_wrong_format_validation(df)
    assert fmt == "unknown"
    assert summary is None
    assert "doesn't look like financial P&L" in errors[0]
