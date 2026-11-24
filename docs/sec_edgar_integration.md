# External Data Integration

Original Step 11 combines standardized annual US-GAAP facts from SEC EDGAR with
optional end-of-day market prices from Alpha Vantage. Provider responses are
cached locally and every import is saved to a timestamped raw-data snapshot.

The SEC states that `data.sec.gov` provides JSON submissions and XBRL data
without authentication or API keys. Automated clients must declare an
identifying User-Agent and comply with the SEC's fair-access policy, including
the current maximum rate of 10 requests per second.

Official references:

- [EDGAR Application Programming Interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [SEC Developer Resources](https://www.sec.gov/about/developer-resources)

## Configure your identity

Provide a real name or organization and a monitored contact email:

```bash
export SEC_USER_AGENT="Your Name your.email@example.com"
```

Do not commit personal contact information to the repository.

For optional end-of-day prices, create an Alpha Vantage API key and set:

```bash
export ALPHA_VANTAGE_API_KEY="your-key"
```

Alpha Vantage documents `GLOBAL_QUOTE` as a one-symbol quote endpoint. Its
default free response is end-of-day rather than realtime. The provider
currently states that its standard free service permits 25 requests per day,
so the cache avoids unnecessary repeat calls.

- [Alpha Vantage API documentation](https://www.alphavantage.co/documentation/)
- [Alpha Vantage API limits](https://www.alphavantage.co/support/)

## Import a target and peers

Pass the target first, followed by peer tickers:

```bash
valuation-sec AAPL MSFT GOOGL ORCL CRM ADBE
```

The importer writes:

- `historical_financials.csv`: canonical three-year financial table
- `sec_xbrl_provenance.csv`: exact taxonomy, concept, unit, and transformation
- `sec_company_reference.csv`: ticker, company name, CIK, and target/peer role
- `companies_draft.csv`: company template with available end-of-day prices
- `market_quote_provenance.csv`: provider, trading day, price, and volume
- `REVIEW_REQUIRED.txt`: mandatory completion and review instructions

By default, the command fails if a required metric is unavailable. Use
`--allow-missing` only to export partial data for manual completion and review.

## Metrics and transformations

The importer uses explicit fallback lists for standardized `us-gaap` concepts.
It imports revenue, operating income, D&A, interest expense, tax expense, net
income, diluted EPS, capital expenditure, and change in operating assets and
liabilities. It then:

- converts USD facts to USD millions;
- derives EBITDA as operating income plus D&A;
- retains diluted EPS as reported;
- converts capex to a positive model outflow; and
- reverses the operating-assets-and-liabilities fact to match the model's
  convention that positive change in NWC is a cash outflow.

## Caching and dated snapshots

Raw JSON responses are stored beneath `data/cache/` with provider, fetch time,
source label, and payload. Credentials are never written to cache metadata.
Fresh entries are reused for 24 hours unless `--refresh` is supplied.

Each command defaults to a UTC-stamped directory such as:

```text
data/raw/imports/20260924T053000Z/
```

This separates untouched provider snapshots from reviewed model inputs and
makes later reconciliation reproducible.

## Why some market inputs remain manual

SEC Company Facts contains filed financial-statement data, not an
analyst-approved peer group. Alpha Vantage supplies the available end-of-day
price and trading date. Diluted shares used for valuation, debt/cash
adjustments, sector classification, peer selection, and forecast assumptions
remain visible review fields. The Streamlit input editors provide the manual
override layer after the reviewed CSVs are assembled.

## Mandatory review

XBRL mappings differ across issuers and reporting periods. Before using an SEC
import in the valuation application:

1. reconcile each mapped concept to the filed 10-K;
2. review amended filings and fiscal-year boundaries;
3. confirm D&A and EBITDA construction;
4. confirm capex and working-capital signs; and
5. complete the remaining canonical input files from reviewed sources.

The importer is a research aid, not a substitute for filing review or a
licensed market-data service.
