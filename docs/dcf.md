# Discounted Cash-Flow Analysis

Step 5 implements a five-year unlevered DCF using end-of-year discounting. All
monetary values use USD millions except per-share amounts.

## Operating forecast

Each forecast year is calculated from the user-supplied assumptions:

```text
Revenue(t) = Revenue(t-1) × (1 + Revenue growth(t))
EBITDA(t) = Revenue(t) × EBITDA margin(t)
D&A(t) = Revenue(t) × D&A % of revenue(t)
EBIT(t) = EBITDA(t) - D&A(t)
NOPAT(t) = EBIT(t) × (1 - Tax rate(t))
Capex(t) = Revenue(t) × Capex % of revenue(t)
Change in NWC(t) = Revenue(t) × Change in NWC % of revenue(t)

FCFF(t) = NOPAT(t) + D&A(t) - Capex(t) - Change in NWC(t)
```

The current MVP applies the tax rate directly to EBIT, including when EBIT is
negative. It does not separately model tax-loss carryforwards.

## Present value

The model uses end-of-year discounting:

```text
Discount factor(t) = 1 ÷ (1 + WACC)^t
Present value of FCFF(t) = FCFF(t) × Discount factor(t)
```

## Terminal value

Both terminal-value approaches use the Year 5 discount factor.

### Perpetuity-growth method

```text
Terminal value = FCFF(5) × (1 + g) ÷ (WACC - g)
```

Terminal growth must be lower than WACC.

### Exit-multiple method

```text
Terminal value = EBITDA(5) × Terminal EV/EBITDA
```

## Enterprise and equity value

```text
Enterprise value = Sum of present-value forecast FCFF
                 + Present value of terminal value

Equity value = Enterprise value
             - Debt
             - Non-controlling interest
             - Preferred stock
             + Cash
             + Non-operating investments

Implied share price = Equity value ÷ Diluted shares
```

The engine warns when discounted terminal value exceeds 80% of enterprise
value, since this indicates that the result is especially sensitive to terminal
assumptions.

## Run the example

```bash
.venv/bin/valuation-dcf data/raw/example
```

The command writes `dcf_forecast.csv` and `dcf_valuation_summary.csv` to
`outputs/step_05/`. The example data is fictional and provided only for model
demonstration and testing.

