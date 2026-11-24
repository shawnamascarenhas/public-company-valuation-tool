"""Tests for the Step 3 input schema and validation rules."""

from pathlib import Path
from shutil import copytree

import pandas as pd
import pytest

from valuation_tool.config import RAW_DATA_DIR
from valuation_tool.data_loader import InputValidationError, load_input_bundle

EXAMPLE_DIR = RAW_DATA_DIR / "example"


def copy_example(tmp_path: Path) -> Path:
    destination = tmp_path / "input"
    copytree(EXAMPLE_DIR, destination)
    return destination


def test_example_dataset_loads_and_normalizes() -> None:
    bundle = load_input_bundle(EXAMPLE_DIR)

    assert bundle.target_ticker == "ALPH"
    assert bundle.peer_tickers == ["BRVO", "CRWN", "DLTA", "ECHO", "FLUX"]
    assert len(bundle.companies) == 6
    assert len(bundle.historicals) == 18
    assert len(bundle.forecast_assumptions) == 5
    assert pd.api.types.is_datetime64_any_dtype(bundle.companies["valuation_date"])


def test_terminal_growth_must_be_below_wacc(tmp_path: Path) -> None:
    input_dir = copy_example(tmp_path)
    path = input_dir / "valuation_assumptions.csv"
    assumptions = pd.read_csv(path)
    assumptions.loc[0, "terminal_growth_rate"] = assumptions.loc[0, "wacc"]
    assumptions.to_csv(path, index=False)

    with pytest.raises(InputValidationError, match="terminal growth must be lower"):
        load_input_bundle(input_dir)


def test_missing_required_column_is_reported(tmp_path: Path) -> None:
    input_dir = copy_example(tmp_path)
    path = input_dir / "companies.csv"
    companies = pd.read_csv(path).drop(columns="share_price")
    companies.to_csv(path, index=False)

    with pytest.raises(InputValidationError, match="missing columns: share_price"):
        load_input_bundle(input_dir)


def test_unknown_historical_ticker_is_reported(tmp_path: Path) -> None:
    input_dir = copy_example(tmp_path)
    path = input_dir / "historical_financials.csv"
    historicals = pd.read_csv(path)
    historicals.loc[0, "ticker"] = "UNKNOWN"
    historicals.to_csv(path, index=False)

    with pytest.raises(InputValidationError, match="unknown tickers"):
        load_input_bundle(input_dir)


def test_peer_count_is_enforced(tmp_path: Path) -> None:
    input_dir = copy_example(tmp_path)
    companies_path = input_dir / "companies.csv"
    historicals_path = input_dir / "historical_financials.csv"
    companies = pd.read_csv(companies_path)
    historicals = pd.read_csv(historicals_path)
    companies = companies.loc[companies["ticker"] != "FLUX"]
    historicals = historicals.loc[historicals["ticker"] != "FLUX"]
    companies.to_csv(companies_path, index=False)
    historicals.to_csv(historicals_path, index=False)

    with pytest.raises(InputValidationError, match="requires 5 to 10 peers; found 4"):
        load_input_bundle(input_dir)
