"""Golden-request regression suite.

Locks the routing behaviour for (a) the probe cases that previously failed and
(b) the high-frequency ambiguity rules documented in references/routing-catalog.md.
Any change to references/module-catalog.json, task-catalog patterns, or
scripts/route_request.py must keep this suite green or update it together with
the routing-catalog narrative in the same change.
"""

import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import _bootstrap  # noqa: E402,F401  (bytecode hygiene)

from route_request import route  # noqa: E402


class ProbeRegressionTests(unittest.TestCase):
    """Cases that misrouted before the batch-1 router patch."""

    def test_stock_analysis_with_position_sizing_owned_by_portfolio(self) -> None:
        result = route("Analyze this stock and tell me how much to buy")
        self.assertEqual(result["primary_module"], "portfolio-management")
        self.assertEqual(result["module_chain"], ["equity-research", "portfolio-management"])

    def test_etf_comparison_into_portfolio_owned_by_portfolio(self) -> None:
        result = route("Compare SPY with VOO and add to my portfolio")
        self.assertEqual(result["primary_module"], "portfolio-management")
        self.assertEqual(result["module_chain"], ["fund-etf", "portfolio-management"])

    def test_valuation_plus_teaser_owned_by_corporate_finance(self) -> None:
        result = route("Value this company and prepare a Teaser")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("deal-teaser", result["specialist_tasks"])

    def test_latest_earnings_reading_stays_retail(self) -> None:
        result = route("Analyze Tesla's latest financial report")
        self.assertEqual(result["primary_module"], "equity-research")
        self.assertEqual(result["module_chain"], ["equity-research"])
        self.assertEqual(result["specialist_tasks"], [])

    def test_earnings_update_email_hits_plugin_task(self) -> None:
        result = route("Give me a quick earnings commentary email for Tesla")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("earnings-update", result["specialist_tasks"])

    def test_deal_screening_routes_to_corporate_finance(self) -> None:
        result = route("Screen a batch of investment opportunities")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("deal-screening-scorecard", result["specialist_tasks"])

    def test_research_to_roadshow_materials_chain(self) -> None:
        # O2 Phase 1: produce new materials (roadshow materials) into corporate-finance research-materials-pack.
        result = route("Research NVIDIA and prepare roadshow materials")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertEqual(result["module_chain"], ["equity-research", "corporate-finance"])
        self.assertIn("research-materials-pack", result["specialist_tasks"])

    def test_ecm_profile_owned_by_corporate_finance(self) -> None:
        # O2 Phase 1: migrate ECM pre-meeting files into corporate-finance ecm-company-profile.
        result = route("Generate ECM pre-meeting company profile")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("ecm-company-profile", result["specialist_tasks"])

    def test_ic_scorecard_owned_by_corporate_finance(self) -> None:
        result = route("Review this private equity deal's investment committee scorecard for me")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("business-quality-scorecard", result["specialist_tasks"])

    def test_corp_fin_context_with_minutes_hits_meeting_minutes_task(self) -> None:
        result = route("The corporate finance team needs meeting minutes")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("meeting-minutes", result["specialist_tasks"])


class HighFrequencyAmbiguityTests(unittest.TestCase):
    """Rules from routing-catalog §high-frequency-ambiguity that must hold in the router."""

    def test_lbo_with_buy_decision_owned_by_corporate_finance(self) -> None:
        result = route("Run an LBO and tell me whether this company is worth acquiring")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("lbo-model", result["specialist_tasks"])

    def test_backtest_my_portfolio_owned_by_backtesting(self) -> None:
        result = route("Backtest my portfolio strategy")
        self.assertEqual(result["primary_module"], "portfolio-management")
        self.assertIn("quant-backtesting", result["module_chain"])

    def test_option_roll_stays_in_options_without_real_order(self) -> None:
        result = route("Analyze whether to roll my options positions")
        self.assertEqual(result["primary_module"], "options-strategy")
        self.assertNotIn("trade-planning", result["module_chain"])

    def test_make_and_send_teaser_flags_non_trading_side_effect(self) -> None:
        result = route("Prepare and send the Blind Teaser for this deal")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertFalse(result["transaction_requested"])
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertTrue(result["external_side_effect_possible"])
        self.assertIn("non_trading_external_side_effect", result["risk_flags"])
        self.assertIn("references/execution-safety.md", result["references"])

    def test_meeting_minutes_from_recording_hits_plugin_task(self) -> None:
        result = route("Convert this buy-side roadshow recording into meeting minutes")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("meeting-minutes", result["specialist_tasks"])
        self.assertTrue(result["privacy_triggered"])

    def test_dcf_workbook_request_hits_plugin(self) -> None:
        result = route("Build a DCF and Public Comps Excel for Apple")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertEqual(result["specialist_tasks"], ["dcf-model", "public-comps"])

    def test_diligence_and_cim_single_module_chain(self) -> None:
        result = route("Make a due diligence request list for this company and prepare a CIM")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertEqual(result["module_chain"], ["corporate-finance"])

    def test_teaser_materials_owned_by_corporate_finance(self) -> None:
        # All institutional materials production now lives in the plugin.
        result = route("The investment banking team needs a deal teaser presentation")
        self.assertEqual(result["primary_module"], "corporate-finance")


class LimitedSupportTests(unittest.TestCase):
    """FX / futures / commodities have no dedicated module (routing-catalog §limited-support)."""

    def test_pure_fx_analysis_returns_limited_support(self) -> None:
        result = route("Analyze EUR/USD trend")
        self.assertEqual(result["status"], "limited_support")
        self.assertEqual(result["max_confidence"], "medium")
        self.assertTrue(result["limited_support_note"])

    def test_commodity_futures_backtest_reroutes_to_backtesting(self) -> None:
        result = route("Backtest a crude oil futures strategy")
        self.assertEqual(result["status"], "routed")
        self.assertEqual(result["primary_module"], "quant-backtesting")
        self.assertTrue(result.get("limited_support_note"))

    def test_gold_futures_order_reroutes_to_manual_trade_plan(self) -> None:
        result = route("Place an order to buy gold futures for me")
        self.assertEqual(result["status"], "routed")
        self.assertEqual(result["primary_module"], "trade-planning")
        self.assertTrue(result["transaction_requested"])
        self.assertEqual(result["transaction_request_disposition"], "redirected_to_manual_plan")
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertFalse(result["external_side_effect_possible"])
        self.assertIn("financial_transaction_prohibited", result["risk_flags"])
        self.assertTrue(result.get("limited_support_note"))
        self.assertEqual(result["governance_tier"], "full")


class GuardrailTests(unittest.TestCase):
    def test_real_estate_stays_out_of_scope(self) -> None:
        result = route("Help me with real estate underwriting and rent calculations")
        self.assertEqual(result["status"], "out_of_scope")

    def test_empty_request_needs_clarification(self) -> None:
        result = route("   ")
        self.assertEqual(result["status"], "needs_clarification")


if __name__ == "__main__":
    unittest.main()
