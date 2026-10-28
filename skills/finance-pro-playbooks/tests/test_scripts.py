from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
TESTS = SKILL_ROOT / "tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import _bootstrap  # noqa: E402,F401  (bytecode hygiene)

from finance_metrics import MetricError, calculate  # noqa: E402
from route_request import (  # noqa: E402
    CONDITIONAL_REFERENCE_BY_MODULE,
    REFERENCE_BY_MODULE,
    REQUIRED_REFERENCE_BY_MODULE,
    route,
)
import ensure_runtime as ensure_runtime_module  # noqa: E402
from ensure_runtime import RuntimePreparationError, ensure_runtime  # noqa: E402
import fetch_yahoo_finance as yahoo_module  # noqa: E402
import validate_yahoo_source as yahoo_validator_module  # noqa: E402
import render_report as render_report_module  # noqa: E402
from render_report import (  # noqa: E402
    IMPORTANT_NOTICE_HEADING,
    IMPORTANT_NOTICE_TEXT,
    TRANSACTION_REQUEST_BOUNDARY,
    render_report,
)
from result_fixtures import ALL_MODULES, valid_result  # noqa: E402
import validate_result as validate_result_module  # noqa: E402
from validate_result import validate_result  # noqa: E402
from validate_skill import (  # noqa: E402
    DOMAIN_CONDITIONAL_REFERENCES,
    DOMAIN_REQUIRED_REFERENCES,
    validate,
)


class RouterTests(unittest.TestCase):
    def test_equity_research(self) -> None:
        result = route("Analyze Apple Inc.'s fundamentals, financials, and valuation range")
        self.assertEqual(result["status"], "routed")
        self.assertEqual(result["primary_module"], "equity-research")
        self.assertEqual(result["module_chain"], ["equity-research"])

    def test_equity_then_options(self) -> None:
        result = route("Analyze Apple's fundamentals and design a covered call strategy")
        self.assertEqual(result["module_chain"], ["equity-research", "options-strategy"])

    def test_portfolio_transaction_request_redirects_to_manual_plan(self) -> None:
        result = route("Rebalance my portfolio based on my holdings, then help me place real orders")
        self.assertEqual(result["primary_module"], "trade-planning")
        self.assertEqual(result["module_chain"], ["portfolio-management", "trade-planning"])
        self.assertTrue(result["privacy_triggered"])
        self.assertTrue(result["transaction_requested"])
        self.assertEqual(result["transaction_request_disposition"], "redirected_to_manual_plan")
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertFalse(result["external_side_effect_possible"])
        self.assertIn("financial_transaction_prohibited", result["risk_flags"])
        self.assertIn("references/privacy-security.md", result["references"])
        self.assertIn("references/execution-safety.md", result["references"])
        self.assertTrue(
            any(
                "final proposed manual plan" in question
                and "user-controlled self-execution guidance" in question
                for question in result["clarifying_questions"]
            )
        )

    def test_crypto_then_backtest(self) -> None:
        result = route("Backtest a funding-rate strategy for Bitcoin perpetual futures")
        self.assertEqual(result["module_chain"], ["crypto-analysis", "quant-backtesting"])

    def test_meeting_minutes_materials(self) -> None:
        result = route("Convert this buy-side roadshow recording into meeting minutes")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("meeting-minutes", result["specialist_tasks"])
        self.assertTrue(result["privacy_triggered"])

    def test_corporate_finance_dcf_and_comps_plugin_route(self) -> None:
        result = route("Build a DCF and Public Comps Excel for Apple")
        self.assertEqual(result["status"], "routed")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertEqual(result["module_chain"], ["corporate-finance"])
        self.assertEqual(result["specialist_tasks"], ["dcf-model", "public-comps"])
        self.assertIn(
            "references/corporate-finance/playbooks/valuation/dcf-model.md",
            result["references"],
        )
        self.assertIn(
            "references/corporate-finance/playbooks/valuation/public-comps.md",
            result["references"],
        )
        self.assertIn(
            "references/corporate-finance/playbooks/valuation/_overview.md",
            result["references"],
        )
        self.assertIn(
            "references/corporate-finance/formats/excel_standards.md",
            result["references"],
        )
        self.assertIn(
            "references/corporate-finance/formats/metric_disambiguation.md",
            result["references"],
        )

    def test_corporate_finance_lbo_task_union(self) -> None:
        result = route("Build an LBO model, debt schedule, and return attribution")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertEqual(
            result["specialist_tasks"],
            ["lbo-model", "lbo-debt-schedule", "irr-attribution"],
        )
        self.assertIn(
            "references/corporate-finance/playbooks/lbo-structuring/lbo-model.md",
            result["references"],
        )
        self.assertIn(
            "references/corporate-finance/playbooks/returns-analysis/irr-attribution.md",
            result["references"],
        )

    def test_corporate_finance_can_follow_equity_research(self) -> None:
        result = route("First research Apple's fundamentals, then build a DCF model")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertEqual(result["module_chain"], ["equity-research", "corporate-finance"])
        self.assertEqual(result["specialist_tasks"], ["dcf-model"])

    def test_domain_required_dependencies_are_merged(self) -> None:
        result = route("Analyze Apple Inc.'s fundamentals")
        expected = set(REQUIRED_REFERENCE_BY_MODULE["equity-research"])
        self.assertTrue(expected.issubset(result["references"]))
        self.assertEqual(
            set(result["reference_resolution"]["domain_required_dependencies"]),
            expected,
        )

    def test_options_conditional_scoring_dependency(self) -> None:
        plain = route("Design a covered call strategy")
        scored = route("Score the covered call strategy and output confidence")
        scoring = "references/scoring-standard.md"
        self.assertNotIn(scoring, plain["references"])
        self.assertIn(scoring, scored["references"])
        self.assertIn(
            scoring,
            scored["reference_resolution"]["domain_conditional_dependencies"],
        )
        self.assertIn("scoring", CONDITIONAL_REFERENCE_BY_MODULE["options-strategy"])

    def test_trade_planning_mandatory_safety_and_privacy(self) -> None:
        result = route("Generate a stock trading plan and stop-loss levels")
        self.assertEqual(result["primary_module"], "trade-planning")
        self.assertIn("references/privacy-security.md", result["references"])
        self.assertIn("references/execution-safety.md", result["references"])
        self.assertTrue(result["privacy_triggered"])
        self.assertFalse(result["transaction_requested"])
        self.assertEqual(result["transaction_request_disposition"], "no_transaction_requested")
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertFalse(result["external_side_effect_possible"])

    def test_all_transaction_verbs_are_prohibited_and_redirected(self) -> None:
        requests = (
            "Place a limit order for 10 shares of AAPL for me",
            "Modify my AAPL order from 220 to 225",
            "Cancel the open order for AAPL",
            "Execute this options trade for me",
            "The plan is confirmed; proceed with execution now",
            "Sign and broadcast this Ethereum transaction",
            "Approve this token allowance and transfer the tokens",
            "Rebalance my portfolio for me",
        )
        for request in requests:
            with self.subTest(request=request):
                result = route(request)
                self.assertEqual(result["primary_module"], "trade-planning")
                self.assertTrue(result["transaction_requested"])
                self.assertEqual(result["transaction_request_disposition"], "redirected_to_manual_plan")
                self.assertFalse(result["skill_financial_transaction_possible"])
                self.assertFalse(result["external_side_effect_possible"])
                self.assertIn("financial_transaction_prohibited", result["risk_flags"])
                self.assertIn("references/execution-safety.md", result["references"])

    def test_non_trading_publication_remains_separately_confirmable(self) -> None:
        result = route("Prepare and publish an IPO investor roadshow presentation")
        self.assertFalse(result["transaction_requested"])
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertTrue(result["external_side_effect_possible"])
        self.assertIn("non_trading_external_side_effect", result["risk_flags"])

    def test_materials_review_metric_dependency(self) -> None:
        # After the ir module merged into corporate-finance, metric-dictionary is a required plugin dependency;
        # Verify that both static material requests and calculated requests invoke the plugin, and that the latter include the metric dictionary.
        plain = route("Convert this buy-side meeting recording into meeting minutes")
        calculated = route("Calculate transaction returns and prepare investment committee materials")
        metric = "references/metric-dictionary.md"
        self.assertEqual(plain["primary_module"], "corporate-finance")
        self.assertIn(metric, calculated["references"])

    def test_reference_union_is_deduplicated(self) -> None:
        result = route("Rebalance based on my portfolio and generate real orders")
        self.assertEqual(len(result["references"]), len(set(result["references"])))
        self.assertTrue(result["transaction_requested"])
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertFalse(result["external_side_effect_possible"])
        self.assertIn("entry_condition_dependencies", result["reference_resolution"])
        self.assertIn("domain_required_dependencies", result["reference_resolution"])
        self.assertIn("domain_conditional_dependencies", result["reference_resolution"])

    def test_real_estate_is_out_of_scope(self) -> None:
        result = route("Create a real estate underwriting model and rent projections")
        self.assertEqual(result["status"], "out_of_scope")
        self.assertEqual(result["module_chain"], [])

    def test_unknown_needs_clarification(self) -> None:
        result = route("Review this for me")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertIsNone(result["primary_module"])


class MetricTests(unittest.TestCase):
    def test_return_metrics(self) -> None:
        result = calculate(
            {
                "operation": "return_metrics",
                "values": [100, 110, 121],
                "periods_per_year": 1,
                "calendar_days": 730,
            }
        )["result"]
        self.assertAlmostEqual(result["total_return"], 0.21)
        self.assertAlmostEqual(result["annualized_arithmetic_return"], 0.10)
        self.assertAlmostEqual(result["cagr"], 0.1)
        self.assertEqual(result["max_drawdown"]["value"], 0.0)
        self.assertIsNone(result["sharpe"])

    def test_max_drawdown(self) -> None:
        result = calculate(
            {
                "operation": "return_metrics",
                "values": [100, 120, 90, 110],
                "periods_per_year": 252,
            }
        )["result"]
        drawdown = result["max_drawdown"]
        self.assertAlmostEqual(drawdown["value"], -0.25)
        self.assertEqual(drawdown["peak_index"], 1)
        self.assertEqual(drawdown["trough_index"], 2)

    def test_portfolio_metrics(self) -> None:
        result = calculate(
            {
                "operation": "portfolio_metrics",
                "weights": [0.5, 0.5],
                "target_weights": [0.6, 0.4],
                "top_n": 1,
                "covariance": [[0.04, 0.01], [0.01, 0.09]],
            }
        )["result"]
        self.assertAlmostEqual(result["hhi"], 0.5)
        self.assertAlmostEqual(result["effective_number_of_holdings"], 2.0)
        self.assertAlmostEqual(result["top_n_concentration"], 0.5)
        self.assertAlmostEqual(result["one_way_turnover"], 0.1)
        self.assertTrue(math.isclose(sum(result["risk_contribution_share"]), 1.0))

    def test_invalid_weights_fail(self) -> None:
        with self.assertRaises(MetricError):
            calculate({"operation": "portfolio_metrics", "weights": [0.2, 0.2]})

    def test_technical_metrics(self) -> None:
        closes = list(range(1, 41))
        result = calculate(
            {
                "operation": "technical_metrics",
                "closes": closes,
                "highs": [value + 1 for value in closes],
                "lows": [value - 1 for value in closes],
                "period": 14,
            }
        )["result"]
        self.assertEqual(result["rsi_wilder"], 100.0)
        self.assertIsNotNone(result["atr_wilder"])
        self.assertIsNotNone(result["macd"]["line"])

    def test_option_scenario(self) -> None:
        result = calculate(
            {
                "operation": "option_scenario",
                "underlying_prices": [110],
                "legs": [
                    {
                        "kind": "call",
                        "side": "long",
                        "strike": 100,
                        "premium": 5,
                        "quantity": 1,
                        "multiplier": 100,
                    }
                ],
            }
        )["result"]
        self.assertAlmostEqual(result["scenarios"][0]["total_pnl"], 500.0)

    def test_defi_metrics(self) -> None:
        result = calculate(
            {
                "operation": "defi_metrics",
                "price_ratio": 4,
                "fees": 100,
                "average_capital": 10000,
                "days": 10,
            }
        )["result"]
        self.assertAlmostEqual(result["constant_product_50_50_impermanent_loss"], -0.2)
        self.assertAlmostEqual(result["simple_fee_apr"], 0.365)


class RuntimePreparationTests(unittest.TestCase):
    def test_ready_runtime_skips_installation(self) -> None:
        ready = {
            "runtime_contract": ensure_runtime_module.RUNTIME_CONTRACT,
            "status": "ready",
            "dependency": "jsonschema",
            "required": ensure_runtime_module.REQUIRED_SPECIFIER,
            "version": "4.26.0",
        }
        runner = mock.Mock()
        with mock.patch.object(ensure_runtime_module, "inspect_runtime", return_value=ready):
            state = ensure_runtime(runner=runner)
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["action"], "none")
        runner.assert_not_called()

    def test_missing_runtime_installs_locked_dependencies_and_rechecks(self) -> None:
        missing = {
            "runtime_contract": ensure_runtime_module.RUNTIME_CONTRACT,
            "status": "missing",
            "dependency": "jsonschema",
            "required": ensure_runtime_module.REQUIRED_SPECIFIER,
            "version": None,
        }
        ready = {**missing, "status": "ready", "version": "4.26.0"}
        completed = mock.Mock(returncode=0, stdout="installed", stderr="")
        runner = mock.Mock(return_value=completed)
        with mock.patch.object(ensure_runtime_module, "inspect_runtime", side_effect=[missing, ready]):
            state = ensure_runtime(runner=runner)
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["action"], "installed")
        self.assertEqual(state["installer"], "uv")
        command = runner.call_args.args[0]
        self.assertEqual(tuple(command[:5]), ("sudo", "uv", "pip", "install", "--system"))
        self.assertIn(str(ensure_runtime_module.LOCK_FILE), command)

    def test_incompatible_runtime_is_replaced_from_lock(self) -> None:
        incompatible = {
            "runtime_contract": ensure_runtime_module.RUNTIME_CONTRACT,
            "status": "incompatible",
            "dependency": "jsonschema",
            "required": ensure_runtime_module.REQUIRED_SPECIFIER,
            "version": "5.0.0",
        }
        ready = {**incompatible, "status": "ready", "version": "4.26.0"}
        completed = mock.Mock(returncode=0, stdout="installed", stderr="")
        runner = mock.Mock(return_value=completed)
        with mock.patch.object(ensure_runtime_module, "inspect_runtime", side_effect=[incompatible, ready]):
            state = ensure_runtime(runner=runner)
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["action"], "installed")

    def test_install_failure_is_fail_closed(self) -> None:
        missing = {
            "runtime_contract": ensure_runtime_module.RUNTIME_CONTRACT,
            "status": "missing",
            "dependency": "jsonschema",
            "required": ensure_runtime_module.REQUIRED_SPECIFIER,
            "version": None,
        }
        completed = mock.Mock(returncode=1, stdout="", stderr="offline")
        runner = mock.Mock(return_value=completed)
        with mock.patch.object(ensure_runtime_module, "inspect_runtime", return_value=missing):
            with self.assertRaises(RuntimePreparationError) as context:
                ensure_runtime(runner=runner)
        self.assertEqual(context.exception.state["status"], "blocked")
        self.assertEqual(runner.call_count, 2)

    def test_disabled_auto_install_is_fail_closed(self) -> None:
        missing = {
            "runtime_contract": ensure_runtime_module.RUNTIME_CONTRACT,
            "status": "missing",
            "dependency": "jsonschema",
            "required": ensure_runtime_module.REQUIRED_SPECIFIER,
            "version": None,
        }
        runner = mock.Mock()
        environment = {ensure_runtime_module.DISABLE_AUTO_INSTALL_ENV: "1"}
        with mock.patch.object(ensure_runtime_module, "inspect_runtime", return_value=missing):
            with mock.patch.dict(ensure_runtime_module.os.environ, environment, clear=False):
                with self.assertRaises(RuntimePreparationError) as context:
                    ensure_runtime(runner=runner)
        self.assertEqual(context.exception.state["status"], "blocked")
        runner.assert_not_called()

    def test_result_validation_propagates_runtime_block(self) -> None:
        error = RuntimePreparationError(
            "runtime unavailable",
            state={"status": "blocked", "dependency": "jsonschema"},
        )
        validate_result_module._jsonschema_api.cache_clear()
        with mock.patch.object(validate_result_module, "_jsonschema_api", side_effect=error):
            report = validate_result_module.validate_result(valid_result("equity-research"))
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["runtime"]["status"], "blocked")
        self.assertTrue(any("runtime preparation failed" in item for item in report["errors"]))

    def test_uv_failure_falls_back_to_locked_pip_installation(self) -> None:
        missing = {
            "runtime_contract": ensure_runtime_module.RUNTIME_CONTRACT,
            "status": "missing",
            "dependency": "jsonschema",
            "required": ensure_runtime_module.REQUIRED_SPECIFIER,
            "version": None,
        }
        ready = {**missing, "status": "ready", "version": "4.26.0"}
        runner = mock.Mock(
            side_effect=[
                mock.Mock(returncode=1, stdout="", stderr="uv unavailable"),
                mock.Mock(returncode=0, stdout="installed", stderr=""),
            ]
        )
        with mock.patch.object(ensure_runtime_module, "inspect_runtime", side_effect=[missing, ready]):
            state = ensure_runtime(runner=runner)
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["installer"], "pip3")
        self.assertEqual(runner.call_count, 2)

    def test_post_install_recheck_failure_is_fail_closed(self) -> None:
        missing = {
            "runtime_contract": ensure_runtime_module.RUNTIME_CONTRACT,
            "status": "missing",
            "dependency": "jsonschema",
            "required": ensure_runtime_module.REQUIRED_SPECIFIER,
            "version": None,
        }
        broken = {**missing, "status": "broken", "version": "4.26.0", "detail": "import failed"}
        completed = mock.Mock(returncode=0, stdout="installed", stderr="")
        runner = mock.Mock(return_value=completed)
        with mock.patch.object(ensure_runtime_module, "inspect_runtime", side_effect=[missing, broken]):
            with self.assertRaises(RuntimePreparationError) as context:
                ensure_runtime(runner=runner)
        self.assertEqual(context.exception.state["status"], "blocked")
        self.assertEqual(context.exception.state["action"], "install_failed")

    def test_direct_report_rendering_propagates_runtime_block(self) -> None:
        error = RuntimePreparationError(
            "runtime unavailable",
            state={"status": "blocked", "dependency": "jsonschema"},
        )
        with mock.patch.object(render_report_module, "ensure_runtime", side_effect=error):
            with self.assertRaises(RuntimePreparationError):
                render_report_module.render_report(valid_result("equity-research"))


class YahooFinanceTests(unittest.TestCase):
    @staticmethod
    def args(*values: str):
        return yahoo_module.build_parser().parse_args(list(values))

    @staticmethod
    def chart_response() -> dict:
        return {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "symbol": "AAPL",
                            "instrumentType": "EQUITY",
                            "currency": "USD",
                            "exchangeName": "NMS",
                            "regularMarketTime": {"raw": 1720000000},
                            "regularMarketPrice": {"raw": 200.5, "fmt": "200.50"},
                            "longName": "must not pass the whitelist",
                        },
                        "timestamp": [1719900000, 1719986400],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [198.0, 199.0],
                                    "high": [201.0, 202.0],
                                    "low": [197.0, 198.5],
                                    "close": [200.0, 201.5],
                                    "volume": [1000, 1100],
                                }
                            ],
                            "adjclose": [{"adjclose": [199.5, 201.0]}],
                        },
                        "events": {
                            "dividends": {
                                "1719900000": {
                                    "amount": {"raw": 0.25},
                                    "date": {"raw": 1719900000},
                                    "unapproved": "drop me",
                                }
                            },
                            "unknownEvent": {"secret": "drop me"},
                        },
                    }
                ],
                "error": None,
            }
        }

    def test_chart_fetch_normalizes_and_builds_traceable_artifact(self) -> None:
        response = self.chart_response()

        class FakeClient:
            calls: list[tuple[str, dict]] = []

            def call_api(self, operation: str, query: dict) -> dict:
                self.calls.append((operation, query))
                return response

        args = self.args(
            "chart",
            "--symbol",
            "AAPL",
            "--range",
            "5d",
            "--min-interval",
            "0",
            "--timeout",
            "1",
        )
        with mock.patch.object(yahoo_module, "utc_now", return_value="2026-07-28T12:00:00Z"):
            artifact = yahoo_module.fetch(args, client_class=FakeClient)

        self.assertEqual(artifact["status"], "ok")
        self.assertEqual(artifact["operation"], "YahooFinance/get_stock_chart")
        self.assertEqual(artifact["data"]["meta"]["regularMarketPrice"], 200.5)
        self.assertNotIn("longName", artifact["data"]["meta"])
        dividend = artifact["data"]["events"]["dividends"]["1719900000"]
        self.assertEqual(dividend, {"amount": 0.25, "date": 1719900000})
        self.assertNotIn("unknownEvent", artifact["data"]["events"])
        self.assertNotIn("raw_response", artifact)
        self.assertEqual(
            FakeClient.calls,
            [
                (
                    "YahooFinance/get_stock_chart",
                    {
                        "symbol": "AAPL",
                        "interval": "1d",
                        "range": "5d",
                        "includePrePost": False,
                        "includeAdjustedClose": True,
                    },
                )
            ],
        )
        self.assertEqual(artifact["source_manifest_entry"]["source_ref"], "yf-chart-aapl-20260728120000")
        self.assertEqual(artifact["source_manifest_entry"]["data_as_of"], artifact["data_as_of"])

    def test_insights_query_excludes_unsupported_region_and_language(self) -> None:
        args = self.args(
            "insights",
            "--symbol",
            "AAPL",
            "--region",
            "US",
            "--lang",
            "en-US",
        )
        self.assertEqual(yahoo_module.build_query(args), {"symbol": "AAPL"})

    def test_invalid_requests_fail_closed_without_echoing_malformed_symbol(self) -> None:
        cases = (
            (self.args("chart", "--symbol", "bad symbol", "--min-interval", "0"), "invalid-symbol"),
            (self.args("chart", "--symbol", "AAPL", "--timeout", "0", "--min-interval", "0"), "AAPL"),
            (
                self.args(
                    "chart",
                    "--symbol",
                    "AAPL",
                    "--period1",
                    "200",
                    "--period2",
                    "100",
                    "--min-interval",
                    "0",
                ),
                "AAPL",
            ),
        )
        for args, expected_symbol in cases:
            with self.subTest(symbol=args.symbol, timeout=args.timeout):
                artifact = yahoo_module.fetch(args, client_class=mock.Mock)
                self.assertEqual(artifact["status"], "failed")
                self.assertEqual(artifact["error"]["code"], "invalid_request")
                self.assertIsNone(artifact["data"])
                self.assertEqual(artifact["symbol"], expected_symbol)
                self.assertEqual(artifact["query"]["symbol"], expected_symbol)

    def test_equity_only_operations_reject_other_asset_classes_before_client_initialization(self) -> None:
        class UnexpectedClient:
            def __init__(self) -> None:
                raise AssertionError("client must not be initialized")

        args = self.args(
            "profile",
            "--symbol",
            "BTC-USD",
            "--asset-class",
            "crypto",
            "--min-interval",
            "0",
        )
        artifact = yahoo_module.fetch(args, client_class=UnexpectedClient)
        self.assertEqual(artifact["status"], "failed")
        self.assertEqual(artifact["error"]["code"], "unsupported_asset_operation")

    def test_profile_normalization_omits_contact_fields(self) -> None:
        response = {
            "quoteSummary": {
                "result": [
                    {
                        "assetProfile": {
                            "sector": "Technology",
                            "industry": "Consumer Electronics",
                            "longBusinessSummary": "Approved summary.",
                            "country": "United States",
                            "address1": "private address",
                            "city": "private city",
                            "phone": "private phone",
                        },
                        "price": {
                            "symbol": "AAPL",
                            "regularMarketTime": {"raw": 1720000000},
                            "regularMarketPrice": {"raw": 200.5},
                        },
                    }
                ]
            }
        }
        normalized, data_as_of, warnings = yahoo_module.normalize_profile(response)
        self.assertEqual(warnings, [])
        self.assertIsNotNone(data_as_of)
        self.assertEqual(normalized["profile"]["sector"], "Technology")
        self.assertFalse({"address1", "city", "phone"}.intersection(normalized["profile"]))

    def test_holders_normalization_omits_person_names_and_contact_fields(self) -> None:
        response = {
            "quoteSummary": {
                "result": [
                    {
                        "majorHoldersBreakdown": {"institutionsCount": {"raw": 12}},
                        "institutionOwnership": {
                            "ownershipList": [
                                {
                                    "organization": "Example Asset Management",
                                    "pctHeld": {"raw": 0.05},
                                    "position": {"raw": 1000},
                                    "reportDate": {"raw": 1719900000},
                                    "name": "private person",
                                }
                            ]
                        },
                        "insiderHolders": {
                            "holders": [
                                {
                                    "name": "private person",
                                    "relation": "Director",
                                    "positionDirect": {"raw": 100},
                                    "positionDirectDate": {"raw": 1719900000},
                                    "address1": "private address",
                                }
                            ]
                        },
                    }
                ]
            }
        }
        normalized, data_as_of, warnings = yahoo_module.normalize_holders(response)
        self.assertIsNotNone(data_as_of)
        self.assertTrue(any("names" in warning for warning in warnings))
        self.assertEqual(normalized["institutional_holders"][0]["organization"], "Example Asset Management")
        self.assertEqual(normalized["insider_positions"][0]["relation"], "Director")
        rendered = repr(normalized)
        self.assertNotIn("private person", rendered)
        self.assertNotIn("private address", rendered)
        self.assertNotIn("name", rendered.lower())

    def test_insights_normalization_omits_reports_and_strips_nested_unknown_fields(self) -> None:
        response = {
            "finance": {
                "result": {
                    "instrumentInfo": {
                        "keyTechnicals": {
                            "provider": "Example Provider",
                            "support": {"raw": 190.0},
                            "unknown": "drop me",
                        },
                        "technicalEvents": {
                            "provider": "Example Provider",
                            "shortTermOutlook": {
                                "direction": "Bullish",
                                "score": {"raw": 3},
                                "author": "private analyst",
                            },
                        },
                        "valuation": {
                            "provider": "Example Provider",
                            "relativeValue": "Near Fair Value",
                            "reportText": "drop me",
                        },
                    },
                    "companySnapshot": {
                        "company": {"hiring": 0.7, "unknown": "drop me"},
                        "sector": {"hiring": 0.5},
                        "sectorInfo": "Technology",
                    },
                    "recommendation": {
                        "provider": "Example Provider",
                        "rating": "BUY",
                        "targetPrice": {"raw": 220.0},
                        "analystName": "private analyst",
                    },
                    "events": [
                        {
                            "eventType": "PriceCross",
                            "startDate": {"raw": 1719900000},
                            "title": "drop me",
                        }
                    ],
                    "reports": [
                        {
                            "reportTitle": "Full report",
                            "headHtml": "copyrighted report text",
                            "author": "private analyst",
                        }
                    ],
                }
            }
        }
        normalized, data_as_of, warnings = yahoo_module.normalize_insights(response)
        self.assertIsNotNone(data_as_of)
        self.assertTrue(any("reports" in warning for warning in warnings))
        self.assertEqual(normalized["instrument_info"]["key_technicals"]["support"], 190.0)
        self.assertEqual(normalized["company_snapshot"]["sector_info"], "Technology")
        self.assertEqual(normalized["recommendation"]["targetPrice"], 220.0)
        rendered = repr(normalized)
        for prohibited in ("reports", "reportTitle", "headHtml", "private analyst", "unknown", "reportText"):
            self.assertNotIn(prohibited, rendered)

    def test_filings_normalization_retains_discovery_fields_only(self) -> None:
        response = {
            "quoteSummary": {
                "result": [
                    {
                        "secFilings": {
                            "filings": [
                                {
                                    "date": "2026-07-01",
                                    "epochDate": {"raw": 1782864000},
                                    "type": "10-Q",
                                    "title": "Quarterly report",
                                    "edgarUrl": "https://www.sec.gov/example",
                                    "rawText": "drop me",
                                    "exhibits": [
                                        {
                                            "type": "EX-99.1",
                                            "url": "https://www.sec.gov/exhibit",
                                            "description": "drop me",
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                ]
            }
        }
        normalized, data_as_of, warnings = yahoo_module.normalize_filings(response)
        self.assertIsNotNone(data_as_of)
        self.assertTrue(any("discovery" in warning for warning in warnings))
        self.assertEqual(set(normalized), {"filings"})
        self.assertNotIn("rawText", normalized["filings"][0])
        self.assertEqual(normalized["filings"][0]["exhibits"][0], {"type": "EX-99.1", "url": "https://www.sec.gov/exhibit"})

    def test_provider_timeout_returns_structured_failed_artifact(self) -> None:
        class TimeoutClient:
            def call_api(self, _operation: str, query: dict) -> dict:
                raise yahoo_module.ProviderTimeoutError("deadline reached")

        args = self.args("chart", "--symbol", "AAPL", "--min-interval", "0", "--timeout", "1")
        artifact = yahoo_module.fetch(args, client_class=TimeoutClient)
        self.assertEqual(artifact["status"], "failed")
        self.assertEqual(artifact["error"]["code"], "provider_timeout")
        self.assertIsNone(artifact["data"])

    def test_valid_source_artifact_passes_schema_and_raw_response_is_rejected(self) -> None:
        response = self.chart_response()

        class FakeClient:
            def call_api(self, _operation: str, _query: dict) -> dict:
                return response

        args = self.args("chart", "--symbol", "AAPL", "--min-interval", "0", "--timeout", "1")
        with mock.patch.object(yahoo_module, "utc_now", return_value="2026-07-28T12:00:00Z"):
            artifact = yahoo_module.fetch(args, client_class=FakeClient)

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "source.json"
            yahoo_module.write_json(path, artifact)
            report = yahoo_validator_module.validate(path)
            self.assertEqual(report["status"], "valid", report)

            artifact["raw_response"] = {"secret": "must not pass"}
            yahoo_module.write_json(path, artifact)
            report = yahoo_validator_module.validate(path)
            self.assertEqual(report["status"], "invalid")
            self.assertTrue(any("Additional properties" in error for error in report["errors"]))

    def test_semantic_validator_rejects_holder_names_and_insight_report_text(self) -> None:
        retrieved_at = "2026-07-28T12:00:00Z"
        holders = yahoo_module.base_artifact(
            status="partial",
            symbol="AAPL",
            operation="holders",
            query={"symbol": "AAPL"},
            retrieved_at=retrieved_at,
            data_as_of="2026-06-30T00:00:00Z",
            data={"insider_positions": [{"name": "private person", "relation": "Director"}]},
            warnings=["Privacy check fixture."],
            error=None,
        )
        holder_errors = yahoo_validator_module.semantic_errors(holders)
        self.assertTrue(any("personal identifiers" in error for error in holder_errors))

        insights = yahoo_module.base_artifact(
            status="partial",
            symbol="AAPL",
            operation="insights",
            query={"symbol": "AAPL"},
            retrieved_at=retrieved_at,
            data_as_of="2026-06-30T00:00:00Z",
            data={"reports": [{"headHtml": "full report text"}]},
            warnings=["Report-text check fixture."],
            error=None,
        )
        insight_errors = yahoo_validator_module.semantic_errors(insights)
        self.assertTrue(any("report text" in error for error in insight_errors))


class ContractTests(unittest.TestCase):
    def test_all_domain_results_pass_schema(self) -> None:
        for module in ALL_MODULES:
            with self.subTest(module=module):
                report = validate_result(valid_result(module))
                self.assertEqual(report["status"], "passed", report)

    def test_redirected_transaction_request_passes_with_plan_and_user_guidance(self) -> None:
        result = valid_result("trade-planning")
        result["payload"]["transaction_request_disposition"] = "redirected_to_manual_plan"
        report = validate_result(result)
        self.assertEqual(report["status"], "passed", report)

    def test_redirected_transaction_request_requires_manual_plan_mode(self) -> None:
        result = valid_result("trade-planning")
        result["payload"]["transaction_request_disposition"] = "redirected_to_manual_plan"
        result["payload"]["mode"] = "analysis"
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("manual_plan mode" in error for error in report["errors"]), report)

    def test_redirected_transaction_request_requires_plan_or_explicit_error(self) -> None:
        result = valid_result("trade-planning")
        result["payload"]["transaction_request_disposition"] = "redirected_to_manual_plan"
        result["payload"]["order_plan"] = None
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("proposed manual plan" in error for error in report["errors"]), report)

    def test_redirected_transaction_request_requires_three_user_steps(self) -> None:
        result = valid_result("trade-planning")
        result["payload"]["transaction_request_disposition"] = "redirected_to_manual_plan"
        result["payload"]["user_action_steps"] = result["payload"]["user_action_steps"][:1]
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("at least three" in error for error in report["errors"]), report)

    def test_redirected_transaction_request_requires_user_verification_check(self) -> None:
        result = valid_result("trade-planning")
        result["payload"]["transaction_request_disposition"] = "redirected_to_manual_plan"
        result["payload"]["plan_checks"][0]["status"] = "passed"
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("user_verification_required" in error for error in report["errors"]), report)

    def test_redirected_transaction_report_orders_boundary_plan_and_user_guidance(self) -> None:
        result = valid_result("trade-planning")
        result["payload"]["transaction_request_disposition"] = "redirected_to_manual_plan"
        markdown = render_report(result)
        self.assertIn(TRANSACTION_REQUEST_BOUNDARY, markdown)
        self.assertIn("## User-Controlled Self-Execution Guidance", markdown)
        self.assertIn("## Manual-Execution Notice", markdown)
        self.assertLess(markdown.index(TRANSACTION_REQUEST_BOUNDARY), markdown.index("## Proposed, Unsubmitted Order Plan"))
        self.assertLess(markdown.index("## Proposed, Unsubmitted Order Plan"), markdown.index("## User-Controlled Self-Execution Guidance"))
        self.assertIn("proposed_unsubmitted", markdown)

    def test_all_domain_reports_render_required_sections(self) -> None:
        for module in ALL_MODULES:
            with self.subTest(module=module):
                markdown = render_report(valid_result(module))
                self.assertIn("## Executive Summary", markdown)
                self.assertIn("## Risks and Failure Conditions", markdown)
                self.assertIn("## Data and Sources", markdown)
                self.assertIn("## Attachments and Security Status", markdown)
                self.assertEqual(markdown.count("## Important Notice"), 1)
                self.assertIn(IMPORTANT_NOTICE_TEXT, markdown)
                self.assertLess(markdown.index("## Attachments and Security Status"), markdown.index("## Important Notice"))
                self.assertTrue(markdown.rstrip().endswith(IMPORTANT_NOTICE_TEXT))

    def test_report_rejects_missing_important_notice(self) -> None:
        result = valid_result("equity-research")
        source = (SKILL_ROOT / "templates" / "equity-research.md").read_text(encoding="utf-8")
        notice_block = f"{IMPORTANT_NOTICE_HEADING}\n\n{IMPORTANT_NOTICE_TEXT}"
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            templates = temporary_root / "templates"
            templates.mkdir()
            (templates / "equity-research.md").write_text(
                source.replace(notice_block, ""),
                encoding="utf-8",
            )
            with mock.patch.object(render_report_module, "ROOT", temporary_root):
                with self.assertRaisesRegex(ValueError, "template missing required heading"):
                    render_report_module.render_report(result)

    def test_report_rejects_empty_important_notice(self) -> None:
        result = valid_result("equity-research")
        source = (SKILL_ROOT / "templates" / "equity-research.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            templates = temporary_root / "templates"
            templates.mkdir()
            (templates / "equity-research.md").write_text(
                source.replace(IMPORTANT_NOTICE_TEXT, ""),
                encoding="utf-8",
            )
            with mock.patch.object(render_report_module, "ROOT", temporary_root):
                with self.assertRaisesRegex(ValueError, "template missing canonical Important Notice text"):
                    render_report_module.render_report(result)

    def test_skill_transaction_capability_is_required_and_false_for_every_module(self) -> None:
        for module in ALL_MODULES:
            with self.subTest(module=module):
                result = valid_result(module)
                self.assertIs(result["skill_financial_transaction_possible"], False)

    def test_skill_transaction_capability_cannot_be_enabled(self) -> None:
        result = valid_result("equity-research")
        result["skill_financial_transaction_possible"] = True
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(
            any("skill_financial_transaction_possible" in error for error in report["errors"]),
            report,
        )

    def test_presentation_profile_must_match_primary_module(self) -> None:
        result = valid_result("equity-research")
        result["presentation"]["profile"] = "fund-etf"
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("presentation.profile" in error for error in report["errors"]))

    def test_unconfirmed_side_effect_fails(self) -> None:
        result = valid_result("equity-research")
        result["execution"] = {"external_side_effect": True, "confirmation_status": "pending"}
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("confirmed" in error for error in report["errors"]))

    def test_corporate_task_results_must_match_specialist_tasks(self) -> None:
        result = valid_result("corporate-finance")
        result["payload"]["task_results"][0]["task_id"] = "public-comps"
        report = validate_result(result)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("task_results" in error for error in report["errors"]))

    def test_skill_structure(self) -> None:
        report = validate(SKILL_ROOT)
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["counts"]["domain_dependency_declarations"], 8)
        self.assertEqual(report["counts"]["templates"], 8)
        self.assertEqual(report["counts"]["schemas"], 1)
        self.assertEqual(report["counts"]["corporate_finance_tasks"], 54)
        self.assertEqual(report["counts"]["corporate_finance_playbooks"], 54)
        self.assertEqual(report["counts"]["corporate_finance_formats"], 3)

    def test_router_and_declaration_dependency_matrices_match(self) -> None:
        for module, reference_path in REFERENCE_BY_MODULE.items():
            filename = Path(reference_path).name
            router_required = {Path(item).name for item in REQUIRED_REFERENCE_BY_MODULE[module]}
            router_conditional = {
                Path(item).name
                for references in CONDITIONAL_REFERENCE_BY_MODULE[module].values()
                for item in references
            }
            self.assertEqual(router_required, DOMAIN_REQUIRED_REFERENCES[filename], module)
            self.assertEqual(router_conditional, DOMAIN_CONDITIONAL_REFERENCES[filename], module)


if __name__ == "__main__":
    unittest.main()
