"""Generate Step 6 sensitivity tables and valuation charts."""

import argparse
from pathlib import Path

from valuation_tool.charts import (
    create_football_field,
    create_forecast_chart,
    create_sensitivity_heatmap,
)
from valuation_tool.config import OUTPUT_DIR
from valuation_tool.data_loader import load_input_bundle
from valuation_tool.dcf import run_dcf_analysis
from valuation_tool.multiples import run_comps_analysis
from valuation_tool.sensitivity import run_sensitivity_analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate valuation analytics")
    parser.add_argument(
        "input_directory",
        nargs="?",
        default="data/raw/example",
        type=Path,
    )
    parser.add_argument(
        "--output-directory",
        default=OUTPUT_DIR / "step_06",
        type=Path,
    )
    args = parser.parse_args()

    bundle = load_input_bundle(args.input_directory)
    comps = run_comps_analysis(bundle)
    dcf = run_dcf_analysis(bundle)
    sensitivity = run_sensitivity_analysis(bundle, comps)
    args.output_directory.mkdir(parents=True, exist_ok=True)

    sensitivity.perpetuity_growth.to_csv(
        args.output_directory / "perpetuity_growth_sensitivity.csv"
    )
    sensitivity.exit_multiple.to_csv(
        args.output_directory / "exit_multiple_sensitivity.csv"
    )
    sensitivity.football_field.to_csv(
        args.output_directory / "football_field_ranges.csv", index=False
    )

    charts = {
        "perpetuity_growth_heatmap.html": create_sensitivity_heatmap(
            sensitivity.perpetuity_growth,
            title="DCF Sensitivity — WACC vs. Terminal Growth",
            column_format=".1%",
        ),
        "exit_multiple_heatmap.html": create_sensitivity_heatmap(
            sensitivity.exit_multiple,
            title="DCF Sensitivity — WACC vs. Exit Multiple",
            column_format=".1f",
        ),
        "valuation_football_field.html": create_football_field(
            sensitivity.football_field, sensitivity.current_share_price
        ),
        "operating_forecast.html": create_forecast_chart(dcf.forecast),
    }
    for filename, figure in charts.items():
        figure.write_html(
            args.output_directory / filename,
            include_plotlyjs="cdn",
            full_html=True,
        )

    print(f"Sensitivity analysis complete for {bundle.target_ticker}")
    print(f"Outputs: {args.output_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
