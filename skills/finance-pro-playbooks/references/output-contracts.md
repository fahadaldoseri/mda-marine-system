# Unified Input/Output Contract

Read this file when producing any intermediate artifacts or final deliverables. This file is the single source of truth for the result hierarchy, common fields, status semantics, presentation formats, attachment interfaces, and file naming; the definitive definition of machine fields is in [`schemas/finance-analysis-result.schema.json`](schemas/finance-analysis-result.schema.json).

## Mandatory Output Process

All framework modules and plugin tasks must deliver in the following order; do not skip the structured result to produce free-form writing.

1. Construct a compliant result object according to `finance-analysis-pro/1.2`.
2. Validate fields, types, domain payloads, status, privacy, non-trading external-action conditions, the SKILL's financial-transaction capability prohibition, and attachment references using `scripts/validate_result.py`.
3. If the user does not request machine-only format, render a Markdown report from the template specified by `presentation.profile`.
4. Generate CSV, XLSX, PNG, HTML, DOCX, PDF, PPTX, or Python attachments only when required by the task or requested by the user.
5. For corporate finance tasks, produce genuine editable files following professional format specifications, and establish consistent references between the `deliverables[]` payload and the top-level `artifacts[]`.
6. Check file existence, naming, status, sensitivity level, and accessibility before delivering.

## Three-Tier Output

| Tier | Default file | Purpose | Delivery rules |
|---|---|---|---|
| Machine result | `result.json` | Module handoff, auditing, validation, and automation | Always construct internally; deliver when the user requests JSON, API, or automation |
| User report | `report.md` | Default human-readable output | Generate by default unless machine-only format requested |
| Professional attachments | `.csv`, `.xlsx`, `.png`, `.html`, `.docx`, `.pdf`, `.pptx`, `.py` | Data, models, charts, memos, reports, and presentations | Generate only as needed; do not fake formats by changing extensions |

## Format Selection

| User request | `presentation.formats` | Default behavior |
|---|---|---|
| Unspecified | `[markdown]` | Output domain Markdown report; retain validated result object internally |
| Short answer | `[markdown]`, `detail_level=brief` | Preserve status, data cutoff, conclusion, risks, invalidation conditions, and next steps |
| Deep report, IC, or audit materials | `[markdown]`, `detail_level=deep` | Include methods, calculations, sensitivities, sources, and audit appendices |
| JSON, API, or automation | `[json]` or `[json, markdown]` | JSON must fully validate against the Schema; include the report only if requested by the user |
| Tabular or model details | Add `csv` or `xlsx` | Use CSV for flat data; use XLSX for multiple sheets, formulas, models, and audit trail |
| Formal memos or reports | Add `docx` or `pdf` | Prefer delivering editable DOCX; generate PDF only when explicitly requested by the user |
| Charts | Add `png` or `html` | Use PNG for static delivery; use HTML for interactive charts |
| Presentation materials | Add `pptx` | Create genuine presentation files and register them as artifacts |

Unless the user explicitly requests machine-only format, prioritize presenting a human-readable report rather than dumping JSON.

## Common Result Envelope

The top-level object must contain all the fields below; use `null`, empty objects, or empty lists for fields that are not applicable, but do not remove audit fields.

```yaml
schema_version: finance-analysis-pro/1.2
skill_financial_transaction_possible: false  # immutable SKILL capability boundary; does not limit the user's independent activity outside the SKILL
request_id: string
subject: normalized instrument, company, portfolio, strategy, order or project name
primary_module: equity-research | fund-etf | options-strategy | crypto-analysis | portfolio-management | quant-backtesting | trade-planning | corporate-finance
module_chain: [module, ...]
governance_tier: light | full  # optional; default to full. light results must not include xlsx/docx/pptx professional attachments or external side effects
as_of: RFC-3339 date-time with an explicit `Z` or `±HH:MM` timezone
data_cutoff: ISO-8601 calendar date (`YYYY-MM-DD`) or timezone-qualified RFC-3339 date-time
status: complete | provisional | insufficient_data | failed | blocked
presentation:
  profile: same-as-primary_module
  language: BCP-47 string
  detail_level: brief | standard | deep
  audience: retail | professional | trader | investment_committee | management | buyer | seller | custom
  formats: [markdown | json | yaml | csv | xlsx | png | html | docx | pdf | pptx | txt, ...]
summary: non-empty string
payload: module-specific object
facts: []
assumptions: []
metrics: []
scores: []
risks: []
invalidation_conditions: []
data_gaps: []
source_manifest: []
privacy:
  data_classes_used: []
  redactions_applied: []
  retention_status: string
execution:
  external_side_effect: boolean
  confirmation_status: not_applicable | pending | confirmed | expired
artifacts: []
```

`skill_financial_transaction_possible` is required and must always be `false`. It states only that this SKILL cannot place, modify, cancel, sign, broadcast, submit, or otherwise execute a real financial transaction; it does not restrict the user's independent decisions or activity outside the SKILL. `subject` must be the normalized instrument, company, portfolio, strategy, order, or project name with unrelated personal identifiers removed. `primary_module` is the module responsible for the final deliverable and must be present in `module_chain`; `module_chain` should be ordered by data dependency and does not require the primary module to be first. `presentation.profile` must equal `primary_module`. Multi-module invocations produce a single final envelope; downstream modules must not redefine common facts, metrics, risks, sources, or execution status.

## Common Object Formats

| Object | Required fields | Description |
|---|---|---|
| `facts[]` | `fact_id`, `statement`, `source_ref`, `observation_time` | Include only verifiable facts; source references must map to the manifest |
| `assumptions[]` | `assumption_id`, `statement`, `impact`, `status` | For professional defaults, also provide `source_ref`, `overridable`, and `domain` |
| `metrics[]` | `name`, `value`, `unit`, `method`, `window`, `status`, `source_refs` | Reference metric dictionary for formula definitions; set `value=null` if not computable |
| `scores[]` | `name`, `score`, lower_bound and upper_bound, `weight`, `rationale`, `confidence` | Use weights in 0–1; scores must have anchors and rationale |
| `risks[]` | `risk_id`, `category`, `description`, `severity`, `likelihood`, `mitigation` | Do not hide risks inside domain payloads |
| `invalidation_conditions[]` | `condition`, `observable_evidence`, `action` | Specify when conclusions become invalid and how to respond |
| `data_gaps[]` | `field`, `reason`, `impact`, `remediation` | Do not use zero values to represent unknowns |
| `source_manifest[]` | `source_ref`, `title`, `publisher`, `url`, `retrieved_at`, `data_as_of` | May include `source_type`, `period`, and `original_or_derived` |
| `artifacts[]` | `name`, `path`, `format`, `purpose`, `sensitivity` | For professional attachments, also provide `artifact_id`, `task_ids`, `status`, `editable`, `checksum`, and upstream artifact references |

## Domain Payloads and Presentation Templates

All eight domain payloads are strictly defined by JSON Schema; do not use undefined `{}` or `[]` to bypass field contracts. Default reports must use the corresponding template and retain required sections.

| `primary_module` | Core domain payload objects | Default template |
|---|---|---|
| `equity-research` | Research paradigm, investment thesis, conviction, three valuation scenarios, supporting/refuting evidence, catalysts, monitoring items | [`../templates/equity-research.md`](../templates/equity-research.md) |
| `fund-etf` | Comparative universe, candidate products, tiered recommendations, operational ranges, constraints | [`../templates/fund-etf.md`](../templates/fund-etf.md) |
| `options-strategy` | Underlying view, volatility environment, strategy legs, P&L, scenarios, management, roll and lockout conditions | [`../templates/options-strategy.md`](../templates/options-strategy.md) |
| `crypto-analysis` | Assets, market structure, derivatives and on-chain signals, strategies, positions/LP, fact verification | [`../templates/crypto-analysis.md`](../templates/crypto-analysis.md) |
| `portfolio-management` | Portfolio overview, constraints, risk concentration, research conflicts, actions, allocation scenarios, before-and-after comparisons | [`../templates/portfolio-management.md`](../templates/portfolio-management.md) |
| `quant-backtesting` | Strategy specification, data inventory, benchmark, performance, robustness, parameters, file paths, validation status | [`../templates/quant-backtesting.md`](../templates/quant-backtesting.md) |
| `trade-planning` | Plan-only mode, signal card, manual order plan, plan checks, hypothetical simulation, user-controlled verification and self-execution steps outside the SKILL, mandatory capability-boundary notice, transaction-request disposition, and planning errors | [`../templates/trade-planning.md`](../templates/trade-planning.md) |
| `corporate-finance` | Entity card, specialist tasks, task results, model checks, professional deliverables, review status, and scope limitations; for existing-materials tasks also populate the optional `materials_review` payload (verified facts, scores, inconsistencies, red flags, issues, publication status) | [`../templates/corporate-finance.md`](../templates/corporate-finance.md) |

Placeholders like `{{path.to.field}}` in templates represent result object paths only; do not create new fact fields outside the Schema in templates. When lists or tables are empty, display "None" or "Not applicable"; do not remove required sections to hide data gaps.

When a `trade-planning` payload uses `transaction_request_disposition=redirected_to_manual_plan`, the user-visible output must not end at a bare refusal. It must present, in order, a concise statement that the SKILL cannot transact, the final proposed and unsubmitted manual plan, current-data/risk/account/platform verification items, and user-controlled self-execution guidance, then stop without an external side effect. A user's statement that the plan is confirmed, approved, or ready to execute is only a review of the proposal; it must not change `order_plan.status=proposed_unsubmitted`, `execution.external_side_effect=false`, or `execution.confirmation_status=not_applicable`.

### Mandatory Important Notice

Every user-visible Markdown report, regardless of `primary_module`, `governance_tier`, `detail_level`, `status`, or `audience`, must end with the following canonical section:

```markdown
## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
```

Do not omit, rename, shorten, or replace this section with a generic phrase such as "for reference only." The heading and complete canonical text are required even when the report is `brief`, `failed`, `blocked`, or based only on user-provided data. This section is presentation-layer boilerplate and does not add a field to the result Schema.

## Corporate Finance Plugin Payload

The `corporateFinancePayload` is the stable interface between the framework and 54 specialist tasks. When existing-materials tasks (`deal-screening-scorecard`, `pre-ic-consistency-review`, `meeting-minutes`) are triggered, populate the optional `materials_review` object in the payload (see Schema `materialsReview` for definition).

```yaml
scope: string
decision_context: market_research | company_analysis | valuation | financial_modeling | transaction_analysis | due_diligence | investment_committee | deal_marketing | credit_analysis | other
entity_card:
  legal_name: string
  aliases: []
  ticker: string-or-null
  exchange: string-or-null
  country: string-or-null
  industry: string-or-null
  currency: string
  fiscal_year_end: string-or-null
  reporting_standard: GAAP | IFRS | local | mixed | unknown
  period_basis: FY | LTM | NTM | quarterly | mixed | unknown
  valuation_date: string-or-null
  transaction_context: string-or-null
specialist_tasks: [task-id, ...]
task_results:
  - task_id: task-id
    status: complete | provisional | blocked | failed
    summary: string
    key_outputs: {}
    open_items: []
    source_refs: []
    artifact_refs: []
model_checks:
  - name: string
    status: passed | failed | warning | not_applicable
    evidence: string
    impact: string
deliverables:
  - name: string
    deliverable_type: analysis | model | workbook | memo | report | presentation | data_book | checklist | tracker | other
    format: file-format
    path: string-or-null
    status: planned | draft | ready | blocked
    task_ids: [task-id, ...]
    sensitivity: public | internal | confidential | restricted
review_status:
  financial_integrity: passed | failed | warning | not_run
  period_consistency: passed | failed | warning | not_run
  source_traceability: passed | failed | warning | not_run
  format_quality: passed | failed | warning | not_run
  overall: ready | provisional | blocked | failed
  reviewer_notes: []
scope_limitations: []
```

Task IDs must come from [`corporate-finance/task-catalog.json`](corporate-finance/task-catalog.json). `specialist_tasks[]` and `task_results[].task_id` should cover the same set of tasks; each `artifact_refs[]` must point to a top-level `artifacts[].artifact_id`. Model-type tasks must at minimum perform accounting identities, period consistency, source traceability, and unit checks; checks that were not run must be explicitly flagged and must not be assumed passed.

## Professional Attachment Interface

The `deliverables[]` describe business delivery status, and the top-level `artifacts[]` describe real files. Align the two by path and task ID. Each ready deliverable should have a real artifact; `planned` or `blocked` items may lack a path but must explain why.

```yaml
artifacts:
  - artifact_id: model-001
    name: targetco-lbo-model
    path: /absolute/or-delivered/path/targetco_lbo_model.xlsx
    format: xlsx
    purpose: auditable LBO model
    sensitivity: confidential
    task_ids: [lbo-model, lbo-debt-schedule]
    status: ready
    editable: true
    mime_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    checksum: string-or-null
    source_artifact_refs: []
```

Do not mark planned files as `ready`, do not register non-existent paths, and do not disguise Markdown content as DOCX, PDF, PPTX, or XLSX. Corporate finance Excel files, documents, and presentations must conform to the plugin format specifications.

## Level of Detail

| `detail_level` | Can omit | Must not omit |
|---|---|---|
| `brief` | Method details, full metric tables, secondary scenarios, and appendices | Status, data cutoff, conclusion, primary risks, invalidation conditions, data gaps, external-action status, transaction disposition when applicable, and the complete Important Notice |
| `standard` | Only raw detail and audit attachments | All core template sections, including the complete Important Notice |
| `deep` | Do not omit analysis content verified by tasks | Add methods, calculations, sensitivities, sources, and audit appendices; retain the complete Important Notice |

## Status Semantics

| Status | Usage conditions | Output requirements |
|---|---|---|
| `complete` | All key inputs and validations passed | `data_gaps` should be empty |
| `provisional` | Conclusion available but relying on estimates, minor gaps, or pending cross-checks | Mark the summary as provisional and list assumptions and impacts |
| `insufficient_data` | Critical fields missing, cannot form a reliable conclusion | List gaps and remediation; do not output pseudo-precise numbers |
| `failed` | Computation, generation, or validation failed | List failure reasons and steps tried |
| `blocked` | Blocked by permissions, privacy, confirmation for a non-trading external action, security, or external conditions | List blocking conditions; do not bypass safety gates or treat `blocked` as authority to transact |

A **non-trading** external side effect such as sending or publishing materials is allowed only when `execution.external_side_effect=true` and `confirmation_status=confirmed`. A financial transaction is never allowed, regardless of these fields. Analyses, manual order plans, paper simulations, and unsent materials must use `external_side_effect=false`; every `trade-planning` result must also use `confirmation_status=not_applicable` and must never claim a placement, modification, cancellation, fill, receipt, settlement, or reconciliation.

## Cross-Module Handoffs

Multi-module chains should exchange only structured intermediate objects; downstream modules must not infer fields from natural language summaries or override upstream assumptions.

```yaml
handoff_version: finance-analysis-pro/1.2
producer: module-or-specialist-task
consumer: module-or-specialist-task
as_of: ISO-8601 datetime
subject: string
verified_fact_refs: []
analysis_conclusions: []
quantitative_inputs: {}
constraints: {}
assumption_refs: []
invalidation_conditions: []
unresolved_conflicts: []
data_gaps: []
source_refs: []
artifact_refs: []
```

If a downstream component changes an upstream assumption, add a new `overridden` assumption and explain the impact; do not modify the upstream object in place. Specialist defaults for the corporate finance plugin must be recorded as overridable assumptions and must not be implicit in models or narrative.

## File Naming

```text
{primary_module}_{instrument-or-project}_{artifact}_{YYYYMMDD}.{ext}
```

Use lowercase letters, digits, hyphens, or underscores in names; do not include account numbers, full wallet addresses, ID numbers, phone numbers, emails, or other unnecessary identifiers. For example:

```text
equity-research_aapl_report_20260723.md
quant-backtesting_momentum_trade-log_20260723.csv
corporate-finance_project-alpha_lbo-model_20260723.xlsx
corporate-finance_project-alpha_cim_20260723.pptx
```

## Runtime Preparation and Validation Commands

Before calculation, result validation or report rendering, run the deterministic runtime preflight. It verifies that `jsonschema` is importable and satisfies `>=4.18,<5`. If the dependency is missing, broken or incompatible, it may install only the exact versions declared in `requirements.lock`, then must re-run the import and version checks. A preparation or verification failure is a hard `blocked` state: do not render, deliver or substitute a reduced validator.

```bash
python3 scripts/ensure_runtime.py
python3 scripts/validate_result.py result.json
python3 scripts/render_report.py result.json --output report.md
```

`validate_result.py` and direct `render_report.py` execution repeat the same preflight internally so that alternate invocation paths cannot bypass it. `FINANCE_SKILL_DISABLE_AUTO_INSTALL=1` is diagnostic only: when the dependency is not already ready, this setting must produce `blocked`, not a degraded report.

After generating the report, also check: runtime status is `ready`; the template matches `primary_module`; required sections are present; the data cutoff is visible; metric units and windows are visible; corporate finance tasks, model checks, and attachment references are consistent; risks, invalidation conditions, data gaps, sources, privacy, execution status, and the complete canonical Important Notice are not omitted; and attachment paths actually exist.
