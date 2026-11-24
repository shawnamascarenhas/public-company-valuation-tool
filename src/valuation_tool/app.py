"""Complete Streamlit interface for the public-company valuation tool."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import streamlit as st

from valuation_tool.charts import (
    create_football_field,
    create_forecast_chart,
    create_sensitivity_heatmap,
)
from valuation_tool.config import APP_NAME, RAW_DATA_DIR
from valuation_tool.data_loader import (
    InputBundle,
    InputValidationError,
    load_input_bundle,
    validate_input_bundle,
)
from valuation_tool.dcf import run_dcf_analysis
from valuation_tool.multiples import run_comps_analysis
from valuation_tool.report import build_excel_report
from valuation_tool.schemas import SCHEMAS
from valuation_tool.sensitivity import run_sensitivity_analysis


def _apply_page_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        [data-testid="stMetric"] {
            background: #f3f6f9;
            border: 1px solid #dce4eb;
            border-radius: 0.5rem;
            padding: 0.75rem;
        }
        .model-note {
            border-left: 4px solid #1f4e78;
            background: #f3f6f9;
            padding: 0.8rem 1rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _load_uploaded_bundle() -> InputBundle | None:
    st.sidebar.markdown("#### Upload the four model files")
    uploads = {}
    for name, schema in SCHEMAS.items():
        uploads[name] = st.sidebar.file_uploader(
            schema.filename,
            type="csv",
            key=f"upload_{name}",
        )
    if not all(uploads.values()):
        st.sidebar.info("Upload all four CSV files to run a custom valuation.")
        return None

    with TemporaryDirectory(prefix="valuation-input-") as temporary_directory:
        directory = Path(temporary_directory)
        for name, uploaded_file in uploads.items():
            (directory / SCHEMAS[name].filename).write_bytes(uploaded_file.getvalue())
        return load_input_bundle(directory)


def _select_input_bundle() -> InputBundle | None:
    st.sidebar.header("Model controls")
    source = st.sidebar.radio(
        "Data source",
        ("Bundled example", "Upload CSV files"),
        help="The example dataset is fictional and uses USD millions.",
    )
    with st.sidebar.expander("SEC EDGAR import"):
        st.caption(
            "Use the optional command-line importer to create reviewed annual "
            "financial inputs, then upload the completed canonical CSV files."
        )
        st.code("valuation-sec TARGET PEER1 PEER2 PEER3 PEER4 PEER5", language="bash")
    try:
        if source == "Bundled example":
            return load_input_bundle(RAW_DATA_DIR / "example")
        return _load_uploaded_bundle()
    except InputValidationError as exc:
        st.sidebar.error(str(exc))
        return None


def _edit_inputs(bundle: InputBundle) -> InputBundle:
    st.markdown(
        '<div class="model-note"><strong>Input convention:</strong> Monetary '
        "values are USD millions except per-share values. Percentages are "
        "decimals, so 0.095 means 9.5%.</div>",
        unsafe_allow_html=True,
    )

    st.subheader("Company and market data")
    companies = st.data_editor(
        bundle.companies,
        key="companies_editor",
        hide_index=True,
        width="stretch",
        num_rows="fixed",
    )

    st.subheader("Historical financials")
    historicals = st.data_editor(
        bundle.historicals,
        key="historicals_editor",
        hide_index=True,
        width="stretch",
        num_rows="fixed",
    )

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Five-year forecast assumptions")
        forecast_assumptions = st.data_editor(
            bundle.forecast_assumptions,
            key="forecast_editor",
            hide_index=True,
            width="stretch",
            num_rows="fixed",
        )
    with right:
        st.subheader("Terminal assumptions")
        valuation_assumptions = st.data_editor(
            bundle.valuation_assumptions,
            key="valuation_editor",
            hide_index=True,
            width="stretch",
            num_rows="fixed",
        )

    return InputBundle(
        companies=pd.DataFrame(companies),
        historicals=pd.DataFrame(historicals),
        forecast_assumptions=pd.DataFrame(forecast_assumptions),
        valuation_assumptions=pd.DataFrame(valuation_assumptions),
    )


def _format_money(value: float) -> str:
    return f"${value:,.1f}m"


def _render_overview(bundle: InputBundle, multiples: pd.DataFrame) -> None:
    target_company = bundle.companies.loc[bundle.companies["role"] == "target"].iloc[0]
    target = multiples.loc[multiples["role"] == "target"].iloc[0]

    st.subheader(f"{target_company['company_name']} ({bundle.target_ticker})")
    st.caption(
        f"{target_company['sector']} · Valuation date "
        f"{target_company['valuation_date']:%d %b %Y} · USD millions"
    )
    primary_metrics = st.columns(3)
    primary_metrics[0].metric("Share price", f"${target['share_price']:,.2f}")
    primary_metrics[1].metric(
        "Market capitalization", _format_money(target["market_capitalization"])
    )
    primary_metrics[2].metric(
        "Enterprise value", _format_money(target["enterprise_value"])
    )
    operating_metrics = st.columns(2)
    operating_metrics[0].metric("Latest revenue", _format_money(target["revenue"]))
    operating_metrics[1].metric("Latest EBITDA", _format_money(target["ebitda"]))

    st.subheader("Historical performance")
    history = bundle.historicals.loc[
        bundle.historicals["ticker"] == bundle.target_ticker
    ].copy()
    st.dataframe(
        history,
        hide_index=True,
        width="stretch",
        column_config={
            column: st.column_config.NumberColumn(format="$%.1f")
            for column in (
                "revenue",
                "ebitda",
                "ebit",
                "net_income",
                "capital_expenditure",
                "change_nwc",
            )
        },
    )


def _render_comps(comps: object) -> None:
    st.subheader("Peer trading multiples")
    st.dataframe(
        comps.peer_multiples,
        hide_index=True,
        width="stretch",
        column_config={
            "share_price": st.column_config.NumberColumn(format="$%.2f"),
            "market_capitalization": st.column_config.NumberColumn(format="$%.1f"),
            "enterprise_value": st.column_config.NumberColumn(format="$%.1f"),
            "ev_revenue": st.column_config.NumberColumn(format="%.2fx"),
            "ev_ebitda": st.column_config.NumberColumn(format="%.2fx"),
            "pe": st.column_config.NumberColumn(format="%.2fx"),
        },
    )
    if comps.warnings:
        for warning in comps.warnings:
            st.warning(warning)

    left, right = st.columns([1, 2])
    with left:
        st.subheader("Peer statistics")
        st.dataframe(
            comps.summary_statistics,
            width="stretch",
            column_config={
                column: st.column_config.NumberColumn(format="%.2fx")
                for column in comps.summary_statistics.columns
            },
        )
    with right:
        st.subheader("Implied valuation")
        st.dataframe(
            comps.implied_valuation,
            hide_index=True,
            width="stretch",
            column_config={
                "selected_multiple": st.column_config.NumberColumn(format="%.2fx"),
                "implied_share_price": st.column_config.NumberColumn(format="$%.2f"),
                "current_share_price": st.column_config.NumberColumn(format="$%.2f"),
                "premium_discount": st.column_config.NumberColumn(format="percent"),
            },
        )


def _render_dcf(dcf: object) -> None:
    st.plotly_chart(create_forecast_chart(dcf.forecast), width="stretch")
    st.subheader("Unlevered free-cash-flow forecast")
    st.dataframe(
        dcf.forecast,
        hide_index=True,
        width="stretch",
        column_config={
            "revenue_growth": st.column_config.NumberColumn(format="percent"),
            "ebitda_margin": st.column_config.NumberColumn(format="percent"),
            "tax_rate": st.column_config.NumberColumn(format="percent"),
            "revenue": st.column_config.NumberColumn(format="$%.1f"),
            "ebitda": st.column_config.NumberColumn(format="$%.1f"),
            "fcff": st.column_config.NumberColumn(format="$%.1f"),
            "present_value_fcff": st.column_config.NumberColumn(format="$%.1f"),
        },
    )
    st.subheader("DCF valuation summary")
    st.dataframe(
        dcf.valuation_summary,
        hide_index=True,
        width="stretch",
        column_config={
            "wacc": st.column_config.NumberColumn(format="percent"),
            "terminal_value_percentage": st.column_config.NumberColumn(
                format="percent"
            ),
            "implied_share_price": st.column_config.NumberColumn(format="$%.2f"),
            "current_share_price": st.column_config.NumberColumn(format="$%.2f"),
            "premium_discount": st.column_config.NumberColumn(format="percent"),
        },
    )
    for warning in dcf.warnings:
        st.warning(warning)


def _render_sensitivities(sensitivity: object) -> None:
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            create_sensitivity_heatmap(
                sensitivity.perpetuity_growth,
                title="WACC vs. Terminal Growth",
                column_format=".1%",
            ),
            width="stretch",
        )
    with right:
        st.plotly_chart(
            create_sensitivity_heatmap(
                sensitivity.exit_multiple,
                title="WACC vs. Exit Multiple",
                column_format=".1f",
            ),
            width="stretch",
        )
    with st.expander("View sensitivity source tables"):
        st.markdown("**Perpetuity-growth implied share price**")
        st.dataframe(sensitivity.perpetuity_growth, width="stretch")
        st.markdown("**Exit-multiple implied share price**")
        st.dataframe(sensitivity.exit_multiple, width="stretch")


def _render_summary(
    bundle: InputBundle,
    comps: object,
    dcf: object,
    sensitivity: object,
) -> None:
    st.plotly_chart(
        create_football_field(
            sensitivity.football_field, sensitivity.current_share_price
        ),
        width="stretch",
    )
    st.dataframe(
        sensitivity.football_field,
        hide_index=True,
        width="stretch",
        column_config={
            "low": st.column_config.NumberColumn(format="$%.2f"),
            "high": st.column_config.NumberColumn(format="$%.2f"),
            "midpoint": st.column_config.NumberColumn(format="$%.2f"),
        },
    )

    report = build_excel_report(bundle, comps, dcf, sensitivity)
    st.download_button(
        "Download complete valuation workbook",
        data=report,
        file_name=f"{bundle.target_ticker.lower()}_valuation.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    st.caption(
        "Educational model only. The fictional example is not investment advice "
        "and does not contain live market data."
    )


def run() -> None:
    """Render the complete valuation application."""
    st.set_page_config(page_title=APP_NAME, page_icon="📊", layout="wide")
    _apply_page_style()
    st.title(APP_NAME)
    st.caption("Comparable-company analysis and five-year unlevered DCF")

    source_bundle = _select_input_bundle()
    if source_bundle is None:
        st.info("Select the example dataset or upload all four input files to begin.")
        return

    tabs = st.tabs(
        [
            "Inputs",
            "Company Overview",
            "Comparable Companies",
            "DCF",
            "Sensitivity",
            "Valuation Summary",
        ]
    )

    with tabs[0]:
        bundle = _edit_inputs(source_bundle)

    try:
        validate_input_bundle(bundle)
        comps = run_comps_analysis(bundle)
        dcf = run_dcf_analysis(bundle)
        sensitivity = run_sensitivity_analysis(bundle, comps)
    except (InputValidationError, ValueError, TypeError) as exc:
        with tabs[0]:
            st.error(str(exc))
        st.sidebar.error("Resolve the input errors before reviewing valuation outputs.")
        return

    st.sidebar.success(
        f"Validated: {bundle.target_ticker} with {len(bundle.peer_tickers)} peers"
    )
    st.sidebar.caption("All model outputs update when an input cell changes.")

    with tabs[1]:
        _render_overview(bundle, comps.company_multiples)
    with tabs[2]:
        _render_comps(comps)
    with tabs[3]:
        _render_dcf(dcf)
    with tabs[4]:
        _render_sensitivities(sensitivity)
    with tabs[5]:
        _render_summary(bundle, comps, dcf, sensitivity)
