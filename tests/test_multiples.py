"""Formula-level tests for comparable-company valuation."""

import math

import pandas as pd
import pytest

from valuation_tool.config import RAW_DATA_DIR
from valuation_tool.data_loader import InputBundle, load_input_bundle
from valuation_tool.multiples import run_comps_analysis
from valuation_tool.valuation import (
    enterprise_to_equity_value,
    equity_to_enterprise_value,
    per_share_value,
)


@pytest.fixture
def bundle() -> InputBundle:
    return load_input_bundle(RAW_DATA_DIR / "example")


def test_enterprise_value_and_trading_multiples(bundle: InputBundle) -> None:
    analysis = run_comps_analysis(bundle)
    bravo = analysis.company_multiples.set_index("ticker").loc["BRVO"]

    expected_market_cap = 58.0 * 95.0
    expected_enterprise_value = expected_market_cap + 420.0 - 180.0 - 20.0

    assert bravo["market_capitalization"] == pytest.approx(expected_market_cap)
    assert bravo["enterprise_value"] == pytest.approx(expected_enterprise_value)
    assert bravo["ev_revenue"] == pytest.approx(expected_enterprise_value / 1780.0)
    assert bravo["ev_ebitda"] == pytest.approx(expected_enterprise_value / 365.0)
    assert bravo["pe"] == pytest.approx(58.0 / 2.23)


def test_peer_summary_median_is_independently_reconciled(
    bundle: InputBundle,
) -> None:
    analysis = run_comps_analysis(bundle)
    peer_values = analysis.peer_multiples["ev_ebitda"].tolist()
    expected_median = sorted(peer_values)[len(peer_values) // 2]

    assert analysis.summary_statistics.loc["median", "ev_ebitda"] == pytest.approx(
        expected_median
    )


def test_implied_ev_ebitda_valuation_reconciles(bundle: InputBundle) -> None:
    analysis = run_comps_analysis(bundle)
    result = analysis.implied_valuation.query(
        "method == 'ev_ebitda' and statistic == 'median'"
    ).iloc[0]

    selected_multiple = analysis.summary_statistics.loc["median", "ev_ebitda"]
    expected_ev = selected_multiple * 435.0
    expected_equity = expected_ev - 650.0 + 240.0 + 35.0
    expected_share_price = expected_equity / 120.0

    assert result["implied_enterprise_value"] == pytest.approx(expected_ev)
    assert result["implied_equity_value"] == pytest.approx(expected_equity)
    assert result["implied_share_price"] == pytest.approx(expected_share_price)
    assert result["premium_discount"] == pytest.approx(expected_share_price / 42.0 - 1)


def test_pe_valuation_uses_target_eps(bundle: InputBundle) -> None:
    analysis = run_comps_analysis(bundle)
    result = analysis.implied_valuation.query(
        "method == 'pe' and statistic == 'median'"
    ).iloc[0]
    peer_median = analysis.summary_statistics.loc["median", "pe"]

    assert result["implied_share_price"] == pytest.approx(peer_median * 2.06)


def test_non_positive_denominators_are_unavailable(bundle: InputBundle) -> None:
    historicals = bundle.historicals.copy()
    latest_bravo = (historicals["ticker"] == "BRVO") & (
        historicals["fiscal_year"] == 2025
    )
    historicals.loc[latest_bravo, ["ebitda", "diluted_eps"]] = -1.0
    modified = InputBundle(
        companies=bundle.companies,
        historicals=historicals,
        forecast_assumptions=bundle.forecast_assumptions,
        valuation_assumptions=bundle.valuation_assumptions,
    )

    analysis = run_comps_analysis(modified)
    bravo = analysis.peer_multiples.set_index("ticker").loc["BRVO"]

    assert math.isnan(bravo["ev_ebitda"])
    assert math.isnan(bravo["pe"])
    assert any("BRVO" in warning for warning in analysis.warnings)


def test_non_positive_target_denominator_suppresses_valuation(
    bundle: InputBundle,
) -> None:
    historicals = bundle.historicals.copy()
    latest_target = (historicals["ticker"] == "ALPH") & (
        historicals["fiscal_year"] == 2025
    )
    historicals.loc[latest_target, "ebitda"] = -1.0
    modified = InputBundle(
        companies=bundle.companies,
        historicals=historicals,
        forecast_assumptions=bundle.forecast_assumptions,
        valuation_assumptions=bundle.valuation_assumptions,
    )

    analysis = run_comps_analysis(modified)
    ev_ebitda = analysis.implied_valuation.query("method == 'ev_ebitda'")

    assert ev_ebitda["implied_share_price"].isna().all()
    assert any("target denominator" in warning for warning in analysis.warnings)


def test_value_bridge_round_trip() -> None:
    bridge = {
        "total_debt": 500.0,
        "cash": 120.0,
        "non_controlling_interest": 10.0,
        "preferred_stock": 20.0,
        "investments": 30.0,
    }
    equity_value = enterprise_to_equity_value(2_500.0, **bridge)

    assert equity_value == pytest.approx(2_120.0)
    assert equity_to_enterprise_value(equity_value, **bridge) == pytest.approx(2_500.0)
    assert per_share_value(equity_value, 100.0) == pytest.approx(21.2)


def test_output_tables_have_no_accidental_duplicate_rows(bundle: InputBundle) -> None:
    analysis = run_comps_analysis(bundle)

    assert not analysis.company_multiples["ticker"].duplicated().any()
    assert not analysis.implied_valuation.duplicated(["method", "statistic"]).any()
    assert isinstance(analysis.summary_statistics, pd.DataFrame)
