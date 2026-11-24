"""DCF sensitivity tables and consolidated valuation ranges."""

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from valuation_tool.data_loader import InputBundle
from valuation_tool.dcf import (
    build_unlevered_forecast,
    calculate_terminal_values,
    discount_forecast,
)
from valuation_tool.multiples import CompsAnalysis
from valuation_tool.valuation import enterprise_to_equity_value, per_share_value


@dataclass(frozen=True)
class SensitivityAnalysis:
    """DCF sensitivity grids and football-field source data."""

    perpetuity_growth: pd.DataFrame
    exit_multiple: pd.DataFrame
    football_field: pd.DataFrame
    current_share_price: float


def default_sensitivity_inputs(bundle: InputBundle) -> dict[str, list[float]]:
    """Return symmetric five-point grids around the base assumptions."""
    assumptions = bundle.valuation_assumptions.iloc[0]
    base_wacc = float(assumptions["wacc"])
    base_growth = float(assumptions["terminal_growth_rate"])
    base_multiple = float(assumptions["terminal_ev_ebitda"])
    return {
        "wacc_values": [
            round(base_wacc + offset, 6) for offset in (-0.02, -0.01, 0, 0.01, 0.02)
        ],
        "growth_values": [
            round(base_growth + offset, 6) for offset in (-0.01, -0.005, 0, 0.005, 0.01)
        ],
        "exit_multiples": [
            round(base_multiple + offset, 6) for offset in (-2, -1, 0, 1, 2)
        ],
    }


def _validate_grid(values: Iterable[float], name: str) -> list[float]:
    grid = sorted({float(value) for value in values})
    if not grid:
        raise ValueError(f"{name} must contain at least one value")
    return grid


def _bridge_inputs(bundle: InputBundle) -> tuple[dict[str, float], float]:
    target = bundle.companies.loc[bundle.companies["role"] == "target"].iloc[0]
    bridge = {
        "total_debt": float(target["total_debt"]),
        "cash": float(target["cash"]),
        "non_controlling_interest": float(target["non_controlling_interest"]),
        "preferred_stock": float(target["preferred_stock"]),
        "investments": float(target["investments"]),
    }
    return bridge, float(target["diluted_shares"])


def build_perpetuity_growth_sensitivity(
    bundle: InputBundle,
    wacc_values: Iterable[float],
    growth_values: Iterable[float],
) -> pd.DataFrame:
    """Calculate implied share price for every WACC/growth combination."""
    wacc_grid = _validate_grid(wacc_values, "wacc_values")
    growth_grid = _validate_grid(growth_values, "growth_values")
    if min(wacc_grid) <= max(growth_grid):
        raise ValueError("Every WACC sensitivity must exceed every growth sensitivity")

    base_forecast = build_unlevered_forecast(bundle)
    bridge, diluted_shares = _bridge_inputs(bundle)
    rows: list[list[float]] = []

    for wacc in wacc_grid:
        forecast = discount_forecast(base_forecast, wacc)
        present_value_forecast = float(forecast["present_value_fcff"].sum())
        row: list[float] = []
        for growth in growth_grid:
            terminals = calculate_terminal_values(
                forecast,
                wacc=wacc,
                terminal_growth_rate=growth,
                terminal_ev_ebitda=1.0,
            )
            present_value_terminal = float(
                terminals.loc[
                    terminals["method"] == "perpetuity_growth",
                    "present_value_terminal",
                ].iloc[0]
            )
            enterprise_value = present_value_forecast + present_value_terminal
            equity_value = enterprise_to_equity_value(enterprise_value, **bridge)
            row.append(per_share_value(equity_value, diluted_shares))
        rows.append(row)

    return pd.DataFrame(
        rows,
        index=pd.Index(wacc_grid, name="wacc"),
        columns=pd.Index(growth_grid, name="terminal_growth_rate"),
    )


def build_exit_multiple_sensitivity(
    bundle: InputBundle,
    wacc_values: Iterable[float],
    exit_multiples: Iterable[float],
) -> pd.DataFrame:
    """Calculate implied share price for every WACC/exit-multiple combination."""
    wacc_grid = _validate_grid(wacc_values, "wacc_values")
    multiple_grid = _validate_grid(exit_multiples, "exit_multiples")
    if min(wacc_grid) <= 0 or max(wacc_grid) >= 1:
        raise ValueError("WACC sensitivities must be between 0% and 100%")
    if min(multiple_grid) <= 0:
        raise ValueError("Exit-multiple sensitivities must be positive")

    base_growth = float(bundle.valuation_assumptions.iloc[0]["terminal_growth_rate"])
    base_forecast = build_unlevered_forecast(bundle)
    bridge, diluted_shares = _bridge_inputs(bundle)
    rows: list[list[float]] = []

    for wacc in wacc_grid:
        forecast = discount_forecast(base_forecast, wacc)
        present_value_forecast = float(forecast["present_value_fcff"].sum())
        row: list[float] = []
        for multiple in multiple_grid:
            terminals = calculate_terminal_values(
                forecast,
                wacc=wacc,
                terminal_growth_rate=base_growth,
                terminal_ev_ebitda=multiple,
            )
            present_value_terminal = float(
                terminals.loc[
                    terminals["method"] == "exit_multiple",
                    "present_value_terminal",
                ].iloc[0]
            )
            enterprise_value = present_value_forecast + present_value_terminal
            equity_value = enterprise_to_equity_value(enterprise_value, **bridge)
            row.append(per_share_value(equity_value, diluted_shares))
        rows.append(row)

    return pd.DataFrame(
        rows,
        index=pd.Index(wacc_grid, name="wacc"),
        columns=pd.Index(multiple_grid, name="terminal_ev_ebitda"),
    )


def build_football_field_data(
    comps: CompsAnalysis,
    perpetuity_sensitivity: pd.DataFrame,
    exit_sensitivity: pd.DataFrame,
) -> pd.DataFrame:
    """Create consistent low/high per-share ranges for each valuation method."""
    rows: list[dict[str, float | str]] = []
    labels = {
        "ev_revenue": "EV / Revenue",
        "ev_ebitda": "EV / EBITDA",
        "pe": "Price / Earnings",
    }
    for method, label in labels.items():
        values = comps.implied_valuation.loc[
            (comps.implied_valuation["method"] == method)
            & comps.implied_valuation["statistic"].isin(
                ["25th_percentile", "75th_percentile"]
            ),
            "implied_share_price",
        ]
        rows.append(
            {
                "method": label,
                "low": float(values.min()),
                "high": float(values.max()),
                "midpoint": float(values.mean()),
                "range_basis": "25th to 75th peer percentile",
            }
        )

    for label, table in (
        ("DCF — Perpetuity Growth", perpetuity_sensitivity),
        ("DCF — Exit Multiple", exit_sensitivity),
    ):
        low = float(table.min().min())
        high = float(table.max().max())
        rows.append(
            {
                "method": label,
                "low": low,
                "high": high,
                "midpoint": (low + high) / 2,
                "range_basis": "Full sensitivity grid",
            }
        )

    return pd.DataFrame(rows)


def run_sensitivity_analysis(
    bundle: InputBundle, comps: CompsAnalysis
) -> SensitivityAnalysis:
    """Run default sensitivity tables and consolidate valuation ranges."""
    grids = default_sensitivity_inputs(bundle)
    perpetuity = build_perpetuity_growth_sensitivity(
        bundle, grids["wacc_values"], grids["growth_values"]
    )
    exit_multiple = build_exit_multiple_sensitivity(
        bundle, grids["wacc_values"], grids["exit_multiples"]
    )
    football_field = build_football_field_data(comps, perpetuity, exit_multiple)
    target = bundle.companies.loc[bundle.companies["role"] == "target"].iloc[0]
    return SensitivityAnalysis(
        perpetuity_growth=perpetuity,
        exit_multiple=exit_multiple,
        football_field=football_field,
        current_share_price=float(target["share_price"]),
    )
