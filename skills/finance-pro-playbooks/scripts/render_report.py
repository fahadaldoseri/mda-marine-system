#!/usr/bin/env python3
"""Render a validated finance-analysis-pro/1.2 result as a domain-specific Markdown report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from ensure_runtime import RuntimePreparationError, ensure_runtime
from validate_result import validate_result


ROOT = Path(__file__).resolve().parents[1]
IMPORTANT_NOTICE_HEADING = '## Important Notice'
IMPORTANT_NOTICE_TEXT = (
    "This analysis is based on the data and assumptions stated above and does not guarantee future performance. "
    "It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot "
    "place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to "
    "the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity "
    "outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, "
    "exchange, wallet, or other platform."
)
IMPORTANT_NOTICE_BLOCK = f"{IMPORTANT_NOTICE_HEADING}\n\n{IMPORTANT_NOTICE_TEXT}"
TRANSACTION_REQUEST_BOUNDARY = (
    "This SKILL cannot perform or submit the requested financial transaction. "
    "The request has been converted into a proposed, unsubmitted manual plan that the user may "
    "independently review, change, use, or ignore outside the SKILL."
)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def _cell(value: Any) -> str:
    if value is None:
        return "Not provided"
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    if isinstance(value, (list, tuple)):
        return ";".join(_cell(item) for item in value) if value else "None"
    if isinstance(value, dict):
        return ";".join(f"{key}={_cell(item)}" for key, item in value.items()) if value else "None"
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    normalized = [list(row) for row in rows]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    if not normalized:
        normalized = [["None"] + [""] * (len(headers) - 1)]
    lines.extend("| " + " | ".join(_cell(value) for value in row) + " |" for row in normalized)
    return "\n".join(lines)


def _bullets(values: Any, keys: tuple[str, ...] = ()) -> str:
    if not isinstance(values, list) or not values:
        return "None"
    lines: list[str] = []
    for item in values:
        if isinstance(item, dict) and keys:
            parts = [f"**{key}:** {_cell(item.get(key))}" for key in keys if key in item]
            lines.append("- " + "; ".join(parts))
        else:
            lines.append("- " + _cell(item))
    return "\n".join(lines)


def _header(
    result: dict[str, Any],
    title: str,
    *,
    summary_prefix: str | None = None,
) -> list[str]:
    presentation = result["presentation"]
    summary_lines = [] if summary_prefix is None else [summary_prefix, ""]
    summary_lines.extend([_cell(result["summary"]), ""])
    return [
        f"# {_cell(result['subject'])} {title}",
        "",
        (
            f"> **Status:** {_cell(result['status'])} | **Data cutoff:** {_cell(result['data_cutoff'])} "
            f"| **Generated at:** {_cell(result['as_of'])} | **Detail level:** {_cell(presentation['detail_level'])}"
        ),
        "",
        "## Executive Summary",
        "",
        *summary_lines,
    ]


def _render_equity(result: dict[str, Any]) -> list[str]:
    p = result["payload"]
    valuation = p["valuation"]
    lines = _header(result, "Equity Research")
    lines += [
        "## Investment View",
        "",
        _table(
            ["Research Paradigm", "Investment View", "Confidence", "Module Chain"],
            [[p["paradigm"], p["investment_view"], p["confidence"], result["module_chain"]]],
        ),
        "",
        "## Valuation Scenarios",
        "",
        _table(
            ["Method", "Currency", "Bear", "Base", "Bull", "Valuation Date"],
            [[valuation["method"], valuation["currency"], valuation["bear"], valuation["base"], valuation["bull"], valuation["as_of"]]],
        ),
        "",
        "## Core Arguments",
        "",
        _table(
            ["Argument", "Impact", "Evidence References"],
            [[item["statement"], item["impact"], item["evidence_refs"]] for item in p["key_arguments"]],
        ),
        "",
        "## Counterarguments and Controversies",
        "",
        _table(
            ["Counterevidence", "Impact", "Evidence References"],
            [[item["statement"], item["impact"], item["evidence_refs"]] for item in p["counter_evidence"]],
        ),
        "",
        "## Catalysts",
        "",
        _table(
            ["Event", "Expected Window", "Observable Signals"],
            [[item["event"], item["expected_window"], item["observable_signal"]] for item in p["catalysts"]],
        ),
        "",
        "## Monitoring Items",
        "",
        _table(
            ["Monitoring Item", "Trigger Condition", "Response"],
            [[item["item"], item["trigger"], item["response"]] for item in p["monitoring_items"]],
        ),
        "",
    ]
    return lines


def _render_fund(result: dict[str, Any]) -> list[str]:
    p = result["payload"]
    r = p["recommendations"]
    lines = _header(result, "Fund and ETF Comparison")
    lines += [
        "## Comparison Objectives and Scope",
        "",
        _table(["Comparison Scope", "Decision Band", "Constraints", "Module Chain"], [[p["comparison_scope"], p["decision_band"], p["constraints"], result["module_chain"]]]),
        "",
        "## Candidate Product Comparison",
        "",
        _table(
            ["Ticker", "Name", "Exposure Fit", "Structural Risk", "Cost", "Liquidity", "Performance Basis"],
            [[item["symbol"], item["name"], item["exposure_fit"], item["structural_risks"], item["cost_summary"], item["liquidity_summary"], item["performance_summary"]] for item in p["candidates"]],
        ),
        "",
        "## Tiered Recommendations",
        "",
        _table(["Dimension", "Result"], [["Best Overall", r["overall"]], ["Lowest Cost", r["lowest_cost"]], ["Most Robust Structure", r["strongest_structure"]]]),
        "",
        "## Structural Risks and Applicability Limits",
        "",
        _bullets(p["constraints"]),
        "",
    ]
    return lines


def _render_options(result: dict[str, Any]) -> list[str]:
    p = result["payload"]
    s = p["recommended_strategy"]
    lines = _header(result, "Options Strategy")
    lines += [
        "## Underlying View and Strategy Selection",
        "",
        _table(["Underlying View", "Volatility Regime", "Preferred Structure", "Alternative Structures"], [[p["underlying_view"], p["volatility_regime"], s["structure"], p["alternatives"]]]),
        "",
        "## Strategy Legs",
        "",
        _table(["Side", "Type", "Quantity", "Strike", "Expiration", "Premium"], [[item["side"], item["option_type"], item["quantity"], item["strike"], item["expiration"], item["premium"]] for item in s["legs"]]),
        "",
        "## P&L and Capital Usage",
        "",
        _table(["Currency", "Net Premium", "Sign Convention", "Max Profit", "Max Loss", "Breakevens", "Capital Usage"], [[s["currency"], s["net_premium"], s["premium_convention"], s["max_profit"], s["max_loss"], s["breakevens"], s["margin_or_capital"]]]),
        "",
        "## Scenario Analysis",
        "",
        _table(["Scenario", "Underlying Price", "Strategy P&L", "Unit"], [[item["scenario"], item["underlying_price"], item["pnl"], item["unit"]] for item in p["scenario_results"]]),
        "",
        "## Management and Roll Rules",
        "",
        _bullets(p["management_rules"], ("condition", "action")),
        "",
        _bullets(p["roll_conditions"], ("condition", "action")),
        "",
        "## Exclusion Criteria",
        "",
        _bullets(p["no_trade_conditions"]),
        "",
    ]
    return lines


def _render_crypto(result: dict[str, Any]) -> list[str]:
    p = result["payload"]
    lines = _header(result, "Crypto Asset Analysis")
    lines += [
        "## Assets and Market Background",
        "",
        _table(["Asset", "Network", "Venue"], [[item["symbol"], item["network"], item["venue"]] for item in p["assets"]]),
        "",
        _cell(p["market_context"]),
        "",
        "## Market Structure",
        "",
        _table(["Trend", "Key Levels", "Liquidity Zones"], [[p["structure"]["trend"], p["structure"]["key_levels"], p["structure"]["liquidity_zones"]]]),
        "",
        "## Derivatives Signals",
        "",
        _table(["Signal", "Value", "Interpretation", "As of", "Source"], [[item["name"], item["value"], item["interpretation"], item["as_of"], item["source_refs"]] for item in p["derivatives_signals"]]),
        "",
        "## On-chain Signals",
        "",
        _table(["Signal", "Value", "Interpretation", "As of", "Source"], [[item["name"], item["value"], item["interpretation"], item["as_of"], item["source_refs"]] for item in p["onchain_signals"]]),
        "",
        "## Strategy Candidates",
        "",
        _table(["Name", "Setup", "Entry Condition", "Invalidation", "Risk"], [[item["name"], item["setup"], item["entry_condition"], item["invalidation"], item["risk"]] for item in p["strategy_candidates"]]),
        "",
        "## Position and LP Analysis",
        "",
        _table(["Position Risk", "LP Analysis"], [[p["position_risk"], p["lp_analysis"]]]),
        "",
        "## Fact Verification",
        "",
        _table(["Status", "Evidence References"], [[p["fact_check"]["status"], p["fact_check"]["evidence_refs"]]]),
        "",
    ]
    return lines


def _render_portfolio(result: dict[str, Any]) -> list[str]:
    p = result["payload"]
    s = p["portfolio_summary"]
    actions = p["recommended_actions"]
    lines = _header(result, "Portfolio Management Report")
    lines += [
        "## Portfolio Overview",
        "",
        _table(["Currency", "Net Asset Value", "Holdings Count", "Cash Weight"], [[s["currency"], s["nav"], s["holdings_count"], s["cash_weight"]]]),
        "",
        "## Constraint Status",
        "",
        _table(["Constraint", "Status", "Evidence"], [[item["constraint"], item["status"], item["evidence"]] for item in p["constraint_status"]]),
        "",
        "## Risk and Concentration Exposures",
        "",
        _table(["Metric", "Value", "Unit", "Status"], [[item["name"], item["value"], item["unit"], item["status"]] for item in p["risk_metrics"]]),
        "",
        _table(["Dimension", "Exposure Name", "Current Weight", "Limit", "Status"], [[item["dimension"], item["name"], item["weight"], item["limit"], item["status"]] for item in p["concentration_exposures"]]),
        "",
        "## Research Conflicts",
        "",
        _table(["Instrument", "Conflict", "Resolution"], [[item["instrument"], item["conflict"], item["resolution"]] for item in p["research_conflicts"]]),
        "",
        "## Recommended Actions",
        "",
        _table(["Category", "Instrument", "Action", "Current Weight", "Target Weight", "Rationale", "Priority"], [[kind, item["instrument"], item["action"], item["current_weight"], item["target_weight"], item["rationale"], item["priority"]] for kind in ("primary", "alternatives", "do_not_do") for item in actions[kind]]),
        "",
        "## Allocation Scenarios",
        "",
        _table(["Scenario", "Assumptions", "Target Weights", "Expected Impact"], [[item["name"], item["assumptions"], item["target_weights"], item["expected_impact"]] for item in p["allocation_scenarios"]]),
        "",
        "## Before and After Comparison",
        "",
        _table(["Metric", "Before", "After", "Unit", "Status"], [[item["metric"], item["before"], item["after"], item["unit"], item["status"]] for item in p["post_trade_comparison"]]),
        "",
        "## Monitoring Triggers",
        "",
        _table(["Trigger", "Threshold", "Response"], [[item["trigger"], item["threshold"], item["response"]] for item in p["monitoring_triggers"]]),
        "",
    ]
    return lines


def _render_quant(result: dict[str, Any]) -> list[str]:
    p = result["payload"]
    s = p["strategy_spec"]
    d = p["data_manifest"]
    lines = _header(result, "Quantitative Backtest Report")
    lines += [
        "## Strategy Specification",
        "",
        _table(["Name", "Universe", "Frequency", "Signal", "Entry", "Exit", "Position", "Risk"], [[s["name"], s["universe"], s["frequency"], s["signal"], s["entry_rule"], s["exit_rule"], s["sizing_rule"], s["risk_rule"]]]),
        "",
        "## Data and Matching Assumptions",
        "",
        _table(["Start", "End", "Frequency", "Adjustment", "Timezone", "Sources", "Benchmark"], [[d["start"], d["end"], d["frequency"], d["adjustment"], d["timezone"], d["sources"], p["benchmark"]]]),
        "",
        "## Performance Metrics",
        "",
        _table(["Metric", "Value", "Unit", "Method", "Window", "Status", "Source"], [[item["name"], item["value"], item["unit"], item["method"], item["window"], item["status"], item["source_refs"]] for item in p["performance_metrics"]]),
        "",
        "## Robustness Checks",
        "",
        _table(["Test", "Method", "Result", "Status"], [[item["name"], item["method"], item["result"], item["status"]] for item in p["robustness_tests"]]),
        "",
        "## Parameter Results",
        "",
        _table(["Parameters", "In-sample", "Out-of-sample", "Selected"], [[item["parameters"], item["in_sample"], item["out_of_sample"], item["selected"]] for item in p["parameter_results"]]),
        "",
        "## Failure Reasons and Applicability Boundaries",
        "",
        _bullets(p["failure_reasons"]),
        "",
        "## Reproducibility Files and Charts",
        "",
        _table(["Trade Log", "Backtest Script", "Charts"], [[p["trade_log_path"], p["script_path"], p["chart_paths"]]]),
        "",
    ]
    return lines


def _render_trade(result: dict[str, Any]) -> list[str]:
    p = result["payload"]
    signal = p["signal_card"]
    order = p["order_plan"]
    simulation = p["simulation"]
    boundary = (
        TRANSACTION_REQUEST_BOUNDARY
        if p["transaction_request_disposition"] == "redirected_to_manual_plan"
        else None
    )
    lines = _header(result, "Manual Trade Plan", summary_prefix=boundary)
    lines += [
        "## Plan-Only Status",
        "",
        _table(
            ["Mode", "Transaction Request", "External Side Effect", "Confirmation Status"],
            [[
                p["mode"],
                p["transaction_request_disposition"],
                result["execution"]["external_side_effect"],
                result["execution"]["confirmation_status"],
            ]],
        ),
        "",
        "## Signal Card",
        "",
        _table(
            ["Instrument", "Direction", "Entry", "Stop", "Take Profit", "Horizon", "Invalidation"],
            [[
                signal["instrument"],
                signal["direction"],
                signal["entry_condition"],
                signal["stop_condition"],
                signal["take_profit_condition"],
                signal["horizon"],
                signal["invalidation"],
            ]],
        ),
        "",
        "## Proposed, Unsubmitted Order Plan",
        "",
        _table(
            [
                "Manual Intent", "Status", "Instrument", "Side", "Type", "Quantity", "Unit",
                "Limit Price", "Stop Price", "Time in Force", "Expiry", "Risk Budget",
                "Estimated Notional", "Currency", "Estimated Fees", "Maximum Modeled Loss",
                "Platform Verification Required",
            ],
            [] if order is None else [[
                order["manual_intent"],
                order["status"],
                order["instrument"],
                order["side"],
                order["order_type"],
                order["quantity"],
                order["quantity_unit"],
                order["limit_price"],
                order["stop_price"],
                order["time_in_force"],
                order["expiry"],
                order["risk_budget"],
                order["estimated_notional"],
                order["currency"],
                order["estimated_fees"],
                order["maximum_modeled_loss"],
                order["platform_verification_required"],
            ]],
        ),
        "",
        "## Plan Checks",
        "",
        _table(
            ["Check", "Status", "Evidence"],
            [[item["name"], item["status"], item["evidence"]] for item in p["plan_checks"]],
        ),
        "",
        "## Simulation",
        "",
        _table(
            ["Assumptions", "Modeled Outcome", "Estimated Costs", "Maximum Modeled Loss"],
            [] if simulation is None else [[
                simulation["assumptions"],
                simulation["modeled_outcome"],
                simulation["estimated_costs"],
                simulation["maximum_modeled_loss"],
            ]],
        ),
        "",
        "## User-Controlled Self-Execution Guidance",
        "",
        _bullets(p["user_action_steps"]),
        "",
        "## Manual-Execution Notice",
        "",
        f"> {p['manual_execution_notice']}",
        "",
        "## Errors and Remediation",
        "",
        _table(
            ["Code", "Message", "Remediation"],
            [[item["code"], item["message"], item["remediation"]] for item in p["errors"]],
        ),
        "",
    ]
    return lines


def _render_materials_review(p: dict[str, Any], result: dict[str, Any]) -> list[str]:
    """Render the optional materials_review section of a corporate-finance payload
    (existing-material tasks migrated from the former ir-deal-materials module)."""
    lines = [
        "## Existing Materials Handling (Materials Review)",
        "",
        _table(["Task Type", "Publication Status", "Module Chain"], [[p["task_type"], p["publication_status"], result["module_chain"]]]),
        "",
        "### Materials Reviewed",
        "",
        _table(["Source Reference", "Role", "Version or Date"], [[item["source_ref"], item["role"], item["version_or_date"]] for item in p["materials_reviewed"]]),
        "",
        "### Verified Facts",
        "",
        _bullets(p["verified_fact_refs"]),
        "",
        "### Scoring and Screening Conclusions",
        "",
        _cell(p["scorecard"]),
        "",
        "### Document Inconsistencies",
        "",
        _table(["Topic", "Sources", "Description", "Severity", "Recommended Resolution"], [[item["topic"], item["sources"], item["description"], item["severity"], item["recommended_resolution"]] for item in p["inconsistencies"]]),
        "",
        "### Red Flags",
        "",
        _table(["Flag", "Evidence References", "Impact", "Status"], [[item["flag"], item["evidence_refs"], item["impact"], item["status"]] for item in p["red_flags"]]),
        "",
        "### Open Questions and Follow-up Due Diligence",
        "",
        _table(["Question", "Owner", "Due Date", "Priority"], [[item["question"], item["owner"], item["due"], item["priority"]] for item in p["open_questions"]]),
        "",
        "### Deliverables",
        "",
        _table(["Name", "Format", "Path", "Status"], [[item["name"], item["format"], item["path"], item["status"]] for item in p["deliverables"]]),
        "",
        "### Publication Status and Authorization",
        "",
        _table(["Publication Status", "External Side Effect", "Confirmation Status"], [[p["publication_status"], result["execution"]["external_side_effect"], result["execution"]["confirmation_status"]]]),
        "",
    ]
    return lines


def _render_corporate_finance(result: dict[str, Any]) -> list[str]:
    p = result["payload"]
    entity = p["entity_card"]
    review = p["review_status"]
    lines = _header(result, "Corporate Finance Professional Deliverables")
    lines += [
        "## Project Scope and Module Chain",
        "",
        _table(
            ["Project Scope", "Decision Scenario", "Professional Tasks", "Module Chain"],
            [[p["scope"], p["decision_context"], p["specialist_tasks"], result["module_chain"]]],
        ),
        "",
        "## Entity Card",
        "",
        _table(
            ["Legal Name", "Ticker/Exchange", "Country/Industry", "Currency", "Fiscal Year End", "Accounting Standard", "Period", "Valuation Date", "Transaction Background"],
            [[
                entity["legal_name"],
                [entity["ticker"], entity["exchange"]],
                [entity["country"], entity["industry"]],
                entity["currency"],
                entity["fiscal_year_end"],
                entity["reporting_standard"],
                entity["period_basis"],
                entity["valuation_date"],
                entity["transaction_context"],
            ]],
        ),
        "",
        "## Professional Task Results",
        "",
        _table(
            ["Task ID", "Status", "Summary", "Key Outputs", "Open Items", "Sources", "Attachment References"],
            [[
                item["task_id"], item["status"], item["summary"], item["key_outputs"],
                item["open_items"], item["source_refs"], item["artifact_refs"]
            ] for item in p["task_results"]],
        ),
        "",
        "## Models and Quality Checks",
        "",
        _table(
            ["Check", "Status", "Evidence", "Impact"],
            [[item["name"], item["status"], item["evidence"], item["impact"]] for item in p["model_checks"]],
        ),
        "",
        "## Professional Deliverables",
        "",
        _table(
            ["Name", "Type", "Format", "Path", "Status", "Task", "Sensitivity Level"],
            [[
                item["name"], item["deliverable_type"], item["format"], item["path"],
                item["status"], item["task_ids"], item["sensitivity"]
            ] for item in p["deliverables"]],
        ),
        "",
        "## Review Status",
        "",
        _table(
            ["Financial Integrity", "Period Consistency", "Source Traceability", "Format Quality", "Overall", "Review Notes"],
            [[
                review["financial_integrity"], review["period_consistency"],
                review["source_traceability"], review["format_quality"],
                review["overall"], review["reviewer_notes"]
            ]],
        ),
        "",
        "## Scope Limitations",
        "",
        _bullets(p["scope_limitations"]),
        "",
    ]
    materials_review = p.get("materials_review")
    if materials_review:
        lines += _render_materials_review(materials_review, result)
    return lines


def _common_sections(result: dict[str, Any]) -> list[str]:
    metrics = result["metrics"]
    scores = result["scores"]
    risks = result["risks"]
    invalidations = result["invalidation_conditions"]
    gaps = result["data_gaps"]
    assumptions = result["assumptions"]
    sources = result["source_manifest"]
    artifacts = result["artifacts"]
    return [
        "## Key Metrics and Scoring",
        "",
        _table(["Metric", "Value", "Unit", "Method", "Window", "Status", "Source"], [[item["name"], item["value"], item["unit"], item["method"], item["window"], item["status"], item["source_refs"]] for item in metrics]),
        "",
        _table(["Score", "Value", "Scale", "Weight", "Rationale", "Confidence"], [[item["name"], item["score"], f"{item['scale_min']}–{item['scale_max']}", item["weight"], item["rationale"], item["confidence"]] for item in scores]),
        "",
        "## Risks and Failure Conditions",
        "",
        _table(["Risk", "Category", "Description", "Severity", "Likelihood", "Mitigation"], [[item["risk_id"], item["category"], item["description"], item["severity"], item["likelihood"], item["mitigation"]] for item in risks]),
        "",
        _table(["Failure Condition", "Observable Evidence", "Response"], [[item["condition"], item["observable_evidence"], item["action"]] for item in invalidations]),
        "",
        "## Data Gaps and Assumptions",
        "",
        _table(["Field", "Reason", "Impact", "Remediation"], [[item["field"], item["reason"], item["impact"], item["remediation"]] for item in gaps]),
        "",
        _table(["Assumption", "Statement", "Impact", "Status"], [[item["assumption_id"], item["statement"], item["impact"], item["status"]] for item in assumptions]),
        "",
        "## Data and Sources",
        "",
        _table(["Reference", "Title", "Publisher", "Data As Of", "Retrieved At", "URL"], [[item["source_ref"], item["title"], item["publisher"], item["data_as_of"], item["retrieved_at"], item["url"]] for item in sources]),
        "",
        "## Attachments and Security Status",
        "",
        _table(["Attachment ID", "Name", "Format", "Purpose", "Sensitivity", "Status", "Task", "Path"], [[item.get("artifact_id"), item["name"], item["format"], item["purpose"], item["sensitivity"], item.get("status"), item.get("task_ids", []), item["path"]] for item in artifacts]),
        "",
        _table(["Data Classes", "Redactions Applied", "Retention Status", "External Side Effect", "Confirmation Status"], [[result["privacy"]["data_classes_used"], result["privacy"]["redactions_applied"], result["privacy"]["retention_status"], result["execution"]["external_side_effect"], result["execution"]["confirmation_status"]]]),
        "",
        IMPORTANT_NOTICE_HEADING,
        "",
        IMPORTANT_NOTICE_TEXT,
        "",
    ]


RENDERERS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "equity-research": _render_equity,
    "fund-etf": _render_fund,
    "options-strategy": _render_options,
    "crypto-analysis": _render_crypto,
    "portfolio-management": _render_portfolio,
    "quant-backtesting": _render_quant,
    "trade-planning": _render_trade,
    "corporate-finance": _render_corporate_finance,
}


def render_report(result: dict[str, Any]) -> str:
    ensure_runtime()
    module = result["primary_module"]
    renderer = RENDERERS[module]
    template_path = ROOT / "templates" / f"{module}.md"
    if not template_path.is_file():
        raise FileNotFoundError(f"missing template: {template_path}")
    template_text = template_path.read_text(encoding="utf-8")
    required_common = ["## Executive Summary", "## Risks and Failure Conditions", "## Data and Sources", IMPORTANT_NOTICE_HEADING]
    for heading in required_common:
        if heading not in template_text:
            raise ValueError(f"template missing required heading: {heading}")
    if IMPORTANT_NOTICE_BLOCK not in template_text:
        raise ValueError("template missing canonical Important Notice text")
    if not template_text.rstrip().endswith(IMPORTANT_NOTICE_BLOCK):
        raise ValueError("template must end with the canonical Important Notice")
    lines = renderer(result) + _common_sections(result)
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validation-output", type=Path)
    args = parser.parse_args()

    try:
        data = _load_json(args.result)
        report = validate_result(data, result_path=args.result.resolve())
        if args.validation_output:
            args.validation_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if report["status"] != "passed":
            print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        markdown = render_report(data)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(markdown, encoding="utf-8")
        else:
            print(markdown, end="")
        return 0
    except RuntimePreparationError as error:
        payload = {"status": "blocked", "error": str(error), "runtime": error.state}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
        print(f"render failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
