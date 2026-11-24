# Interview Guide

## 30-second summary

I built a Python public-company valuation platform that combines comparable
companies and a five-year unlevered DCF. It validates financial inputs, handles
invalid multiples explicitly, runs two terminal-value methods and sensitivities,
and produces an interactive dashboard plus an Excel report. I also added an
optional SEC EDGAR importer with XBRL concept provenance so automated data never
becomes a black box.

## Strong discussion points

### Why separate the engines from the interface?

The same calculations support tests, command-line workflows, Streamlit, and
Excel export. This reduces duplicated logic and makes financial reconciliation
possible without testing through the browser.

### Why keep peer selection manual?

Peer selection is an analytical judgment involving business model, geography,
growth, margin, size, and capital intensity. Automating it in the MVP would add
false precision and weaken the valuation discussion.

### Why exclude negative denominators?

P/E and EV/EBITDA become economically misleading when earnings or EBITDA are
non-positive. The model retains those companies visibly but excludes the
invalid observation only from the affected statistic.

### Why show two terminal values?

Perpetuity growth tests long-run cash-generation assumptions, while an exit
multiple anchors the terminal value to market pricing. Comparing both reveals
how much the conclusion depends on the terminal framework.

### What would you build next?

I would add last-twelve-month normalization, consensus estimates, a transparent
WACC build-up, sector-specific templates, and an analyst review queue for SEC
XBRL mappings before adding more automated market data.

## Risks to acknowledge

- Terminal value drives a large portion of most DCFs.
- Comparable-company results depend on peer quality and accounting consistency.
- Filed XBRL tags vary between issuers.
- A technically correct model can still be wrong if assumptions are weak.

