from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "tests"))

import _bootstrap  # noqa: E402,F401  (bytecode hygiene)

from finance_metrics import MetricError, calculate  # noqa: E402
from route_request import REQUIRED_REFERENCE_BY_MODULE, route  # noqa: E402
from result_fixtures import valid_result  # noqa: E402
from validate_result import validate_result  # noqa: E402


class CompositeRoutingRegressionTests(unittest.TestCase):
    def test_portfolio_and_fund_chain(self) -> None:
        result = route("Compare two ETFs for my portfolio and perform asset allocation")
        self.assertEqual(result["status"], "routed")
        self.assertEqual(result["module_chain"], ["fund-etf", "portfolio-management"])
        self.assertTrue(result["privacy_triggered"])

    def test_full_research_to_trade_chain(self) -> None:
        result = route("Analyze Apple's fundamentals, design options, backtest rules, then generate a trading plan")
        self.assertEqual(
            result["module_chain"],
            ["equity-research", "options-strategy", "quant-backtesting", "trade-planning"],
        )
        self.assertFalse(result["external_side_effect_possible"])
        self.assertIn("references/execution-safety.md", result["references"])
        expected = set().union(
            *(REQUIRED_REFERENCE_BY_MODULE[module] for module in result["module_chain"])
        )
        self.assertTrue(expected.issubset(result["references"]))
        self.assertEqual(len(result["references"]), len(set(result["references"])))

    def test_research_then_materials(self) -> None:
        # O2 Phase 1: Producing ECM roadshow materials constitutes new material production; assign to corporate-finance.
        result = route("Analyze Apple's financial statements and valuation, then prepare ECM roadshow materials")
        self.assertEqual(result["module_chain"], ["equity-research", "corporate-finance"])
        self.assertIn("research-materials-pack", result["specialist_tasks"])

    def test_portfolio_mandatory_privacy_without_personal_wording(self) -> None:
        result = route("Perform a risk diagnosis on the portfolio")
        self.assertEqual(result["module_chain"], ["portfolio-management"])
        self.assertIn("references/privacy-security.md", result["references"])
        self.assertTrue(result["privacy_triggered"])

    def test_trade_language_does_not_imply_live_mode(self) -> None:
        result = route("Buy 100 shares of Apple, give me an order draft")
        self.assertEqual(result["primary_module"], "trade-planning")
        self.assertFalse(result["external_side_effect_possible"])

    def test_explicit_live_request_is_prohibited_and_redirected(self) -> None:
        result = route("Place a live order now to buy 100 shares of Apple for me")
        self.assertEqual(result["primary_module"], "trade-planning")
        self.assertTrue(result["transaction_requested"])
        self.assertEqual(result["transaction_request_disposition"], "redirected_to_manual_plan")
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertFalse(result["external_side_effect_possible"])
        self.assertIn("financial_transaction_prohibited", result["risk_flags"])
        self.assertIn("references/execution-safety.md", result["references"])

    def test_multi_asset_research_asks_for_clarification(self) -> None:
        result = route("Compare a company's fundamentals with Bitcoin on-chain data")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["routing_confidence"], "low")

    def test_empty_request(self) -> None:
        result = route("   ")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["reason"], "empty_request")


class FailurePathRegressionTests(unittest.TestCase):
    def test_nonpositive_price_series_fails(self) -> None:
        with self.assertRaises(MetricError):
            calculate({"operation": "return_metrics", "values": [100, 0, 105], "periods_per_year": 252})

    def test_benchmark_length_mismatch_fails(self) -> None:
        with self.assertRaises(MetricError):
            calculate(
                {
                    "operation": "return_metrics",
                    "values": [100, 101, 102],
                    "benchmark_values": [100, 101],
                    "periods_per_year": 252,
                }
            )

    def test_option_without_multiplier_fails(self) -> None:
        with self.assertRaises(MetricError):
            calculate(
                {
                    "operation": "option_scenario",
                    "underlying_prices": [100],
                    "legs": [{"kind": "call", "side": "long", "strike": 100, "premium": 2}],
                }
            )

    def test_misaligned_technical_data_fails(self) -> None:
        with self.assertRaises(MetricError):
            calculate(
                {
                    "operation": "technical_metrics",
                    "closes": [1, 2, 3],
                    "highs": [2, 3],
                    "lows": [0, 1, 2],
                }
            )

    def test_unknown_operation_fails(self) -> None:
        with self.assertRaises(MetricError):
            calculate({"operation": "future_prediction"})


class GovernanceTierRegressionTests(unittest.TestCase):
    """S2: light tier must not carry professional artifacts or external side effects."""

    def test_light_tier_rejects_professional_artifact(self) -> None:
        result = valid_result("equity-research")
        result["governance_tier"] = "light"
        result["artifacts"] = [
            {
                "artifact_id": "a1",
                "type": "model",
                "format": "xlsx",
                "status": "planned",
                "editable": True,
            }
        ]
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("governance_tier=light" in error for error in report["errors"]))

    def test_light_tier_rejects_external_side_effect(self) -> None:
        result = valid_result("equity-research")
        result["governance_tier"] = "light"
        result["execution"] = {"external_side_effect": True, "confirmation_status": "confirmed"}
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("governance_tier=light" in error for error in report["errors"]))

    def test_full_tier_keeps_existing_behaviour(self) -> None:
        result = valid_result("equity-research")
        result["governance_tier"] = "full"
        report = validate_result(result)
        self.assertEqual(report["status"], "passed")

    def test_router_marks_simple_lookup_light(self) -> None:
        from route_request import route as _route

        simple = _route("Analyze Apple Inc.'s fundamentals")
        self.assertEqual(simple["governance_tier"], "light")
        heavy = _route("Build an Excel DCF model for Apple")
        self.assertEqual(heavy["governance_tier"], "full")


class PrivacyAndExecutionRegressionTests(unittest.TestCase):
    @staticmethod
    def base_result() -> dict:
        return valid_result("equity-research")

    def test_secret_like_value_is_rejected(self) -> None:
        result = self.base_result()
        result["summary"] = "token=abcdefghijklmnop123456"
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("secret" in error for error in report["errors"]))

    def test_full_wallet_is_warned(self) -> None:
        result = self.base_result()
        result["summary"] = "wallet 0x1234567890abcdef1234567890abcdef12345678"
        report = validate_result(result)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(any("wallet" in warning for warning in report["warnings"]))

    def test_invalid_primary_chain_is_rejected(self) -> None:
        result = self.base_result()
        result["module_chain"] = ["fund-etf", "equity-research"]
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")

    def test_complete_with_gaps_is_warned(self) -> None:
        result = self.base_result()
        result["data_gaps"] = [{"field": "peer_data", "reason": "unavailable", "impact": "relative valuation incomplete", "remediation": "obtain verified peers"}]
        report = validate_result(result)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(any("data_gaps" in warning for warning in report["warnings"]))

    def test_confirmed_side_effect_can_pass_contract(self) -> None:
        result = self.base_result()
        result["execution"] = {"external_side_effect": True, "confirmation_status": "confirmed"}
        report = validate_result(result)
        self.assertEqual(report["status"], "passed")

    def test_unknown_payload_field_is_rejected(self) -> None:
        result = self.base_result()
        result["payload"]["free_form_extra"] = "not allowed"
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("Additional properties" in error for error in report["errors"]))

    def test_missing_source_reference_is_rejected(self) -> None:
        result = self.base_result()
        result["facts"] = [{"fact_id": "f1", "statement": "verified fact", "as_of": "2026-07-22", "source_ref": "src-missing", "status": "verified"}]
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("missing referenced sources" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
