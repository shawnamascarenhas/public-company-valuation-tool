"""Build all portfolio demonstration artifacts from the example dataset."""

from pathlib import Path

from valuation_tool.charts import (
    create_football_field,
    create_forecast_chart,
    create_sensitivity_heatmap,
)
from valuation_tool.config import OUTPUT_DIR, RAW_DATA_DIR
from valuation_tool.data_loader import load_input_bundle
from valuation_tool.dcf import run_dcf_analysis
from valuation_tool.multiples import run_comps_analysis
from valuation_tool.report import build_excel_report
from valuation_tool.sensitivity import run_sensitivity_analysis


def build_release(output_directory: Path = OUTPUT_DIR / "release") -> Path:
    """Generate a reproducible release package and return its directory."""
    bundle = load_input_bundle(RAW_DATA_DIR / "example")
    comps = run_comps_analysis(bundle)
    dcf = run_dcf_analysis(bundle)
    sensitivity = run_sensitivity_analysis(bundle, comps)
    output_directory.mkdir(parents=True, exist_ok=True)

    tables = {
        "company_multiples.csv": comps.company_multiples,
        "peer_summary_statistics.csv": comps.summary_statistics,
        "comps_implied_valuation.csv": comps.implied_valuation,
        "dcf_forecast.csv": dcf.forecast,
        "dcf_valuation_summary.csv": dcf.valuation_summary,
        "perpetuity_growth_sensitivity.csv": sensitivity.perpetuity_growth,
        "exit_multiple_sensitivity.csv": sensitivity.exit_multiple,
        "football_field_ranges.csv": sensitivity.football_field,
    }
    for filename, table in tables.items():
        table.to_csv(output_directory / filename, index=table.index.name is not None)

    workbook = build_excel_report(bundle, comps, dcf, sensitivity)
    (output_directory / "alpha_software_valuation.xlsx").write_bytes(workbook)

    charts = {
        "operating_forecast.html": create_forecast_chart(dcf.forecast),
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
    }
    for filename, figure in charts.items():
        figure.write_html(
            output_directory / filename,
            include_plotlyjs="cdn",
            full_html=True,
        )

    manifest = [
        "Public Company Valuation Tool — Example Release",
        "Dataset: fictional Alpha Software and five fictional peers",
        f"Target: {bundle.target_ticker}",
        f"Files generated: {len(tables) + len(charts) + 1}",
        "Educational use only; not investment advice.",
    ]
    (output_directory / "MANIFEST.txt").write_text("\n".join(manifest) + "\n")
    return output_directory


if __name__ == "__main__":
    destination = build_release()
    print(f"Release artifacts generated: {destination}")
