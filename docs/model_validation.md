# Model Validation and Reconciliation

## Validation objective

The release was tested at four levels: input contracts, finance formulas,
cross-method reconciliation, and rendered application behavior. The bundled
dataset is fictional so expected outputs remain stable and reproducible.

## Automated controls

- Required files, columns, types, dates, units, roles, and row counts
- Cross-file ticker consistency
- Three consecutive historical years and five consecutive forecast years
- Terminal growth below WACC
- Positive share counts and valid valuation denominators
- Exclusion of invalid peer multiples
- Enterprise-value/equity-value bridge round trips
- DCF base cases reconciled to sensitivity-table center cells
- Streamlit rendering and Excel workbook sheet verification
- Mocked SEC responses, XBRL mappings, scaling, and missing-concept behavior

## Formula reconciliation

### Comparable companies

The tests independently recompute market capitalization, enterprise value,
EV/Revenue, EV/EBITDA, P/E, peer medians, implied enterprise value, implied
equity value, share price, and premium/discount.

For the fictional example, median implied values are:

| Method | Implied share price |
|---|---:|
| EV/Revenue | $51.78 |
| EV/EBITDA | $46.87 |
| P/E | $46.30 |

### Discounted cash flow

Each Year 1 forecast line is independently recomputed from assumptions. Tests
also reconcile revenue compounding, end-of-year discount factors, both terminal
values, the EV-to-equity bridge, and value per share.

| Method | Enterprise value | Equity value | Share price |
|---|---:|---:|---:|
| Perpetuity growth | $5,814.54m | $5,439.54m | $45.33 |
| Exit multiple | $6,183.69m | $5,808.69m | $48.41 |

The WACC 9.5% / terminal-growth 3.0% sensitivity cell equals $45.33. The WACC
9.5% / 10.0x exit-multiple cell equals $48.41.

## Release quality gates

Run all release checks with:

```bash
make lint
make coverage
make validate
make release
```

The GitHub Actions workflow enforces formatting, linting, tests, and at least
85% coverage of business-logic modules. UI and CLI shells are excluded from
the coverage denominator but receive smoke and integration tests.

## Residual limitations

- The model uses end-of-year rather than mid-year discounting.
- It does not model tax-loss carryforwards.
- DCF working-capital investment is modeled as a percentage of revenue.
- Peer selection and valuation-date market data require analyst judgment.
- SEC XBRL facts require reconciliation to the filed 10-K.
- Financial institutions and sector-specific valuation frameworks are outside
  the MVP scope.

