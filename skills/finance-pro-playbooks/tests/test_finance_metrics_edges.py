"""Comprehensive deterministic edge coverage for the finance metrics engine."""

from __future__ import annotations

import contextlib
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_ROOT = Path(__file__).resolve().parent
SCRIPT_ROOT = TEST_ROOT.parent / "scripts"
for path in (SCRIPT_ROOT, TEST_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import _bootstrap  # noqa: E402,F401
import finance_metrics as subject  # noqa: E402


class MetricPrimitiveTests(unittest.TestCase):
    def test_number_positive_and_rate_validators_cover_invalid_types_and_ranges(self) -> None:
        for value in (True, "1"):
            with self.subTest(value=value), self.assertRaisesRegex(subject.MetricError, "must be numeric"):
                subject._numbers([value], "values")
        for value in (math.inf, math.nan):
            with self.subTest(value=value), self.assertRaisesRegex(subject.MetricError, "must be finite"):
                subject._numbers([value], "values")
        with self.assertRaisesRegex(subject.MetricError, "at least 2"):
            subject._numbers([1], "values", minimum=2)
        for value in (True, "1"):
            with self.subTest(value=value), self.assertRaisesRegex(subject.MetricError, "must be numeric"):
                subject._positive(value, "value")
        for value in (0, -1, math.inf, math.nan):
            with self.subTest(value=value), self.assertRaisesRegex(subject.MetricError, "finite and > 0"):
                subject._positive(value, "value")
        for value, expected in ((1, 1), (2.0, 2), ("3", 3)):
            with self.subTest(value=value):
                self.assertEqual(subject._positive_integer(value, "value"), expected)
        for value in (True, 0, -1, 1.5, math.inf, math.nan, "", "1.5", None):
            with self.subTest(value=value), self.assertRaisesRegex(subject.MetricError, "positive integer"):
                subject._positive_integer(value, "value")
        with self.assertRaisesRegex(subject.MetricError, "greater than -1"):
            subject._period_rate(-1, 12)

    def test_simple_returns_and_drawdown_recovery_states(self) -> None:
        with self.assertRaisesRegex(subject.MetricError, "must be > 0"):
            subject.simple_returns([1, 0])
        self.assertAlmostEqual(subject.simple_returns([100, 110])[0], 0.1)
        recovered = subject.max_drawdown([100, 80, 110])
        self.assertAlmostEqual(recovered["value"], -0.2)
        self.assertEqual({key: recovered[key] for key in ("peak_index", "trough_index", "recovery_index")}, {"peak_index": 0, "trough_index": 1, "recovery_index": 2})
        unrecovered = subject.max_drawdown([100, 90, 80])
        self.assertIsNone(unrecovered["recovery_index"])
        flat = subject.max_drawdown([100, 100])
        self.assertEqual(flat["value"], 0.0)


class ReturnMetricEdgeTests(unittest.TestCase):
    def test_two_values_have_nullable_volatility_and_calendar_cagr(self) -> None:
        result = subject.return_metrics(
            {
                "values": [100, 121],
                "periods_per_year": 1,
                "calendar_days": 730,
                "risk_free_annual": 0,
                "minimum_acceptable_annual": 0,
            }
        )
        self.assertIsNone(result["annualized_volatility"])
        self.assertIsNone(result["sharpe"])
        self.assertAlmostEqual(result["cagr"], 0.1)

    def test_calendar_and_annual_rate_boundaries(self) -> None:
        with self.assertRaisesRegex(subject.MetricError, "calendar_days"):
            subject.return_metrics({"values": [100, 101], "periods_per_year": 1, "calendar_days": 0})
        for key in ("risk_free_annual", "minimum_acceptable_annual"):
            with self.subTest(key=key), self.assertRaisesRegex(subject.MetricError, "greater than -1"):
                subject.return_metrics({"values": [100, 101], "periods_per_year": 1, key: -1})

    def test_benchmark_constant_and_identical_paths_return_nullable_ratios(self) -> None:
        identical = subject.return_metrics(
            {
                "values": [100, 110, 121],
                "benchmark_values": [100, 110, 121],
                "periods_per_year": 12,
            }
        )
        self.assertEqual(identical["tracking_error"], 0.0)
        self.assertIsNone(identical["information_ratio"])
        self.assertIsNone(identical["beta"])
        self.assertIsNone(identical["alpha_annual"])

    def test_benchmark_variable_path_computes_beta_alpha_and_information_ratio(self) -> None:
        result = subject.return_metrics(
            {
                "values": [100, 105, 103, 110],
                "benchmark_values": [100, 102, 101, 104],
                "periods_per_year": 12,
                "risk_free_annual": 0.02,
            }
        )
        self.assertIsNotNone(result["tracking_error"])
        self.assertIsNotNone(result["information_ratio"])
        self.assertIsNotNone(result["beta"])
        self.assertIsNotNone(result["alpha_annual"])


class PortfolioMetricEdgeTests(unittest.TestCase):
    def test_top_n_target_and_covariance_shape_failures(self) -> None:
        cases = [
            ({"weights": [1], "top_n": 0}, "top_n"),
            ({"weights": [0.5, 0.5], "target_weights": [1]}, "align"),
            ({"weights": [0.5, 0.5], "target_weights": [0.4, 0.4]}, "sum to 1.0"),
            ({"weights": [0.5, 0.5], "covariance": {}}, "square matrix"),
            ({"weights": [0.5, 0.5], "covariance": [[1, 0]]}, "square matrix"),
            ({"weights": [0.5, 0.5], "covariance": [[1, 0, 0], [0, 1]]}, "square"),
        ]
        for payload, fragment in cases:
            with self.subTest(payload=payload), self.assertRaisesRegex(subject.MetricError, fragment):
                subject.portfolio_metrics(payload)

    def test_negative_zero_and_positive_covariance_paths(self) -> None:
        with self.assertRaisesRegex(subject.MetricError, "cannot be negative"):
            subject.portfolio_metrics({"weights": [1], "covariance": [[-1]]})
        zero = subject.portfolio_metrics({"weights": [0.5, 0.5], "covariance": [[0, 0], [0, 0]]})
        self.assertEqual(zero["portfolio_volatility_per_period"], 0.0)
        self.assertIsNone(zero["risk_contribution"])
        self.assertIsNone(zero["risk_contribution_share"])
        positive = subject.portfolio_metrics(
            {
                "weights": [0.6, 0.4],
                "target_weights": [0.5, 0.5],
                "covariance": [[0.04, 0.01], [0.01, 0.09]],
                "top_n": 1,
            }
        )
        self.assertAlmostEqual(positive["one_way_turnover"], 0.1)
        self.assertAlmostEqual(positive["top_n_concentration"], 0.6)
        self.assertAlmostEqual(sum(positive["risk_contribution_share"]), 1.0)


class TechnicalMetricEdgeTests(unittest.TestCase):
    def test_alignment_high_low_and_period_failures(self) -> None:
        cases = [
            ({"closes": [1, 2], "highs": [2, 3], "lows": [0]}, "at least 2"),
            ({"closes": [1, 2], "highs": [0, 3], "lows": [1, 1]}, "high"),
            ({"closes": [1, 2], "highs": [2, 3], "lows": [0, 1], "period": 1}, "period"),
        ]
        for payload, fragment in cases:
            with self.subTest(payload=payload), self.assertRaisesRegex(subject.MetricError, fragment):
                subject.technical_metrics(payload)

    def test_insufficient_history_and_monotonic_rsi_branches(self) -> None:
        short = subject.technical_metrics(
            {"closes": [1, 2], "highs": [2, 3], "lows": [0, 1], "period": 14, "bollinger_period": 20}
        )
        self.assertIsNone(short["rsi_wilder"])
        self.assertIsNone(short["atr_wilder"])
        self.assertIsNone(short["bollinger"]["middle"])
        self.assertIsNone(short["macd"]["line"])

        closes = [float(index) for index in range(1, 50)]
        rising = subject.technical_metrics(
            {
                "closes": closes,
                "highs": [value + 1 for value in closes],
                "lows": [value - 1 for value in closes],
                "period": 14,
                "bollinger_period": 20,
                "bollinger_k": 2.5,
            }
        )
        self.assertEqual(rising["rsi_wilder"], 100.0)
        self.assertIsNotNone(rising["bollinger"]["upper"])
        self.assertIsNotNone(rising["macd"]["line"])
        self.assertIsNotNone(rising["macd"]["signal"])
        self.assertIsNotNone(rising["macd"]["histogram"])

    def test_bollinger_period_must_be_a_positive_integer(self) -> None:
        for value in (0, -1, True, 1.5, math.inf, "1.5"):
            with self.subTest(value=value), self.assertRaisesRegex(subject.MetricError, "bollinger_period"):
                subject.technical_metrics(
                    {
                        "closes": [1, 2],
                        "highs": [2, 3],
                        "lows": [0, 1],
                        "period": 2,
                        "bollinger_period": value,
                    }
                )


class OptionAndDefiMetricEdgeTests(unittest.TestCase):
    def test_option_leg_contract_failures(self) -> None:
        base = {"underlying_prices": [100]}
        legs = [
            (None, "non-empty"),
            ([], "non-empty"),
            (["bad"], "object"),
            ([{"kind": "stock", "side": "long"}], "kind/side"),
            ([{"kind": "call", "side": "hold"}], "kind/side"),
            ([{"kind": "call", "side": "long", "strike": 0, "premium": 1, "multiplier": 100}], "strike"),
            ([{"kind": "call", "side": "long", "strike": 100, "premium": 1, "quantity": 0, "multiplier": 100}], "quantity"),
            ([{"kind": "call", "side": "long", "strike": 100, "premium": 1, "multiplier": 0}], "multiplier"),
        ]
        for value, fragment in legs:
            payload = dict(base)
            if value is not None:
                payload["legs"] = value
            with self.subTest(value=value), self.assertRaisesRegex(subject.MetricError, fragment):
                subject.option_scenario(payload)

    def test_long_short_call_put_payoffs_and_fees(self) -> None:
        result = subject.option_scenario(
            {
                "underlying_prices": [90, 110],
                "legs": [
                    {"kind": "call", "side": "long", "strike": 100, "premium": 2, "quantity": 1, "multiplier": 100, "fees": 1},
                    {"kind": "put", "side": "short", "strike": 100, "premium": 3, "quantity": 2, "multiplier": 100, "fees": 2},
                ],
            }
        )
        self.assertEqual(len(result["scenarios"]), 2)
        self.assertEqual(len(result["scenarios"][0]["legs"]), 2)
        self.assertNotEqual(result["scenarios"][0]["total_pnl"], result["scenarios"][1]["total_pnl"])

    def test_defi_optional_apr_and_missing_bundle_failures(self) -> None:
        self.assertEqual(subject.defi_metrics({"price_ratio": 1})["constant_product_50_50_impermanent_loss"], 0.0)
        result = subject.defi_metrics({"price_ratio": 2, "fees": 100, "average_capital": 10000, "days": 10})
        self.assertAlmostEqual(result["simple_fee_apr"], 0.365)
        with self.assertRaises((TypeError, subject.MetricError)):
            subject.defi_metrics({"price_ratio": 2, "fees": 100})
        with self.assertRaisesRegex(subject.MetricError, "price_ratio"):
            subject.defi_metrics({"price_ratio": 0})


class MetricDispatcherAndCliTests(unittest.TestCase):
    def test_dispatcher_success_and_unknown_operation(self) -> None:
        response = subject.calculate({"operation": "defi_metrics", "price_ratio": 1})
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["operation"], "defi_metrics")
        with self.assertRaisesRegex(subject.MetricError, "operation must be one of"):
            subject.calculate({"operation": "unknown"})

    def run_main(self, argv: list[str]) -> tuple[int, str]:
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["finance_metrics.py", *argv]), contextlib.redirect_stdout(output):
            code = subject.main()
        return code, output.getvalue()

    def test_main_stdout_output_file_and_error_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.json"
            valid.write_text(json.dumps({"operation": "defi_metrics", "price_ratio": 1}), encoding="utf-8")
            code, rendered = self.run_main([str(valid)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(rendered)["status"], "ok")

            destination = root / "result.json"
            code, rendered = self.run_main([str(valid), "--output", str(destination)])
            self.assertEqual(code, 0)
            self.assertEqual(rendered, "")
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["status"], "ok")

            cases = {
                "array.json": "[]",
                "invalid.json": "{",
            }
            for name, content in cases.items():
                path = root / name
                path.write_text(content, encoding="utf-8")
                with self.subTest(name=name):
                    code, rendered = self.run_main([str(path)])
                    self.assertEqual(code, 2)
                    self.assertEqual(json.loads(rendered)["status"], "error")
            code, rendered = self.run_main([str(root / "missing.json")])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(rendered)["status"], "error")


if __name__ == "__main__":
    unittest.main()
