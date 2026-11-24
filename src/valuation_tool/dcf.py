"""Five-year unlevered discounted cash-flow valuation engine."""

from dataclasses import dataclass

import pandas as pd

from valuation_tool.data_loader import InputBundle
from valuation_tool.valuation import enterprise_to_equity_value, per_share_value


@dataclass(frozen=True)
class DCFAnalysis:
    """Complete output of the discounted cash-flow engine."""

    forecast: pd.DataFrame
    valuation_summary: pd.DataFrame
    warnings: tuple[str, ...]


def build_unlevered_forecast(bundle: InputBundle) -> pd.DataFrame:
    """Build revenue, operating profit, and FCFF for five forecast years."""
    target_ticker = bundle.target_ticker
    target_historicals = bundle.historicals.loc[
        bundle.historicals["ticker"] == target_ticker
    ]
    latest = target_historicals.loc[target_historicals["fiscal_year"].idxmax()]
    assumptions = bundle.forecast_assumptions.sort_values("forecast_year")

    prior_revenue = float(latest["revenue"])
    rows: list[dict[str, float | int | str]] = []

    for period, assumption in enumerate(assumptions.itertuples(index=False), start=1):
        revenue = prior_revenue * (1 + float(assumption.revenue_growth))
        ebitda = revenue * float(assumption.ebitda_margin)
        depreciation_amortization = revenue * float(
            assumption.depreciation_amortization_pct_revenue
        )
        ebit = ebitda - depreciation_amortization
        nopat = ebit * (1 - float(assumption.tax_rate))
        capital_expenditure = revenue * float(
            assumption.capital_expenditure_pct_revenue
        )
        change_nwc = revenue * float(assumption.change_nwc_pct_revenue)
        fcff = nopat + depreciation_amortization - capital_expenditure - change_nwc

        rows.append(
            {
                "ticker": target_ticker,
                "forecast_year": int(assumption.forecast_year),
                "period": period,
                "revenue_growth": float(assumption.revenue_growth),
                "revenue": revenue,
                "ebitda_margin": float(assumption.ebitda_margin),
                "ebitda": ebitda,
                "depreciation_amortization": depreciation_amortization,
                "ebit": ebit,
                "tax_rate": float(assumption.tax_rate),
                "nopat": nopat,
                "capital_expenditure": capital_expenditure,
                "change_nwc": change_nwc,
                "fcff": fcff,
            }
        )
        prior_revenue = revenue

    return pd.DataFrame(rows)


def discount_forecast(forecast: pd.DataFrame, wacc: float) -> pd.DataFrame:
    """Apply end-of-year discounting to forecast free cash flow."""
    if not 0 < wacc < 1:
        raise ValueError("WACC must be between 0% and 100%")

    discounted = forecast.copy()
    discounted["discount_factor"] = 1 / (1 + wacc) ** discounted["period"]
    discounted["present_value_fcff"] = (
        discounted["fcff"] * discounted["discount_factor"]
    )
    return discounted


def calculate_terminal_values(
    forecast: pd.DataFrame,
    *,
    wacc: float,
    terminal_growth_rate: float,
    terminal_ev_ebitda: float,
) -> pd.DataFrame:
    """Calculate terminal values under perpetuity-growth and exit-multiple methods."""
    if terminal_growth_rate >= wacc:
        raise ValueError("Terminal growth rate must be lower than WACC")
    if terminal_ev_ebitda <= 0:
        raise ValueError("Terminal EV/EBITDA must be greater than zero")

    final_year = forecast.iloc[-1]
    final_discount_factor = float(final_year["discount_factor"])
    perpetuity_terminal_value = (
        float(final_year["fcff"]) * (1 + terminal_growth_rate)
    ) / (wacc - terminal_growth_rate)
    exit_multiple_terminal_value = float(final_year["ebitda"]) * terminal_ev_ebitda

    return pd.DataFrame(
        [
            {
                "method": "perpetuity_growth",
                "terminal_assumption": terminal_growth_rate,
                "terminal_value": perpetuity_terminal_value,
                "present_value_terminal": (
                    perpetuity_terminal_value * final_discount_factor
                ),
            },
            {
                "method": "exit_multiple",
                "terminal_assumption": terminal_ev_ebitda,
                "terminal_value": exit_multiple_terminal_value,
                "present_value_terminal": (
                    exit_multiple_terminal_value * final_discount_factor
                ),
            },
        ]
    )


def _target_bridge_inputs(bundle: InputBundle) -> dict[str, float]:
    target = bundle.companies.loc[bundle.companies["role"] == "target"].iloc[0]
    return {
        "total_debt": float(target["total_debt"]),
        "cash": float(target["cash"]),
        "non_controlling_interest": float(target["non_controlling_interest"]),
        "preferred_stock": float(target["preferred_stock"]),
        "investments": float(target["investments"]),
    }


def run_dcf_analysis(bundle: InputBundle) -> DCFAnalysis:
    """Run the forecast, terminal-value, and equity-value calculations."""
    assumptions = bundle.valuation_assumptions.iloc[0]
    wacc = float(assumptions["wacc"])
    terminal_growth_rate = float(assumptions["terminal_growth_rate"])
    terminal_ev_ebitda = float(assumptions["terminal_ev_ebitda"])

    forecast = discount_forecast(build_unlevered_forecast(bundle), wacc)
    terminal_values = calculate_terminal_values(
        forecast,
        wacc=wacc,
        terminal_growth_rate=terminal_growth_rate,
        terminal_ev_ebitda=terminal_ev_ebitda,
    )

    target = bundle.companies.loc[bundle.companies["role"] == "target"].iloc[0]
    present_value_forecast = float(forecast["present_value_fcff"].sum())
    bridge_inputs = _target_bridge_inputs(bundle)
    rows: list[dict[str, float | str]] = []
    warnings: list[str] = []

    for terminal in terminal_values.itertuples(index=False):
        enterprise_value = present_value_forecast + float(
            terminal.present_value_terminal
        )
        equity_value = enterprise_to_equity_value(enterprise_value, **bridge_inputs)
        implied_share_price = per_share_value(
            equity_value, float(target["diluted_shares"])
        )
        terminal_value_percentage = (
            float(terminal.present_value_terminal) / enterprise_value
        )
        if terminal_value_percentage > 0.80:
            warnings.append(
                f"{terminal.method} terminal value represents "
                f"{terminal_value_percentage:.1%} of enterprise value"
            )

        rows.append(
            {
                "method": terminal.method,
                "wacc": wacc,
                "terminal_assumption": float(terminal.terminal_assumption),
                "present_value_forecast_fcff": present_value_forecast,
                "terminal_value": float(terminal.terminal_value),
                "present_value_terminal": float(terminal.present_value_terminal),
                "terminal_value_percentage": terminal_value_percentage,
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
                "implied_share_price": implied_share_price,
                "current_share_price": float(target["share_price"]),
                "premium_discount": (
                    implied_share_price / float(target["share_price"]) - 1
                ),
            }
        )

    return DCFAnalysis(
        forecast=forecast,
        valuation_summary=pd.DataFrame(rows),
        warnings=tuple(warnings),
    )
