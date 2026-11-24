"""Canonical CSV schemas for valuation-model inputs."""

from dataclasses import dataclass

COMPANIES_FILE = "companies.csv"
HISTORICALS_FILE = "historical_financials.csv"
FORECAST_ASSUMPTIONS_FILE = "dcf_forecast_assumptions.csv"
VALUATION_ASSUMPTIONS_FILE = "valuation_assumptions.csv"

COMPANY_COLUMNS = (
    "ticker",
    "company_name",
    "role",
    "fiscal_year_end",
    "valuation_date",
    "currency",
    "sector",
    "share_price",
    "diluted_shares",
    "total_debt",
    "cash",
    "non_controlling_interest",
    "preferred_stock",
    "investments",
)

HISTORICAL_COLUMNS = (
    "ticker",
    "fiscal_year",
    "revenue",
    "ebitda",
    "ebit",
    "depreciation_amortization",
    "interest_expense",
    "tax_expense",
    "net_income",
    "diluted_eps",
    "capital_expenditure",
    "change_nwc",
)

FORECAST_ASSUMPTION_COLUMNS = (
    "ticker",
    "forecast_year",
    "revenue_growth",
    "ebitda_margin",
    "depreciation_amortization_pct_revenue",
    "tax_rate",
    "capital_expenditure_pct_revenue",
    "change_nwc_pct_revenue",
)

VALUATION_ASSUMPTION_COLUMNS = (
    "ticker",
    "wacc",
    "terminal_growth_rate",
    "terminal_ev_ebitda",
)


@dataclass(frozen=True)
class TableSchema:
    """Metadata describing one input table."""

    filename: str
    required_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...]
    date_columns: tuple[str, ...] = ()


SCHEMAS = {
    "companies": TableSchema(
        filename=COMPANIES_FILE,
        required_columns=COMPANY_COLUMNS,
        numeric_columns=(
            "share_price",
            "diluted_shares",
            "total_debt",
            "cash",
            "non_controlling_interest",
            "preferred_stock",
            "investments",
        ),
        date_columns=("fiscal_year_end", "valuation_date"),
    ),
    "historicals": TableSchema(
        filename=HISTORICALS_FILE,
        required_columns=HISTORICAL_COLUMNS,
        numeric_columns=HISTORICAL_COLUMNS[1:],
    ),
    "forecast_assumptions": TableSchema(
        filename=FORECAST_ASSUMPTIONS_FILE,
        required_columns=FORECAST_ASSUMPTION_COLUMNS,
        numeric_columns=FORECAST_ASSUMPTION_COLUMNS[1:],
    ),
    "valuation_assumptions": TableSchema(
        filename=VALUATION_ASSUMPTIONS_FILE,
        required_columns=VALUATION_ASSUMPTION_COLUMNS,
        numeric_columns=VALUATION_ASSUMPTION_COLUMNS[1:],
    ),
}
