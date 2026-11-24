"""Tests for DCF sensitivities and valuation visualizations."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from valuation_tool.charts import (
    create_football_field,
    create_forecast_chart,
    create_sensitivity_heatmap,
)
from valuation_tool.config import RAW_DATA_DIR
from valuation_tool.data_loader import InputBundle, load_input_bundle
from valuation_tool.dcf import run_dcf_analysis
from valuation_tool.multiples import run_comps_analysis
from valuation_tool.sensitivity import (
    build_exit_multiple_sensitivity,
    build_perpetuity_growth_sensitivity,
    run_sensitivity_analysis,
)


@pytest.fixture
def bundle() -> InputBundle:
    return load_input_bundle(RAW_DATA_DIR / "example")


def test_base_assumptions_reconcile_to_dcf_summary(bundle: InputBundle) -> None:
    comps = run_comps_analysis(bundle)
    dcf = run_dcf_analysis(bundle).valuation_summary.set_index("method")
    sensitivity = run_sensitivity_analysis(bundle, comps)

    assert sensitivity.perpetuity_growth.loc[0.095, 0.030] == pytest.approx(
        dcf.loc["perpetuity_growth", "implied_share_price"]
    )
    assert sensitivity.exit_multiple.loc[0.095, 10.0] == pytest.approx(
        dcf.loc["exit_multiple", "implied_share_price"]
    )


def test_sensitivity_tables_are_five_by_five(bundle: InputBundle) -> None:
    sensitivity = run_sensitivity_analysis(bundle, run_comps_analysis(bundle))

    assert sensitivity.perpetuity_growth.shape == (5, 5)
    assert sensitivity.exit_multiple.shape == (5, 5)
    assert sensitivity.perpetuity_growth.index.name == "wacc"
    assert sensitivity.exit_multiple.columns.name == "terminal_ev_ebitda"


def test_expected_sensitivity_directions(bundle: InputBundle) -> None:
    sensitivity = run_sensitivity_analysis(bundle, run_comps_analysis(bundle))
    perpetuity = sensitivity.perpetuity_growth
    exit_multiple = sensitivity.exit_multiple

    assert perpetuity.loc[0.075, 0.030] > perpetuity.loc[0.115, 0.030]
    assert perpetuity.loc[0.095, 0.040] > perpetuity.loc[0.095, 0.020]
    assert exit_multiple.loc[0.095, 12.0] > exit_multiple.loc[0.095, 8.0]


def test_invalid_sensitivity_grids_are_rejected(bundle: InputBundle) -> None:
    with pytest.raises(ValueError, match="WACC sensitivity must exceed"):
        build_perpetuity_growth_sensitivity(bundle, [0.03], [0.03])
    with pytest.raises(ValueError, match="must be positive"):
        build_exit_multiple_sensitivity(bundle, [0.095], [0.0])


def test_football_field_uses_comps_interquartile_ranges(
    bundle: InputBundle,
) -> None:
    comps = run_comps_analysis(bundle)
    sensitivity = run_sensitivity_analysis(bundle, comps)
    ranges = sensitivity.football_field.set_index("method")
    ev_ebitda_values = comps.implied_valuation.query(
        "method == 'ev_ebitda' and statistic in ['25th_percentile', '75th_percentile']"
    )["implied_share_price"]

    assert ranges.loc["EV / EBITDA", "low"] == pytest.approx(ev_ebitda_values.min())
    assert ranges.loc["EV / EBITDA", "high"] == pytest.approx(ev_ebitda_values.max())
    assert len(ranges) == 5


def test_chart_functions_return_plotly_figures(bundle: InputBundle) -> None:
    comps = run_comps_analysis(bundle)
    dcf = run_dcf_analysis(bundle)
    sensitivity = run_sensitivity_analysis(bundle, comps)

    figures = [
        create_sensitivity_heatmap(
            sensitivity.perpetuity_growth,
            title="Test",
            column_format=".1%",
        ),
        create_football_field(
            sensitivity.football_field, sensitivity.current_share_price
        ),
        create_forecast_chart(dcf.forecast),
    ]

    assert all(isinstance(figure, go.Figure) for figure in figures)
    assert all(len(figure.data) > 0 for figure in figures)
    assert isinstance(sensitivity.football_field, pd.DataFrame)
