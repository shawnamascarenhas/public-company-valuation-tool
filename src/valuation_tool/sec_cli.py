"""Command-line interface for importing SEC Company Facts."""

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from valuation_tool.cache import JsonResponseCache
from valuation_tool.config import CACHE_DIR, RAW_DATA_DIR
from valuation_tool.market_data import AlphaVantageClient, MarketDataError
from valuation_tool.sec_edgar import SECClient, SECDataError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import annual US-GAAP financials from SEC EDGAR"
    )
    parser.add_argument("tickers", nargs="+", help="Target first, then peer tickers")
    parser.add_argument(
        "--user-agent",
        default=os.getenv("SEC_USER_AGENT"),
        help="Required SEC identity, e.g. 'Your Name email@example.com'",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        help="Defaults to a timestamped directory under data/raw/imports",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Export partial data for manual completion instead of failing",
    )
    parser.add_argument(
        "--alpha-vantage-api-key",
        default=os.getenv("ALPHA_VANTAGE_API_KEY"),
        help="Optional key for end-of-day Global Quote prices",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh market quotes instead of using a fresh cache entry",
    )
    args = parser.parse_args()

    if not args.user_agent:
        parser.error("--user-agent or SEC_USER_AGENT is required by SEC policy")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_directory = args.output_directory or RAW_DATA_DIR / "imports" / timestamp
    cache = JsonResponseCache(CACHE_DIR)
    client = SECClient(args.user_agent, cache=cache)
    market_client = (
        AlphaVantageClient(args.alpha_vantage_api_key, cache=cache)
        if args.alpha_vantage_api_key
        else None
    )
    historicals: list[pd.DataFrame] = []
    provenance: list[pd.DataFrame] = []
    references: list[dict[str, str]] = []
    companies: list[dict[str, object]] = []
    quote_provenance: list[dict[str, object]] = []

    try:
        for position, ticker in enumerate(args.tickers):
            imported = client.import_historicals(ticker, strict=not args.allow_missing)
            historicals.append(imported.historicals)
            provenance.append(imported.provenance)
            references.append(
                {
                    "ticker": imported.ticker,
                    "company_name": imported.company_name,
                    "cik": imported.cik,
                    "role": "target" if position == 0 else "peer",
                }
            )
            share_price: float | None = None
            valuation_date: str | None = None
            if market_client:
                try:
                    quote = market_client.fetch_quote(
                        imported.ticker, refresh=args.refresh
                    )
                    share_price = quote.price
                    valuation_date = quote.trading_day.isoformat()
                    quote_provenance.append(
                        {
                            "ticker": quote.ticker,
                            "provider": quote.provider,
                            "freshness": quote.freshness,
                            "trading_day": quote.trading_day,
                            "price": quote.price,
                            "volume": quote.volume,
                        }
                    )
                except MarketDataError as exc:
                    print(f"Warning [{imported.ticker}]: {exc}")
            companies.append(
                {
                    "ticker": imported.ticker,
                    "company_name": imported.company_name,
                    "role": "target" if position == 0 else "peer",
                    "fiscal_year_end": None,
                    "valuation_date": valuation_date,
                    "currency": "USD",
                    "sector": "REVIEW_REQUIRED",
                    "share_price": share_price,
                    "diluted_shares": None,
                    "total_debt": None,
                    "cash": None,
                    "non_controlling_interest": 0.0,
                    "preferred_stock": 0.0,
                    "investments": 0.0,
                    "review_status": "Complete blank fields and verify all values",
                }
            )
            for warning in imported.warnings:
                print(f"Warning [{imported.ticker}]: {warning}")
    except SECDataError as exc:
        print(f"SEC import failed: {exc}")
        return 1

    output_directory.mkdir(parents=True, exist_ok=True)
    pd.concat(historicals, ignore_index=True).to_csv(
        output_directory / "historical_financials.csv", index=False
    )
    pd.concat(provenance, ignore_index=True).to_csv(
        output_directory / "sec_xbrl_provenance.csv", index=False
    )
    pd.DataFrame(references).to_csv(
        output_directory / "sec_company_reference.csv", index=False
    )
    pd.DataFrame(companies).to_csv(
        output_directory / "companies_draft.csv", index=False
    )
    if quote_provenance:
        pd.DataFrame(quote_provenance).to_csv(
            output_directory / "market_quote_provenance.csv", index=False
        )
    (output_directory / "REVIEW_REQUIRED.txt").write_text(
        "This is a dated raw-data snapshot, not a validated model input set.\n"
        "Complete blank company fields, verify XBRL mappings and signs against "
        "the 10-K, then copy reviewed files into a separate input directory.\n"
    )
    print(f"External-data snapshot complete: {output_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
