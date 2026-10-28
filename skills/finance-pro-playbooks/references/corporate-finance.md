# Corporate Finance Specialty Plugin

When a user requests industry research, company-specific deliverables, valuation models, financial models, LBO, return attribution, transaction due diligence, Teaser, CIM, Buyer List, or other IB/PE/VC/CorpDev work products, read this file.

## Sole Primary Responsibility

This plugin is responsible for transforming confirmed facts about companies, transactions, industries, or assets into professional corporate finance analysis and institution-grade attachments. The framework layer remains solely responsible for primary module selection, cross-module invocation chains, shared data and metrics, privacy, real-world execution safety, result envelopes, and final validation.

This plugin must not take over fund/ETF product selection, personal portfolio construction, option structuring, crypto analysis, formal quantitative backtesting, or transaction handling. Concrete trade requests route to `trade-planning` for a user-executed manual plan only; no framework module may transact.

## Common Dependency Declaration

| Type | Resource | Load Conditions |
|---|---|---|
| Required | [`data-source-policy.md`](data-source-policy.md) | All corporate finance tasks |
| Required | [`metric-dictionary.md`](metric-dictionary.md) | All tasks involving financials, valuation, returns, or screening metrics |
| Conditional | [`scoring-standard.md`](scoring-standard.md) | Screening, Scorecard, IC and quantitative evaluation tasks |
| Conditional | [`privacy-security.md`](privacy-security.md) | VDR, clients, transactions, contacts and non-public materials |
| Required | [`output-contracts.md`](output-contracts.md) | All structured results and attachments |
| Conditional | [`execution-safety.md`](execution-safety.md) | Sending, uploading, publishing, submitting or other external side effects |

Take the union of this plugin's dependencies and the framework module's dependencies, deduplicate paths, and read them once. Public governance files take precedence over Playbooks; specialist Playbooks only supplement corporate finance processes, defaults, and delivery checks.

## Startup Workflow

1. Create and reuse an Entity Card for any named company or fund before any data pull.
2. Select one or more `task_id` from [`corporate-finance/task-catalog.json`](corporate-finance/task-catalog.json); do not invent ad hoc task names.
3. If scope or assumptions would materially change a model or materials, ask the minimum necessary clarification questions first.
4. Determine the reference date, fiscal periods, currency, units, and source baseline before fetching or calculating data.
5. Decide once which Playbooks and format standards are required, then read them in dependency order before execution.
6. Execute Pre-Delivery Checks for each task; all hard-coded numbers must be traceable to their sources. If Yahoo Finance is used for secondary market data or discovery, validate its source artifact and retain original-disclosure evidence for valuation-critical facts.
7. Package task results into the `corporate-finance` domain payload, and register Excel, Word, PPT, PDF, or other files in the top-level `artifacts[]`.
8. Disclose metric bases, timing, assumptions, sources, and confidence, and any applicable compliance caveats at delivery.

## Entity Card

Create the following object before the first data pull and reuse it across all plugin subtasks. Leave fields `null` if unknown; do not guess.

```yaml
legal_name: null
common_name: null
ticker: null
exchange: null
listing_status: public | private | delisted | pre_ipo | null
fiscal_year_end_month: null
reporting_currency: null
reporting_unit: null
industry_classification: null
reference_date: YYYY-MM-DD
```

The Entity Card is only for entity and period anchoring and does not replace top-level `facts[]`, `assumptions[]`, or `source_manifest[]`. For IPO, S-1, F-1, or listing status questions, return to regulatory filings for verification; do not rely on memory.

## Task Groups and Direct Resources

| Task Group | Typical Tasks | Directory and Overview |
|---|---|---|
| `market-research` | Industry Primer, Top-Down/Bottom-Up TAM, Market Map | [`corporate-finance/playbooks/market-research/_overview.md`](corporate-finance/playbooks/market-research/_overview.md) |
| `company-analysis` | Earnings Update, PIB, Adverse Media, Private Company Screening, AI Disruption | [`corporate-finance/playbooks/company-analysis/_overview.md`](corporate-finance/playbooks/company-analysis/_overview.md) |
| `valuation` | DCF, Public Comps, Precedents, SOTP, FDSO | [`corporate-finance/playbooks/valuation/_overview.md`](corporate-finance/playbooks/valuation/_overview.md) |
| `financial-models` | Three-statement, M&A accretion/dilution, synergies, IPO, model audit and editing | [`corporate-finance/playbooks/financial-models/_overview.md`](corporate-finance/playbooks/financial-models/_overview.md) |
| `lbo-structuring` | LBO, Debt Schedule, Sources & Uses, Structured Equity, Earnout, Bolt-on, Dividend Recap, Sale-Leaseback | [`corporate-finance/playbooks/lbo-structuring/_overview.md`](corporate-finance/playbooks/lbo-structuring/_overview.md) |
| `returns-analysis` | IRR Attribution, Value Creation Bridge, Liquidation Waterfall, MIP | [`corporate-finance/playbooks/returns-analysis/_overview.md`](corporate-finance/playbooks/returns-analysis/_overview.md) |
| `due-diligence` | DRL, DD Tracker, VDR Gap, QoE, revenue & customer analysis, interviews, credit agreement summaries, Pre-IC consistency review, meeting minutes | [`corporate-finance/playbooks/due-diligence/_overview.md`](corporate-finance/playbooks/due-diligence/_overview.md) |
| `deal-materials` | Teaser, CIM, Buyer List, Cross-Holder, Initiating Coverage, Scorecard, Project Overview, ECM file, research materials, opportunity screening | [`corporate-finance/playbooks/deal-materials/_overview.md`](corporate-finance/playbooks/deal-materials/_overview.md) |

Split Playbooks by task level: one directory per task group containing a group-level `_overview.md` (scope, shared defaults, format dependencies) and one `<task-id>.md` per task. Only read the task-level file(s) corresponding to the hit task(s) and the `_overview.md` of their group; do not load an entire group. Machine routing, task IDs, trigger patterns, task-level Playbook paths (`playbook` and `playbook_overview` fields), format dependencies, and common attachment types are authoritative in [`corporate-finance/task-catalog.json`](corporate-finance/task-catalog.json). Task-level file titles must match the `label` in the catalog.

## Format Resources

Read format standards only when the corresponding deliverable is required; do not load format files for plain-text responses.

| Condition | Format Standard |
|---|---|
| Creating or modifying any financial Excel workbook | [`corporate-finance/formats/excel_standards.md`](corporate-finance/formats/excel_standards.md) |
| Creating Word, PPT, Teaser, CIM or structured documents | [`corporate-finance/formats/document_standards.md`](corporate-finance/formats/document_standards.md) |
| Using EBITDA, EPS, TEV, multiples, FCF or other easily-confused corporate finance metrics | Use formulas and conventions in the public [`metric-dictionary.md`](metric-dictionary.md) as the sole authority; read [`corporate-finance/formats/metric_disambiguation.md`](corporate-finance/formats/metric_disambiguation.md) before sourcing to avoid data endpoint traps |

The public metric dictionary and the disambiguation file have a master/auxiliary relationship rather than equal authority: metric formulas, default conventions, and exception handling are authoritative in the public dictionary; the disambiguation file is an appendix for data-source pitfalls (naming and inclusion differences of standardized endpoints). In case of conflict, follow the public dictionary and correct the disambiguation file; for adjustments such as `Adjusted`/`Covenant`/`Pro Forma`, rebuild from original disclosures per the dictionary's "custom and adjusted metric" section and record the adjudication in `assumptions[]`.

## Boundaries with Framework Modules

| User Final Objective | `primary_module` | Recommended Invocation Chain |
|---|---|---|
| Formulate a stock investment view, risks, catalysts, and failure conditions | `equity-research` | `equity-research` |
| Convert stock research into DCF, Comps, quick financial commentary, or a formal coverage report | `corporate-finance` | `equity-research` → `corporate-finance` |
| Industry, TAM, Market Map or company screening | `corporate-finance` | `corporate-finance` |
| Three-statement models, M&A, IPO, LBO, Waterfall or model audit | `corporate-finance` | `corporate-finance` |
| DRL, VDR, QoE, customer cohorts or credit agreement summaries | `corporate-finance` | `corporate-finance` |
| Teaser, CIM, Buyer List or deal-specific materials | `corporate-finance` | Upstream research/valuation/diligence → `corporate-finance` |
| Review or organize existing materials (opportunity screening, Pre-IC consistency files, meeting recordings/minutes) | `corporate-finance` | `corporate-finance` (use `deal-screening-scorecard` / `pre-ic-consistency-review` / `meeting-minutes`; results use the `materials_review` payload) |
| Produce ECM pre-meeting packs or research materials (`ecm-company-profile` / `research-materials-pack`) | `corporate-finance` | Corresponding research module → `corporate-finance` |
| Convert company research or valuation conclusions into portfolio positions | `portfolio-management` | `equity-research`/`corporate-finance` → `portfolio-management` |
| Strategy backtesting or a concrete manual trade plan | `quant-backtesting`/`trade-planning` | Upstream research → backtest → user-executed manual plan; the SKILL never transacts |

Choose the primary module according to the final deliverable objective. Specialist models or transaction files should use `corporate-finance` when they are the final deliverable; investment judgments should use `equity-research` when they are the final deliverable, with specialist models as upstream inputs or attachments. Do not change the user's objective to hit this plugin.

## Multi-task Orchestration

List all `task_id` values first, then deduplicate Playbook and format paths. Execute tasks in data-dependency order; a typical sequence is:

```text
Entity Card
  → market/company research
  → financial model
  → valuation
  → transaction structure / returns
  → diligence synthesis
  → deal or IC materials
```

Each task must produce only its own outputs. Downstream tasks may reference upstream facts, assumptions, and attachments but must not silently modify them; if model conclusions change, generate a new assumptions version and record the impact.

## Data and Period Discipline

The public [`data-source-policy.md`](data-source-policy.md) is the sole authority for data governance. Yahoo Finance may be used through the approved adapter for secondary historical or delayed price context, company descriptors, holder screening, provider analytics and official-filing discovery. It must not be the authoritative source for financial statements, transaction terms, capital structure, adjusted metrics, valuation-critical facts, legal conclusions or diligence evidence. The discovered filing URL must be opened and cited directly before use.

This plugin adds the following corporate finance constraints:

1. Bind every data pull to an explicit `reference_date` and map to fiscal periods using the Entity Card's fiscal year end month.
2. Treat filing date as distinct from fiscal period; do not mix forward-looking estimates and realized data in the same series.
3. Specify which quarter LTM covers; LTM used in deal comparables must predate the transaction announcement date.
4. Use structured data for standardized filings and market series; rebuild Adjusted EBITDA, OIBDA, covenant metrics and company-specific KPIs from original disclosures. Treat Yahoo Finance fields as secondary standardized data that require confirmation against issuer or regulatory disclosures before entering a model.
5. Resolve source conflicts by returning to original disclosures; search summaries may be used for discovery only and not as final evidence.
6. Read real returned fields, units and adjustment bases; do not rely on assumed schemas.
7. Control survivorship bias, information timing, and at least one trading-day decision isolation for historical screens and lightweight backtests; hand over formal backtesting to `quant-backtesting`.

## Assumptions and Defaults

Defaults marked in Playbooks as `Defaults (apply silently, disclose at delivery)` may be applied silently when they do not change task boundaries, but record each in the top-level `assumptions[]`. Do not apply silently and ask first when any of the following conditions are met:

- The choice would change valuation or returns conclusions;
- The choice would change transaction structure, capital structure, or buyer universe;
- The choice would change anonymization, confidentiality, or external publication boundaries;
- The user has provided a conflicting preference or an existing model base;
- The Playbook's Ask First explicitly requires confirmation.

## Output Format

Construct a `finance-analysis-pro/1.2` result object, run `python3 scripts/ensure_runtime.py`, and then run [`../scripts/validate_result.py`](../scripts/validate_result.py). If runtime preparation is not `ready` or validation fails, stop; do not bypass or downgrade validation. Corporate finance deliverables must set `primary_module=corporate-finance`, `presentation.profile=corporate-finance`, and use [`../templates/corporate-finance.md`](../templates/corporate-finance.md).

```yaml
primary_module: corporate-finance
module_chain: [upstream-module, corporate-finance]
presentation:
  profile: corporate-finance
payload:
  scope: string
  decision_context: valuation
  entity_card: {}
  specialist_tasks: []
  task_results: []
  model_checks: []
  deliverables: []
  review_status: {}
  scope_limitations: []
```

The domain payload should only contain plugin tasks, the Entity Card, task results, model checks, specialist deliverables, review status, and scope limitations. Public facts, metrics, scores, risks, failure conditions, data gaps, sources, privacy and execution state should remain at the top level and must not be redefined.

Register real specialist documents in the top-level `artifacts[]`, including at minimum `artifact_id`, name, path, format, purpose, corresponding `task_ids`, sensitivity level, and status. Use `payload.deliverables[]` to describe business delivery status and `artifacts[]` for real files; align the two by path and task ID. Hard-coded values inside attachments must also have source traceability; add cell source comments to Excel per the specialist format file.

## Quality Gates

| Gate | Passing Criteria | Failure Handling |
|---|---|---|
| Task Validity | All `task_id` values originate from the task catalog | Reroute; do not create ad hoc IDs |
| Entity Clarity | Entity Card sufficiently distinguishes company, listing venue, period, currency and units | Ask minimal clarification questions |
| Source Traceability | Hard-coded numbers and key facts are traceable to sources | Mark as TBD or block conclusions |
| Model Auditability | Assumptions, formulas, links, errors and sanity checks are clear | Fix and recheck |
| Consistent Conventions | GAAP/adjusted conventions, LTM/NTM, TEV/Equity Value and units are consistent | Return to original disclosures and rebuild |
| Confidential Compliance | Blind/Named, client names, filenames and metadata, publication authorizations all checked | Keep as draft; do not publish externally |
| Default Disclosure | All applied Playbook defaults are included in `assumptions[]` | Supplement before delivery |
| Result Validity | Schema, cross-field rules, templates and attachment status all pass | Correct result object; do not bypass validation |

## Exclusions

This plugin does not handle quantitative trading systems, real order execution, private banking and tax, legal dispute calculations, real estate underwriting, or personalized investment advice based on a user's personal accounts. If a request combines plugin tasks with these scenarios, retain support for the applicable parts and hand off the rest to the corresponding framework modules; do not expand the plugin's privileges.
