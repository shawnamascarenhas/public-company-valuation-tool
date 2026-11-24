# Sensitivity Analysis and Valuation Visualizations

Step 6 adds two DCF sensitivity tables and consolidates comps and DCF ranges in
a valuation football field.

## Default sensitivity grids

The grids are centered on the base-case assumptions:

- WACC: base case ±2.0%, using 1.0% increments
- Terminal growth: base case ±1.0%, using 0.5% increments
- Terminal EV/EBITDA: base case ±2.0x, using 1.0x increments

Every sensitivity cell reruns forecast discounting and terminal value before
performing the enterprise-to-equity bridge. The base-case cell therefore
reconciles exactly to the Step 5 DCF summary.

The perpetuity-growth grid rejects any configuration where a terminal-growth
rate is greater than or equal to a WACC value. Exit multiples must be positive.

## Football-field ranges

The football field uses the following consistent per-share ranges:

| Method | Low/high definition |
|---|---|
| EV/Revenue | 25th and 75th peer percentiles |
| EV/EBITDA | 25th and 75th peer percentiles |
| P/E | 25th and 75th peer percentiles |
| DCF — perpetuity growth | Minimum and maximum of the sensitivity grid |
| DCF — exit multiple | Minimum and maximum of the sensitivity grid |

The current share price appears as a vertical reference line and is not itself
a valuation method.

## Generated visualizations

- WACC versus terminal-growth heatmap
- WACC versus exit-multiple heatmap
- Valuation football field
- Five-year revenue and EBITDA forecast chart

## Run the example

```bash
.venv/bin/valuation-analytics data/raw/example
```

CSV source tables and standalone interactive HTML charts are written to
`outputs/step_06/`. The charts load Plotly from its public CDN when opened, so
an internet connection is required for the standalone HTML rendering.

