"""Formula-level tests for the unlevered DCF engine."""

import pandas as pd
import pytest

from valuation_tool.config import RAW_DATA_DIR
from valuation_tool.data_loader import InputBundle, load_input_bundle
from valuation_tool.dcf import (
    build_unlevered_forecast,
    calculate_terminal_values,
    discount_forecast,
    run_dcf_analysis,
)


@pytest.fixture
def bundle() -> InputBundle:
    return load_input_bundle(RAW_DATA_DIR / "example")


def test_first_forecast_year_reconciles_to_manual_formula(
    bundle: InputBundle,
) -> None:
    forecast = build_unlevered_forecast(bundle)
    year_one = forecast.iloc[0]

    revenue = 2_110.0 * (1 + 0.110)
    ebitda = revenue * 0.213
    depreciation_amortization = revenue * 0.037
    ebit = ebitda - depreciation_amortization
    nopat = ebit * (1 - 0.240)
    capital_expenditure = revenue * 0.044
    change_nwc = revenue * 0.012
    fcff = nopat + depreciation_amortization - capital_expenditure - change_nwc

    assert year_one["revenue"] == pytest.approx(revenue)
    assert year_one["ebitda"] == pytest.approx(ebitda)
    assert year_one["depreciation_amortization"] == pytest.approx(
        depreciation_amortization
    )
    assert year_one["ebit"] == pytest.approx(ebit)
    assert year_one["nopat"] == pytest.approx(nopat)
    assert year_one["fcff"] == pytest.approx(fcff)


def test_revenue_forecast_compounds_from_prior_year(bundle: InputBundle) -> None:
    forecast = build_unlevered_forecast(bundle)

    assert forecast.iloc[1]["revenue"] == pytest.approx(
        forecast.iloc[0]["revenue"] * 1.10
    )
    assert forecast.iloc[-1]["period"] == 5


def test_end_of_year_discounting(bundle: InputBundle) -> None:
    forecast = discount_forecast(build_unlevered_forecast(bundle), 0.095)

    assert forecast.iloc[0]["discount_factor"] == pytest.approx(1 / 1.095)
    assert forecast.iloc[-1]["discount_factor"] == pytest.approx(1 / 1.095**5)
    assert forecast.iloc[-1]["present_value_fcff"] == pytest.approx(
        forecast.iloc[-1]["fcff"] / 1.095**5
    )


def test_both_terminal_values_reconcile(bundle: InputBundle) -> None:
    forecast = discount_forecast(build_unlevered_forecast(bundle), 0.095)
    terminal = calculate_terminal_values(
        forecast,
        wacc=0.095,
        terminal_growth_rate=0.030,
        terminal_ev_ebitda=10.0,
    ).set_index("method")
    final_year = forecast.iloc[-1]

    expected_perpetuity = final_year["fcff"] * 1.03 / (0.095 - 0.030)
    expected_exit = final_year["ebitda"] * 10.0

    assert terminal.loc["perpetuity_growth", "terminal_value"] == pytest.approx(
        expected_perpetuity
    )
    assert terminal.loc["exit_multiple", "terminal_value"] == pytest.approx(
        expected_exit
    )
    assert terminal.loc["perpetuity_growth", "present_value_terminal"] == pytest.approx(
        expected_perpetuity / 1.095**5
    )


def test_dcf_enterprise_to_equity_bridge_reconciles(bundle: InputBundle) -> None:
    analysis = run_dcf_analysis(bundle)
    result = analysis.valuation_summary.set_index("method").loc["perpetuity_growth"]

    expected_enterprise_value = (
        result["present_value_forecast_fcff"] + result["present_value_terminal"]
    )
    expected_equity_value = expected_enterprise_value - 650.0 + 240.0 + 35.0

    assert result["enterprise_value"] == pytest.approx(expected_enterprise_value)
    assert result["equity_value"] == pytest.approx(expected_equity_value)
    assert result["implied_share_price"] == pytest.approx(expected_equity_value / 120.0)


def test_invalid_terminal_assumptions_are_rejected(bundle: InputBundle) -> None:
    forecast = discount_forecast(build_unlevered_forecast(bundle), 0.095)

    with pytest.raises(ValueError, match="lower than WACC"):
        calculate_terminal_values(
            forecast,
            wacc=0.095,
            terminal_growth_rate=0.095,
            terminal_ev_ebitda=10.0,
        )
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_terminal_values(
            forecast,
            wacc=0.095,
            terminal_growth_rate=0.030,
            terminal_ev_ebitda=0.0,
        )


def test_dcf_outputs_are_complete(bundle: InputBundle) -> None:
    analysis = run_dcf_analysis(bundle)

    assert len(analysis.forecast) == 5
    assert set(analysis.valuation_summary["method"]) == {
        "perpetuity_growth",
        "exit_multiple",
    }
    assert isinstance(analysis.forecast, pd.DataFrame)
    assert analysis.valuation_summary["implied_share_price"].notna().all()
