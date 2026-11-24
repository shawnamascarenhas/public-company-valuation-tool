"""Command-line interface for validating an input dataset."""

import argparse
from pathlib import Path

from valuation_tool.data_loader import InputValidationError, load_input_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate valuation input CSV files")
    parser.add_argument(
        "input_directory",
        nargs="?",
        default="data/raw/example",
        type=Path,
        help="Directory containing the four model-input CSV files",
    )
    args = parser.parse_args()

    try:
        bundle = load_input_bundle(args.input_directory)
    except InputValidationError as exc:
        print(exc)
        return 1

    print(f"Valid dataset: {args.input_directory}")
    print(f"Target: {bundle.target_ticker}")
    print(f"Peers: {', '.join(bundle.peer_tickers)}")
    print(f"Historical rows: {len(bundle.historicals)}")
    print(f"Forecast years: {len(bundle.forecast_assumptions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
