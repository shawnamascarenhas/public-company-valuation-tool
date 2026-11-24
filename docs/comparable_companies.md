# Comparable-Company Analysis

Step 4 uses each company's latest historical year and its valuation-date market
inputs to calculate trading multiples and implied target valuation ranges.

## Core formulas

```text
Market capitalization = Share price × Diluted shares

Enterprise value = Market capitalization
                 + Total debt
                 + Non-controlling interest
                 + Preferred stock
                 - Cash
                 - Non-operating investments

EV/Revenue = Enterprise value ÷ Revenue
EV/EBITDA  = Enterprise value ÷ EBITDA
P/E        = Share price ÷ Diluted EPS
```

A multiple is unavailable when its denominator is zero or negative. Such an
observation is excluded from that multiple's peer statistics but remains
visible in the company table.

## Peer statistics

The engine calculates the minimum, 25th percentile, median, 75th percentile,
and maximum independently for EV/Revenue, EV/EBITDA, and P/E. Pandas' linear
quantile interpolation is used for percentile observations between two peers.

## Implied target valuation

EV-based methods apply the selected peer statistic to the target's revenue or
EBITDA, then convert enterprise value to common equity value:

```text
Equity value = Enterprise value
             - Total debt
             - Non-controlling interest
             - Preferred stock
             + Cash
             + Non-operating investments

Implied share price = Equity value ÷ Diluted shares
```

P/E applies the selected peer statistic directly to target diluted EPS. The
engine then calculates equity value and an equivalent enterprise value so all
methods share the same output format.

## Run the example

```bash
.venv/bin/valuation-comps data/raw/example
```

The command writes these auditable CSV files to `outputs/step_04/`:

- `company_multiples.csv`
- `peer_summary_statistics.csv`
- `implied_valuation.csv`

The bundled companies and values are fictional and provided solely for model
demonstration and testing.

