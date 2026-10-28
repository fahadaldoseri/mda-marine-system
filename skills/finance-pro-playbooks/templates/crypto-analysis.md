# {{subject}} Crypto Asset Analysis

> **Status:** {{status}} | **Data cutoff:** {{data_cutoff}} | **Generated:** {{as_of}} | **Fact-check:** {{payload.fact_check.status}}

## Executive Summary

{{summary}}

## Subject and Market Context

| Field | Content |
|---|---|
| Assets and venues | {{payload.assets}} |
| Market context | {{payload.market_context}} |
| Primary module and call chain | {{primary_module}}; {{module_chain}} |

Specify code, network, and trading venue according to `payload.assets[]`; do not mix data from different exchanges, spot and perpetuals, or different quote currencies.

## Market Structure

| Trend | Key levels | Liquidity zones |
|---|---|---|
| {{payload.structure.trend}} | {{payload.structure.key_levels}} | {{payload.structure.liquidity_zones}} |

Output key levels by type, price, and rationale; liquidity zones must include bounds and explanation. If unable to reliably estimate, return `null` and include in data gaps.

## Derivatives Signals

Output according to `payload.derivatives_signals[]`:

| Signal | Value | Interpretation | As of | Source |
|---|---|---|---|---|
| `name` | `value` | `interpretation` | `as_of` | `source_refs` |

Do not derive a definitive directional conclusion based solely on a single funding rate or open interest signal.

## On-chain Signals

For `payload.onchain_signals[]`, use the same fields as derivatives signals. Distinguish exchange flows, active addresses, concentration of holdings, protocol data, and derived metrics; specify chain, contract, and observation window.

## Strategy Candidates

| Name | Setup | Entry Condition | Invalidation Condition | Risk |
|---|---|---|---|---|
| `payload.strategy_candidates[].name` | `setup` | `entry_condition` | `invalidation` | `risk` |

If historical testing is required, mark for transfer to quantitative backtesting; if orders are required, mark for transfer to trade planning. Do not imply in this section that actual orders have been placed.

## Position and LP Analysis

Output `payload.position_risk` and `payload.lp_analysis` only when applicable. Mask wallet and account identifiers; LP analysis must disclose ranges, fees, price path, trading fees, impermanent loss, rebalancing costs, and contract risks.

## Fact-check

Show `payload.fact_check.status` and `evidence_refs`. If unable to verify from primary or independent sources, explicitly write "unverified"; do not rewrite as fact.

## Risks and Failure Conditions

Display funding rate, Basis, on-chain, LP, yield and risk metrics according to public `metrics[]`, then output `risks[]` and `invalidation_conditions[]`.

## Data Gaps and Assumptions

Output `data_gaps[]` and `assumptions[]` separately, emphasizing venue, chain, timestamp, quote currency, contract addresses, and estimation methods.

## Data and Sources

List `source_manifest[]`. For high-risk topics, prioritize citing protocol sources, block explorers, exchange notices, or regulatory primary sources.

## Attachments and Security Status

List `artifacts[]`, privacy redaction, and execution status. Do not output private keys, seed phrases, full wallet addresses, or replayable signatures; any on-chain signature must be separately confirmed.

## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
