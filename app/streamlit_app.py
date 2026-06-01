"""AI Financial Analyst Agent — dashboard + metric-backed AI summaries."""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st
from schemas.chat import ChatTurn
from schemas.financial import ValidationResult
from schemas.summary import ExecutiveSummary

from analytics.anomalies import (
    chart_anomaly_months,
    detect_all_anomalies,
    report_to_context_dict,
)
from analytics.charts import (
    forecast_chart,
    profit_chart,
    revenue_chart,
    top_expenses_chart,
    trends_chart,
)
from analytics.forecasting import ForecastError, forecast_series, forecast_to_context_dict
from analytics.ingest import IngestResult, load_and_clean
from analytics.kpis import KpiSummary, compute_kpis
from analytics.snapshot import build_metrics_snapshot, snapshot_to_json
from llm.anomaly_explain import AnomalyExplainError, AnomalyExplanation, explain_anomalies
from llm.chat import ChatError, build_context, run_chat
from llm.forecast_explain import ForecastExplainError, explain_forecast
from llm.summarize import SummaryError, generate_executive_summary
from reports.builder import build_executive_report
from reports.explainability import build_why_panel
from schemas.anomaly import AnomalyReport
from schemas.forecast import ForecastExplanation, ForecastPayload
from schemas.report import ReportArtifacts

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "datasets" / "sample"

DISCLAIMER = (
    "For analysis and demonstration only — not financial advice. "
    "Uploaded data is processed locally. AI features send computed metrics to OpenAI "
    "(not your raw CSV)."
)

CHAT_EXAMPLES = [
    "Which month had the highest revenue?",
    "Why did net profit change in the latest month?",
    "What are the top expense categories?",
    "Compare the first and last month",
    "Are there any unusual months?",
    "What anomalies were detected?",
]

DEMO_OPTIONS = {
    "Retail monthly P&L": "retail_monthly_pl.csv",
    "SaaS monthly P&L": "saas_monthly_pl.csv",
    "Retail + expense categories": "retail_with_categories.csv",
    "Template (3 months)": "template_monthly_pl.csv",
}

# One entry per file — template is listed once (also in DEMO_OPTIONS for loading).
DOWNLOADABLE_SAMPLES = {
    "Starter template": "template_monthly_pl.csv",
    "Retail monthly P&L": "retail_monthly_pl.csv",
    "SaaS monthly P&L": "saas_monthly_pl.csv",
    "Retail + expense categories": "retail_with_categories.csv",
}


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #0b1220 0%, #111827 100%); }
        h1, h2, h3 { color: #f8fafc !important; font-weight: 600 !important; }
        [data-testid="stMetricValue"] { font-size: 1.6rem !important; color: #f1f5f9 !important; }
        [data-testid="stMetricLabel"] { color: #94a3b8 !important; }
        div[data-testid="stFileUploader"] {
            border: 1px dashed #334155;
            border-radius: 12px;
            padding: 0.5rem;
        }
        .metric-verify {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fmt_currency(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def _render_kpi_row(kpis: KpiSummary) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest revenue", _fmt_currency(kpis.latest_revenue), _fmt_pct(kpis.mom_revenue_growth_pct))
    c2.metric("Latest net profit", _fmt_currency(kpis.latest_net_profit), _fmt_pct(kpis.mom_profit_growth_pct))
    c3.metric("Gross margin", f"{kpis.latest_gross_margin_pct:.1f}%")
    c4.metric("Opex ratio", f"{kpis.latest_opex_ratio_pct:.1f}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("3-mo avg revenue", _fmt_currency(kpis.avg_revenue_3m))
    c6.metric("3-mo avg profit", _fmt_currency(kpis.avg_profit_3m))
    c7.metric("Best month (revenue)", kpis.best_month_by_revenue)
    c8.metric("Period total revenue", _fmt_currency(kpis.total_revenue))


def _render_metrics_verification(snapshot: dict) -> None:
    """Metrics-only panel — verify numbers before trusting AI narrative."""
    m = snapshot["metrics"]
    st.subheader("Verified metrics (source of truth)")
    st.caption("The AI summary may only cite values shown here and in the snapshot JSON.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest period", m["latest_month"])
    c2.metric("Latest revenue", _fmt_currency(m["latest_revenue"]))
    c3.metric("Latest net profit", _fmt_currency(m["latest_net_profit"]))
    c4.metric("MoM revenue", _fmt_pct(m.get("mom_revenue_growth_pct")))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Gross margin", f"{m['latest_gross_margin_pct']:.1f}%")
    c6.metric("Opex ratio", f"{m['latest_opex_ratio_pct']:.1f}%")
    c7.metric("3-mo avg revenue", _fmt_currency(m["avg_revenue_3m"]))
    c8.metric("Best month", m["best_month_by_revenue"])

    if m.get("top_expense_categories"):
        st.markdown("**Top expense categories (latest / aggregated)**")
        for item in m["top_expense_categories"][:6]:
            st.markdown(f"- **{item['category']}**: {_fmt_currency(item['amount'])}")


def _render_executive_summary(summary: ExecutiveSummary) -> None:
    st.subheader("Executive summary")
    st.markdown(summary.summary)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Trends")
        for bullet in summary.trends:
            st.markdown(f"- {bullet}")
        st.markdown("#### Risks")
        for bullet in summary.risks:
            st.markdown(f"- {bullet}")
    with col2:
        st.markdown("#### Opportunities")
        for bullet in summary.opportunities:
            st.markdown(f"- {bullet}")
        st.markdown("#### Recommendations")
        for bullet in summary.recommendations:
            st.markdown(f"- {bullet}")


def _render_chart_by_type(chart_type: str, ingest: IngestResult) -> None:
    charts = {
        "revenue": revenue_chart,
        "profit": profit_chart,
        "expenses": lambda m: top_expenses_chart(ingest.categories, m),
        "trends": trends_chart,
    }
    fn = charts.get(chart_type)
    if fn:
        st.plotly_chart(fn(ingest.monthly), use_container_width=True)


def _clear_session_artifacts() -> None:
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("fc_"):
            del st.session_state[key]
    st.session_state.pop("forecast_explanation", None)
    st.session_state.pop("anomaly_explanation", None)
    st.session_state.pop("report_artifacts", None)


def _render_reports_tab(
    ingest: IngestResult,
    kpis: KpiSummary,
    snapshot: dict,
    source_label: str,
    anomaly_report: AnomalyReport,
    rev_markers: set[str],
    profit_markers: set[str],
    opex_markers: set[str],
    trend_markers: set[str],
) -> None:
    st.caption("Exportable executive report with KPIs, charts, AI summary, and explainability.")

    why_panel = build_why_panel(kpis, anomaly_report=anomaly_report)
    st.subheader("Explainability — Why panel")
    st.markdown(
        "Every headline metric is traced to its source period and formula "
        "(included in HTML/Markdown/PDF exports)."
    )
    st.dataframe(
        __import__("pandas").DataFrame([w.model_dump() for w in why_panel]),
        use_container_width=True,
        hide_index=True,
    )

    has_ai = "executive_summary" in st.session_state
    if not has_ai:
        st.info(
            "Tip: Generate an **AI executive summary** first (Executive summary tab) "
            "to include narrative sections in the report."
        )

    if st.button("Generate executive report", type="primary", use_container_width=True):
        with st.spinner("Building report (charts + templates)…"):
            executive = st.session_state.get("executive_summary")
            st.session_state["report_artifacts"] = build_executive_report(
                ingest=ingest,
                kpis=kpis,
                snapshot=snapshot,
                source_file=source_label,
                anomaly_report=anomaly_report,
                executive_summary=executive,
                rev_markers=rev_markers,
                profit_markers=profit_markers,
                opex_markers=opex_markers,
                trend_markers=trend_markers,
            )

    pkg: ReportArtifacts | None = st.session_state.get("report_artifacts")
    if pkg is None:
        return

    for warn in pkg.warnings:
        st.warning(warn)

    st.success("Report ready — download below or preview HTML.")

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Download HTML",
        data=pkg.html,
        file_name="executive_report.html",
        mime="text/html",
        use_container_width=True,
    )
    d2.download_button(
        "Download Markdown",
        data=pkg.markdown,
        file_name="executive_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    if pkg.pdf_available and pkg.pdf_bytes:
        d3.download_button(
            "Download PDF",
            data=pkg.pdf_bytes,
            file_name="executive_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        d3.caption("PDF unavailable — `pip install xhtml2pdf`")

    with st.expander("Preview report (HTML)", expanded=False):
        st.components.v1.html(pkg.html, height=720, scrolling=True)


def _render_anomalies_tab(ingest: IngestResult, report: AnomalyReport) -> None:
    st.caption("Z-score, IQR, month-over-month opex spikes, and Isolation Forest (8+ months).")

    for warn in report.warnings:
        st.warning(warn)

    summary = report.summary
    c1, c2, c3 = st.columns(3)
    c1.metric("Flags detected", summary.get("count", 0))
    c2.metric("High severity", summary.get("high_severity", 0))
    c3.metric("Months flagged", summary.get("months_flagged", 0))

    if summary.get("by_method"):
        st.markdown("**By method:** " + ", ".join(f"{k}: {v}" for k, v in summary["by_method"].items()))

    if not report.flags:
        st.success("No statistical anomalies detected for this dataset.")
    else:
        rows = [f.model_dump() for f in report.flags]
        st.dataframe(
            __import__("pandas").DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    st.download_button(
        label="Download anomalies.json",
        data=json.dumps(report_to_context_dict(report), indent=2),
        file_name="anomalies.json",
        mime="application/json",
        key="dl_anomalies",
    )

    if report.flags and st.button("Explain anomalies (AI)", use_container_width=True):
        api_key = _get_openai_api_key()
        if not api_key:
            st.error("Add your OpenAI API key in the sidebar or set OPENAI_API_KEY in `.env`.")
        else:
            with st.spinner("Explaining anomalies…"):
                try:
                    st.session_state["anomaly_explanation"] = explain_anomalies(
                        report_to_context_dict(report),
                        api_key=api_key,
                    )
                except AnomalyExplainError as exc:
                    st.error(str(exc))

    if "anomaly_explanation" in st.session_state:
        expl: AnomalyExplanation = st.session_state["anomaly_explanation"]
        st.markdown("#### AI summary")
        st.markdown(expl.summary)
        st.markdown("**Highlights**")
        for line in expl.highlights:
            st.markdown(f"- {line}")
        st.markdown("**Suggested actions**")
        for line in expl.suggested_actions:
            st.markdown(f"- {line}")


def _render_forecast_tab(ingest: IngestResult, source_label: str) -> None:
    st.caption("Prophet forecasts with 80% confidence intervals — not financial advice.")

    metric = st.radio(
        "Metric",
        options=["revenue", "opex"],
        format_func=lambda m: "Revenue" if m == "revenue" else "Operating expenses (opex)",
        horizontal=True,
    )
    horizon_choice = st.radio(
        "Horizon",
        options=["1 quarter (3 months)", "1 year (12 months)"],
        horizontal=True,
    )
    horizon_months = 3 if "quarter" in horizon_choice else 12

    cache_key = f"fc_{source_label}_{metric}_{horizon_months}"
    col_run, col_refresh = st.columns([1, 1])
    run = col_run.button("Run forecast", type="primary", use_container_width=True)
    refresh = col_refresh.button("Refresh", use_container_width=True)

    if run or refresh or cache_key not in st.session_state:
        try:
            st.session_state[cache_key] = forecast_series(
                ingest.monthly, metric, horizon_months  # type: ignore[arg-type]
            )
            st.session_state.pop("forecast_explanation", None)
        except ForecastError as exc:
            st.error(str(exc))
            return

    payload: ForecastPayload = st.session_state[cache_key]
    summary = payload.summary

    for warn in payload.warnings:
        st.warning(warn)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Forecast total", f"${summary['forecast_total']:,.0f}")
    m2.metric("Avg monthly (forecast)", f"${summary['forecast_avg_monthly']:,.0f}")
    m3.metric("Last actual", f"${summary['last_actual_value']:,.0f}")
    m4.metric("End of horizon", f"${summary['forecast_end_value']:,.0f}")

    st.plotly_chart(forecast_chart(payload), use_container_width=True)

    with st.expander("Forecast data (JSON)"):
        st.json(forecast_to_context_dict(payload))

    st.download_button(
        label="Download forecast.json",
        data=json.dumps(forecast_to_context_dict(payload), indent=2),
        file_name=f"forecast_{metric}_{horizon_months}m.json",
        mime="application/json",
        key=f"dl_fc_{cache_key}",
    )

    if st.button("Explain forecast (AI)", use_container_width=True):
        api_key = _get_openai_api_key()
        if not api_key:
            st.error("Add your OpenAI API key in the sidebar or set OPENAI_API_KEY in `.env`.")
        else:
            with st.spinner("Explaining forecast…"):
                try:
                    st.session_state["forecast_explanation"] = explain_forecast(
                        forecast_to_context_dict(payload),
                        api_key=api_key,
                    )
                except ForecastExplainError as exc:
                    st.error(str(exc))

    if "forecast_explanation" in st.session_state:
        expl: ForecastExplanation = st.session_state["forecast_explanation"]
        st.markdown("#### AI outlook")
        st.markdown(expl.outlook)
        st.markdown("**Key figures**")
        for line in expl.key_figures:
            st.markdown(f"- {line}")
        st.markdown("**Risks & caveats**")
        for line in expl.risks_and_caveats:
            st.markdown(f"- {line}")


def _render_chat_tab(
    ingest: IngestResult,
    kpis: KpiSummary,
    snapshot: dict,
    source_label: str,
) -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    st.caption("Tool-based Q&A over your computed metrics — not generic RAG on CSV rows.")

    ex_cols = st.columns(2)
    for i, example in enumerate(CHAT_EXAMPLES):
        if ex_cols[i % 2].button(example, key=f"chat_ex_{i}", use_container_width=True):
            st.session_state["_chat_pending"] = example

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                st.markdown(f"**Sources:** {', '.join(msg['sources'])}")
            if msg.get("chart") and msg["role"] == "assistant":
                _render_chart_by_type(msg["chart"], ingest)

    if st.button("Clear chat", key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

    prompt = st.session_state.pop("_chat_pending", None)
    user_input = st.chat_input("Ask about revenue, profit, expenses, anomalies…")
    if user_input:
        prompt = user_input

    if not prompt:
        return

    api_key = _get_openai_api_key()
    if not api_key:
        st.error("Add your OpenAI API key in the sidebar or set OPENAI_API_KEY in `.env`.")
        return

    history = [
        ChatTurn(role=m["role"], content=m["content"])
        for m in st.session_state.chat_messages
    ]
    st.session_state.chat_messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing with tools…"):
            try:
                ctx = build_context(
                    ingest.monthly,
                    kpis,
                    snapshot,
                    categories=ingest.categories,
                    source_file=source_label,
                )
                reply = run_chat(prompt, ctx, history=history, api_key=api_key)
            except ChatError as exc:
                st.error(str(exc))
                st.session_state.chat_messages.pop()
                return

        st.markdown(reply.answer)
        if reply.sources:
            st.markdown(f"**Sources:** {', '.join(reply.sources)}")
        if reply.chart:
            _render_chart_by_type(reply.chart, ingest)

    st.session_state.chat_messages.append(
        {
            "role": "assistant",
            "content": reply.answer,
            "sources": reply.sources,
            "chart": reply.chart,
        }
    )


def _load_demo_file(name: str) -> tuple[bytes, str]:
    path = SAMPLE_DIR / name
    return path.read_bytes(), path.name


def _get_openai_api_key() -> str | None:
    if "openai_api_key" in st.session_state and st.session_state.openai_api_key:
        return st.session_state.openai_api_key.strip()
    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        return st.secrets.get("OPENAI_API_KEY", "").strip() or None
    except Exception:  # noqa: BLE001
        return None


def _sidebar_data_panel() -> tuple[bytes | None, str | None]:
    st.header("Data")
    st.markdown(
        "**Required:** `date`, `revenue`  \n"
        "**Optional:** `cogs`, `opex`, `category`, `amount`  \n"
        "See README for full data contract."
    )

    for label, fname in DOWNLOADABLE_SAMPLES.items():
        path = SAMPLE_DIR / fname
        if path.exists():
            st.download_button(
                label=f"Download {label}",
                data=path.read_bytes(),
                file_name=fname,
                mime="text/csv",
                use_container_width=True,
                key=f"dl_{label.replace(' ', '_')}",
            )

    st.divider()
    demo = st.selectbox("Load demo dataset", ["(none)", *DEMO_OPTIONS.keys()])
    if demo != "(none)":
        return _load_demo_file(DEMO_OPTIONS[demo])

    return None, None


def main() -> None:
    st.set_page_config(
        page_title="AI Financial Analyst",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

    st.title("AI Financial Analyst")
    st.caption("Upload → dashboard → anomalies → forecast → summary → reports → chat")
    st.info(DISCLAIMER)

    with st.sidebar:
        demo_bytes, demo_name = _sidebar_data_panel()
        st.divider()
        st.header("AI (Steps 2–6)")
        api_input = st.text_input(
            "OpenAI API key",
            type="password",
            placeholder="sk-... (or set OPENAI_API_KEY)",
            help="Used for summaries, forecast/anomaly explanations, and chat.",
        )
        if api_input:
            st.session_state.openai_api_key = api_input
        elif _get_openai_api_key():
            st.caption("Using API key from environment / secrets.")

    uploaded = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls"],
    )

    file_bytes: bytes | None = None
    filename: str | None = None

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        filename = uploaded.name
    elif demo_bytes is not None:
        file_bytes, filename = demo_bytes, demo_name
        st.sidebar.success(f"Loaded: {filename}")

    if file_bytes is None:
        st.markdown("---")
        st.subheader("Get started")
        st.markdown(
            "1. **Download** the starter template from the sidebar, or  \n"
            "2. **Load a demo dataset** from the sidebar, or  \n"
            "3. **Upload** your own CSV/XLSX."
        )
        with st.expander("Preview template schema"):
            template = SAMPLE_DIR / "template_monthly_pl.csv"
            if template.exists():
                st.dataframe(
                    __import__("pandas").read_csv(template),
                    use_container_width=True,
                )
        return

    result = load_and_clean(file_bytes, filename or "upload.csv")

    if isinstance(result, ValidationResult):
        st.error("Could not process this file")
        for err in result.errors:
            st.markdown(f"- {err}")
        if result.warnings:
            st.warning("Warnings")
            for w in result.warnings:
                st.markdown(f"- {w}")
        return

    assert isinstance(result, IngestResult)
    for w in result.validation.warnings:
        st.warning(w)

    kpis = compute_kpis(result.monthly, result.categories)
    source_label = filename or "upload.csv"
    if st.session_state.get("_loaded_source") != source_label:
        st.session_state.pop("executive_summary", None)
        st.session_state.pop("chat_messages", None)
        _clear_session_artifacts()
        st.session_state["_loaded_source"] = source_label

    snapshot = build_metrics_snapshot(
        kpis,
        source_file=source_label,
        period_count=len(result.monthly),
    )
    snapshot_json = snapshot_to_json(snapshot)

    st.session_state["metrics_snapshot"] = snapshot

    st.success(
        f"Loaded **{len(result.monthly)}** months · latest period **{kpis.latest_month}**"
    )

    anomaly_report = detect_all_anomalies(result.monthly, result.categories)
    rev_markers = chart_anomaly_months(anomaly_report, "revenue")
    profit_markers = chart_anomaly_months(anomaly_report, "profit")
    opex_markers = chart_anomaly_months(anomaly_report, "opex")
    trend_markers = chart_anomaly_months(anomaly_report, "trends")

    dash_tab, anomalies_tab, forecast_tab, summary_tab, reports_tab, chat_tab = st.tabs(
        ["Dashboard", "Anomalies", "Forecast", "Executive summary", "Reports", "Chat"]
    )

    with dash_tab:
        if anomaly_report.summary.get("count", 0) > 0:
            st.info(
                f"**{anomaly_report.summary['count']}** anomaly flag(s) detected — "
                "see **Anomalies** tab. Charts show ◆ markers."
            )
        _render_kpi_row(kpis)
        st.markdown("---")
        c1, c2, c3, c4 = st.tabs(["Revenue", "Profit", "Expenses", "Trends"])
        with c1:
            st.plotly_chart(
                revenue_chart(result.monthly, rev_markers),
                use_container_width=True,
            )
        with c2:
            st.plotly_chart(
                profit_chart(result.monthly, profit_markers),
                use_container_width=True,
            )
        with c3:
            st.plotly_chart(
                top_expenses_chart(result.categories, result.monthly, opex_markers),
                use_container_width=True,
            )
        with c4:
            st.plotly_chart(
                trends_chart(result.monthly, trend_markers),
                use_container_width=True,
            )

        with st.expander("Monthly data table"):
            display = result.monthly.copy()
            display.insert(0, "period", display["month"].dt.strftime("%Y-%m"))
            display = display.drop(columns=["month"])
            st.dataframe(display, use_container_width=True)

        with st.expander("Upload preview (first rows)"):
            st.dataframe(result.raw_preview, use_container_width=True)

    with anomalies_tab:
        _render_anomalies_tab(result, anomaly_report)

    with forecast_tab:
        _render_forecast_tab(result, source_label)

    with summary_tab:
        _render_metrics_verification(snapshot)

        st.download_button(
            label="Download metrics_snapshot.json",
            data=snapshot_json,
            file_name="metrics_snapshot.json",
            mime="application/json",
        )

        with st.expander("View snapshot JSON"):
            st.json(snapshot)

        if st.button("Generate executive summary", type="primary", use_container_width=True):
            api_key = _get_openai_api_key()
            if not api_key:
                st.error("Add your OpenAI API key in the sidebar or set OPENAI_API_KEY in `.env`.")
            else:
                with st.spinner("Analyzing metrics (OpenAI)…"):
                    try:
                        summary = generate_executive_summary(snapshot, api_key=api_key)
                        st.session_state["executive_summary"] = summary
                    except SummaryError as exc:
                        st.error(str(exc))

        if "executive_summary" in st.session_state:
            st.markdown("---")
            _render_executive_summary(st.session_state["executive_summary"])

    with reports_tab:
        _render_reports_tab(
            result,
            kpis,
            snapshot,
            source_label,
            anomaly_report,
            rev_markers,
            profit_markers,
            opex_markers,
            trend_markers,
        )

    with chat_tab:
        _render_chat_tab(result, kpis, snapshot, source_label)


if __name__ == "__main__":
    main()
