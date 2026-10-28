# Quantitative Strategy and Backtesting Module

Read this file when the user requests definition of quantitative strategies, grid parameter design, historical backtesting, parameter optimization, quantitative stock selection, daily scanning, or validation of indicator effectiveness.

## Sole Responsibility

Be responsible for translating trading assumptions into reproducible simulation rules, completing historical simulation, parameter checks, robustness assessment, and reproducible reporting. Must not substitute for subjective fundamental research and must never place, modify, cancel, or automate real transactions. Any fills in this module are hypothetical backtest events only.

## Common Dependency Declaration

| Type | Public Reference | Trigger and Purpose |
|---|---|---|
| Required | [`data-source-policy.md`](data-source-policy.md) | Unify rules for point-in-time data, adjustment for corporate actions, time zones, missing values, sample bias, and availability |
| Required | [`metric-dictionary.md`](metric-dictionary.md) | Unify definitions for returns, risk, drawdown, performance, turnover and trade metrics |
| Required | [`scoring-standard.md`](scoring-standard.md) | Unify strategy comparison, robustness scoring, confidence levels and hard thresholds |
| Required | [`output-contracts.md`](output-contracts.md) | Use the common result envelope and the `quant-backtesting` domain payload |
| Conditional | [`privacy-security.md`](privacy-security.md) | Load when using user accounts, proprietary strategies, private trade records, or non-public data |
| Conditional | [`execution-safety.md`](execution-safety.md) | Load when requesting live handover, transaction automation, scheduled trading, or real orders; transaction actions are prohibited and may only be converted to manual plans |

## Input Contract

| Field | Requirement | Description |
|---|---|---|
| `instruments` | Required | Instrument identifiers, market, asset type and benchmark |
| `strategy_spec` | Required | Signals, entry, exit, position sizing, rebalancing and conflict resolution rules |
| `start`, `end` | Required | Backtest period; if the user does not specify, use a reasonable default only after disclosure |
| `initial_capital` | Required | Initial capital and currency |
| `cost_model` | Required | Commissions, taxes, spreads, slippage, borrow/financing and funding rates |
| `data_frequency` | Required | Daily, minute, or other frequency |
| `parameter_space` | Optional | Parameter ranges and step sizes to be tested |
| `constraints` | Optional | Max position, leverage, participation rate, suspensions and non-tradability rules |

If the strategy depends on crypto-specific mechanisms, read `crypto-analysis.md` first, then hand verified asset assumptions to this module.

## Yahoo Finance Use

Use validated `chart` artifacts only for historical or delayed price/volume research when the requested instrument, interval and period are supported under [`data-source-policy.md`](data-source-policy.md). Record the exact request parameters, retrieval time, timezone, currency and adjustment basis so the run is reproducible. Do not presume point-in-time constituent membership, survivorship-free coverage, delisted securities, announcement-time fundamentals, corporate-action completeness, intraday execution quality or total-return semantics. If any of those are material, use an authoritative or specialist dataset or mark the backtest incomplete.

## Workflow

1. Formalize the strategy. Convert natural-language rules into unambiguous specifications; clarify signals, execution prices, position priority at the same timestamp, re-entry rules, handling of missing data, and corporate actions.
2. Review the data. Check adjustments, time zones, survivor bias, look-ahead bias, delisting samples, missing values and frequency alignment according to `data-source-policy.md`. For Yahoo Finance inputs, validate the source artifact and explicitly test symbol coverage, timestamp alignment and adjustment semantics. Do not use information unavailable at execution time.
3. Establish baselines. Define buy-and-hold or appropriate benchmarks and compare on the same period, currency, fees and risk definitions.
4. Execute matching. Trade at the first tradable timestamp after signal generation; include fees, slippage, minimum trade units, liquidity and leverage constraints. Do not assume zero cost by default.
5. Compute performance. Use the public metric dictionary to calculate returns, volatility, drawdowns, Sharpe, Sortino, Calmar, win rate, profit factor, turnover and exposures, and preserve raw series.
6. Run robustness tests. Perform at minimum in-sample/out-of-sample, parameter sensitivity, different market regimes and cost stress tests. Use rolling or walk-forward methods where applicable.
7. Control optimization. Predefine the parameter space and objective function; retain all trial results; do not report only the single best combination. Flag multiple-comparison and overfitting risks when many trials are performed.
8. Produce reproducible deliverables. Output the strategy specification, data inventory, scripts, parameters, trade logs, metrics tables, equity curves and failure analysis.

## Minimum Execution Conventions

| Item | Default Requirement |
|---|---|
| Signals and fills | Do not assume signals generated from close data will execute frictionlessly at the same close price |
| Costs | Specify commissions, taxes, spreads and slippage; if unknown, use scenario ranges |
| Adjustments | Use total return for return series or explicitly state dividend handling |
| Liquidity | Do not assume fills when volume is insufficient, suspended, or at limit up/down |
| Positioning | After rounding orders to tradable units, recheck cash, margin and leverage |
| Shorts | Include borrow availability, borrow rates and recall risk |
| Derivatives | Include contract multiplier, expirations, roll, funding rates and margin |

## Quality Gates

| Gate | Pass Criteria | Failure Handling |
|---|---|---|
| Rules completeness | All decision branches can be executed by code | List undefined rules first; do not run |
| No look-ahead | Each field is available at the time of the decision | Correct time alignment and rerun |
| Data coverage | Period and market regimes are sufficient | Reduce strength of conclusions |
| Cost realism | Fees and slippage are non-zero and traceable | Output cost sensitivity; do not give execution recommendations |
| Robustness | Out-of-sample and parameter neighborhood do not collapse | Flag strategy as unverified |

## Handover Rules

| Request Extension | Call Chain |
|---|---|
| Subjective company valuation | `equity-research` |
| Crypto market mechanisms and assumptions | `crypto-analysis` → `quant-backtesting` |
| Integrate strategy into existing portfolio | `quant-backtesting` → `portfolio-management` |
| Prepare a manual order plan, including a prohibited request to execute or automate orders | `quant-backtesting` → `trade-planning`; the user must transact independently |

## Output Format

1. Construct a `finance-analysis-pro/1.2` result object according to [`schemas/finance-analysis-result.schema.json`](schemas/finance-analysis-result.schema.json), and set `primary_module=quant-backtesting`, `presentation.profile=quant-backtesting`.
2. In the domain payload retain only the strategy specification, data inventory, benchmarks, performance, robustness, parameter results, scripts and validation status; keep public facts, metrics, scores, risks, failure conditions, data gaps, sources, privacy and execution state at the top level, and do not duplicate definitions.
3. Run `python3 scripts/ensure_runtime.py`, then run `python3 scripts/validate_result.py result.json`. If runtime preparation is not `ready` or validation fails, stop and correct the environment or result object; do not bypass or downgrade validation to generate the report.
4. Unless the user explicitly requests only JSON, YAML or other machine formats, generate Markdown following the section order in [`../templates/quant-backtesting.md`](../templates/quant-backtesting.md).
5. Use `brief` to compress analysis details but preserve state, data cutoff, execution summary, main risks, failure conditions, data gaps and execution state; use `standard` to retain the template core sections; use `deep` to add methods, calculations, sensitivities, sources and audit appendices.
6. Generate dedicated attachments as needed and register them in `artifacts[]`; do not temporarily add fact fields not present in the template—if extension is required, update the public Schema first.
