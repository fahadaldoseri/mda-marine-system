# Fund and ETF Module

Read this file when the user requests comparing funds or ETFs, finding lower-cost alternatives, reviewing product structure, or evaluating whether to add to a fund position.

## Sole Primary Responsibility

Responsible for peer product comparison, structural risk review, and product-level decisions for funds and ETFs. Must not substitute for single-equity valuation, nor unilaterally decide final capital allocation for multi-asset portfolios.

## Common Dependency Declaration

| Type | Public Reference | Trigger and Use |
|---|---|---|
| Required | [`data-source-policy.md`](data-source-policy.md) | Unify NAV, price, dividend, currency, adjustment, index and product data sources |
| Required | [`metric-dictionary.md`](metric-dictionary.md) | Unify return, volatility, drawdown, fees, tracking and liquidity metric definitions |
| Required | [`scoring-standard.md`](scoring-standard.md) | Unify product comparison, ranking, confidence and hard thresholds |
| Required | [`output-contracts.md`](output-contracts.md) | Use common result envelope and `fund-etf` domain payload |
| Conditional | [`privacy-security.md`](privacy-security.md) | Load when user provides existing holdings, cash, accounts or personal constraints |
| Conditional | [`execution-safety.md`](execution-safety.md) | Load when requesting trading plans, orders, automation, or any transaction; transactions are prohibited and may only be converted to manual plans |

## Input Contract

| Field | Requirement | Description |
|---|---|---|
| `funds` | Conditionally required | Specify comparison targets; if only an asset class is given, construct a candidate set first |
| `target_exposure` | Conditionally required | Index, sector, factor, region or asset class to be tracked |
| `jurisdiction` | Optional | Listing, tax or regulatory constraints; only for filtering, not personal tax advice |
| `currency` | Optional | Currency to normalize comparisons |
| `horizon` | Optional | Holding horizon |
| `user_context` | Optional and sensitive | Existing holdings, cash proportion and constraints; use only for suitability judgment |
| `as_of` | Optional | Data cut-off date |

## Yahoo Finance Use

Use `scripts/fetch_yahoo_finance.py chart` for historical or delayed exchange-traded ETF price and volume context when permitted by [`data-source-policy.md`](data-source-policy.md), then validate and register the source artifact. Do not use Yahoo Finance as the authoritative source for official NAV, TER, legal structure, benchmark methodology, holdings, distributions, registration status, creation/redemption terms or tax treatment; obtain those from the fund sponsor, prospectus, index provider, exchange or regulator. A Yahoo adjusted-close series is not presumed to be total return without evidence of the adjustment basis.

## Workflow

1. Define the comparison domain. Confirm target exposure, market, currency, domicile, dividend treatment and tradability. Do not directly rank products with different economic exposures.
2. Construct the candidate set. Include at minimum the user-specified products, direct peers, low-cost candidates and alternatives feasible under user constraints. If no reasonable alternative exists, state explicitly.
3. Collect structural data. Obtain index, replication method, total expense, size, liquidity, spreads, tracking performance, securities lending, dividend treatment, currency hedging, registration structure and concentration. Yahoo Finance chart data may supplement exchange-traded price and volume history, but must not replace sponsor, prospectus, index-provider or exchange evidence for product structure.
4. Perform a structural risk review. Identify synthetic replication, leveraged/inverse, maturity or path dependence, concentrated holdings, liquidity mismatch, cross-border tax frictions and custody risk. Describe only general tax implications; do not provide personal tax conclusions.
5. Compare realized returns. Present both price return and total return including dividends, normalize currency, time window and frequency; do not annualize or make misleading comparisons for incomplete-cycle data.
6. Form layered conclusions. Separately present overall optimal, cost-optimal, structurally most robust and applicability constraints. Output an overall score only when scoring anchors are complete.
7. Assess operational decisions. For requests to increase position / average down / open new position / wait, first check investment logic, valuation or exposure, portfolio concentration, alternatives and failure conditions; if precise sizing is required, hand off to the portfolio module.

## Minimum Comparison Fields

| Category | Fields |
|---|---|
| Exposure | Index, region, sector/factor, position concentration |
| Cost | TER/expense ratio, trading spread, tracking difference, estimated tax frictions |
| Structure | Replication method, domicile, currency hedging, dividend treatment, leverage/inverse |
| Trading | AUM, turnover, spreads, market making and creation/redemption mechanism |
| Performance | Price return, total return, volatility, max drawdown, tracking error |
| Risk | Concentration, liquidity, counterparty, path dependence, closure or merger risk |

## Handoff Rules

| Request Extension | Call Chain |
|---|---|
| Configure selected ETFs into an existing portfolio | `fund-etf` → `portfolio-management` |
| Analyze the investment value of companies heavily held by a fund | `equity-research` |
| Backtest ETF rotation or regular investment strategies | `quant-backtesting` |
| Generate a specific manual order plan, including a prohibited request to execute a buy or sell | `fund-etf` → `trade-planning`; the user must transact independently |
| Analyze digital asset fundamentals | `crypto-analysis` |

## Output Format

1. First construct a result object according to [`schemas/finance-analysis-result.schema.json`](schemas/finance-analysis-result.schema.json) as `finance-analysis-pro/1.2`, and set `primary_module=fund-etf`, `presentation.profile=fund-etf`.
2. In the domain payload keep only candidate products, exposure mapping, structural risk, costs, liquidity and layered recommendations; keep common facts, metrics, scores, risks, failure conditions, data gaps, sources, privacy and execution status at the top level. Prohibit duplicate definitions.
3. Run `python3 scripts/ensure_runtime.py`, then run `python3 scripts/validate_result.py result.json`. If runtime preparation is not `ready` or validation fails, stop and correct the environment or result object; do not bypass or downgrade validation to generate the report.
4. Unless the user explicitly requests only JSON, YAML or other machine formats, generate Markdown following the section order in [`../templates/fund-etf.md`](../templates/fund-etf.md).
5. Use `brief` to compress analytical detail, but retain status, data cut-off, executive summary, key risks, failure conditions, data gaps and execution status; use `standard` to retain template core sections; use `deep` to add methodology, calculations, sensitivity analysis, sources and audit appendix.
6. Generate dedicated attachments as needed and register them in `artifacts[]`; do not add ad hoc fact fields not present in the template—if extension is necessary, update the public schema first.
