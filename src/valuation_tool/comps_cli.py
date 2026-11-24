"""Command-line runner for comparable-company analysis."""

import argparse
from pathlib import Path

from valuation_tool.config import OUTPUT_DIR
from valuation_tool.data_loader import load_input_bundle
from valuation_tool.multiples import run_comps_analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Run comparable-company valuation")
    parser.add_argument(
        "input_directory",
        nargs="?",
        default="data/raw/example",
        type=Path,
    )
    parser.add_argument(
        "--output-directory",
        default=OUTPUT_DIR / "step_04",
        type=Path,
    )
    args = parser.parse_args()

    bundle = load_input_bundle(args.input_directory)
    analysis = run_comps_analysis(bundle)
    args.output_directory.mkdir(parents=True, exist_ok=True)

    analysis.company_multiples.to_csv(
        args.output_directory / "company_multiples.csv", index=False
    )
    analysis.summary_statistics.to_csv(
        args.output_directory / "peer_summary_statistics.csv"
    )
    analysis.implied_valuation.to_csv(
        args.output_directory / "implied_valuation.csv", index=False
    )

    print(f"Comparable-company analysis complete for {bundle.target_ticker}")
    print(f"Outputs: {args.output_directory}")
    for warning in analysis.warnings:
        print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
