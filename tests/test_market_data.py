"""Tests for market quotes and the persistent provider cache."""

import json
from pathlib import Path
from typing import Any

import pytest

from valuation_tool.cache import JsonResponseCache
from valuation_tool.market_data import AlphaVantageClient, MarketDataError


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls = 0

    def get(self, *_args: Any, **_kwargs: Any) -> FakeResponse:
        self.calls += 1
        return FakeResponse(self.payload)


def quote_payload() -> dict[str, Any]:
    return {
        "Global Quote": {
            "01. symbol": "AAPL",
            "05. price": "245.5000",
            "06. volume": "12345678",
            "07. latest trading day": "2026-09-23",
        }
    }


def test_market_quote_is_normalized_and_cached(tmp_path: Path) -> None:
    session = FakeSession(quote_payload())
    cache = JsonResponseCache(tmp_path)
    client = AlphaVantageClient("secret-key", session=session, cache=cache)

    first = client.fetch_quote("aapl")
    second = client.fetch_quote("AAPL")

    assert first.price == pytest.approx(245.5)
    assert first.trading_day.isoformat() == "2026-09-23"
    assert first.volume == 12_345_678
    assert second == first
    assert session.calls == 1

    cache_file = next(tmp_path.rglob("*.json"))
    stored = json.loads(cache_file.read_text())
    assert "secret-key" not in cache_file.read_text()
    assert stored["source"] == "GLOBAL_QUOTE"


def test_refresh_bypasses_cache(tmp_path: Path) -> None:
    session = FakeSession(quote_payload())
    client = AlphaVantageClient(
        "secret-key", session=session, cache=JsonResponseCache(tmp_path)
    )

    client.fetch_quote("AAPL")
    client.fetch_quote("AAPL", refresh=True)

    assert session.calls == 2


def test_provider_messages_become_clear_errors() -> None:
    session = FakeSession({"Note": "Daily request limit reached"})
    client = AlphaVantageClient("secret-key", session=session)

    with pytest.raises(MarketDataError, match="Daily request limit"):
        client.fetch_quote("AAPL")


def test_incomplete_quote_is_rejected() -> None:
    client = AlphaVantageClient("secret-key", session=FakeSession({"Global Quote": {}}))

    with pytest.raises(MarketDataError, match="incomplete"):
        client.fetch_quote("AAPL")


def test_api_key_is_required() -> None:
    with pytest.raises(ValueError, match="API key"):
        AlphaVantageClient("  ")
