"""SEC EDGAR Company Facts integration for annual US-GAAP financials."""

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
import requests

from valuation_tool.cache import JsonResponseCache

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


class SECDataError(RuntimeError):
    """Raised when SEC data cannot be fetched or mapped safely."""


@dataclass(frozen=True)
class SECCompanyData:
    """Normalized annual financials and their XBRL provenance."""

    ticker: str
    company_name: str
    cik: str
    historicals: pd.DataFrame
    provenance: pd.DataFrame
    warnings: tuple[str, ...]


CONCEPTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "revenue": (
        (
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ),
        ("USD",),
    ),
    "ebit": (("OperatingIncomeLoss",), ("USD",)),
    "depreciation_amortization": (
        (
            "DepreciationDepletionAndAmortization",
            "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
            "DepreciationDepletionAndAmortizationPropertyPlantAndEquipmentAndIntangibleAssets",
        ),
        ("USD",),
    ),
    "interest_expense": (
        ("InterestExpenseNonOperating", "InterestExpenseDebt", "InterestExpense"),
        ("USD",),
    ),
    "tax_expense": (("IncomeTaxExpenseBenefit",), ("USD",)),
    "net_income": (
        (
            "NetIncomeLoss",
            "ProfitLoss",
            "NetIncomeLossAvailableToCommonStockholdersBasic",
        ),
        ("USD",),
    ),
    "diluted_eps": (("EarningsPerShareDiluted",), ("USD/shares", "USD-per-shares")),
    "capital_expenditure": (
        (
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsForAdditionsToPropertyPlantAndEquipment",
        ),
        ("USD",),
    ),
    "change_nwc": (
        (
            "IncreaseDecreaseInOperatingAssetsAndLiabilities",
            "IncreaseDecreaseInOperatingCapital",
        ),
        ("USD",),
    ),
}


def _duration_days(fact: dict[str, Any]) -> int | None:
    if not fact.get("start") or not fact.get("end"):
        return None
    try:
        return (
            date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])
        ).days
    except ValueError:
        return None


def _annual_facts(entries: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Select the latest-filed annual 10-K fact for each fiscal end year."""
    candidates: list[dict[str, Any]] = []
    for fact in entries:
        duration = _duration_days(fact)
        if fact.get("form") not in {"10-K", "10-K/A"}:
            continue
        if duration is None or not 300 <= duration <= 430:
            continue
        try:
            fiscal_year = date.fromisoformat(fact["end"]).year
            filed = date.fromisoformat(fact["filed"])
        except (KeyError, ValueError):
            continue
        normalized = dict(fact)
        normalized["_fiscal_year"] = fiscal_year
        normalized["_filed_date"] = filed
        candidates.append(normalized)

    selected: dict[int, dict[str, Any]] = {}
    for fact in sorted(candidates, key=lambda item: item["_filed_date"]):
        selected[fact["_fiscal_year"]] = fact
    return selected


def _extract_metric(
    company_facts: dict[str, Any],
    concepts: tuple[str, ...],
    units: tuple[str, ...],
) -> tuple[dict[int, float], str, str] | None:
    us_gaap = company_facts.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        concept_data = us_gaap.get(concept)
        if not concept_data:
            continue
        available_units = concept_data.get("units", {})
        for unit in units:
            entries = available_units.get(unit)
            if not entries:
                continue
            annual = _annual_facts(entries)
            if annual:
                values = {year: float(fact["val"]) for year, fact in annual.items()}
                return values, concept, unit
    return None


class SECClient:
    """Small SEC client with declared identity and bounded request timeouts."""

    def __init__(
        self,
        user_agent: str,
        *,
        session: requests.Session | None = None,
        cache: JsonResponseCache | None = None,
        timeout: float = 20.0,
    ) -> None:
        if "@" not in user_agent or len(user_agent.strip()) < 8:
            raise ValueError(
                "SEC User-Agent must identify an organization and contact email"
            )
        self.session = session or requests.Session()
        self.cache = cache
        self.timeout = timeout
        self.headers = {
            "User-Agent": user_agent.strip(),
            "Accept-Encoding": "gzip, deflate",
        }
        self._ticker_index: dict[str, tuple[str, str]] | None = None

    def _get_json(self, url: str, cache_key: str) -> dict[str, Any]:
        if self.cache:
            cached = self.cache.get("sec_edgar", cache_key)
            if cached is not None:
                return cached
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise SECDataError(f"SEC request failed for {url}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SECDataError(f"SEC returned an unexpected response for {url}")
        if self.cache:
            self.cache.set("sec_edgar", cache_key, payload, source=url)
        return payload

    def ticker_index(self) -> dict[str, tuple[str, str]]:
        """Map uppercase ticker to zero-padded CIK and company name."""
        if self._ticker_index is not None:
            return self._ticker_index
        payload = self._get_json(SEC_TICKERS_URL, "company_tickers_exchange")
        fields = payload.get("fields", [])
        data = payload.get("data", [])
        try:
            cik_index = fields.index("cik")
            name_index = fields.index("name")
            ticker_index = fields.index("ticker")
        except ValueError as exc:
            raise SECDataError("SEC ticker file has an unexpected schema") from exc

        self._ticker_index = {
            str(row[ticker_index]).upper(): (
                str(row[cik_index]).zfill(10),
                str(row[name_index]),
            )
            for row in data
            if row[ticker_index]
        }
        return self._ticker_index

    def resolve_ticker(self, ticker: str) -> tuple[str, str]:
        """Resolve a ticker to CIK and SEC company name."""
        normalized = ticker.strip().upper()
        try:
            return self.ticker_index()[normalized]
        except KeyError as exc:
            raise SECDataError(
                f"Ticker not found in SEC company index: {normalized}"
            ) from exc

    def fetch_company_facts(self, cik: str) -> dict[str, Any]:
        """Fetch all standardized XBRL facts for a CIK."""
        normalized_cik = str(cik).zfill(10)
        return self._get_json(
            SEC_COMPANY_FACTS_URL.format(cik=normalized_cik),
            f"companyfacts_{normalized_cik}",
        )

    def import_historicals(
        self,
        ticker: str,
        *,
        years: int = 3,
        strict: bool = True,
    ) -> SECCompanyData:
        """Import canonical annual financials for one US-listed company."""
        if years <= 0:
            raise ValueError("years must be positive")
        normalized_ticker = ticker.strip().upper()
        cik, index_name = self.resolve_ticker(normalized_ticker)
        company_facts = self.fetch_company_facts(cik)
        company_name = str(company_facts.get("entityName") or index_name)

        extracted: dict[str, dict[int, float]] = {}
        provenance_rows: list[dict[str, str]] = []
        missing: list[str] = []
        for metric, (concepts, units) in CONCEPTS.items():
            result = _extract_metric(company_facts, concepts, units)
            if result is None:
                missing.append(metric)
                continue
            values, concept, unit = result
            extracted[metric] = values
            provenance_rows.append(
                {
                    "ticker": normalized_ticker,
                    "metric": metric,
                    "taxonomy": "us-gaap",
                    "concept": concept,
                    "unit": unit,
                    "transformation": (
                        "divide by 1,000,000"
                        if unit == "USD" and metric != "diluted_eps"
                        else "as reported"
                    ),
                }
            )

        if "revenue" not in extracted:
            raise SECDataError(
                f"No supported annual revenue concept found for {normalized_ticker}"
            )

        fiscal_years = sorted(extracted["revenue"], reverse=True)[:years]
        if len(fiscal_years) < years:
            raise SECDataError(
                f"Only {len(fiscal_years)} annual revenue periods found for "
                f"{normalized_ticker}; {years} required"
            )

        required_metrics = set(CONCEPTS)
        gaps = sorted(
            metric
            for metric in required_metrics
            if metric not in extracted
            or any(year not in extracted[metric] for year in fiscal_years)
        )
        if strict and gaps:
            raise SECDataError(
                f"SEC facts are incomplete for {normalized_ticker}: {', '.join(gaps)}. "
                "Use non-strict mode to export available fields for manual review."
            )

        rows: list[dict[str, float | int | str]] = []
        for fiscal_year in sorted(fiscal_years):
            values: dict[str, float] = {}
            for metric in required_metrics:
                raw_value = extracted.get(metric, {}).get(fiscal_year, float("nan"))
                values[metric] = (
                    raw_value / 1_000_000
                    if metric != "diluted_eps" and pd.notna(raw_value)
                    else raw_value
                )
            if pd.notna(values["change_nwc"]):
                values["change_nwc"] *= -1
            rows.append(
                {
                    "ticker": normalized_ticker,
                    "fiscal_year": fiscal_year,
                    "revenue": values["revenue"],
                    "ebitda": values["ebit"] + values["depreciation_amortization"],
                    "ebit": values["ebit"],
                    "depreciation_amortization": values["depreciation_amortization"],
                    "interest_expense": values["interest_expense"],
                    "tax_expense": values["tax_expense"],
                    "net_income": values["net_income"],
                    "diluted_eps": values["diluted_eps"],
                    "capital_expenditure": abs(values["capital_expenditure"]),
                    "change_nwc": values["change_nwc"],
                }
            )

        warnings = [
            "Review XBRL concept mappings and signs against the filed 10-K "
            "before valuation.",
            "EBITDA is derived as operating income plus reported D&A.",
            "Change in NWC reverses the SEC cash-flow fact to match the "
            "model's positive-outflow convention.",
        ]
        if missing or gaps:
            warnings.append(
                "Missing or incomplete metrics: "
                + ", ".join(sorted(set(missing + gaps)))
            )

        return SECCompanyData(
            ticker=normalized_ticker,
            company_name=company_name,
            cik=cik,
            historicals=pd.DataFrame(rows),
            provenance=pd.DataFrame(provenance_rows),
            warnings=tuple(warnings),
        )
