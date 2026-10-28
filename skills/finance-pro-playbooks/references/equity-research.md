# Equity Research Module

Read this file when the user requests analysis of a single listed company, financial statements, competitiveness, valuation, holding alerts, or a single-stock investment recommendation.

## Sole Primary Responsibility

Be responsible for single-stock fundamental research, industry and competition analysis, multi-method valuation, and single-stock decisions. Do not be responsible for portfolio-level capital allocation, options-structure design, historical strategy backtesting, or transaction execution. Concrete trade requests route to `trade-planning` for a user-executed manual plan only.

## Common Dependency Declaration

| Type | Public Reference | Trigger and Use |
|---|---|---|
| Required | [`data-source-policy.md`](data-source-policy.md) | Standardize financial-report periods, market data, currencies, corporate actions, tick/interval data and source traceability |
| Required | [`metric-dictionary.md`](metric-dictionary.md) | Standardize financial, valuation, returns, risk and technical metric definitions |
| Required | [`scoring-standard.md`](scoring-standard.md) | Standardize investment views, quality scoring, confidence levels and hard thresholds |
| Required | [`output-contracts.md`](output-contracts.md) | Use the common result envelope and the `equity-research` domain payload |
| Conditional | [`privacy-security.md`](privacy-security.md) | Load when the user provides holdings, cost basis, account information, or non-public materials |
| Conditional | [`execution-safety.md`](execution-safety.md) | Load when the request includes trading signals, orders, automation, or external publication |

## Input Contract

| Field | Requirement | Description |
|---|---|---|
| `ticker` | Required | Stock ticker or uniquely identifiable company name; use a list for multi-security comparisons |
| `market` | Conditionally required | Provide when the ticker is ambiguous across markets |
| `detail_level` | Optional | `brief`, `standard` or `deep`, default `standard`; share the same name and enum as the normalized field in SKILL.md and Schema `presentation.detail_level` |
| `focus` | Optional | financials, valuation, competition, catalysts, risks, technical confirmation, etc. |
| `holding_context` | Optional and sensitive | quantity, cost basis and holding period; for holding alerts only |
| `as_of` | Optional | Data cutoff date; default to the most recent available data and disclose |

## Yahoo Finance Use

Use the approved adapter under [`data-source-policy.md §Yahoo Finance via Manus Data API`](data-source-policy.md#yahoo-finance-via-manus-data-api): `chart` for historical or delayed price context, `profile` for secondary company descriptors, `holders` for ownership screening, `insights` for clearly labeled provider analytics, and `filings` only to discover official filings. Validate every generated source artifact with `scripts/validate_yahoo_source.py` and register its `source_manifest_entry`. Financial statements, valuation-critical facts, capital structure and filing evidence still require issuer, exchange, regulator or direct filing sources; Yahoo Finance is never an execution-grade quote.

## Workflow

1. Confirm the security and paradigm. Confirm market, security type and analysis cutoff date; determine whether current pricing is primarily driven by earnings quality, growth expectations, asset value, cyclicality, events, or liquidity.
2. Build the factual working paper. Collect business segments, financial statements, guidance, valuations, prices, expectations and material events. When the approved Yahoo Finance adapter is used, preserve and validate the source artifact before importing any fields. Record facts, company disclosures, market-consensus expectations, provider analytics and analytical assumptions in separate columns.
3. Analyze fundamentals. Assess growth quality, profit and cash conversion, capital efficiency, balance sheet, accounting anomalies and key unit economics. Do not present metrics alone; explain drivers.
4. Analyze industry and moat. Clarify market structure, competitors, substitutes, customer and supplier bargaining power, entry barriers, and evidence that could weaken the moat.
5. Construct valuation. Select primary methods matching the pricing paradigm, and execute the public metric dictionary [`metric-dictionary.md §General Valuation Discipline`](metric-dictionary.md#general-valuation-discipline) (declare primary methods, cross-validate, produce bear/base/bull three scenarios, run sensitivity and constrain parameters); reference all formulas and definitions to the public metric dictionary and do not rewrite them in this document.
6. Assess expectation gaps and catalysts. Distinguish expectations already priced in from potential new information; provide catalyst time windows and observable evidence.
7. Formulate the single-stock conclusion. Output the recommendation, confidence, valuation range, core arguments, risks, monitoring items and failure conditions. If technical entry is needed, output only research-layer confirmation conditions and do not substitute for the trade planning module.
8. Holding alerts. Only evaluate three classes of alerts—fundamentals, expectations and price—when the user provides holding context; do not expose unrelated account identifiers in results.

## Quality Gates

| Gate | Pass Criteria | Failure Handling |
|---|---|---|
| Security identification | Security and market uniquely identified | Ask one clarifying question |
| Data timeliness | Key data include dates and sources | Lower confidence and list gaps |
| Financial consistency | Statement periods, currencies and accounting bases are consistent | Normalize first; avoid direct comparison until standardized |
| Valuation reproducibility | Inputs, formulas, units and scenarios are traceable | Do not output pseudo-precise target prices |
| Argument balance | Include both supporting and opposing evidence | Add counter-evidence before concluding |

## Handover Rules

| Request Extension | Call Chain |
|---|---|
| Design an options strategy for the stock | `equity-research` → `options-strategy` |
| Decide how much to buy across the portfolio | `equity-research` → `portfolio-management` |
| Backtest technical or factor strategies | `quant-backtesting` |
| Generate a concrete manual trade plan, including a prohibited request to place, modify, or cancel an order | `equity-research` → `trade-planning`; the user must implement any transaction independently |
| Prepare IC, roadshow, or ECM materials | `equity-research` → `corporate-finance` (`research-materials-pack` / `ecm-company-profile`) |
| Compare funds or ETFs | `fund-etf` |

## Output Format

1. Construct the `finance-analysis-pro/1.2` result object according to [`schemas/finance-analysis-result.schema.json`](schemas/finance-analysis-result.schema.json), and set `primary_module=equity-research`, `presentation.profile=equity-research`.
2. In the domain payload retain only the investment view, valuation scenarios, supporting and opposing evidence, catalysts and monitoring items; keep public facts, metrics, scores, risks, failure conditions, data gaps, sources, privacy and execution status at the top level, and prohibit duplicate definitions.
3. Run `python3 scripts/ensure_runtime.py`, then run `python3 scripts/validate_result.py result.json`. If runtime preparation is not `ready` or validation fails, stop and correct the environment or result object; do not bypass or downgrade validation to generate the report.
4. Unless the user explicitly requests only JSON, YAML or other machine formats, generate Markdown following the section order in [`../templates/equity-research.md`](../templates/equity-research.md).
5. Allow `brief` to compress analytical detail, but retain state, data cutoff, executive summary, principal risks, failure conditions, data gaps and execution status; have `standard` retain the template's core sections; have `deep` add methods, calculations, sensitivity analysis, sources and an audit appendix.
6. Generate dedicated attachments as needed and register them in `artifacts[]`; do not add temporary fact fields not present in the template, and if extension is necessary, update the public Schema first.
