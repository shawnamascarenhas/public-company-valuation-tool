"""Load and validate the four-table MVP input dataset."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from valuation_tool.config import FORECAST_YEARS, HISTORICAL_YEARS
from valuation_tool.schemas import SCHEMAS, TableSchema


class InputValidationError(ValueError):
    """Raised when one or more model-input validation rules fail."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("Input validation failed:\n- " + "\n- ".join(issues))


@dataclass(frozen=True)
class InputBundle:
    """Validated input tables used by downstream valuation engines."""

    companies: pd.DataFrame
    historicals: pd.DataFrame
    forecast_assumptions: pd.DataFrame
    valuation_assumptions: pd.DataFrame

    @property
    def target_ticker(self) -> str:
        return str(
            self.companies.loc[self.companies["role"] == "target", "ticker"].iloc[0]
        )

    @property
    def peer_tickers(self) -> list[str]:
        return self.companies.loc[self.companies["role"] == "peer", "ticker"].tolist()


def validate_input_bundle(bundle: InputBundle) -> None:
    """Validate an in-memory bundle, such as tables edited in the UI."""
    issues: list[str] = []
    tables = {
        "companies": bundle.companies,
        "historicals": bundle.historicals,
        "forecast_assumptions": bundle.forecast_assumptions,
        "valuation_assumptions": bundle.valuation_assumptions,
    }
    ready: dict[str, bool] = {}
    for name, frame in tables.items():
        schema = SCHEMAS[name]
        missing = [
            column for column in schema.required_columns if column not in frame.columns
        ]
        ready[name] = not missing
        if missing:
            issues.append(f"{schema.filename} is missing columns: {', '.join(missing)}")
            continue
        null_columns = [
            column for column in schema.required_columns if frame[column].isna().any()
        ]
        if null_columns:
            issues.append(
                f"{schema.filename} contains blank required values in: "
                + ", ".join(null_columns)
            )

    if ready["companies"]:
        issues.extend(_validate_companies(bundle.companies))
    if ready["companies"] and ready["historicals"]:
        issues.extend(_validate_historicals(bundle.historicals, bundle.companies))

    target_ticker: str | None = None
    if ready["companies"]:
        targets = bundle.companies.loc[bundle.companies["role"] == "target"]
        if len(targets) == 1:
            target_ticker = str(targets.iloc[0]["ticker"])
    if ready["forecast_assumptions"]:
        issues.extend(
            _validate_forecast_assumptions(bundle.forecast_assumptions, target_ticker)
        )
    if ready["valuation_assumptions"]:
        issues.extend(
            _validate_valuation_assumptions(bundle.valuation_assumptions, target_ticker)
        )

    if issues:
        raise InputValidationError(issues)


def _load_table(path: Path, schema: TableSchema) -> tuple[pd.DataFrame, list[str]]:
    issues: list[str] = []
    if not path.is_file():
        return pd.DataFrame(), [f"Missing required file: {schema.filename}"]

    try:
        frame = pd.read_csv(path)
    except Exception as exc:  # pandas exposes multiple parser/encoding exceptions
        return pd.DataFrame(), [f"Could not read {schema.filename}: {exc}"]

    missing = [
        column for column in schema.required_columns if column not in frame.columns
    ]
    if missing:
        return frame, [f"{schema.filename} is missing columns: {', '.join(missing)}"]

    frame = frame.loc[:, list(schema.required_columns)].copy()

    for column in ("ticker", "company_name", "role", "currency", "sector"):
        if column in frame:
            frame[column] = frame[column].astype("string").str.strip()
    if "ticker" in frame:
        frame["ticker"] = frame["ticker"].str.upper()
    if "role" in frame:
        frame["role"] = frame["role"].str.lower()
    if "currency" in frame:
        frame["currency"] = frame["currency"].str.upper()

    for column in schema.numeric_columns:
        converted = pd.to_numeric(frame[column], errors="coerce")
        bad_values = frame[column].notna() & converted.isna()
        if bad_values.any():
            rows = (frame.index[bad_values] + 2).tolist()
            issues.append(
                f"{schema.filename}.{column} has non-numeric values on CSV rows {rows}"
            )
        frame[column] = converted

    for column in schema.date_columns:
        converted = pd.to_datetime(frame[column], errors="coerce")
        bad_values = frame[column].notna() & converted.isna()
        if bad_values.any():
            rows = (frame.index[bad_values] + 2).tolist()
            issues.append(
                f"{schema.filename}.{column} has invalid dates on CSV rows {rows}"
            )
        frame[column] = converted

    null_columns = [
        column for column in schema.required_columns if frame[column].isna().any()
    ]
    if null_columns:
        joined_columns = ", ".join(null_columns)
        issues.append(
            f"{schema.filename} contains blank required values in: {joined_columns}"
        )

    return frame, issues


def _validate_companies(companies: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    if companies.empty:
        return issues

    if companies["ticker"].duplicated().any():
        issues.append("companies.csv must contain one row per ticker")

    invalid_roles = sorted(set(companies["role"].dropna()) - {"target", "peer"})
    if invalid_roles:
        issues.append(f"companies.csv has invalid roles: {invalid_roles}")

    target_count = int((companies["role"] == "target").sum())
    peer_count = int((companies["role"] == "peer").sum())
    if target_count != 1:
        issues.append(
            f"companies.csv requires exactly one target; found {target_count}"
        )
    if not 5 <= peer_count <= 10:
        issues.append(f"companies.csv requires 5 to 10 peers; found {peer_count}")

    if not companies["currency"].dropna().eq("USD").all():
        issues.append("MVP companies must report in USD")

    for column in ("share_price", "diluted_shares"):
        if (companies[column] <= 0).any():
            issues.append(f"companies.csv.{column} must be greater than zero")

    for column in (
        "total_debt",
        "cash",
        "non_controlling_interest",
        "preferred_stock",
        "investments",
    ):
        if (companies[column] < 0).any():
            issues.append(f"companies.csv.{column} cannot be negative")

    return issues


def _validate_historicals(
    historicals: pd.DataFrame, companies: pd.DataFrame
) -> list[str]:
    issues: list[str] = []
    if historicals.empty or companies.empty:
        return issues

    if historicals.duplicated(["ticker", "fiscal_year"]).any():
        issues.append("historical_financials.csv has duplicate ticker/fiscal_year rows")

    known = set(companies["ticker"])
    unknown = sorted(set(historicals["ticker"]) - known)
    if unknown:
        issues.append(f"historical_financials.csv has unknown tickers: {unknown}")

    for ticker in sorted(known):
        rows = historicals.loc[historicals["ticker"] == ticker]
        years = sorted(rows["fiscal_year"].dropna().astype(int).tolist())
        if len(years) != HISTORICAL_YEARS:
            found = len(years)
            issues.append(
                f"{ticker} requires {HISTORICAL_YEARS} historical years; found {found}"
            )
        elif years != list(range(years[0], years[0] + HISTORICAL_YEARS)):
            issues.append(f"{ticker} historical fiscal years must be consecutive")

    if (historicals["revenue"] <= 0).any():
        issues.append("historical_financials.csv.revenue must be greater than zero")
    if (historicals["depreciation_amortization"] < 0).any():
        issues.append("historical depreciation and amortization cannot be negative")
    if (historicals["capital_expenditure"] < 0).any():
        issues.append(
            "historical capital expenditure must be entered as a positive outflow"
        )

    return issues


def _validate_forecast_assumptions(
    assumptions: pd.DataFrame, target_ticker: str | None
) -> list[str]:
    issues: list[str] = []
    if assumptions.empty or target_ticker is None:
        return issues

    tickers = set(assumptions["ticker"])
    if tickers != {target_ticker}:
        issues.append(
            "dcf_forecast_assumptions.csv must contain only the target ticker"
        )

    if assumptions["forecast_year"].duplicated().any():
        issues.append("dcf forecast years must be unique")

    years = sorted(assumptions["forecast_year"].dropna().astype(int).tolist())
    if len(years) != FORECAST_YEARS:
        issues.append(
            f"DCF requires {FORECAST_YEARS} forecast years; found {len(years)}"
        )
    elif years != list(range(years[0], years[0] + FORECAST_YEARS)):
        issues.append("DCF forecast years must be consecutive")

    ranges = {
        "revenue_growth": (-1.0, 2.0),
        "ebitda_margin": (-1.0, 1.0),
        "depreciation_amortization_pct_revenue": (0.0, 1.0),
        "tax_rate": (0.0, 1.0),
        "capital_expenditure_pct_revenue": (0.0, 1.0),
        "change_nwc_pct_revenue": (-1.0, 1.0),
    }
    for column, (minimum, maximum) in ranges.items():
        if (
            assumptions[column].lt(minimum).any()
            or assumptions[column].gt(maximum).any()
        ):
            issues.append(
                f"dcf_forecast_assumptions.csv.{column} must be between "
                f"{minimum:.0%} and {maximum:.0%}"
            )

    return issues


def _validate_valuation_assumptions(
    assumptions: pd.DataFrame, target_ticker: str | None
) -> list[str]:
    issues: list[str] = []
    if assumptions.empty or target_ticker is None:
        return issues

    if len(assumptions) != 1 or set(assumptions["ticker"]) != {target_ticker}:
        issues.append(
            "valuation_assumptions.csv requires exactly one row for the target"
        )
        return issues

    row = assumptions.iloc[0]
    if not 0 < row["wacc"] < 1:
        issues.append("WACC must be between 0% and 100%")
    if not -0.05 <= row["terminal_growth_rate"] <= 0.10:
        issues.append("terminal growth must be between -5% and 10%")
    if row["terminal_growth_rate"] >= row["wacc"]:
        issues.append("terminal growth must be lower than WACC")
    if row["terminal_ev_ebitda"] <= 0:
        issues.append("terminal EV/EBITDA must be greater than zero")

    return issues


def load_input_bundle(input_directory: str | Path) -> InputBundle:
    """Load, normalize, and validate all model-input CSV files.

    Args:
        input_directory: Directory containing the four canonical CSV files.

    Raises:
        InputValidationError: If any structural or business rule fails.
    """
    directory = Path(input_directory)
    frames: dict[str, pd.DataFrame] = {}
    issues: list[str] = []

    for name, schema in SCHEMAS.items():
        frame, table_issues = _load_table(directory / schema.filename, schema)
        frames[name] = frame
        issues.extend(table_issues)

    companies = frames["companies"]
    historicals = frames["historicals"]
    forecast = frames["forecast_assumptions"]
    valuation = frames["valuation_assumptions"]

    companies_ready = set(SCHEMAS["companies"].required_columns).issubset(
        companies.columns
    )
    historicals_ready = set(SCHEMAS["historicals"].required_columns).issubset(
        historicals.columns
    )
    forecast_ready = set(SCHEMAS["forecast_assumptions"].required_columns).issubset(
        forecast.columns
    )
    valuation_ready = set(SCHEMAS["valuation_assumptions"].required_columns).issubset(
        valuation.columns
    )

    if companies_ready:
        issues.extend(_validate_companies(companies))
    if companies_ready and historicals_ready:
        issues.extend(_validate_historicals(historicals, companies))

    target_ticker: str | None = None
    if companies_ready and int((companies["role"] == "target").sum()) == 1:
        target_ticker = str(
            companies.loc[companies["role"] == "target", "ticker"].iloc[0]
        )

    if forecast_ready:
        issues.extend(_validate_forecast_assumptions(forecast, target_ticker))
    if valuation_ready:
        issues.extend(_validate_valuation_assumptions(valuation, target_ticker))

    if issues:
        raise InputValidationError(issues)

    return InputBundle(
        companies=companies.sort_values(["role", "ticker"]).reset_index(drop=True),
        historicals=historicals.sort_values(["ticker", "fiscal_year"]).reset_index(
            drop=True
        ),
        forecast_assumptions=forecast.sort_values("forecast_year").reset_index(
            drop=True
        ),
        valuation_assumptions=valuation.reset_index(drop=True),
    )
