#!/usr/bin/env python3
"""Deterministic first-pass router for the finance-pro-playbooks Skill.

The router selects one framework module as final owner, builds an ordered module
chain, resolves corporate-finance plugin tasks, and returns the dependency union.
Semantic ambiguity must still follow references/routing-catalog.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
TASK_CATALOG_PATH = SKILL_ROOT / "references/corporate-finance/task-catalog.json"
TASK_CATALOG_REFERENCE = "references/corporate-finance/task-catalog.json"
MODULE_CATALOG_PATH = SKILL_ROOT / "references/module-catalog.json"


def _load_module_catalog() -> dict[str, Any]:
    payload = json.loads(MODULE_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload.get("modules"), dict):
        raise ValueError("module catalog must contain a modules object")
    return payload


_MODULE_CATALOG = _load_module_catalog()

PATTERNS: dict[str, tuple[str, ...]] = {
    module: tuple(spec["patterns"]) for module, spec in _MODULE_CATALOG["modules"].items()
}

OUT_OF_SCOPE = tuple(_MODULE_CATALOG["out_of_scope_patterns"])

_LIMITED_SUPPORT = _MODULE_CATALOG.get("limited_support", {})
LIMITED_SUPPORT_ASSET_PATTERNS = tuple(_LIMITED_SUPPORT.get("asset_patterns", ()))
LIMITED_SUPPORT_NOTE = str(_LIMITED_SUPPORT.get("note", ""))
LIMITED_SUPPORT_REROUTE = tuple(
    (tuple(rule.get("intent_patterns", ())), str(rule.get("module", "")))
    for rule in _LIMITED_SUPPORT.get("reroute", ())
)

# NOTE: Keep transaction and non-trading external-action terms synchronized with execution-safety.md.
PRIVACY_PATTERNS = (
    r"My positions", r"My investment portfolio", r"My portfolio", r"Account", r"Account number", r"Wallet address", r"Transaction history",
    r"Cost price", r"Order", r"Recording", r"Contact", r"Email", r"Phone", r"Non-public", r"Internal documents",
    r"Client list", r"Data room", r"\bvdr\b", r"portfolio holdings", r"account", r"data room",
)

TRANSACTION_PATTERNS = (
    r"Live trading", r"Real order placement", r"Place orders? for me", r"Automated order placement",
    r"Order modification", r"Order cancellation", r"Automatic execution", r"Copy[- ]?trad(?:e|ing)",
    r"place (?:an? )?orders?", r"place (?:real )?orders?", r"place (?:a )?(?:live|real) orders?",
    r"submit (?:an? )?orders?", r"send (?:the )?orders?", r"route (?:the )?orders?", r"generate (?:real|live) orders?",
    r"modify (?:an? |the )?orders?", r"amend (?:an? |the )?orders?", r"replace (?:an? |the )?orders?",
    r"cancel (?:an? |the )?orders?", r"execute (?:the )?(?:trade|order|transaction)", r"live trad",
    r"sign (?:the )?(?:transaction|payload)", r"broadcast (?:the )?transaction", r"approve (?:the )?(?:token|allowance|transaction)",
    r"transfer (?:the )?(?:funds|cash|assets|tokens|crypto)", r"rebalance (?:it|this|my portfolio) for me",
    r"\b(?:place|submit|route|modify|amend|replace|cancel|execute)\b.{0,48}\b(?:order|trade|transaction)\b",
    r"\b(?:sign|broadcast)\b.{0,32}\b(?:transaction|payload)\b",
    r"\bapprove\b.{0,32}\b(?:token|allowance|transaction)\b",
    r"\btransfer\b.{0,32}\b(?:funds|cash|assets|tokens|crypto)\b",
    r"\brebalance\b.{0,32}\bfor me\b",
    r"\b(?:trade|order|transaction|investment|portfolio|rebalance|plan)\b.{0,48}\b(?:confirmed|approved)\b.{0,48}\b(?:execute|execution|submit|submission|proceed)\b",
    r"\b(?:proceed|continue)\b.{0,32}\b(?:trade|order|transaction|execution|submission)\b",
)

NON_TRADING_EXTERNAL_ACTION_PATTERNS = (
    r"Publish", r"Send to", r"Send email", r"Upload materials",
    r"(Send|Send externally|Send to).{0,12}(Materials|teaser|cim|Report|Email|Buyer|Client)",
    r"Create and send", r"publish", r"send email", r"send to", r"upload materials", r"submit materials",
)

AUTOMATION_PATTERNS = (
    r"Automation", r"Scheduling", r"Daily scan", r"Daily run", r"strategy hosting",
    r"automation", r"scheduled", r"daily scan", r"host (?:the )?strategy",
)

CONFIDENTIAL_PATTERNS = (
    r"Non-public", r"Internal documents", r"Data room", r"\bvdr\b", r"Client list", r"Transaction model", r"blind teaser",
    r"Anonymous project", r"Confidential", r"confidential", r"buyer list", r"\bcim\b", r"data room",
)

SCORING_PATTERNS = (
    r"Scoring", r"Scoring", r"Rating", r"Ranking", r"Confidence", r"Weight", r"score", r"rank", r"rating",
    r"confidence", r"weight", r"scorecard",
)

METRIC_CALCULATION_PATTERNS = (
    r"Calculation", r"Estimate", r"Valuation", r"Financial metrics", r"Return", r"Return rate", r"Leverage", r"Multiples", r"Model",
    r"\birr\b", r"\bnpv\b", r"valuation", r"calculate", r"metric", r"return", r"leverage",
            r"multiple", r"model", r"waterfall", r"accretion", r"dilution", r"Debt schedule",

)

SAFETY_CONDITION_PATTERNS = (
    r"Order", r"order plan", r"manual order", r"On-chain signature", r"on-chain sign",
)

REFERENCE_BY_MODULE = {
    module: spec["reference"] for module, spec in _MODULE_CATALOG["modules"].items()
}

COMMON_REFERENCE_ORDER = (
    "references/data-source-policy.md",
    "references/metric-dictionary.md",
    "references/scoring-standard.md",
    "references/privacy-security.md",
    "references/execution-safety.md",
    "references/output-contracts.md",
)

REQUIRED_REFERENCE_BY_MODULE: dict[str, tuple[str, ...]] = {
    module: tuple(spec["required_references"])
    for module, spec in _MODULE_CATALOG["modules"].items()
}

CONDITIONAL_REFERENCE_BY_MODULE: dict[str, dict[str, tuple[str, ...]]] = {
    module: {condition: tuple(refs) for condition, refs in spec["conditional_references"].items()}
    for module, spec in _MODULE_CATALOG["modules"].items()
}

# Chain ordering follows data dependency (upstream research feeds downstream delivery).
DEPENDENCY_ORDER = tuple(_MODULE_CATALOG["dependency_order"])

# Primary ownership is a SEPARATE concept from chain ordering. The catalog mirrors
# the six-level priority documented in references/routing-catalog.md §Primary module decision priority.
PRIMARY_PRIORITY = tuple(_MODULE_CATALOG["primary_priority"])


def _matches(text: str, patterns: tuple[str, ...] | list[str]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE)]


def _load_task_catalog() -> list[dict[str, Any]]:
    payload = json.loads(TASK_CATALOG_PATH.read_text(encoding="utf-8"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("corporate-finance task catalog must contain a tasks array")
    return tasks


def _match_specialist_tasks(text: str) -> tuple[list[str], dict[str, list[str]], list[str]]:
    task_ids: list[str] = []
    evidence: dict[str, list[str]] = {}
    references: list[str] = []
    for task in _load_task_catalog():
        task_id = str(task["id"])
        found = _matches(text, list(task.get("patterns", [])))
        if not found:
            continue
        if task.get("require_deliverable_signal"):
            deliverable_found = _matches(text, list(task.get("deliverable_patterns", [])))
            if not deliverable_found:
                continue
            found = found + deliverable_found
        task_ids.append(task_id)
        evidence[task_id] = found
        overview = task.get("playbook_overview")
        if overview:
            references.append(str(overview))
        references.append(str(task["playbook"]))
        format_registry = {
            "excel": "references/corporate-finance/formats/excel_standards.md",
            "document": "references/corporate-finance/formats/document_standards.md",
            "metrics": "references/corporate-finance/formats/metric_disambiguation.md",
        }
        references.extend(format_registry[name] for name in task.get("formats", []) if name in format_registry)
    return task_ids, evidence, _dedupe(references)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _ordered_chain(candidates: set[str]) -> list[str]:
    return [module for module in DEPENDENCY_ORDER if module in candidates]


def _primary_module(candidates: set[str]) -> str:
    for module in PRIMARY_PRIORITY:
        if module in candidates:
            return module
    raise ValueError("cannot select primary module from empty candidate set")


def _non_routed_capability_state() -> dict[str, Any]:
    """Return the invariant no-transaction capability state for early exits."""

    return {
        "privacy_triggered": False,
        "transaction_requested": False,
        "transaction_request_disposition": "no_transaction_requested",
        "skill_financial_transaction_possible": False,
        "external_side_effect_possible": False,
        "risk_flags": [],
    }


def route(text: str) -> dict[str, Any]:
    normalized = " ".join(text.strip().split()).lower()
    if not normalized:
        return {
            "status": "needs_clarification",
            "reason": "empty_request",
            "primary_module": None,
            "module_chain": [],
            "specialist_tasks": [],
            "references": ["references/routing-catalog.md"],
            **_non_routed_capability_state(),
        }

    out_of_scope_matches = _matches(normalized, OUT_OF_SCOPE)
    if out_of_scope_matches:
        return {
            "status": "out_of_scope",
            "reason": "request targets an explicitly excluded capability",
            "matched_patterns": out_of_scope_matches,
            "primary_module": None,
            "module_chain": [],
            "specialist_tasks": [],
            "references": ["references/routing-catalog.md"],
            **_non_routed_capability_state(),
        }

    evidence: dict[str, list[str]] = {}
    candidates: set[str] = set()
    for module, patterns in PATTERNS.items():
        found = _matches(normalized, patterns)
        if found:
            candidates.add(module)
            evidence[module] = found

    # Limited-support asset classes (module-catalog.json §limited_support): FX / futures /
    # commodities have no dedicated module. Reroute by intent when possible; otherwise
    # return status=limited_support instead of pretending to own a methodology.
    limited_support_hits = _matches(normalized, LIMITED_SUPPORT_ASSET_PATTERNS)
    limited_support_note = LIMITED_SUPPORT_NOTE if limited_support_hits else None
    if limited_support_hits:
        for intent_patterns, target_module in LIMITED_SUPPORT_REROUTE:
            if target_module in PATTERNS and _matches(normalized, intent_patterns):
                candidates.add(target_module)
                evidence.setdefault(target_module, []).append("limited-support-reroute")
        if not candidates:
            return {
                "status": "limited_support",
                "reason": "asset class has no dedicated module (FX / futures / commodities)",
                "matched_patterns": limited_support_hits,
                "limited_support_note": LIMITED_SUPPORT_NOTE,
                "primary_module": None,
                "module_chain": [],
                "specialist_tasks": [],
                "closest_modules": [module for _, module in LIMITED_SUPPORT_REROUTE],
                "max_confidence": "medium",
                "references": ["references/routing-catalog.md"],
                **_non_routed_capability_state(),
            }

    specialist_tasks, specialist_evidence, specialist_references = _match_specialist_tasks(normalized)
    if specialist_tasks:
        candidates.add("corporate-finance")
        evidence.setdefault("corporate-finance", []).append("task-catalog-match")
        research_upstream_tasks = {
            str(task["id"]) for task in _load_task_catalog() if task.get("requires_research_upstream")
        }
        if _matches(normalized, (r"Research", r"Investment thesis", r"analy[sz]e", r"investment thesis")) and any(
            task_id in research_upstream_tasks for task_id in specialist_tasks
        ):
            candidates.add("equity-research")
            evidence.setdefault("equity-research", []).append("research-upstream-for-specialist-task")

    transaction_hits = _matches(normalized, TRANSACTION_PATTERNS)
    if transaction_hits:
        candidates.add("trade-planning")
        evidence.setdefault("trade-planning", []).append("transaction-request-redirect")

    if not candidates:
        return {
            "status": "needs_clarification",
            "reason": "no finance domain intent matched",
            "primary_module": None,
            "module_chain": [],
            "specialist_tasks": [],
            "references": ["references/routing-catalog.md"],
            "clarifying_questions": [
                "Do you require research, product comparison, portfolio diagnostics, backtesting, a trading plan, a corporate finance model, or materials preparation?",
                "What is the analysis subject, and what output format and timeframe do you expect?",
            ],
            **_non_routed_capability_state(),
        }

    chain = _ordered_chain(candidates)
    primary = _primary_module(candidates)

    # Specialist deliverables may declare a final output owner without changing
    # dependency-chain composition. Transaction safety redirection always wins.
    if specialist_tasks and not transaction_hits:
        task_map = {str(task["id"]): task for task in _load_task_catalog()}
        owner_tasks = [
            (task_id, str(task_map.get(task_id, {}).get("final_owner", "")))
            for task_id in specialist_tasks
            if task_map.get(task_id, {}).get("final_owner")
        ]
        final_owners = _dedupe([owner for _, owner in owner_tasks])
        if len(final_owners) == 1 and final_owners[0] in candidates:
            primary = final_owners[0]
            owner_task_id = next(task_id for task_id, owner in owner_tasks if owner == primary)
            evidence.setdefault(primary, []).append(f"final-owner-override:{owner_task_id}")

    privacy_hits = _matches(normalized, PRIVACY_PATTERNS)
    non_trading_external_action_hits = _matches(normalized, NON_TRADING_EXTERNAL_ACTION_PATTERNS)
    automation_hits = _matches(normalized, AUTOMATION_PATTERNS)
    confidential_hits = _matches(normalized, CONFIDENTIAL_PATTERNS)
    scoring_hits = _matches(normalized, SCORING_PATTERNS)
    metric_hits = _matches(normalized, METRIC_CALCULATION_PATTERNS)
    safety_condition_hits = _matches(normalized, SAFETY_CONDITION_PATTERNS)

    condition_flags = {
        "privacy": bool(privacy_hits or confidential_hits),
        "execution": bool(
            transaction_hits
            or non_trading_external_action_hits
            or automation_hits
            or safety_condition_hits
        ),
        "scoring": bool(scoring_hits),
        "metrics": bool(metric_hits),
    }

    entry_dependencies: set[str] = {"references/output-contracts.md"}
    if condition_flags["privacy"]:
        entry_dependencies.add("references/privacy-security.md")
    if condition_flags["execution"]:
        entry_dependencies.add("references/execution-safety.md")
    if condition_flags["scoring"]:
        entry_dependencies.add("references/scoring-standard.md")
    if condition_flags["metrics"]:
        entry_dependencies.add("references/metric-dictionary.md")

    domain_required_dependencies: set[str] = set()
    domain_conditional_dependencies: set[str] = set()
    for module in chain:
        domain_required_dependencies.update(REQUIRED_REFERENCE_BY_MODULE[module])
        for condition, module_references in CONDITIONAL_REFERENCE_BY_MODULE[module].items():
            if condition_flags[condition]:
                domain_conditional_dependencies.update(module_references)

    merged_dependencies = entry_dependencies | domain_required_dependencies | domain_conditional_dependencies

    ambiguity = False
    clarification: list[str] = []
    research_modules = candidates.intersection({"equity-research", "fund-etf", "crypto-analysis"})
    if len(research_modules) > 1 and not candidates.intersection({"portfolio-management", "corporate-finance"}):
        ambiguity = True
        clarification.append("The request matches multiple asset research modules; confirm whether to compare these assets or analyze them separately.")
    if "corporate-finance" in candidates and not specialist_tasks:
        ambiguity = True
        clarification.append("Identified as a corporate finance request; confirm whether you need industry research, valuation, a financial model, an LBO, due diligence, returns analysis, or transaction materials.")
    if "trade-planning" in candidates:
        clarification.append(
            "Process only in analysis, paper, or manual_plan mode. This capability limit applies only to the SKILL; the user remains free to decide and act independently outside it."
        )
    if transaction_hits:
        clarification.append(
            "State the transaction-capability boundary briefly, then provide the final proposed manual plan, user verification checks, and user-controlled self-execution guidance. The SKILL cannot perform the requested transaction; any user confirmation is plan review only and cannot expand the SKILL's capabilities. The user remains free to act independently outside it."
        )

    references = [REFERENCE_BY_MODULE[module] for module in chain]
    if "corporate-finance" in candidates:
        references.append(TASK_CATALOG_REFERENCE)
        references.extend(specialist_references)
    references.extend(reference for reference in COMMON_REFERENCE_ORDER if reference in merged_dependencies)
    references = _dedupe(references)

    risk_flags: list[str] = []
    if privacy_hits:
        risk_flags.append("personal_or_sensitive_financial_data")
    if confidential_hits:
        risk_flags.append("confidential_material")
    if transaction_hits:
        risk_flags.append("financial_transaction_prohibited")
    if non_trading_external_action_hits:
        risk_flags.append("non_trading_external_side_effect")
    if automation_hits:
        risk_flags.append("automation_requires_separate_architecture")

    confidence = "high" if specialist_tasks or len(candidates) == 1 else "medium"
    if ambiguity:
        confidence = "low"

    # Governance tier (module-catalog.json §governance_tier): any full condition hit -> full, otherwise light.
    governance_tier = "light"
    if (
        risk_flags
        or transaction_hits
        or non_trading_external_action_hits
        or automation_hits
        or specialist_tasks
        or "references/privacy-security.md" in merged_dependencies
        or "trade-planning" in candidates
    ):
        governance_tier = "full"

    return {
        "status": "needs_clarification" if ambiguity else "routed",
        "primary_module": primary,
        "module_chain": chain,
        "specialist_tasks": specialist_tasks,
        "references": references,
        "matched_evidence": evidence,
        "specialist_task_evidence": specialist_evidence,
        "risk_flags": risk_flags,
        "governance_tier": governance_tier,
        "privacy_triggered": "references/privacy-security.md" in merged_dependencies,
        "transaction_requested": bool(transaction_hits),
        "transaction_request_disposition": (
            "redirected_to_manual_plan" if transaction_hits else "no_transaction_requested"
        ),
        "skill_financial_transaction_possible": False,
        "external_side_effect_possible": bool(non_trading_external_action_hits),
        "reference_resolution": {
            "entry_condition_dependencies": [
                reference for reference in COMMON_REFERENCE_ORDER if reference in entry_dependencies
            ],
            "domain_required_dependencies": [
                reference for reference in COMMON_REFERENCE_ORDER if reference in domain_required_dependencies
            ],
            "domain_conditional_dependencies": [
                reference for reference in COMMON_REFERENCE_ORDER if reference in domain_conditional_dependencies
            ],
            "specialist_dependencies": specialist_references,
            "condition_flags": condition_flags,
        },
        "routing_confidence": confidence,
        "clarifying_questions": clarification,
        **({"limited_support_note": limited_support_note, "max_confidence": "medium"} if limited_support_note else {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", help="Natural-language request; stdin is used if omitted")
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    args = parser.parse_args()
    text = args.request if args.request is not None else sys.stdin.read()
    result = route(text)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
