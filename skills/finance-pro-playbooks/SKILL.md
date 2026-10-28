---
name: finance-pro-playbooks
description: Use when a request is mainly about finance, investing, markets/instruments, portfolios, a proposed trade, corporate finance, investment banking, private equity, or a finance deliverable. Covers market data/filings; stocks, funds/ETFs, options, crypto/DeFi; portfolio analysis; backtesting; valuation, statements/models, M&A, LBO, diligence, returns, financing/credit, IPO/ECM, Teasers, CIMs, and IC materials. Use for lookups through models/documents, including requests to place, change, cancel, sign, or transmit a trade, solely to analyze and produce an unsubmitted manual plan. This SKILL never executes or submits transactions; users may act independently outside it. Do not use for finance-content reformatting, consumer/business banking product selection, or non-finance meanings such as software options, model training, project portfolios, operational diligence, order management, or business planning. Excludes real-estate underwriting, personal tax, bookkeeping, insurance, and legal advice.
---

# Finance Pro Playbooks

Provide institutional-grade finance analysis across public-market research, funds and ETFs, options, crypto, portfolio construction and management, quantitative backtesting, manual trade planning, and corporate finance tasks such as valuation, financial modeling, M&A, LBOs, due diligence, returns attribution, and deal materials preparation. Produce analysis, simulations, and plans only; never perform a financial transaction for the user.

## Core Principles

1. Identify the task, assets, final deliverable, specialist subtasks, and risk level before beginning analysis.
2. Specify only one `primary_module` per request; other modules should be upstream or downstream dependencies in sequence.
3. Apply consistent standards for data, metrics, scoring, privacy, transaction-prohibition safety, result contracts, corporate-finance methodology, model checks, and deliverable formats.
4. Preserve analytical freedom for open research; use structured inputs, deterministic scripts, and verification steps for calculations, scoring, backtesting, models, sensitive data, and external publication.
5. When key inputs are missing, first state the gaps and only ask the minimal questions that would change routing, model foundations, confidentiality boundaries, or conclusions.
6. For named companies or funds, establish an Entity Card first; for all data, establish the reference date and fiscal period.
7. Never use this SKILL, its tools, connectors, APIs, browser access, credentials, or delegated agents to access a broker, exchange, trading venue, custody system, or wallet for a transactional action. User confirmation or prior authorization cannot expand the SKILL's capabilities beyond this boundary.

## Absolute Financial Transaction Boundary

This SKILL may generate research, signals, target weights, position-sizing analysis, hypothetical or paper simulations, and manual order plans. It must never place, route, transmit, submit, sign, modify, replace, or cancel an order or transaction; transfer cash, securities, tokens, or other assets; approve a smart-contract or DeFi action; or represent that such an action was completed.

When a user asks for a transaction, convert the request into a **manual plan that the user may choose to execute independently outside this SKILL**. Use this response order: first state the transaction-capability boundary briefly; then present or restate the final proposed manual plan; then provide current-data, risk, account, and platform checks plus optional user-controlled self-execution guidance; finally stop without producing a transaction side effect. Do not end at a bare refusal when sufficient information exists to provide a useful plan. If the user later confirms the plan or asks the agent to proceed, treat that statement only as the user's review of the plan, keep `status=proposed_unsubmitted`, and return the final plan and user-controlled guidance again as needed.

Do not open or operate the transaction interface, call a write-capable trading endpoint, request transaction credentials, or ask for confirmation as a path to execution. Read-only financial data may be analyzed under the data and privacy policies, but read access must never be upgraded to transaction authority.

This is a capability boundary for the SKILL and any tools or agents operating within it. It does not prohibit, block, or otherwise restrict the user from independently choosing and carrying out a transaction outside this SKILL on a broker, exchange, wallet, or other platform.

## Standard Workflow

### Step 1: Normalize the request

Extract the following fields from the user request. Leave unspecified non-critical fields as `null`; do not fabricate values.

```yaml
intent: research | compare | advise | allocate | backtest | signal | create_order_plan | revise_order_plan | create_materials | review_documents | build_model | value | diligence
asset_class: equity | fund_etf | option | crypto | multi_asset | deal | company | industry | limited_support
instruments: []
requested_output: report | comparison | scorecard | strategy | backtest | signal_card | order_plan | model | diligence | materials
requested_formats: [markdown | json | yaml | csv | xlsx | docx | pdf | png | html | pptx]
detail_level: brief | standard | deep
audience: retail | professional | trader | investment_committee | management | buyer | seller | custom
horizon: intraday | swing | long_term | investment_period | custom | null
specialist_tasks: []
user_data_present: true | false
transaction_requested: true | false
external_publication_requested: true | false
constraints: {}
```

If the request contains multiple intents, choose the `primary_module` based on the final deliverable and establish a directed call chain. Refer to [`references/routing-catalog.md`](references/routing-catalog.md) for detailed ambiguity handling. When `corporate-finance` is selected, `specialist_tasks` must use task IDs from [`references/corporate-finance/task-catalog.json`](references/corporate-finance/task-catalog.json).

### Step 2: Select a single primary module

| Primary module | Triggered by | Not responsible for | Reads |
|---|---|---|---|
| `equity-research` | Single-stock investment views, fundamentals, valuation ranges, risks and catalysts | Professional DCF/LBO workbooks, portfolio allocation, manual order-plan construction | [`references/equity-research.md`](references/equity-research.md) |
| `fund-etf` | Fund/ETF comparison, structural risks, product selection | Single-company financial models, multi-asset holistic allocation | [`references/fund-etf.md`](references/fund-etf.md) |
| `options-strategy` | Option structures, strikes, expiries, volatility and Greeks | Deep stock research, manual order-plan construction | [`references/options-strategy.md`](references/options-strategy.md) |
| `crypto-analysis` | Crypto market analysis, SMC, DeFi LP, crypto fact-checking | General backtest engine, custody, wallet signing, or transaction submission | [`references/crypto-analysis.md`](references/crypto-analysis.md) |
| `portfolio-management` | Portfolio diagnostics, capital allocation, rebalancing, position summaries | Regenerating single-stock research or professional company models | [`references/portfolio-management.md`](references/portfolio-management.md) |
| `quant-backtesting` | Strategy definition, historical backtest, parameter tuning, robustness checks | Subjective valuation, LBO models, manual order-plan construction | [`references/quant-backtesting.md`](references/quant-backtesting.md) |
| `trade-planning` | Trade signals, hypothetical or paper simulations, and manual order plans that the user can enter independently | Broker/platform access, transaction submission, signing, order placement/modification/cancellation, fills, receipts, or custody | [`references/trade-planning.md`](references/trade-planning.md) |
| `corporate-finance` | Industry/TAM, professional financial deliverables, valuation, three-statement models, M&A, IPO, LBO, returns attribution, due diligence, Teaser/CIM/Buyer List, and handling of existing materials (deal screening, Pre-IC review, meeting minutes) | Fund selection, personal portfolios, options, crypto, formal backtests, or financial transaction submission | [`references/corporate-finance.md`](references/corporate-finance.md) |

If the request pertains to real-estate underwriting, property investment, or owner leads, do not route to `corporate-finance`.

FX, futures, and commodities are limited-support asset classes (`asset_class: limited_support`): this Skill has no dedicated analysis module and must not pretend to have a dedicated methodology. Disposition rules: strategy backtest requests → `quant-backtesting` (engine asset-neutral); trade and order requests → `trade-planning` for a manual plan only; macro multi-asset allocation → `portfolio-management`; pure market and fundamental analysis → declare limited support and process with general analysis capabilities, with result confidence no higher than `medium`. Never access a broker or venue transaction interface. See the limited-support section of [`references/routing-catalog.md`](references/routing-catalog.md).

### Step 3: Determine ordered module calls

Execute composite requests in dependency order; prohibit parallel generation of conflicting facts or models.

| User final goal | Recommended call chain |
|---|---|
| Analyze a stock and design an options strategy | `equity-research` → `options-strategy` |
| Select ETFs and configure into a portfolio | `fund-etf` → `portfolio-management` |
| Research a stock and decide position size | `equity-research` → `portfolio-management` |
| Research a company and produce DCF, Comps or financial quick notes | `equity-research` → `corporate-finance` |
| Conduct industry research then screen and value companies | `corporate-finance` |
| Model, value, diligence and produce IC / deal materials | Execute internally within `corporate-finance` according to task DAG |
| Convert professional model conclusions into portfolio positions | `corporate-finance` → `portfolio-management` |
| Design, backtest and prepare a manual trade plan | Relevant asset module → `quant-backtesting` → `trade-planning` |
| Convert general research into roadshow or ECM materials | Relevant research module → `corporate-finance` (`research-materials-pack` / `ecm-company-profile`) |
| Review, organize or cross-check user-provided existing materials | `corporate-finance` (`deal-screening-scorecard` / `pre-ic-consistency-review` / `meeting-minutes`) |
| Convert valuation, diligence or LBO conclusions into Teaser/CIM/IC materials | `corporate-finance` |

Each upstream node must output a structured intermediate artifact. Downstream nodes may reference but must not silently modify upstream facts, assumptions, or versions.

### Step 4: Determine governance channel and load dependencies

First determine the channel according to the `governance_tier` rules in [`references/module-catalog.json`](references/module-catalog.json) (the `governance_tier` field in `scripts/route_request.py` output):

- light channel: Pure analysis, no sensitive data, no professionally editable attachments (xlsx/docx/pptx), no external publication or sending, and no corporate-finance specialist tasks selected. Required reading converges to at most four documents: the primary module domain document + the public envelope section of [`references/output-contracts.md`](references/output-contracts.md) + (if computations involved) [`references/metric-dictionary.md`](references/metric-dictionary.md) + (if external data involved) [`references/data-source-policy.md`](references/data-source-policy.md). Result objects must still pass Schema validation and declare `governance_tier: light` in the envelope; light results must not include professional editable attachments or external side effects (`scripts/validate_result.py` will reject them); if task escalation triggers full conditions, revert to full channel and reload dependencies.
- full channel: All other requests (corporate-finance specialist tasks, sensitive data, professional attachments, external publication or sending, institutional audiences) follow the full rules below. No governance tier permits this SKILL to perform a financial transaction; the user's independent activity outside the SKILL is unaffected.

Under the full channel, each domain Reference declares required and conditional dependencies. Load the union and deduplicate:

```text
required_references =
  entrance condition set
  ∪ required dependencies for all hit domains
  ∪ corporate-finance task entry and selected Playbook
  ∪ all conditionally satisfied domain dependencies
  ∪ satisfied format dependencies
```

If rules conflict, use the shared References for data, privacy, execution safety, and result contracts; use the selected Playbook for corporate-finance methodology, model checks, and attachment formats; apply the stricter security constraint.

| Entrance condition | Add to dependency set |
|---|---|
| Involves external or user-provided data, including Yahoo Finance | [`references/data-source-policy.md`](references/data-source-policy.md); for approved Yahoo Finance operations use `scripts/fetch_yahoo_finance.py` and `scripts/validate_yahoo_source.py` |
| Involves any computed metric | [`references/metric-dictionary.md`](references/metric-dictionary.md); prioritize running `scripts/finance_metrics.py` |
| Involves scoring, weights, ratings or confidence | [`references/scoring-standard.md`](references/scoring-standard.md) |
| Involves positions, accounts, wallets, recordings, files, deal materials or credentials | [`references/privacy-security.md`](references/privacy-security.md) |
| Involves signals, order plans, a request to transact, automation, external publication, or other high-risk actions | [`references/execution-safety.md`](references/execution-safety.md); transaction requests must be redirected to a manual plan |
| Generates any final deliverable | [`references/output-contracts.md`](references/output-contracts.md) |
| Hits any corporate-finance task | [`references/corporate-finance.md`](references/corporate-finance.md) + the Playbook specified by the task catalog |
| Generates corporate-finance Excel/Word/PPT | The format standard specified by the task catalog |

### Step 5: Prepare runtime, analyze, validate, correct

1. Run `python3 scripts/ensure_runtime.py` before any calculation, result validation or report rendering. It must verify `jsonschema>=4.18,<5`, install only the exact versions in `requirements.lock` when the dependency is missing, broken or incompatible, and re-check the runtime after installation. If the returned status is not `ready`, stop; never bypass or downgrade Schema validation.
2. Establish a plan according to the primary module and call chain; when selecting corporate-finance specialist tasks, create an Entity Card and `specialist_tasks` first.
3. When Yahoo Finance is suitable under [`references/data-source-policy.md`](references/data-source-policy.md), fetch only through `scripts/fetch_yahoo_finance.py`, validate the generated source artifact with `scripts/validate_yahoo_source.py`, preserve the artifact, copy its `source_manifest_entry` into the final `source_manifest[]`, and map supported claims to that `source_ref`. A `blocked` or `failed` artifact is a data gap, never permission to use remembered values, undocumented endpoints or an execution-grade conclusion.
4. Calculate metrics using public conventions, and log inputs, time windows, units, sources and exception handling.
5. Execute specialist tasks according to the Playbook and write all defaults into `assumptions[]`.
6. Validate facts, calculations, scoring, models, source artifacts, attachments and conclusions separately; on failure, correct and re-validate.
7. Construct a `finance-analysis-pro/1.2` result object per [`references/output-contracts.md`](references/output-contracts.md); do not bypass the structured result in favor of free-form writing.
8. Run `scripts/validate_result.py` to validate the public envelope, domain payloads, privacy, external-action governance, transaction prohibition, and attachment fields. This script repeats the same runtime preflight before importing the Schema engine.
9. Unless the user explicitly requests machine-only formats, select `templates/{primary_module}.md` according to `presentation.profile` and run `scripts/render_report.py`; direct rendering also repeats the runtime preflight.
10. Before delivery, check period, base conventions, assumptions, risks, failure conditions, data gaps, sources, model checks, attachment status, and the complete canonical `## Important Notice` section; when corporate-finance specialist tasks are selected, reconcile against the Playbook's Pre-Delivery Checks and Scope Boundaries section line by line before delivery.

Do not output falsely precise numbers when key data is missing; do not rewrite "unable to verify" as "verified"; do not use professional formatting to mask data or model gaps.

## Corporate-Finance Task Loading Rules

When `corporate-finance` is hit, read [`references/corporate-finance.md`](references/corporate-finance.md) first, then load Playbooks at the task level per task. For each hit `task_id`, read only the task-level file pointed to by the task catalog `playbook` field (`references/corporate-finance/playbooks/<group>/<task-id>.md`) and its group-level overview pointed to by `playbook_overview` (`references/corporate-finance/playbooks/<group>/_overview.md`), deduplicating paths for multiple tasks. Do not load entire groups or the whole repository of task-level files. Eight task-group directories:

- [`references/corporate-finance/playbooks/market-research/`](references/corporate-finance/playbooks/market-research/_overview.md)
- [`references/corporate-finance/playbooks/company-analysis/`](references/corporate-finance/playbooks/company-analysis/_overview.md)
- [`references/corporate-finance/playbooks/valuation/`](references/corporate-finance/playbooks/valuation/_overview.md)
- [`references/corporate-finance/playbooks/financial-models/`](references/corporate-finance/playbooks/financial-models/_overview.md)
- [`references/corporate-finance/playbooks/lbo-structuring/`](references/corporate-finance/playbooks/lbo-structuring/_overview.md)
- [`references/corporate-finance/playbooks/returns-analysis/`](references/corporate-finance/playbooks/returns-analysis/_overview.md)
- [`references/corporate-finance/playbooks/due-diligence/`](references/corporate-finance/playbooks/due-diligence/_overview.md)
- [`references/corporate-finance/playbooks/deal-materials/`](references/corporate-finance/playbooks/deal-materials/_overview.md)

Format documents are loaded only when generating the corresponding attachments:

- [`references/corporate-finance/formats/excel_standards.md`](references/corporate-finance/formats/excel_standards.md)
- [`references/corporate-finance/formats/document_standards.md`](references/corporate-finance/formats/document_standards.md)
- [`references/corporate-finance/formats/metric_disambiguation.md`](references/corporate-finance/formats/metric_disambiguation.md)

<!-- task-index:start (generated by scripts/validate_skill.py --sync-index; do not edit by hand) -->
<details>
<summary>Plugin task quick-access index (generated by task-catalog.json; expand to jump directly to any task-level Playbook)</summary>

- **company-analysis**(5):[`adverse-media-screen`](references/corporate-finance/playbooks/company-analysis/adverse-media-screen.md) · [`ai-disruption-assessment`](references/corporate-finance/playbooks/company-analysis/ai-disruption-assessment.md) · [`earnings-update`](references/corporate-finance/playbooks/company-analysis/earnings-update.md) · [`private-company-screening`](references/corporate-finance/playbooks/company-analysis/private-company-screening.md) · [`public-information-book`](references/corporate-finance/playbooks/company-analysis/public-information-book.md)
- **deal-materials**(10):[`business-quality-scorecard`](references/corporate-finance/playbooks/deal-materials/business-quality-scorecard.md) · [`buyer-list-development`](references/corporate-finance/playbooks/deal-materials/buyer-list-development.md) · [`cim-executive-summary`](references/corporate-finance/playbooks/deal-materials/cim-executive-summary.md) · [`cross-holder-analysis`](references/corporate-finance/playbooks/deal-materials/cross-holder-analysis.md) · [`deal-screening-scorecard`](references/corporate-finance/playbooks/deal-materials/deal-screening-scorecard.md) · [`deal-teaser`](references/corporate-finance/playbooks/deal-materials/deal-teaser.md) · [`ecm-company-profile`](references/corporate-finance/playbooks/deal-materials/ecm-company-profile.md) · [`initiating-coverage-report`](references/corporate-finance/playbooks/deal-materials/initiating-coverage-report.md) · [`project-overview`](references/corporate-finance/playbooks/deal-materials/project-overview.md) · [`research-materials-pack`](references/corporate-finance/playbooks/deal-materials/research-materials-pack.md)
- **due-diligence**(12):[`buy-side-qoe-review`](references/corporate-finance/playbooks/due-diligence/buy-side-qoe-review.md) · [`credit-agreement-summary`](references/corporate-finance/playbooks/due-diligence/credit-agreement-summary.md) · [`customer-level-revenue-analytics`](references/corporate-finance/playbooks/due-diligence/customer-level-revenue-analytics.md) · [`dd-request-list`](references/corporate-finance/playbooks/due-diligence/dd-request-list.md) · [`dd-tracker`](references/corporate-finance/playbooks/due-diligence/dd-tracker.md) · [`expert-call-guide`](references/corporate-finance/playbooks/due-diligence/expert-call-guide.md) · [`management-meeting-questions`](references/corporate-finance/playbooks/due-diligence/management-meeting-questions.md) · [`meeting-minutes`](references/corporate-finance/playbooks/due-diligence/meeting-minutes.md) · [`pre-ic-consistency-review`](references/corporate-finance/playbooks/due-diligence/pre-ic-consistency-review.md) · [`retention-cohort-analysis`](references/corporate-finance/playbooks/due-diligence/retention-cohort-analysis.md) · [`revenue-data-cleanup-audit`](references/corporate-finance/playbooks/due-diligence/revenue-data-cleanup-audit.md) · [`vdr-gap-analysis`](references/corporate-finance/playbooks/due-diligence/vdr-gap-analysis.md)
- **financial-models**(6):[`ipo-model`](references/corporate-finance/playbooks/financial-models/ipo-model.md) · [`live-model-editing`](references/corporate-finance/playbooks/financial-models/live-model-editing.md) · [`merger-model`](references/corporate-finance/playbooks/financial-models/merger-model.md) · [`model-audit`](references/corporate-finance/playbooks/financial-models/model-audit.md) · [`synergy-analysis`](references/corporate-finance/playbooks/financial-models/synergy-analysis.md) · [`three-statement-model`](references/corporate-finance/playbooks/financial-models/three-statement-model.md)
- **lbo-structuring**(8):[`bolt-on-acquisition-modeling`](references/corporate-finance/playbooks/lbo-structuring/bolt-on-acquisition-modeling.md) · [`dividend-recap-modeling`](references/corporate-finance/playbooks/lbo-structuring/dividend-recap-modeling.md) · [`earnout-modeling`](references/corporate-finance/playbooks/lbo-structuring/earnout-modeling.md) · [`lbo-debt-schedule`](references/corporate-finance/playbooks/lbo-structuring/lbo-debt-schedule.md) · [`lbo-model`](references/corporate-finance/playbooks/lbo-structuring/lbo-model.md) · [`sale-leaseback-modeling`](references/corporate-finance/playbooks/lbo-structuring/sale-leaseback-modeling.md) · [`sources-and-uses`](references/corporate-finance/playbooks/lbo-structuring/sources-and-uses.md) · [`structured-equity-modeling`](references/corporate-finance/playbooks/lbo-structuring/structured-equity-modeling.md)
- **market-research**(4):[`industry-primer`](references/corporate-finance/playbooks/market-research/industry-primer.md) · [`market-map`](references/corporate-finance/playbooks/market-research/market-map.md) · [`tam-bottom-up`](references/corporate-finance/playbooks/market-research/tam-bottom-up.md) · [`tam-top-down`](references/corporate-finance/playbooks/market-research/tam-top-down.md)
- **returns-analysis**(4):[`irr-attribution`](references/corporate-finance/playbooks/returns-analysis/irr-attribution.md) · [`liquidation-waterfall`](references/corporate-finance/playbooks/returns-analysis/liquidation-waterfall.md) · [`mip-modeling`](references/corporate-finance/playbooks/returns-analysis/mip-modeling.md) · [`value-creation-bridge`](references/corporate-finance/playbooks/returns-analysis/value-creation-bridge.md)
- **valuation**(5):[`dcf-model`](references/corporate-finance/playbooks/valuation/dcf-model.md) · [`fully-diluted-share-count`](references/corporate-finance/playbooks/valuation/fully-diluted-share-count.md) · [`precedent-transactions`](references/corporate-finance/playbooks/valuation/precedent-transactions.md) · [`public-comps`](references/corporate-finance/playbooks/valuation/public-comps.md) · [`sotp-valuation`](references/corporate-finance/playbooks/valuation/sotp-valuation.md)

</details>
<!-- task-index:end -->

## Routing and safety gates

| Situation | Action |
|---|---|
| Asset, task or professional deliverable is ambiguous and would change the primary module | Ask one minimal clarifying question and pause domain execution |
| Valuation, capital structure, TAM boundaries, buyer criteria or anonymization choices would materially change results | Confirm before modeling or preparing materials |
| Only optional parameters are missing | Use overridable defaults and record them in `assumptions[]` |
| User uploads positions, models, VDR, deal materials or account files | Read privacy rules and minimize and mask unrelated identifiers |
| User requests any financial transaction, including order placement, amendment, cancellation, payment, transfer, signing, or broadcast | Read execution safety rules; refuse to perform the transactional action and redirect only to a manual plan that the user may choose to carry out independently outside this SKILL |
| User requests a non-trading external transmission or publication | Read execution safety rules and obtain explicit confirmation before that non-trading action |
| Data unavailable or cannot be point-verified | Output data gaps and do not generate trade-level or IC-level deterministic conclusions |
| Request outside supported scope | Decline incorrect routing and explain the closest supported capability |

## Deterministic resources

- `scripts/route_request.py`: Generate the primary module, call chain, specialist tasks, and required references.
- `scripts/finance_metrics.py`: Compute public metrics and perform boundary checks.
- `scripts/ensure_runtime.py`: Check the full Schema runtime, install only `requirements.lock` when necessary, re-verify the dependency, and fail closed on any preparation error.
- `scripts/validate_skill.py`: Check structure, links, dependency declarations, task catalog, Schema, templates and sensitive information.
- `scripts/validate_result.py`: Validate results against JSON Schema and cross-field rules.
- `scripts/render_report.py`: Render a validated result into a primary-module report.
- `references/schemas/finance-analysis-result.schema.json`: Define the `finance-analysis-pro/1.2` public envelope and eight domain payloads.
- `templates/*.md`: Define default Markdown rendering order for the eight domains.

Environment and self-check: run `python3 scripts/ensure_runtime.py` first. If `jsonschema` is missing, broken or outside `>=4.18,<5`, the preflight installs the exact reviewed versions in `requirements.lock` with `sudo uv pip install --system`, falling back to non-interactive `sudo pip3 install`; it then re-checks importability and version. Installation or verification failure returns a machine-readable `blocked` status and prohibits validation or rendering. Set `FINANCE_SKILL_DISABLE_AUTO_INSTALL=1` only for diagnostic check-only environments; it must not be used to bypass validation. After modifying this Skill, run `python3 -m unittest discover -s tests` and `python3 scripts/validate_skill.py`; both must pass. The test suite disables bytecode writing and will not pollute the repository.

## Final checks

Before delivery confirm: runtime preflight status is `ready`; single primary module; ordered call chain and specialist tasks; dependencies collected and deduplicated; only necessary resources loaded; Entity Card and fiscal period clear; metrics and models reproducible; data sources and cutoff dates visible; defaults disclosed; sensitive fields minimized; no financial transaction was performed or enabled by this SKILL; the output does not restrict the user's independent activity outside the SKILL; any separate non-trading external action was explicitly confirmed; result object passes Schema; template matches primary module; professional attachments pass Playbook and format checks; no real-estate, personal tax, legal or other excluded tasks misrouted to this Skill.
