FILE: references/routing-catalog.md

--- BEGIN FILE ---
--- BEGIN FILE ---
# Finance Request Routing Catalog

Read this file only when module selection, ambiguity resolution, or multi-module chaining is required. The framework first determines the single primary module; the corporate-finance plugin parses specialist tasks only upon hit.

## Routing Output

Always first produce the following intermediate artifact before reading domain References:

```json
{
  "primary_module": "corporate-finance",
  "module_chain": ["equity-research", "corporate-finance"],
  "intent": "value",
  "asset_class": "company",
  "requested_output": "model",
  "specialist_tasks": ["dcf-model", "public-comps"],
  "risk_flags": [],
  "required_references": [
    "references/equity-research.md",
    "references/corporate-finance.md",
    "references/corporate-finance/playbooks/valuation/_overview.md",
    "references/corporate-finance/playbooks/valuation/dcf-model.md",
    "references/corporate-finance/playbooks/valuation/public-comps.md",
    "references/corporate-finance/formats/excel_standards.md",
    "references/corporate-finance/formats/metric_disambiguation.md",
    "references/data-source-policy.md",
    "references/metric-dictionary.md",
    "references/output-contracts.md"
  ],
  "missing_critical_inputs": [],
  "assumptions": []
}
```

`primary_module` is responsible for the final delivery; `module_chain` is ordered by data dependency; `specialist_tasks` may be non-empty only if the chain includes `corporate-finance`, and must come from [`corporate-finance/task-catalog.json`](corporate-finance/task-catalog.json).

## Task Priority Routing

| Final Task | Primary Module | Asset or Deliverable Adjustment |
|---|---|---|
| Research a public company's investment thesis, financials, risks, catalysts, and valuation range | `equity-research` | If a specialist DCF/Comps/coverage report is required, change the chain tail to `corporate-finance` |
| Compare funds, ETFs, fees, and tracking structures | `fund-etf` | If configuration into a portfolio is requested, add `portfolio-management` downstream |
| Select option structure, strike prices, or expiries | `options-strategy` | Interpret bare `options` or `call` as financial derivatives only with explicit finance context such as strategy, trading, contract, strike, expiry/expiration, premium, underlying, Greeks, IV, stock/equity/index/ETF, fundamentals, backtest, or trade-plan terms; if an underlying equity assessment is needed, add `equity-research` upstream |
| Analyze crypto price action, SMC, DeFi LPs, or crypto facts | `crypto-analysis` | If formal historical validation is required, add `quant-backtesting` downstream |
| Diagnose an entire investment holding, allocate capital, or rebalance | `portfolio-management` | Require investment context such as holdings, assets, allocation, diversification, concentration, risk, drawdown, turnover, weights, rebalancing, securities, funds, or a financial portfolio; target research or valuation as upstream; do not change final responsibility |
| Backtest, optimize parameters, or assess strategy robustness | `quant-backtesting` | Crypto-specific assumptions may first read `crypto-analysis` |
| Generate signals or manual order plans, including a request to place, modify, replace, or cancel an order | `trade-planning` | Research and backtesting remain upstream; any transaction request is prohibited and converted to a user-executed manual plan |
| Process existing materials: general opportunity screening, Pre-IC file review, meeting recordings/minutes organization | `corporate-finance` | If hitting tasks `deal-screening-scorecard` / `pre-ic-consistency-review` / `meeting-minutes`, return results using the `materials_review` payload |
| Industry/TAM/Market Map, professional earnings updates, PIB or private company screening | `corporate-finance` | Select market research or company analysis tasks from the task catalog |
| DCF, Comps, Precedents, SOTP, or diluted share count | `corporate-finance` | Use the valuation Playbook; load specialist formats when producing Excel |
| Three-statement models, M&A accretion/dilution, synergies, IPO, LBO, waterfall, or model audit | `corporate-finance` | Use the corresponding model, LBO, or returns Playbook |
| DRL, VDR gap, QoE, client cohort, interview guides, or credit summaries | `corporate-finance` | Use the due-diligence Playbook; `expert-call-guide` requires an explicit guide/questions/agenda/outline or creation signal and declares `corporate-finance` as final owner while retaining upstream research modules; sensitive materials trigger privacy rules |
| Teaser, CIM, Buyer List, Initiating Coverage, or specialist IC materials | `corporate-finance` | Complete upstream research, valuation, model, and due diligence first; external distribution triggers security confirmation |

## Corporate Finance Task Parsing

Upon hitting `corporate-finance`, read the plugin entry and task catalog. May select multiple `specialist_tasks`, but deduplicate Playbook and format dependencies, and execute in the following order:

```text
Entity Card
  → market-research / company-analysis
  → financial-models
  → valuation
  → lbo-structuring / returns-analysis
  → due-diligence
  → deal-materials
```

Task tags, IDs, trigger modes, Playbook, formats, and common attachments defer to the task catalog. If text hits multiple tasks but the user requests only one final deliverable, retain one specialist task and treat other hits as upstream analysis steps; do not expand the scope meaninglessly.

## High-Frequency Ambiguities

| User Request | Determination Rule |
|---|---|
| "Analyze this stock and tell me how much to buy" | `equity-research` → `portfolio-management`; final primary module is `portfolio-management` |
| "Compare SPY and VOO and add to my portfolio" | `fund-etf` → `portfolio-management`; final primary module is `portfolio-management` |
| "How to buy Apple now" | Valuation/judgment goes to `equity-research`; short-term price points or order plans go to `trade-planning`; if unclear, ask for time horizon and desired output |
| "Do a valuation for Apple" | If only an investment range is needed, use `equity-research`; if a DCF/Comps/SOTP workbook is explicitly requested, use `corporate-finance` |
| "Create a company presentation" | Creation of new materials (ECM profile, research materials, PIB, Initiating Coverage) goes to `corporate-finance`; if an investment view is required, run `equity-research` upstream; if the user provides existing materials for review or organization, hit existing-materials tasks (e.g., `pre-ic-consistency-review`) |
| "Prepare roadshow materials / ECM pre-meeting files" | New material production hits plugin tasks `research-materials-pack` / `ecm-company-profile`; primary responsibility is `corporate-finance`; if new research conclusions are needed, add the relevant research module upstream |
| "Draft an IC memo" | Always route to `corporate-finance`; assemble research conclusions into deal-materials tasks; if valuation models, due diligence, or transaction structure are included, complete upstream tasks per the task DAG first |
| "Evaluate a project" | For publicly traded securities, use `equity-research`; for institutional trade screening, modeling, or due diligence, use `corporate-finance`; exclude real estate projects |
| "Analyze whether to roll an option position" | `options-strategy`; add `trade-planning` only when a concrete manual roll plan is requested; the user must implement any roll independently |
| "Backtest my portfolio" | `quant-backtesting`; add `portfolio-management` for current portfolio health diagnostics; do not conflate into the same computation |
| "Do an LBO and tell me whether to buy" | `corporate-finance` handles the model; if the final request is a personalized investment decision, limit output to research analysis and state data and applicability boundaries |
| "Create and send a Teaser" | Creation is handled by `corporate-finance`; actual sending is an external operation and requires explicit confirmation before sending |
| "Analyze the company's latest earnings" (no institutional deliverable signal) | Retail-style earnings interpretation goes to `equity-research`; only hit plugin task `earnings-update` when a quick note, memo, or PPT institutional deliverable is explicitly requested |
| "Prepare an expert call guide" | Hit `expert-call-guide`; `corporate-finance` owns the final deliverable, while any company or security research remains upstream in the module chain |
| "Expert call", "earnings call", or "conference call" without an expert-guide deliverable signal | Do not hit `expert-call-guide`, and do not infer `options-strategy` from the bare word `call`; route only on other explicit intents or request clarification |
| "Compare software configuration options" | The generic word `options` has no financial derivative context; do not activate `options-strategy`; request clarification or leave the finance SKILL |
| "Create a project portfolio dashboard" | The generic word `portfolio` has engineering/project context and no investment signal; do not activate `portfolio-management`; request clarification or leave the finance SKILL |

## Merging Rules When Multiple Modules Are Hit

Since catalog 1.1 there is no longer special-case cross-module merging: the former `ir-deal-materials` module has been fully merged into `corporate-finance`. Handling existing materials (opportunity screening, Pre-IC review, meeting minutes) and producing new materials (Teaser, ECM profile, research materials) are determined at the task level by trigger modes in [`corporate-finance/task-catalog.json`](corporate-finance/task-catalog.json). Tasks marked `requires_research_upstream` automatically add `equity-research` upstream when the request contains research verbs.

## Primary Module Decision Priority

When a single request contains multiple actions, determine the primary module by the final deliverable:

1. A concrete trade signal or manual order plan, including any prohibited request for the SKILL to place, modify, replace, or cancel a transaction: `trade-planning`.
2. Portfolio capital allocation or rebalancing: `portfolio-management`.
3. Formal strategy historical validation: `quant-backtesting`.
4. Option structure selection: `options-strategy`.
5. Specialist corporate finance modeling, due diligence, transaction deliverables, and review of existing materials, meeting minutes, opportunity screening: `corporate-finance`.
6. Fundamental research and product comparison: select `equity-research`, `fund-etf`, or `crypto-analysis` by asset.

A matched specialist task may declare `final_owner` in the task catalog. When exactly one declared owner is present, the router may override `primary_module` with that owner without removing candidates or changing dependency-chain order. For `expert-call-guide`, this override applies only after its explicit deliverable-signal gate succeeds. Any request to execute, place, modify, replace, cancel, sign, broadcast, approve, transfer, or otherwise perform a financial transaction takes precedence and remains owned by `trade-planning` as a prohibited-action redirect to a user-executed manual plan.

This priority only determines final responsibility and does not permit skipping upstream research, modeling, validation, or safety rules. No priority, governance tier, credential, connector, or user confirmation authorizes the SKILL to perform a financial transaction.

## Limited-Support Asset Classes (FX, Futures, Commodities)

This Skill has no dedicated analysis modules for FX, futures, or commodities and must not claim proprietary methodologies for them. `scripts/route_request.py` handles these per the [`module-catalog.json`](module-catalog.json) §`limited_support`:

| Request Intent | Handling |
|---|---|
| Strategy backtest, parameter optimization | Route to `quant-backtesting` (engine asset-neutral), attach `limited_support_note` to output |
| Trade plan, order placement request, or order modification request | Route to `trade-planning` for a manual plan only; require the user to verify current market and platform support independently |
| Commodity/FX leaks in multi-asset allocation | Route to `portfolio-management` and treat as a configuration dimension |
| Pure price action, trend, or fundamental analysis | Return `status: limited_support`: declare limited support to the user and handle with general analysis capabilities; result confidence must not exceed `medium`; do not apply any domain-specific template phrasing or conclusions |

If a limited-support asset is hit together with triggers for other modules, keep normal routing and append a `limited_support_note`; the executor must disclose capability boundaries in the delivery.

## Governance Channel Determination

After routing, determine the governance channel per [`module-catalog.json`](module-catalog.json) §`governance_tier`. `scripts/route_request.py` will include a `governance_tier` field in the output:

| Determination | Condition | Behavior |
|---|---|---|
| `full` | Any risk flag, financial-transaction request, non-trading external-action verb, plugin specialist task, privacy rule trigger, or inclusion of `trade-planning` in the chain | Load full dependency rules per Step 4 of SKILL.md; transaction requests remain prohibited and are redirected to manual plans |
| `light` | Other pure analysis requests | Limit referenced files to at most 4; result envelope to declare `governance_tier: light`; must not produce xlsx/docx/pptx professional attachments or external side effects (validator will reject); on escalation switch back to `full` |

## Risk Flags

| Detection Content | Risk Flag | Must Load |
|---|---|---|
| Positions, costs, sizes, cash, trade history | `personal_financial_data` | `privacy-security.md` |
| Account numbers, wallet addresses, order IDs | `financial_identifier` | `privacy-security.md`, `execution-safety.md` |
| API keys, tokens, cookies, private keys | `credential` | `privacy-security.md`, `execution-safety.md` |
| "Help me buy/sell/place order/modify order/cancel order/auto-trade" | `financial_transaction_prohibited` | `execution-safety.md`; set `transaction_request_disposition=redirected_to_manual_plan` |
| Public release, sending emails, uploading or transmitting materials | `external_publication` | `execution-safety.md`, `output-contracts.md` |
| VDRs, recordings, transcripts, client lists, trading models, or non-public materials | `confidential_material` | `privacy-security.md` |
| Blind Teasers, anonymous projects, or confidential buyer processes | `confidential_identity` | `privacy-security.md`, `corporate-finance.md` |
| Models or materials to be used for IC, financing, acquisition, or sale decisions | `institutional_decision_use` | `output-contracts.md`, corresponding Playbook |

## Clarifications and Declines

Ask clarifying questions only when different answers would change the primary module, safety path, valuation base, capital structure, TAM boundary, buyer criteria, or degree of anonymization. Prioritize confirming final output, target audience, reference date, whether an editable model is needed, and whether non-trading external distribution is required. Do not ask whether the user wants the SKILL to execute a trade; it cannot do so.

Scenarios that require immediate refusal or exit from this Skill include real estate underwriting, personal tax filings, bookkeeping or general-ledger reconciliation, insurance arrangement or personal policy advice, legal opinions or explicit legal advice, gambling advice, and requests to bypass compliance, privacy, or security rules. A request for a financial transaction is not executed: state the absolute boundary and, when useful, redirect it to a manual plan that the user may independently implement on the relevant platform. When only optional analytical parameters are missing, use overridable defaults and record them in `assumptions[]`; do not fabricate transaction facts.

--- END FILE ---
--- END FILE ---
