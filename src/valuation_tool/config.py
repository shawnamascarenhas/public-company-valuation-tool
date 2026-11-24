"""Project-wide configuration values."""

from pathlib import Path

APP_NAME = "Public Company Valuation Tool"
HISTORICAL_YEARS = 3
FORECAST_YEARS = 5
MINIMUM_PEERS = 5
MAXIMUM_PEERS = 10

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
