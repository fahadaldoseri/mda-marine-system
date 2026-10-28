# Crypto Asset Analysis Module

Read this file when a user requests analysis of crypto asset prices, market structure, SMC, on-chain and derivatives signals, DeFi liquidity pools, or verification of crypto high-risk topics.

## Primary Responsibility

Be responsible for market structure, trading mechanics, on-chain and DeFi analysis specific to crypto assets. General strategy backtesting is owned by `quant-backtesting`; concrete transaction requests route to `trade-planning` for a user-executed manual plan only. No module may sign, broadcast, approve, transfer, place, modify, or cancel a transaction.

## Common Dependency Declaration

| Type | Public Reference | Trigger and Use |
|---|---|---|
| Required | [`data-source-policy.md`](data-source-policy.md) | Standardize timestamps and sources for exchange, on-chain, derivatives, token, and protocol data |
| Required | [`metric-dictionary.md`](metric-dictionary.md) | Standardize definitions for return & risk, funding rate, basis, on-chain, LP and trading metrics |
| Required | [`output-contracts.md`](output-contracts.md) | Use the common result envelope and the `crypto-analysis` domain payload |
| Conditional | [`scoring-standard.md`](scoring-standard.md) | Load when ranking, scoring, or assessing confidence for assets, protocols, or strategies |
| Conditional | [`privacy-security.md`](privacy-security.md) | Load when wallets, positions, accounts, or credentials are involved; do not request private keys or mnemonics |
| Conditional | [`execution-safety.md`](execution-safety.md) | Load when ordering, custody, automation, signing, broadcasting, token approval, transfer, or any live operation is requested; such transaction actions are absolutely prohibited |

## Input Contract

| Field | Requirement | Description |
|---|---|---|
| `assets` | Required | Asset symbols, trading pair, network, and quote currency |
| `analysis_type` | Required | Market analysis, SMC, derivatives, on-chain, LP, or fact verification |
| `venues` | Optional | Spot/perpetual/futures/DEX venues |
| `timeframes` | Optional | Default to cover at least high, medium, and low timeframes |
| `market_data` | Conditionally required | OHLCV, order book, funding rates, OI, basis, or on-chain data |
| `user_positions` | Optional and sensitive | Positions, cost basis, leverage, margin, and liquidation information |
| `lp_context` | Conditionally required | Protocol, pool, fee tier, price range, capital and duration |
| `as_of` | Optional | Data timestamp |

## Yahoo Finance Use

Use `scripts/fetch_yahoo_finance.py chart` only as a secondary historical or delayed price series for a recognized crypto symbol, then validate and register the source artifact. Yahoo Finance does not identify the authoritative exchange venue, order book, funding rate, open interest, liquidation stream, on-chain state, pool data or executable price. Always cross-check its price series with at least one independent venue or authoritative provider and disclose symbol, quote currency, interval and venue limitations.

## Workflow

1. Confirm assets and venues. Distinguish networks, contract addresses, spot, perpetuals and futures; avoid confusion from same-named tokens and price differences across exchanges.
2. Establish market context. Check trend, volatility, liquidity, BTC/ETH dominance, funding rates, open interest, basis, and material events. Yahoo Finance chart data may supplement price history only after source-artifact validation and independent price cross-checking. Indicate timestamps for each data source.
3. Perform multi-timeframe structure analysis. Identify trend, swing highs/lows, liquidity clusters, supply/demand zones, order blocks and imbalance areas; separate objective structure from subjective SMC labels.
4. Examine derivatives and order flow. Cross-validate using funding rates, open interest, liquidations, CVD and basis signals; do not escalate an anomaly at a single venue to a market-wide conclusion.
5. Handle existing leveraged positions. First verify direction, notional value, margin model and liquidation price before discussing any additional risk. Do not recommend adding to positions when critical fields are missing.
6. Analyze DeFi LPs. Verify protocol and contracts, fee tier, historical price distribution, range coverage, fees, impermanent loss, rebalancing costs and smart contract risk. Do not present nominal APR only.
7. Verify high-risk topics. Apply pessimistic-first verification for exchange yields, token issuances, airdrops, regulatory or security events; output "Unable to verify" when unable to confirm from primary or independent sources.
8. Formulate strategy candidates. Provide direction, conditions, key zones, invalidation conditions and risks; hand off to `quant-backtesting` for historical testing and to `trade-planning` only for an unsubmitted manual plan the user may independently implement.

## Quality Gates

| Gate | Passing Criteria | Failure Handling |
|---|---|---|
| Unique identification | Network, contract, or trading pair unambiguous | Pause and clarify |
| Cross-source price verification | At least two independent sources or document single-source limitations | Lower confidence |
| Venue consistency | Spot/perpetual, quote currency and timezone consistent | Standardize before computing |
| Leverage completeness | Direction, position, margin, leverage and liquidation rules available | Do not provide add-to-position recommendations |
| LP reproducibility | Range, fee tier, price path and cost assumptions visible | Do not output expected yield |

## Handoff Rules

| Request Expansion | Call Chain |
|---|---|
| Backtest grid, trend, or funding-rate strategies | `crypto-analysis` → `quant-backtesting` |
| Generate a manual order or DeFi action plan, including a prohibited request to execute, sign, broadcast, approve, or transfer | `crypto-analysis` → `trade-planning`; stop before any platform interaction |
| Include crypto assets in multi-asset portfolio | `crypto-analysis` → `portfolio-management` |
| Traditional equity or ETF analysis | `equity-research` or `fund-etf` |

## Output Format

1. First construct a `finance-analysis-pro/1.2` result object according to [`schemas/finance-analysis-result.schema.json`](schemas/finance-analysis-result.schema.json), and set `primary_module=crypto-analysis`, `presentation.profile=crypto-analysis`.
2. In the domain payload, keep only market structure, derivatives and on-chain evidence, strategy candidates, position or LP analysis and fact-verification status; keep public facts, metrics, scores, risks, invalidation conditions, data gaps, sources, privacy and execution status at the top level, and prohibit duplicate definitions.
3. Run `python3 scripts/ensure_runtime.py`, then run `python3 scripts/validate_result.py result.json`. If runtime preparation is not `ready` or validation fails, stop and correct the environment or result object; do not bypass or downgrade validation to generate the report.
4. Unless the user explicitly requests JSON, YAML, or other machine format only, generate Markdown following the section order in [`../templates/crypto-analysis.md`](../templates/crypto-analysis.md).
5. `brief` may compress analysis details but must retain status, data as-of, execution summary, key risks, invalidation conditions, data gaps and execution status; `standard` preserve the template core sections; `deep` add methods, calculations, sensitivities, sources and audit appendix.
6. Generate dedicated attachments as needed and register them in `artifacts[]`; do not add fact fields not present in the template temporarily—if extension is necessary, update the common Schema first.
