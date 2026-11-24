# MVP Scope

## 1. Objective

Build a transparent and auditable public-company valuation application that
allows a user to value one target company using a manually selected peer group
and a five-year discounted cash-flow model.

The MVP should demonstrate financial reasoning, clean Python implementation,
and professional presentation. It is not intended to replace institutional
market-data platforms or provide investment advice.

## 2. Primary user journey

1. Select or enter one target company.
2. Enter five to ten comparable-company tickers.
3. Upload or enter historical financial and market data.
4. Review normalized inputs and visible data-quality warnings.
5. Review peer trading multiples and select a valuation statistic.
6. Enter or adjust five-year DCF assumptions.
7. Review implied enterprise value, equity value, and share price.
8. Compare valuation methods in sensitivity tables and a football field.
9. Download valuation tables and charts.

## 3. Included company universe

- US-listed public companies reporting primarily in USD
- Non-financial operating companies
- Companies with positive revenue and sufficient historical disclosure
- A target company plus five to ten manually selected peers

Financial institutions, insurers, banks, pre-revenue companies, and companies
requiring sector-specific valuation frameworks are excluded from the MVP.

## 4. Time periods

- Historical period: latest three completed fiscal years
- Forecast period: five fiscal years
- Valuation date: user-entered
- Market data: share price and diluted shares outstanding as of the valuation
  date, or the closest available date disclosed by the user

No quarterly or last-twelve-month normalization is required in the MVP.

## 5. Input data

### Target and peer identity

- Ticker
- Company name
- Fiscal year end
- Reporting currency
- Sector or industry

### Market and capital structure

- Share price
- Diluted shares outstanding
- Total debt
- Cash and cash equivalents
- Non-controlling interest, preferred stock, and investments as optional
  enterprise-value adjustments

### Historical financials

- Revenue
- EBITDA
- EBIT
- Depreciation and amortization
- Interest expense
- Tax expense or effective tax rate
- Net income
- Diluted EPS
- Capital expenditure
- Net working capital or change in net working capital

### DCF assumptions

- Revenue growth
- EBITDA margin
- Depreciation and amortization
- Tax rate
- Capital expenditure
- Change in net working capital
- WACC
- Terminal growth rate
- Terminal EV/EBITDA multiple

CSV upload and manual entry are the authoritative MVP input methods. External
API integration is deferred until the valuation engines have been validated.

## 6. Required calculations

### Comparable-company analysis

- Market capitalization
- Enterprise value
- EV/Revenue
- EV/EBITDA
- P/E
- Minimum, 25th percentile, median, 75th percentile, and maximum
- Implied target enterprise value
- Enterprise-value-to-equity-value bridge
- Implied equity value and share price

Invalid multiples must be displayed as unavailable rather than forced into the
peer statistics. Examples include P/E for a loss-making company and
EV/EBITDA when EBITDA is zero or negative.

### Discounted cash flow

- Five-year operating forecast
- EBIT after tax
- Unlevered free cash flow
- Present value of forecast cash flows
- Terminal value using the perpetuity-growth method
- Terminal value using the exit-multiple method
- Implied enterprise value
- Enterprise-value-to-equity-value bridge
- Implied equity value and share price

The application must reject a terminal growth rate greater than or equal to
WACC.

## 7. Required outputs

- Target-company overview
- Historical financial summary
- Peer-company trading-multiples table
- Peer-group summary statistics
- Implied valuation ranges by multiple
- Five-year DCF forecast
- DCF valuation summary under both terminal-value methods
- WACC versus terminal-growth sensitivity table
- WACC versus exit-multiple sensitivity table
- Football field showing implied share-price ranges
- Current share price as a reference point
- Downloadable valuation tables and charts
- Visible assumptions, data sources, and warnings

## 8. User-adjustable choices

- Peer group
- Valuation date and current share price
- Peer statistic used for valuation
- Forecast assumptions by year
- WACC
- Terminal growth rate
- Exit multiple
- Sensitivity-table ranges and increments

## 9. Explicit exclusions

The following are not part of the MVP:

- Automated peer selection
- Machine-learning forecasts
- Real-time market-data feeds
- Quarterly and last-twelve-month financials
- Multi-currency conversion
- Bank, insurance, REIT, or other sector-specific valuation models
- Precedent-transactions analysis
- Sum-of-the-parts valuation
- Merger, LBO, or accretion/dilution modeling
- User accounts, persistent cloud storage, and collaboration
- Automated investment recommendations

## 10. Validation and acceptance criteria

Step 1 is complete when the scope is documented and the following MVP success
criteria are fixed:

1. A user can value one eligible target against five to ten peers.
2. All peer multiples reconcile to independently calculated spreadsheet values
   within normal rounding tolerance.
3. Both DCF terminal-value approaches produce an enterprise value, equity
   value, and implied share price.
4. DCF outputs reconcile to an independently built spreadsheet case within
   0.1%, excluding presentation rounding.
5. Invalid denominators and missing inputs produce clear warnings rather than
   silent or misleading results.
6. Sensitivity tables update when the relevant assumptions change.
7. The football field presents comparable valuation ranges on a consistent
   per-share basis.
8. A user can trace every output to a visible input or formula.
9. A complete example valuation can be run without paid data access.
10. Automated tests cover the core valuation calculations before release.

## 11. MVP completion boundary

The MVP is complete when a reviewer can open the application, load the supplied
example dataset, adjust assumptions, reproduce the comps and DCF outputs, view
the valuation ranges, and download the results without editing Python code.

API-based data collection is an enhancement after this boundary, not a
condition for the MVP.

