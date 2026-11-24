# Input Data Specification

The MVP uses four CSV files. All monetary values must use **USD millions**,
except per-share values. Percentages must be entered as decimals: `0.095`
means 9.5%. Capital expenditure is entered as a positive cash outflow.

The files in `data/raw/example/` are fictional and exist only to demonstrate
the model structure. They are not current market data or investment research.

## Dataset layout

```text
input-directory/
├── companies.csv
├── historical_financials.csv
├── dcf_forecast_assumptions.csv
└── valuation_assumptions.csv
```

Run validation from the project directory with:

```bash
.venv/bin/valuation-validate data/raw/example
```

Validation is all-or-nothing: any structural, type, or business-rule error
prevents the dataset from reaching a valuation engine.

## `companies.csv`

One row for the target and one row for each peer.

| Column | Type | Definition |
|---|---:|---|
| `ticker` | text | Unique uppercase security identifier |
| `company_name` | text | Display name |
| `role` | text | `target` or `peer`; exactly one target and 5–10 peers |
| `fiscal_year_end` | date | Latest completed fiscal year end, ISO `YYYY-MM-DD` |
| `valuation_date` | date | Date associated with market values |
| `currency` | text | Must be `USD` in the MVP |
| `sector` | text | Comparable operating sector or industry |
| `share_price` | number | Price per diluted share; must be positive |
| `diluted_shares` | number | Diluted shares outstanding, millions |
| `total_debt` | number | Interest-bearing debt, USD millions |
| `cash` | number | Cash and cash equivalents, USD millions |
| `non_controlling_interest` | number | Enterprise-value adjustment, USD millions |
| `preferred_stock` | number | Enterprise-value adjustment, USD millions |
| `investments` | number | Non-operating investments deducted from EV |

Enterprise value will later be calculated as market capitalization plus debt,
non-controlling interest, and preferred stock, less cash and investments.

## `historical_financials.csv`

Exactly three consecutive fiscal-year rows for every company.

| Column | Type | Definition |
|---|---:|---|
| `ticker` | text | Must exist in `companies.csv` |
| `fiscal_year` | integer | Four-digit completed fiscal year |
| `revenue` | number | Revenue; must be positive |
| `ebitda` | number | Earnings before interest, tax, D&A |
| `ebit` | number | Operating profit |
| `depreciation_amortization` | number | D&A; cannot be negative |
| `interest_expense` | number | Interest expense |
| `tax_expense` | number | Income-tax expense |
| `net_income` | number | Earnings attributable to common shareholders |
| `diluted_eps` | number | Diluted earnings per share |
| `capital_expenditure` | number | Positive cash outflow; cannot be negative |
| `change_nwc` | number | Increase in operating NWC; positive is a cash outflow |

Negative EBITDA, EBIT, net income, or EPS is permitted. The valuation engine
will treat the corresponding multiple as unavailable when its denominator is
not positive.

## `dcf_forecast_assumptions.csv`

Exactly five consecutive forecast-year rows for the target only.

| Column | Type | Definition |
|---|---:|---|
| `ticker` | text | Target ticker |
| `forecast_year` | integer | Forecast fiscal year |
| `revenue_growth` | decimal | Year-over-year revenue growth |
| `ebitda_margin` | decimal | EBITDA divided by revenue |
| `depreciation_amortization_pct_revenue` | decimal | D&A assumption |
| `tax_rate` | decimal | Marginal cash-tax rate |
| `capital_expenditure_pct_revenue` | decimal | Capital expenditure assumption |
| `change_nwc_pct_revenue` | decimal | Change in NWC as a percentage of revenue |

## `valuation_assumptions.csv`

Exactly one row for the target.

| Column | Type | Definition |
|---|---:|---|
| `ticker` | text | Target ticker |
| `wacc` | decimal | Weighted-average cost of capital; between 0% and 100% |
| `terminal_growth_rate` | decimal | Long-term growth; between -5% and 10% and below WACC |
| `terminal_ev_ebitda` | number | Positive terminal-year EBITDA multiple |

## Key validation rules

- All required files, columns, and values must be present.
- Tickers are normalized to uppercase; roles to lowercase.
- Numeric and date fields must parse cleanly.
- Exactly one target and five to ten peers are required.
- Every company must have three unique, consecutive historical years.
- The target must have five unique, consecutive forecast years.
- Terminal growth must be lower than WACC.
- Cross-file ticker references must be consistent.

