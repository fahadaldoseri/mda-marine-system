# {{subject}} Corporate Finance Professional Deliverable

> **Status:** {{status}} | **Decision Context:** {{payload.decision_context}} | **Data Cutoff:** {{data_cutoff}} | **Generated:** {{as_of}} | **Review Status:** {{payload.review_status.overall}}

## Executive Summary

{{summary}}

State the deliverable's purpose, conclusions, the most important quantitative results, key limitations, and scope of applicability in the opening paragraph. If conclusions rely on defaults, estimates, or checks that were not passed, explicitly label them as provisional.

## Project Scope & Call Chain

| Field | Content |
|---|---|
| Project Scope | {{payload.scope}} |
| Primary Module | {{primary_module}} |
| Call Chain | {{module_chain}} |
| Specialist Tasks | {{payload.specialist_tasks}} |
| Audience & Level of Detail | {{presentation.audience}}; {{presentation.detail_level}} |

## Entity Card

| Field | Content |
|---|---|
| Legal Name | {{payload.entity_card.legal_name}} |
| Aliases | {{payload.entity_card.aliases}} |
| Ticker & Exchange | {{payload.entity_card.ticker}}; {{payload.entity_card.exchange}} |
| Country & Industry | {{payload.entity_card.country}}; {{payload.entity_card.industry}} |
| Currency | {{payload.entity_card.currency}} |
| Fiscal Year End | {{payload.entity_card.fiscal_year_end}} |
| Reporting Standard | {{payload.entity_card.reporting_standard}} |
| Period Basis | {{payload.entity_card.period_basis}} |
| Valuation Date | {{payload.entity_card.valuation_date}} |
| Transaction Context | {{payload.entity_card.transaction_context}} |

Display unconfirmed Entity Card fields as `null` or `unknown`; do not treat unverified company names, tickers, currencies, fiscal years, or valuation dates as facts.

## Specialist Task Results

| Task ID | Status | Summary | Key Outputs | Open Items | Attachment References |
|---|---|---|---|---|---|
| `payload.task_results[].task_id` | `status` | `summary` | `key_outputs` | `open_items` | `artifact_refs` |

Trace each task result to the task catalogue, the corresponding Playbook, and its sources. Ensure values in `key_outputs` have consistent definitions in the public `metrics[]` or in auditable attachments.

## Models & Quality Checks

| Check | Status | Evidence | Impact |
|---|---|---|---|
| `payload.model_checks[].name` | `status` | `evidence` | `impact` |

For model-type tasks, explain at minimum financial identities, period consistency, units and currencies, source traceability, and sensitivity checks. For checks not run, use `not_applicable` or mark `not_run` in the review status; do not default to passing.

## Professional Deliverables

| Name | Type | Format | Path | Status | Task | Sensitivity Level |
|---|---|---|---|---|---|---|
| `payload.deliverables[].name` | `deliverable_type` | `format` | `path` | `status` | `task_ids` | `sensitivity` |

Ensure business deliverables are consistent with the top-level `artifacts[]`. Do not show downloadable paths or mark files as `ready` if they have not been produced.

## Review Status

| Dimension | Status |
|---|---|
| Financial Integrity | {{payload.review_status.financial_integrity}} |
| Period Consistency | {{payload.review_status.period_consistency}} |
| Source Traceability | {{payload.review_status.source_traceability}} |
| Format Quality | {{payload.review_status.format_quality}} |
| Overall | {{payload.review_status.overall}} |

Include supplementary output `payload.review_status.reviewer_notes[]`. Ensure any failures affect the overall status, the executive summary, or scope limitations.

## Key Metrics, Valuation & Returns

Output public `metrics[]` by task relevance, specifying units, periods, calculation methods, status, and sources. For valuation, LBO, M&A, IPO, and returns tasks, present base-case scenarios, sensitivities, capital structure, and bridge reconciliations; do not substitute unknown inputs with zero values.

## Facts, Assumptions & Data Gaps

Present `facts[]`, `assumptions[]`, and `data_gaps[]` in order. Specify `source_ref`, whether professional defaults are overridable, and their impact; distinguish user-provided values from overridden values.

## Risks and Failure Conditions

Output `risks[]`, `invalidation_conditions[]`, and `payload.scope_limitations[]` in order, and highlight red flags where applicable. For due diligence, deal materials, and IC tasks, distinguish facts, management representations, analytical inferences, and unverified items.

## Data and Sources

List `source_manifest[]`. Prioritize original disclosures, regulatory filings, and company materials; associate each key conclusion, task result, and model input with a traceable `source_ref` and period.

## Attachments, Privacy & Execution Status

List `artifacts[]`, `privacy`, and `execution`. Treat VDRs, client lists, deal models, Buyer Lists, CIMs, and unpublished materials as confidential or restricted by default; obtain confirmation before external transmission, upload, or publication.

## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
