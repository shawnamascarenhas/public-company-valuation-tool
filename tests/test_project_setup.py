"""Smoke tests for the initial application scaffold."""

from valuation_tool import __version__
from valuation_tool.config import (
    FORECAST_YEARS,
    HISTORICAL_YEARS,
    MAXIMUM_PEERS,
    MINIMUM_PEERS,
    PROJECT_ROOT,
)


def test_package_version() -> None:
    assert __version__ == "1.0.0"


def test_mvp_configuration() -> None:
    assert HISTORICAL_YEARS == 3
    assert FORECAST_YEARS == 5
    assert MINIMUM_PEERS == 5
    assert MAXIMUM_PEERS == 10


def test_project_root_contains_readme() -> None:
    assert (PROJECT_ROOT / "README.md").is_file()
