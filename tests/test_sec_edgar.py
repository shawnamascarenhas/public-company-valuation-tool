"""Tests for SEC EDGAR integration without live network calls."""

from typing import Any

import pytest

from valuation_tool.sec_edgar import SECClient, SECDataError


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = iter(payloads)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse(next(self.payloads))


def annual_entries(values: list[float]) -> list[dict[str, Any]]:
    entries = []
    for year, value in zip((2023, 2024, 2025), values, strict=True):
        entries.append(
            {
                "start": f"{year}-01-01",
                "end": f"{year}-12-31",
                "val": value,
                "form": "10-K",
                "filed": f"{year + 1}-02-15",
            }
        )
    return entries


def concept(unit: str, values: list[float]) -> dict[str, Any]:
    return {"units": {unit: annual_entries(values)}}


def complete_company_facts() -> dict[str, Any]:
    millions = 1_000_000
    return {
        "entityName": "Example Corporation",
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": concept(
                    "USD", [1_000 * millions, 1_100 * millions, 1_200 * millions]
                ),
                "OperatingIncomeLoss": concept(
                    "USD", [160 * millions, 180 * millions, 210 * millions]
                ),
                "DepreciationDepletionAndAmortization": concept(
                    "USD", [30 * millions, 32 * millions, 35 * millions]
                ),
                "InterestExpenseNonOperating": concept(
                    "USD", [10 * millions, 11 * millions, 12 * millions]
                ),
                "IncomeTaxExpenseBenefit": concept(
                    "USD", [30 * millions, 34 * millions, 40 * millions]
                ),
                "NetIncomeLoss": concept(
                    "USD", [120 * millions, 135 * millions, 158 * millions]
                ),
                "EarningsPerShareDiluted": concept("USD/shares", [1.20, 1.35, 1.58]),
                "PaymentsToAcquirePropertyPlantAndEquipment": concept(
                    "USD", [38 * millions, 42 * millions, 45 * millions]
                ),
                "IncreaseDecreaseInOperatingAssetsAndLiabilities": concept(
                    "USD", [-8 * millions, -10 * millions, -12 * millions]
                ),
            }
        },
    }


def ticker_payload() -> dict[str, Any]:
    return {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [[123456, "Example Corporation", "EXM", "NYSE"]],
    }


def test_sec_import_maps_and_scales_annual_facts() -> None:
    session = FakeSession([ticker_payload(), complete_company_facts()])
    client = SECClient("Example Research analyst@example.com", session=session)

    imported = client.import_historicals("exm")
    latest = imported.historicals.set_index("fiscal_year").loc[2025]

    assert imported.ticker == "EXM"
    assert imported.cik == "0000123456"
    assert latest["revenue"] == pytest.approx(1_200.0)
    assert latest["ebit"] == pytest.approx(210.0)
    assert latest["ebitda"] == pytest.approx(245.0)
    assert latest["diluted_eps"] == pytest.approx(1.58)
    assert latest["capital_expenditure"] == pytest.approx(45.0)
    assert latest["change_nwc"] == pytest.approx(12.0)
    assert len(imported.provenance) == 9
    assert session.calls[0]["headers"]["User-Agent"].endswith("@example.com")


def test_strict_import_reports_missing_concepts() -> None:
    facts = complete_company_facts()
    del facts["facts"]["us-gaap"]["InterestExpenseNonOperating"]
    client = SECClient(
        "Example Research analyst@example.com",
        session=FakeSession([ticker_payload(), facts]),
    )

    with pytest.raises(SECDataError, match="interest_expense"):
        client.import_historicals("EXM", strict=True)


def test_non_strict_import_exports_partial_data() -> None:
    facts = complete_company_facts()
    del facts["facts"]["us-gaap"]["InterestExpenseNonOperating"]
    client = SECClient(
        "Example Research analyst@example.com",
        session=FakeSession([ticker_payload(), facts]),
    )

    imported = client.import_historicals("EXM", strict=False)

    assert imported.historicals["interest_expense"].isna().all()
    assert any("interest_expense" in warning for warning in imported.warnings)


def test_user_agent_must_contain_contact_email() -> None:
    with pytest.raises(ValueError, match="contact email"):
        SECClient("anonymous script")


def test_unknown_ticker_is_reported() -> None:
    client = SECClient(
        "Example Research analyst@example.com",
        session=FakeSession([ticker_payload()]),
    )

    with pytest.raises(SECDataError, match="Ticker not found"):
        client.resolve_ticker("NOPE")
