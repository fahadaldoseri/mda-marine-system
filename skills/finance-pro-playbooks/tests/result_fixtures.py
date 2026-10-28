from __future__ import annotations

from copy import deepcopy
from typing import Any


def _common(module: str) -> dict[str, Any]:
    return {
        "schema_version": "finance-analysis-pro/1.2",
        "skill_financial_transaction_possible": False,
        "request_id": f"fixture-{module}",
        "subject": f"Fixture {module}",
        "primary_module": module,
        "module_chain": [module],
        "as_of": "2026-07-23T00:00:00Z",
        "data_cutoff": "2026-07-22",
        "status": "complete",
        "summary": "Complete the analysis within the stated assumptions and data scope.",
        "presentation": {
            "profile": module,
            "formats": ["markdown", "json"],
            "detail_level": "standard",
            "audience": "professional",
            "language": "zh-CN",
        },
        "payload": {},
        "facts": [],
        "assumptions": [],
        "metrics": [],
        "scores": [],
        "risks": [],
        "invalidation_conditions": [],
        "data_gaps": [],
        "source_manifest": [],
        "privacy": {
            "data_classes_used": ["P0"],
            "redactions_applied": [],
            "retention_status": "not_applicable",
        },
        "execution": {
            "external_side_effect": False,
            "confirmation_status": "not_applicable",
        },
        "artifacts": [],
    }


def valid_result(module: str = "equity-research") -> dict[str, Any]:
    result = _common(module)
    payloads: dict[str, dict[str, Any]] = {
        "equity-research": {
            "paradigm": "quality-growth",
            "investment_view": "neutral",
            "confidence": "medium",
            "valuation": {
                "method": "DCF",
                "bear": 80,
                "base": 100,
                "bull": 120,
                "currency": "USD",
                "as_of": "2026-07-22",
            },
            "key_arguments": [],
            "counter_evidence": [],
            "catalysts": [],
            "monitoring_items": [],
        },
        "fund-etf": {
            "comparison_scope": "broad-market equity ETFs",
            "candidates": [
                {
                    "symbol": "TEST",
                    "name": "Fixture ETF",
                    "exposure_fit": "broad-market exposure",
                    "structural_risks": [],
                    "cost_summary": "cost not material in fixture",
                    "liquidity_summary": "liquidity not assessed in fixture",
                    "performance_summary": "performance not assessed in fixture",
                }
            ],
            "recommendations": {
                "overall": None,
                "lowest_cost": None,
                "strongest_structure": None,
            },
            "decision_band": None,
            "constraints": [],
        },
        "options-strategy": {
            "underlying_view": "neutral-to-bullish",
            "volatility_regime": "normal",
            "recommended_strategy": {
                "structure": "long-call",
                "currency": "USD",
                "legs": [
                    {
                        "side": "long",
                        "option_type": "call",
                        "quantity": 1,
                        "strike": 100,
                        "expiration": "2026-09-18",
                        "premium": 5,
                    }
                ],
                "net_premium": 500,
                "premium_convention": "debit_positive",
                "max_profit": None,
                "max_loss": 500,
                "breakevens": [105],
                "margin_or_capital": 500,
            },
            "alternatives": [],
            "scenario_results": [],
            "management_rules": [],
            "roll_conditions": [],
            "no_trade_conditions": [],
        },
        "crypto-analysis": {
            "assets": [{"symbol": "BTC", "network": "Bitcoin", "venue": None}],
            "market_context": "spot market review",
            "structure": {"trend": "range", "key_levels": [], "liquidity_zones": []},
            "derivatives_signals": [],
            "onchain_signals": [],
            "strategy_candidates": [],
            "position_risk": {"weight": None, "max_loss": None, "method": "not_applicable"},
            "lp_analysis": None,
            "fact_check": {"status": "unverified", "evidence_refs": []},
        },
        "portfolio-management": {
            "portfolio_summary": {"currency": "USD", "nav": 100000, "holdings_count": 2, "cash_weight": 0.1},
            "constraint_status": [],
            "risk_metrics": [],
            "concentration_exposures": [],
            "research_conflicts": [],
            "recommended_actions": {"primary": [], "alternatives": [], "do_not_do": []},
            "allocation_scenarios": [],
            "post_trade_comparison": [],
            "monitoring_triggers": [],
        },
        "quant-backtesting": {
            "strategy_spec": {
                "name": "moving-average",
                "universe": ["TEST"],
                "frequency": "daily",
                "signal": "fast_ma_above_slow_ma",
                "entry_rule": "enter next bar",
                "exit_rule": "exit on reverse signal",
                "sizing_rule": "equal weight",
                "risk_rule": "no leverage",
            },
            "data_manifest": {
                "start": "2024-01-01",
                "end": "2026-07-22",
                "frequency": "daily",
                "adjustment": "total-return adjusted",
                "timezone": "UTC",
                "sources": [],
            },
            "benchmark": None,
            "performance_metrics": [],
            "robustness_tests": [],
            "parameter_results": [],
            "trade_log_path": None,
            "script_path": None,
            "chart_paths": [],
            "validation_status": "provisional",
            "failure_reasons": [],
        },
        "trade-planning": {
            "mode": "manual_plan",
            "signal_card": {
                "instrument": "TEST",
                "direction": "long",
                "entry_condition": "limit price at or below 100 USD",
                "stop_condition": "manual stop review at 90 USD",
                "take_profit_condition": "review at 120 USD",
                "horizon": "swing",
                "invalidation": "thesis invalid below 90 USD",
            },
            "order_plan": {
                "manual_intent": "new_order_plan",
                "status": "proposed_unsubmitted",
                "instrument": "TEST",
                "side": "buy",
                "order_type": "limit",
                "quantity": 10,
                "quantity_unit": "shares",
                "limit_price": 100,
                "stop_price": 90,
                "time_in_force": "day",
                "expiry": None,
                "risk_budget": 100,
                "estimated_notional": 1000,
                "currency": "USD",
                "estimated_fees": 1,
                "maximum_modeled_loss": 101,
                "platform_verification_required": True,
            },
            "plan_checks": [
                {
                    "name": "current platform facts",
                    "status": "user_verification_required",
                    "evidence": "If the user independently chooses to act outside the SKILL, they should verify the current price, spread, session, balance, fees, and platform support.",
                }
            ],
            "simulation": None,
            "user_action_steps": [
                "If you independently choose to act outside the SKILL, open the relevant platform yourself and verify the instrument, current price, spread, session status, balance, permissions, fees, and platform support.",
                "Compare the proposed side, quantity, order type, price logic, time in force, estimated costs, and maximum modeled loss with the platform fields before entering anything manually.",
                "If you still choose to proceed, enter the transaction manually and review the platform's final confirmation screen before independently deciding whether to submit it."
            ],
            "manual_execution_notice": "The SKILL did not and cannot perform this financial transaction. This capability limit applies only to the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity outside the SKILL. If the user chooses to transact, they may do so independently on the relevant platform.",
            "transaction_request_disposition": "no_transaction_requested",
            "errors": [],
        },
        "corporate-finance": {
            "scope": "Build example DCF and complete model quality checks.",
            "decision_context": "valuation",
            "entity_card": {
                "legal_name": "FixtureCo",
                "aliases": [],
                "ticker": None,
                "exchange": None,
                "country": None,
                "industry": None,
                "currency": "USD",
                "fiscal_year_end": None,
                "reporting_standard": "unknown",
                "period_basis": "LTM",
                "valuation_date": "2026-07-22",
                "transaction_context": "test fixture",
            },
            "specialist_tasks": ["dcf-model"],
            "task_results": [
                {
                    "task_id": "dcf-model",
                    "status": "complete",
                    "summary": "Example DCF Contract completed.",
                    "key_outputs": {"contract_status": "valid"},
                    "open_items": [],
                    "source_refs": [],
                    "artifact_refs": [],
                }
            ],
            "model_checks": [
                {
                    "name": "schema integrity",
                    "status": "passed",
                    "evidence": "Fixture satisfies Corporate Finance Schema.",
                    "impact": "Allow entry into rendering tests.",
                }
            ],
            "deliverables": [],
            "review_status": {
                "financial_integrity": "passed",
                "period_consistency": "passed",
                "source_traceability": "passed",
                "format_quality": "passed",
                "overall": "ready",
                "reviewer_notes": [],
            },
            "scope_limitations": [],
        },
    }
    result["payload"] = deepcopy(payloads[module])
    return result


ALL_MODULES = (
    "equity-research",
    "fund-etf",
    "options-strategy",
    "crypto-analysis",
    "portfolio-management",
    "quant-backtesting",
    "trade-planning",
    "corporate-finance",
)
