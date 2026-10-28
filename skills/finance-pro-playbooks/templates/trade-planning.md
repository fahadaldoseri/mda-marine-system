# {{subject}} Manual Trade Plan

> **Status:** {{status}} | **Mode:** {{payload.mode}} | **Data Cutoff:** {{data_cutoff}} | **Generated:** {{as_of}} | **Transaction Request:** {{payload.transaction_request_disposition}}

## Executive Summary

{{summary}}

The opening paragraph must state that this deliverable is analysis, a hypothetical paper simulation, or a manual plan. It must also state that the SKILL did not place, modify, cancel, sign, or submit any transaction. When `payload.transaction_request_disposition=redirected_to_manual_plan`, keep this boundary statement brief and continue directly to the proposed plan and user-controlled guidance; never render a bare refusal as the whole response. If the user said that the plan was confirmed or asked the agent to proceed, describe that only as the user's review of the proposal and retain `status=proposed_unsubmitted`.

## Signal Card

| Instrument | Direction | Entry Condition | Stop Condition | Target Condition | Horizon | Invalidation Condition |
|---|---|---|---|---|---|---|
| {{payload.signal_card.instrument}} | {{payload.signal_card.direction}} | {{payload.signal_card.entry_condition}} | {{payload.signal_card.stop_condition}} | {{payload.signal_card.take_profit_condition}} | {{payload.signal_card.horizon}} | {{payload.signal_card.invalidation}} |

## Manual Order Plan

If `payload.order_plan=null`, display **No manual order plan generated**. Otherwise render the proposed fields below for the user's independent review. The user may choose to use, change, or ignore the proposal outside this SKILL.

| Manual Intent | Status | Instrument | Side | Order Type | Quantity | Unit | Limit Price | Stop Price | Time in Force | Expiry | Risk Budget | Estimated Notional | Currency | Estimated Fees | Maximum Modeled Loss | Platform Verification Required |
|---|---|---|---|---|---:|---|---:|---:|---|---|---:|---:|---|---:|---:|---|
| `manual_intent` | `proposed_unsubmitted` | `instrument` | `side` | `order_type` | `quantity` | `quantity_unit` | `limit_price` | `stop_price` | `time_in_force` | `expiry` | `risk_budget` | `estimated_notional` | `currency` | `estimated_fees` | `maximum_modeled_loss` | `true` |

Do not display an account alias, broker order ID, client order ID, transaction hash, signing payload, or any credential. Label every field as a proposal rather than an instruction already sent to a platform.

## Plan Checks

| Check | Status | Evidence or User Verification Required |
|---|---|---|
| `payload.plan_checks[].name` | `status` | `evidence` |

A `user_verification_required` check is not a defect. It means that, if the user chooses to act independently outside the SKILL, they should verify the current platform fact—such as price, spread, session status, balance, approval, fees, or venue support—before deciding whether to proceed.

## Hypothetical Simulation

If `payload.simulation=null`, display **No paper simulation generated**. Otherwise state its assumptions, modeled outcome, estimated costs, slippage assumptions, and maximum modeled loss. Do not describe hypothetical values as actual fills, balances, or returns.

## User-Controlled Self-Execution Guidance

Render `payload.user_action_steps[]` in order. For a redirected transaction request, this section is required practical guidance rather than a bare refusal: it must direct every action to the user and make clear that each step occurs independently outside the SKILL. Cover opening the relevant broker, exchange, or wallet; verifying the instrument and current market state; comparing each proposed field; reassessing suitability and maximum loss; manually entering the transaction if the user still chooses to proceed; and reviewing the platform's own final confirmation screen before the user decides whether to submit.

The steps must never instruct the agent, a connector, an API, or a browser automation flow to perform the transaction. They must not ask the user to reply with confirmation so that the SKILL can continue, and they must not imply that the SKILL will act after the guidance.

## Manual-Execution Notice

> {{payload.manual_execution_notice}}

The notice must unambiguously state that the SKILL cannot perform financial transactions, that this limit applies only to the SKILL and its tools or agents, and that the user remains free to decide and act independently outside it.

## Errors and Limitations

| Code | Message | Remediation |
|---|---|---|
| `payload.errors[].code` | `message` | `remediation` |

Errors describe analytical or planning limitations only. Do not include broker submission errors, order-status polling, fills, receipts, or reconciliation claims.

## Risks and Failure Conditions

List the common `risks[]` followed by `invalidation_conditions[]`. Include market, liquidity, gap, leverage, concentration, model, data, and event risks where relevant.

## Data Gaps and Assumptions

List `data_gaps[]` and `assumptions[]`. Never use assumptions to fabricate current price, spread, buying power, platform support, margin approval, or transaction status.

## Data and Sources

List `source_manifest[]` and distinguish research data, delayed market context, user-provided read-only data, and model assumptions. Do not list a transaction receipt or broker write response as a source.

## Attachments and Security Status

List `privacy`, top-level `execution`, and `artifacts[]`. For this profile, `execution.external_side_effect` must be `false` and `execution.confirmation_status` must be `not_applicable`. Do not produce broker-import files, signed payloads, transaction instruction files, or other artifacts designed for automated submission.

## Important Notice

This analysis is based on the data and assumptions stated above and does not guarantee future performance. It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, exchange, wallet, or other platform.
