"""Comparable-company trading multiples and implied valuation ranges."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from valuation_tool.data_loader import InputBundle
from valuation_tool.valuation import (
    enterprise_to_equity_value,
    equity_to_enterprise_value,
    per_share_value,
)

MULTIPLE_COLUMNS = ("ev_revenue", "ev_ebitda", "pe")
STATISTICS = ("minimum", "25th_percentile", "median", "75th_percentile", "maximum")


@dataclass(frozen=True)
class CompsAnalysis:
    """Complete output of the comparable-company valuation engine."""

    company_multiples: pd.DataFrame
    peer_multiples: pd.DataFrame
    summary_statistics: pd.DataFrame
    implied_valuation: pd.DataFrame
    warnings: tuple[str, ...]


def _safe_multiple(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Return a multiple only where the denominator is strictly positive."""
    return numerator.div(denominator).where(denominator > 0, np.nan)


def calculate_trading_multiples(bundle: InputBundle) -> pd.DataFrame:
    """Calculate market values and latest-year trading multiples."""
    latest_indices = bundle.historicals.groupby("ticker")["fiscal_year"].idxmax()
    latest = bundle.historicals.loc[latest_indices].copy()

    frame = bundle.companies.merge(latest, on="ticker", how="left", validate="1:1")
    frame["market_capitalization"] = frame["share_price"] * frame["diluted_shares"]
    frame["enterprise_value"] = (
        frame["market_capitalization"]
        + frame["total_debt"]
        + frame["non_controlling_interest"]
        + frame["preferred_stock"]
        - frame["cash"]
        - frame["investments"]
    )
    frame["ev_revenue"] = _safe_multiple(frame["enterprise_value"], frame["revenue"])
    frame["ev_ebitda"] = _safe_multiple(frame["enterprise_value"], frame["ebitda"])
    frame["pe"] = _safe_multiple(frame["share_price"], frame["diluted_eps"])

    columns = [
        "ticker",
        "company_name",
        "role",
        "fiscal_year",
        "share_price",
        "diluted_shares",
        "market_capitalization",
        "enterprise_value",
        "revenue",
        "ebitda",
        "net_income",
        "diluted_eps",
        *MULTIPLE_COLUMNS,
    ]
    return frame.loc[:, columns].sort_values(["role", "ticker"]).reset_index(drop=True)


def calculate_peer_statistics(peer_multiples: pd.DataFrame) -> pd.DataFrame:
    """Calculate conventional peer-group valuation statistics."""
    rows: list[dict[str, float | str]] = []
    quantiles = {
        "minimum": 0.00,
        "25th_percentile": 0.25,
        "median": 0.50,
        "75th_percentile": 0.75,
        "maximum": 1.00,
    }
    for statistic, quantile in quantiles.items():
        row: dict[str, float | str] = {"statistic": statistic}
        for multiple in MULTIPLE_COLUMNS:
            row[multiple] = float(peer_multiples[multiple].dropna().quantile(quantile))
        rows.append(row)
    return pd.DataFrame(rows).set_index("statistic")


def _target_bridge_inputs(bundle: InputBundle) -> dict[str, float]:
    target = bundle.companies.loc[bundle.companies["role"] == "target"].iloc[0]
    return {
        "total_debt": float(target["total_debt"]),
        "cash": float(target["cash"]),
        "non_controlling_interest": float(target["non_controlling_interest"]),
        "preferred_stock": float(target["preferred_stock"]),
        "investments": float(target["investments"]),
    }


def calculate_implied_valuation(
    bundle: InputBundle,
    company_multiples: pd.DataFrame,
    summary_statistics: pd.DataFrame,
) -> pd.DataFrame:
    """Apply peer statistics to the target's latest financial metrics."""
    target = company_multiples.loc[company_multiples["role"] == "target"].iloc[0]
    bridge_inputs = _target_bridge_inputs(bundle)
    rows: list[dict[str, float | str]] = []

    for method in MULTIPLE_COLUMNS:
        for statistic in STATISTICS:
            selected_multiple = float(summary_statistics.loc[statistic, method])
            target_denominator = {
                "ev_revenue": float(target["revenue"]),
                "ev_ebitda": float(target["ebitda"]),
                "pe": float(target["diluted_eps"]),
            }[method]
            if target_denominator <= 0 or np.isnan(selected_multiple):
                implied_enterprise_value = np.nan
                implied_equity_value = np.nan
                implied_share_price = np.nan
            elif method == "ev_revenue":
                implied_enterprise_value = selected_multiple * float(target["revenue"])
                implied_equity_value = enterprise_to_equity_value(
                    implied_enterprise_value, **bridge_inputs
                )
                implied_share_price = per_share_value(
                    implied_equity_value, float(target["diluted_shares"])
                )
            elif method == "ev_ebitda":
                implied_enterprise_value = selected_multiple * float(target["ebitda"])
                implied_equity_value = enterprise_to_equity_value(
                    implied_enterprise_value, **bridge_inputs
                )
                implied_share_price = per_share_value(
                    implied_equity_value, float(target["diluted_shares"])
                )
            else:
                implied_share_price = selected_multiple * float(target["diluted_eps"])
                implied_equity_value = implied_share_price * float(
                    target["diluted_shares"]
                )
                implied_enterprise_value = equity_to_enterprise_value(
                    implied_equity_value, **bridge_inputs
                )

            current_share_price = float(target["share_price"])
            premium_discount = (
                implied_share_price / current_share_price - 1
                if not np.isnan(implied_share_price)
                else np.nan
            )
            rows.append(
                {
                    "method": method,
                    "statistic": statistic,
                    "selected_multiple": selected_multiple,
                    "implied_enterprise_value": implied_enterprise_value,
                    "implied_equity_value": implied_equity_value,
                    "implied_share_price": implied_share_price,
                    "current_share_price": current_share_price,
                    "premium_discount": premium_discount,
                }
            )

    return pd.DataFrame(rows)


def run_comps_analysis(bundle: InputBundle) -> CompsAnalysis:
    """Run the complete comparable-company analysis."""
    company_multiples = calculate_trading_multiples(bundle)
    peer_multiples = company_multiples.loc[
        company_multiples["role"] == "peer"
    ].reset_index(drop=True)
    summary = calculate_peer_statistics(peer_multiples)
    implied = calculate_implied_valuation(bundle, company_multiples, summary)

    warnings: list[str] = []
    target = company_multiples.loc[company_multiples["role"] == "target"].iloc[0]
    target_denominators = {
        "ev_revenue": target["revenue"],
        "ev_ebitda": target["ebitda"],
        "pe": target["diluted_eps"],
    }
    for multiple, denominator in target_denominators.items():
        if denominator <= 0:
            warnings.append(
                f"{multiple} implied valuation is unavailable because the target "
                "denominator is non-positive"
            )

    for multiple in MULTIPLE_COLUMNS:
        invalid = peer_multiples.loc[peer_multiples[multiple].isna(), "ticker"].tolist()
        if invalid:
            warnings.append(
                f"{multiple} is unavailable for peers with a non-positive denominator: "
                + ", ".join(invalid)
            )
        valid_count = int(peer_multiples[multiple].notna().sum())
        if valid_count < 3:
            warnings.append(
                f"{multiple} has only {valid_count} valid peers; "
                "interpret its range cautiously"
            )

    return CompsAnalysis(
        company_multiples=company_multiples,
        peer_multiples=peer_multiples,
        summary_statistics=summary,
        implied_valuation=implied,
        warnings=tuple(warnings),
    )
