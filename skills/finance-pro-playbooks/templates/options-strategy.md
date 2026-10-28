# {{subject}} Options Strategy

> **Status:** {{status}} | **Data cutoff:** {{data_cutoff}} | **Generated:** {{as_of}} | **Volatility regime:** {{payload.volatility_regime}}

## Executive Summary

{{summary}}

## Underlying View and Strategy Selection

| Field | Content |
|---|---|
| Underlying view | {{payload.underlying_view}} |
| Volatility environment | {{payload.volatility_regime}} |
| Preferred structure | {{payload.recommended_strategy.structure}} |
| Alternative structures | {{payload.alternatives}} |
| Primary module and invocation chain | {{primary_module}}; {{module_chain}} |

## Strategy Legs

Output each leg in `payload.recommended_strategy.legs[]`:

| Side | Type | Quantity | Strike | Expiration | Premium |
|---|---|---:|---:|---:|---:|
| `side` | `option_type` | `quantity` | `strike` | `expiration` | `premium` |

If the latest option chain is missing, set strike, expiration, or premium to `null`, and set status to `insufficient_data` or `provisional`; do not fabricate trade-level parameters.

## P&L and Capital Usage

| Currency | Net premium | Premium sign convention | Max profit | Max loss | Breakevens | Margin or capital usage |
|---|---:|---|---:|---:|---|---:|
| {{payload.recommended_strategy.currency}} | {{payload.recommended_strategy.net_premium}} | {{payload.recommended_strategy.premium_convention}} | {{payload.recommended_strategy.max_profit}} | {{payload.recommended_strategy.max_loss}} | {{payload.recommended_strategy.breakevens}} | {{payload.recommended_strategy.margin_or_capital}} |

When max profit or loss is unlimited, do not substitute an arbitrarily large number; state this explicitly in "Public Risks" and the main text.

## Scenario Analysis

| Scenario | Underlying price | Strategy P&L | Unit |
|---|---:|---:|---|
| `payload.scenario_results[].scenario` | `underlying_price` | `pnl` | `unit` |

State the scenario time points, volatility and time-value assumptions; do not treat expiration P&L charts as P&L at arbitrary holding-period times.

## Management and Roll Rules

Output `payload.management_rules[]` and `payload.roll_conditions[]` separately; for each rule, specify trigger conditions and actions; do not use non-actionable language such as "adjust as appropriate."

## No-Trade Conditions

Output each item in `payload.no_trade_conditions[]`. If any no-trade condition is met, do not leave any order instructions that could be misinterpreted as immediate trade instructions.

## Risks and Failure Conditions

For public `metrics[]`, present the definitions and timestamps for IV, Greeks, breakevens, probabilities, or risk metrics; then output `risks[]` and `invalidation_conditions[]`.

## Data Gaps and Assumptions

Output `data_gaps[]` and `assumptions[]` separately, emphasizing option chain timestamps, quote quality, interest rates, dividends, and gaps for corporate actions.

## Data and Sources

List `source_manifest[]`; option quotes must indicate exchange or vendor, timestamp, currency, and contract multiplier.

## Artifacts and Security Status

List `artifacts[]`. If only generating a strategy, explicitly set `execution.external_side_effect=false`; if live orders are involved, show confirmation status but redact account and full order identifiers.

## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
