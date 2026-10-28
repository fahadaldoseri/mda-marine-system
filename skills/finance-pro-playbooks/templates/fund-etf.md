# {{subject}} Fund and ETF Comparison

> **Status:** {{status}} | **Data as of:** {{data_cutoff}} | **Generated:** {{as_of}} | **Detail level:** {{presentation.detail_level}}

## Executive Summary

{{summary}}

## Comparison Objectives and Scope

| Field | Content |
|---|---|
| Comparison Scope | {{payload.comparison_scope}} |
| Operating Range | {{payload.decision_band}} |
| Primary Module and Call Chain | {{primary_module}}; {{module_chain}} |
| Applicable Constraints | {{payload.constraints}} |

## Candidate Product Comparison

Output items per `payload.candidates[]`:

| Code | Name | Exposure Fit | Structural Risk | Cost | Liquidity | Historical Performance Convention |
|---|---|---|---|---|---|---|
| `symbol` | `name` | `exposure_fit` | `structural_risks` | `cost_summary` | `liquidity_summary` | `performance_summary` |

Require every return to state whether it is a price return or a total return including dividends, the currency, the time window, and the reporting frequency; do not pseudo-annualize comparisons across different complete periods.

## Tiered Recommendations

| Dimension | Result |
|---|---|
| Best Overall | {{payload.recommendations.overall}} |
| Lowest Cost | {{payload.recommendations.lowest_cost}} |
| Most Robust Structure | {{payload.recommendations.strongest_structure}} |

If scoring coverage is insufficient or hard thresholds are not met, mark the corresponding recommendation as "Not sufficient to recommend" and do not force a ranking.

## Structural Risks and Applicability Constraints

Summarize candidates' replication method, leverage or inverse characteristics, concentration, liquidity, cross-border and custody risks, and map to public `risks[]`. Treat general tax impacts as risk descriptions only; do not provide personal tax conclusions.

## Key Metrics and Scores

Output returns, volatility, drawdown, fees, tracking, and liquidity indicators per public `metrics[]`; output weights, scoring rationale, coverage, and confidence per `scores[]`.

## Risks and Failure Conditions

Output per `risks[]` and `invalidation_conditions[]`. At minimum, describe monitoring approaches for product structure changes, tracking deviation, liquidity deterioration, or exposure drift.

## Data Gaps and Assumptions

Output `data_gaps[]` and `assumptions[]` separately, explaining how missing fund documents, historical periods, asset-level details, or market data affect the comparison.

## Data and Sources

List `source_manifest[]`; prioritize issuer documents for product terms, and note venue and timestamp for price and transaction data.

## Attachments and Security Status

List `artifacts[]`, privacy handling, and execution status. Do not display unrelated account identifiers when existing holdings are involved; real purchases must be confirmed separately.

## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
