# {{subject}} Equity Research

> **Status:** {{status}} | **Data cutoff:** {{data_cutoff}} | **Generated at:** {{as_of}} | **Confidence:** {{payload.confidence}}

## Executive Summary

{{summary}}

## Investment View

| Field | Result |
|---|---|
| Research Paradigm | {{payload.paradigm}} |
| Investment View | {{payload.investment_view}} |
| Confidence | {{payload.confidence}} |
| Primary Module and Call Chain | {{primary_module}}; {{module_chain}} |

## Valuation Scenarios

| Method | Currency | Bear Case | Base Case | Bull Case | Valuation As Of |
|---|---:|---:|---:|---:|---|
| {{payload.valuation.method}} | {{payload.valuation.currency}} | {{payload.valuation.bear}} | {{payload.valuation.base}} | {{payload.valuation.bull}} | {{payload.valuation.as_of}} |

## Key Arguments

Output each item in `payload.key_arguments[]`:

| Argument | Impact | Evidence References |
|---|---|---|
| `statement` | `impact` | `evidence_refs` |

## Counter-Evidence and Controversies

Use the same table format as Key Arguments for `payload.counter_evidence[]`. Do not move counter-evidence to an appendix or omit it.

## Catalysts

| Event | Expected Time Window | Observable Signals |
|---|---|---|
| `payload.catalysts[].event` | `expected_window` | `observable_signal` |

## Key Metrics and Scores

For public `metrics[]`, output name, value, unit, methodology, window, and status; for `scores[]`, output score, scale, weight, rationale, and confidence. `brief` may retain only the metrics that directly support the conclusion, but must not omit anomalous statuses.

## Risks and Failure Conditions

First output for `risks[]` the risk category, severity, likelihood, and mitigation measures; then output for `invalidation_conditions[]` the invalidation condition, observable evidence, and response actions.

## Monitoring Items

| Monitoring Item | Trigger Condition | Response |
|---|---|---|
| `payload.monitoring_items[].item` | `trigger` | `response` |

## Data Gaps and Assumptions

Output `data_gaps[]` and `assumptions[]` separately. If `status=complete` and data gaps exist, downgrade the status or explain why the gaps do not affect the conclusion.

## Data and Sources

List for `source_manifest[]` the title, publisher, data timestamp, retrieval time, and URL; cite `source_ref` for facts in the body. Do not fabricate links.

## Attachments and Security Status

List `artifacts[]`, and disclose `privacy.retention_status`, necessary de-identification measures, and `execution.confirmation_status`. If no real-world transactions were requested, explicitly state that no external side effects occurred.

## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
