# Streamlit Application

Step 7 combines input validation, comparable-company analysis, DCF valuation,
sensitivity analysis, charts, and report export into one interactive workflow.

## Launch

From the project directory:

```bash
source .venv/bin/activate
streamlit run app.py
```

The application opens with the fictional example dataset. Use the sidebar to
switch to custom CSV uploads.

## Workflow

### Inputs

Review or edit all four model tables directly. Every edit triggers validation
and recalculates downstream results. The app stops valuation calculations and
shows actionable errors if the edited inputs violate the Step 3 rules.

### Company Overview

Review the target's market capitalization, enterprise value, latest revenue,
latest EBITDA, and three-year historical performance.

### Comparable Companies

Review peer trading multiples, peer summary statistics, invalid-denominator
warnings, and implied target values across the full peer range.

### DCF

Review the five-year operating forecast, unlevered free cash flow, discounted
cash flows, and valuations under both terminal-value methods.

### Sensitivity

Explore interactive WACC/terminal-growth and WACC/exit-multiple heatmaps. The
underlying numeric tables are available in an expandable section.

### Valuation Summary

Compare all valuation methods in a football field and download the complete
Excel workbook. The workbook contains all input tables, model outputs,
sensitivity grids, and football-field ranges in 12 formatted worksheets.

## Custom data

Select **Upload CSV files** in the sidebar and provide all four canonical input
files. The required filenames and columns are documented in
`docs/input_data.md`. Uploaded data is processed in a temporary directory and
is not persisted by the application.

## Important limitation

This application is an educational valuation model. It does not provide live
market data, verify investment suitability, or constitute investment advice.

