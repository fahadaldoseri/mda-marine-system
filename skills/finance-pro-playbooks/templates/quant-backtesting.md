# {{subject}} Quantitative Backtest Report

> **Status:** {{status}} | **Data Cutoff:** {{data_cutoff}} | **Generated:** {{as_of}} | **Validation Status:** {{payload.validation_status}}

## Executive Summary

{{summary}}

## Strategy Specification

| Field | Content |
|---|---|
| Strategy Name | {{payload.strategy_spec.name}} |
| Universe | {{payload.strategy_spec.universe}} |
| Frequency | {{payload.strategy_spec.frequency}} |
| Signal | {{payload.strategy_spec.signal}} |
| Entry Rules | {{payload.strategy_spec.entry_rule}} |
| Exit Rules | {{payload.strategy_spec.exit_rule}} |
| Sizing Rules | {{payload.strategy_spec.sizing_rule}} |
| Risk Rules | {{payload.strategy_spec.risk_rule}} |

Ensure the strategy description is sufficient for another implementer to reproduce. Do not use undefined language such as "buy when the trend is strong."

## Data and Execution Assumptions

| Start | End | Frequency | Adjustment | Timezone | Sources | Benchmark |
|---|---|---|---|---|---|---|
| {{payload.data_manifest.start}} | {{payload.data_manifest.end}} | {{payload.data_manifest.frequency}} | {{payload.data_manifest.adjustment}} | {{payload.data_manifest.timezone}} | {{payload.data_manifest.sources}} | {{payload.benchmark}} |

Describe fees, slippage, execution timing, liquidity, suspensions, corporate actions, survivor bias, and look‑ahead bias handling in the main text; include unmodeled items in risks or data gaps.

## Performance Metrics

Output according to `payload.performance_metrics[]`:

| Metric | Value | Unit | Method | Window | Status | Source |
|---|---:|---|---|---|---|---|
| `name` | `value` | `unit` | `method` | `window` | `status` | `source_refs` |

At minimum distinguish in‑sample, out‑of‑sample, and benchmark; metrics that cannot be computed must be `null` and state the reason.

## Robustness Validation

| Test | Method | Result | Status |
|---|---|---|---|
| `payload.robustness_tests[].name` | `method` | `result` | `status` |

Do not report only passed tests. Preserve parameter perturbations, rolling windows, out‑of‑sample checks, cost stress tests, or other applicable failures.

## Parameter Results

Output parameters, in‑sample results, out‑of‑sample results, and selection status according to `payload.parameter_results[]`. Do not mask out‑of‑sample results by using full‑sample optimal parameters.

## Risks and Failure Conditions

Output `payload.failure_reasons[]`, common `risks[]`, and `invalidation_conditions[]`, and state the strategy's applicability boundaries. If `validation_status=failed`, make the executive summary explicitly state that the results are not to be used for trading decisions.

## Data Gaps and Assumptions

Output `data_gaps[]` and `assumptions[]` in order, and describe the impact of each gap on returns, drawdown, turnover, execution, or robustness assessments.

## Reproducibility Files and Charts

| Artifact | Path |
|---|---|
| Trade Log | {{payload.trade_log_path}} |
| Backtest Script | {{payload.script_path}} |
| Charts | {{payload.chart_paths}} |

Register all actual files in `artifacts[]`; if a path is empty display "Not generated", and do not display links to non‑existent files.

## Data and Sources

List `source_manifest[]`, including data versions, acquisition times, sample periods, and adjustment methods.

## Attachments and Security Status

Set default backtest result `execution.external_side_effect=false`. If the user requests preparation for execution, only generate handover objects or order drafts, and have the trading execution module complete confirmation.

## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
