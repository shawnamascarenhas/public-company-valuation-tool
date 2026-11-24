"""Optional Alpha Vantage end-of-day market quote integration."""

from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

from valuation_tool.cache import JsonResponseCache

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


class MarketDataError(RuntimeError):
    """Raised when a market-data response is unavailable or invalid."""


@dataclass(frozen=True)
class MarketQuote:
    """Normalized end-of-day equity quote."""

    ticker: str
    price: float
    trading_day: date
    volume: int | None
    provider: str = "Alpha Vantage"
    freshness: str = "end_of_day"


class AlphaVantageClient:
    """Fetch end-of-day Global Quote data with optional persistent caching."""

    def __init__(
        self,
        api_key: str,
        *,
        session: requests.Session | None = None,
        cache: JsonResponseCache | None = None,
        timeout: float = 20.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Alpha Vantage API key is required")
        self.api_key = api_key.strip()
        self.session = session or requests.Session()
        self.cache = cache
        self.timeout = timeout

    def _fetch_payload(self, ticker: str, refresh: bool) -> dict[str, Any]:
        cache_key = f"global_quote_{ticker}"
        if self.cache and not refresh:
            cached = self.cache.get("alpha_vantage", cache_key)
            if cached is not None:
                return cached

        try:
            response = self.session.get(
                ALPHA_VANTAGE_URL,
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": ticker,
                    "apikey": self.api_key,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise MarketDataError(
                f"Alpha Vantage request failed for {ticker}: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise MarketDataError(
                f"Alpha Vantage returned an invalid response for {ticker}"
            )
        for error_key in ("Error Message", "Note", "Information"):
            if payload.get(error_key):
                raise MarketDataError(f"Alpha Vantage: {payload[error_key]}")
        if self.cache:
            self.cache.set(
                "alpha_vantage",
                cache_key,
                payload,
                source="GLOBAL_QUOTE",
            )
        return payload

    def fetch_quote(self, ticker: str, *, refresh: bool = False) -> MarketQuote:
        """Return the latest end-of-day quote exposed by Global Quote."""
        normalized = ticker.strip().upper()
        payload = self._fetch_payload(normalized, refresh)
        quote = payload.get("Global Quote", {})
        try:
            returned_symbol = str(quote["01. symbol"]).upper()
            price = float(quote["05. price"])
            trading_day = date.fromisoformat(quote["07. latest trading day"])
            volume_text = quote.get("06. volume")
            volume = int(volume_text) if volume_text not in (None, "") else None
        except (KeyError, TypeError, ValueError) as exc:
            raise MarketDataError(
                f"Alpha Vantage Global Quote is incomplete for {normalized}"
            ) from exc
        if returned_symbol != normalized or price <= 0:
            raise MarketDataError(
                f"Alpha Vantage returned an invalid quote for {normalized}"
            )
        return MarketQuote(
            ticker=normalized,
            price=price,
            trading_day=trading_day,
            volume=volume,
        )
