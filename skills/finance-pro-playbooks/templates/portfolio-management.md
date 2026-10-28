# {{subject}} Portfolio Management Report

> **Status:** {{status}} | **Data Cutoff:** {{data_cutoff}} | **Generated:** {{as_of}} | **Privacy Handling:** {{privacy.retention_status}}

## Executive Summary

{{summary}}

## Portfolio Overview

| Currency | NAV | Holdings Count | Cash Weight | Primary Module & Call Chain |
|---|---:|---:|---:|---|
| {{payload.portfolio_summary.currency}} | {{payload.portfolio_summary.nav}} | {{payload.portfolio_summary.holdings_count}} | {{payload.portfolio_summary.cash_weight}} | {{primary_module}}; {{module_chain}} |

If NAV or weights are based on incomplete holdings, return `null` or a degraded status; do not extrapolate a complete portfolio from known holdings.

## Constraint Status

| Constraint | Status | Evidence |
|---|---|---|
| `payload.constraint_status[].constraint` | `status` | `evidence` |

Present hard constraints and violations first, then discuss optimizations; do not use high expected returns to override hard threshold failures.

## Risk and Concentration Exposures

Output portfolio risk metrics per `payload.risk_metrics[]`; output concentration exposures per `payload.concentration_exposures[]`:

| Dimension | Exposure Name | Current Weight | Limit | Status |
|---|---|---:|---:|---|
| `dimension` | `name` | `weight` | `limit` | `status` |

Specify the denominator used for weights, currency, valuation timestamp, and derivative look-through methodology.

## Research Conflicts

| Instrument | Conflict | Resolution |
|---|---|---|
| `payload.research_conflicts[].instrument` | `conflict` | `resolution` |

Do not have the portfolio module redo single-issue research; refer conflicts back to the corresponding research module for review.

## Recommended Actions

Output respectively `payload.recommended_actions.primary[]`, `alternatives[]` and `do_not_do[]`.

| Instrument | Action | Current Weight | Target Weight | Rationale | Priority |
|---|---|---:|---:|---|---|
| `instrument` | `action` | `current_weight` | `target_weight` | `rationale` | `priority` |

Sum of target weights and cash must comply with portfolio constraints; if only relative weights are provided, state this explicitly.

## Allocation Scenarios

Output scenario name, assumptions, target weights, and expected impact per `payload.allocation_scenarios[]`. Do not present scenario results as promised returns.

## Before-and-After Comparison

| Metric | Before Adjustment | After Adjustment | Unit | Status |
|---|---:|---:|---|---|
| `payload.post_trade_comparison[].metric` | `before` | `after` | `unit` | `status` |

## Monitoring Triggers

| Trigger | Threshold | Response |
|---|---|---|
| `payload.monitoring_triggers[].trigger` | `threshold` | `response` |

## Risks and Failure Conditions

Output `risks[]` and `invalidation_conditions[]` in order, and specify portfolio constraints, concentration exposures, and recommended invalidation conditions.

## Data Gaps and Assumptions

Output `data_gaps[]` and `assumptions[]` in order. The portfolio report must explicitly state how missing holdings, historical periods, or benchmarks affect recommendations.

## Data and Sources

List `source_manifest[]`, distinguishing user-provided data from public market data; do not display account numbers, full transaction histories, or unrelated personal fields.

## Artifacts and Security Status

List `artifacts[]`, redaction measures and execution status. Portfolio recommendations are not orders; any actual rebalancing must be handed off to trade planning and receive explicit confirmation.

## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
