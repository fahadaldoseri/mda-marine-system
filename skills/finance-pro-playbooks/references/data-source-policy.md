--- BEGIN FILE ---
# Data Sources and Calculation Conventions Policy

Read this file when a task reads external data, user files, market data, financial statements, option chains, on-chain data, or user-provided historical transaction records.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Source Priority](#source-priority)
3. [Yahoo Finance via Manus Data API](#yahoo-finance-via-manus-data-api)
4. [Data Manifest](#data-manifest)
5. [Time and Freshness](#time-and-freshness)
6. [Standardization Rules](#standardization-rules)
7. [Asset-Specific Requirements](#asset-specific-requirements)
8. [Cross-Validation and Conflicts](#cross-validation-and-conflicts)
9. [Missing Data, Estimation, and Failures](#missing-data-estimation-and-failures)

## Core Principles

1. Define the decision timestamp first, then select data available at that time to avoid look-ahead bias.
2. Prefer primary, structured, and traceable sources; use search summaries, secondary reports, and anonymous posts only to surface leads.
3. Record source, fetch time, observation time, currency, unit, frequency, adjustment, and estimation status for key fields.
4. Use different freshness standards for research conclusions, simulations, and concrete manual-plan parameters; never treat any source as authorization or infrastructure for a transaction, and do not use stale data for a manual plan.
5. Do not change the user's question or calculation conventions solely because data are available.

## Source Priority

| Priority | Source | Applicable Content |
|---|---|---|
| 1 | Regulatory filings, exchange and clearinghouse public records, issuer official documents, fund legal documents, protocol official contracts and governance records | Financials, terms, contract specs, NAV, indices, on-chain contracts and public market rules |
| 2 | Verified professional data vendors or direct APIs | Standardized financials, historical prices, real-time quotes, option chains, macro and on-chain metrics |
| 3 | Company websites, investor relations materials, audit reports, official press releases and call transcripts | Management guidance, guidance, business descriptions and events |
| 4 | Editorially responsible financial media, research institutions and industry databases | Background, controversies and cross-checks |
| 5 | Search summaries, aggregator sites, communities, social media and anonymous information | Use only as leads; do not rely solely to support key facts or trading conclusions |
| U | User-provided files or data | Treat as user-specified input; still record date, version and reliability, and do not automatically treat as factual truth |

If a lower-priority source conflicts with a higher-priority source, default to the higher-priority source and retain a record of the conflict; if high-priority sources conflict with each other, do not silently choose one.

## Yahoo Finance via Manus Data API

Yahoo Finance is an approved secondary market-data source only through the confirmed Manus data API operations below. Use `scripts/fetch_yahoo_finance.py` rather than undocumented Yahoo endpoints or scraped pages, then validate each source artifact with `scripts/validate_yahoo_source.py` before using it in a result.

| Adapter Operation | Confirmed API Operation | Approved Use | Evidence Boundary |
|---|---|---|---|
| `chart` | `YahooFinance/get_stock_chart` | Historical or delayed OHLCV, adjusted close, chart metadata, research-level price context and non-execution backtests | Tier 2 market data; not an executable quote, order receipt, official exchange record or guaranteed total-return series |
| `profile` | `YahooFinance/get_stock_profile` | Company identity, sector, industry, business summary and market snapshot | Secondary structured data; verify valuation-critical facts, capital structure and official descriptions against filings or issuer materials |
| `holders` | `YahooFinance/get_stock_holders` | Ownership screening and holder trend context | Secondary data; do not treat as a complete, current ownership register |
| `insights` | `YahooFinance/get_stock_insights` | Provider analytics, technical context and idea generation | Tier 4 analytical content; label provider-derived views and do not use them as sole support for recommendations |
| `filings` | `YahooFinance/get_stock_sec_filing` | Discovering filing references and dates | Discovery only; retrieve and cite the SEC, regulator or issuer filing itself before using filing facts as Tier 1 evidence |

The adapter supports equities for all five operations. `chart` also supports ETF, index, crypto, forex and futures symbols when Yahoo Finance recognizes the instrument. Profile, holder, insight and filing operations are equity-only. The adapter does not provide option chains, fund legal documents, official NAV, intraday order books, executable bid/ask, broker receipts, exchange-confirmed status or point-in-time constituent history.

Only operation-specific normalized fields may enter a source artifact. Do not retain or deliver the raw provider response. Omit personal names and contact fields from holder and profile records, omit full third-party research reports and report text from insights, and reject any artifact that contains fields outside the approved operation whitelist.

For concrete manual-plan parameters, compliance, official filings and fund due diligence, use public or read-only primary venue, exchange, regulator, issuer or fund sources. Never access an account, order-management endpoint, wallet signer or transaction endpoint, and never use a broker connection to place, modify, cancel or monitor an order. For crypto, cross-check Yahoo Finance prices with at least one independent venue or authoritative provider. For backtests, disclose survivorship, delisting, corporate-action and point-in-time limitations; do not infer that a returned adjusted-close series is total return unless the response and methodology establish that basis.

Each successful Yahoo Finance call must preserve the generated source artifact and copy its `source_manifest_entry` into the final result's `source_manifest[]`. Map every Yahoo-supported claim to that `source_ref`; record `retrieved_at`, `data_as_of`, symbol, operation, query parameters, currency, interval and adjustment basis where applicable. Do not cite the local artifact path as the publisher URL; cite the generated Yahoo Finance quote URL and retain the local artifact as supporting evidence.

If the Manus data API runtime is unavailable, the provider returns an error, or the response has no usable result, keep the artifact status as `blocked` or `failed`, list the data gap, and either use an approved alternative source or withhold the affected conclusion. Never substitute remembered values, scrape an undocumented endpoint or silently relabel another provider as Yahoo Finance.

## Data Manifest

Each task must maintain the following minimum `data_manifest`:

```yaml
- field: revenue
  value: 123.4
  unit: USD_million
  observation_time: YYYY-MM-DD
  publication_time: YYYY-MM-DDTHH:MM:SSZ
  retrieval_time: YYYY-MM-DDTHH:MM:SSZ
  source_name: string
  source_url_or_file: string
  source_tier: 1 | 2 | 3 | 4 | 5 | U
  period: FY2025
  currency: USD
  frequency: annual
  adjustment: reported | adjusted | split_adjusted | total_return | none
  status: verified | single_source | estimated | stale | conflicted
  notes: string
```

Data supporting key conclusions must be traceable from reports back to this manifest. For user files, use filename, page number, table name, or paragraph location instead of URL.

## Time and Freshness

| Use Case | Default Maximum Age | Rules |
|---|---:|---|
| Concrete manual-plan or simulated price inputs | 60 seconds | Include bid/ask, venue and timestamp when available; label them non-executable, and when markets are closed generate only conditional manual plans |
| Intraday signals and order flow | 1 analysis period | If current-period data are missing, degrade; do not extrapolate |
| Daily technical analysis | Most recent completed trading day | Do not mix intraday incomplete candlesticks with historical closing series |
| Crypto spot/perpetual analysis | 5 minutes | When venues are fragmented verify at least two sources |
| Option chains | 5 minutes or user-specified | Must include quotes, OI/trade volume dates and underlying price time |
| Portfolio valuation | Most recent available close or user-specified snapshot | Multi-market portfolios may use asynchronous closes but must be flagged |
| Financial statements | Most recent formally disclosed period | Also annotate fiscal year, quarter, publication date and whether restated |
| Fund holdings | Issuer's most recent disclosure period | Do not treat lagged holdings as a real-time portfolio |
| Macro data | Most recently formally published value | Record vintage; backtests must use versions published at the time |
| Institutional trading documents | User-specified version | File version takes precedence over retrieval time |

When users request historical point-in-time analysis, limit all data to information publicly available before that point; subsequent revised data must not replace the version available at the time.

## Standardization Rules

### Identifiers and Entities

Maintain mappings for security codes, exchanges, ISIN/contract codes, company entities, fund share classes, crypto networks and contract addresses. When codes are reused, renumbered, merged, delisted or tokens cross-chain, do not assemble sequences using only display names.

### Currencies and Units

Retain original currency, then convert to the report currency using the exchange rate at the same timestamp. Use period-average rates for flows and period-end rates for balance sheets, and document which is used. Do not mix units like RMB, thousands, millions, or per-share and aggregate amounts.

### Financial Periods

Align by fiscal year rather than calendar year; distinguish quarter, year-to-date, LTM and NTM. Any non-GAAP/adjusted metrics must be columnized by reported statement basis and retain reconciliation items.

### Prices and Corporate Actions

Mark price series as raw, split-adjusted or total-return basis. In backtests handle splits and reverse splits, cash/stock dividends, rights issues, spinoffs, mergers, delistings, halts and code changes; do not improve results by deleting problem dates.

### Time Zones and Trading Days

Preserve original time zone and convert to task-specified time zone; specify daylight saving rules. For cross-market portfolios use each market's trading calendar and explain holiday and asynchronous close handling.

### Missing Values

Do not forward-fill prices, yields, volumes, financial fields, option Greeks or user-provided historical transaction states by default. Fill only when economically meaningful and the method is predefined, and mark in the manifest as `estimated`.

## Asset-Specific Requirements

| Domain | Minimum Required Data |
|---|---|
| Equity research | Official financial statements, publication dates, business segments, fully diluted share count, net debt, prices and comparable data on a consistent basis |
| Fund/ETF | Share classes, index, fees, replication method, AUM, NAV, dividends, trading currency, holdings disclosure dates and legal documents |
| Options | Underlying quotes, expiries, strikes, bid/ask, multiplier, style, IV, Greeks, OI, trade volume, interest rates, dividends and event calendar |
| Crypto | Network/contract, trading pairs, venue, spot/perpetual type, funding rate, OI, basis, on-chain block height or timestamp |
| Portfolio | Holdings snapshot, price time, quantity, cost, cash, liabilities, currency and benchmark; account identifiers not required |
| Backtest | Constituents at each point in time, delisting sample, corporate actions, tradability, fees, slippage, calendar and fields available at decision time |
| Manual trade planning | Current or delayed bid/ask with timestamp and non-executable label, observable liquidity, contract specs, trading sessions, fees and user-stated constraints; no account, order, receipt, signer or transaction identifiers |
| Trading materials | Filename, version, date, authority level, page/paragraph locator and confidentiality status |

## Cross-Validation and Conflicts

Mark a key fact as `verified` only if it meets either of the following conditions: from an authoritative primary source; or from two independent sources whose methods can be explained and whose timestamps are consistent. Prices, net asset values, option chains and funding rates must default to the corresponding venue or authoritative data. Historical transaction status may be discussed only from user-provided read-only records and must not imply platform access.

Conflict resolution steps:

1. Check that entity, period, currency, unit, adjustment, time zone and publication date are consistent.
2. Check for mixing of reported vs. adjusted, initial vs. revised values, and real-time vs. delayed data.
3. Preserve each candidate value and source; do not overwrite original records.
4. When resolvable, record selection rules; when unresolvable, mark `conflicted` and perform scenario analysis or withhold related conclusions.

## Missing Data, Estimation, and Failures

| Status | Action |
|---|---|
| Single source | Mark `single_source`, avoid high-confidence statements |
| Missing critical fields | List fields and impact on conclusions; do not fabricate precise values |
| Stale data | Mark `stale`; do not use for concrete manual-plan parameters or short-term signals |
| Estimated values | Record proxy variables, formulas, assumptions and sensitivity |
| API/web failure | Try alternative authoritative sources; do not fill with numbers recalled from memory |
| User data conflicting with public data | Show both and the differences in conventions, require user choice or provide conditional conclusions |
| Unable to verify high-risk claims | Output `unverified`, do not rephrase as facts |

Use credentials only via secure environment variables or authorized connections; do not write them into the data manifest, scripts, logs, reports, or Reference.

--- END FILE ---
