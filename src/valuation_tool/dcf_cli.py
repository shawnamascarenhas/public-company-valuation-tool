"""Command-line runner for discounted cash-flow analysis."""

import argparse
from pathlib import Path

from valuation_tool.config import OUTPUT_DIR
from valuation_tool.data_loader import load_input_bundle
from valuation_tool.dcf import run_dcf_analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Run five-year DCF valuation")
    parser.add_argument(
        "input_directory",
        nargs="?",
        default="data/raw/example",
        type=Path,
    )
    parser.add_argument(
        "--output-directory",
        default=OUTPUT_DIR / "step_05",
        type=Path,
    )
    args = parser.parse_args()

    bundle = load_input_bundle(args.input_directory)
    analysis = run_dcf_analysis(bundle)
    args.output_directory.mkdir(parents=True, exist_ok=True)
    analysis.forecast.to_csv(args.output_directory / "dcf_forecast.csv", index=False)
    analysis.valuation_summary.to_csv(
        args.output_directory / "dcf_valuation_summary.csv", index=False
    )

    print(f"DCF analysis complete for {bundle.target_ticker}")
    print(f"Outputs: {args.output_directory}")
    for warning in analysis.warnings:
        print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
