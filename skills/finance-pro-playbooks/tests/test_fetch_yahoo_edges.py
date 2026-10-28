"""High-yield boundary coverage for the Yahoo Finance source adapter."""

from __future__ import annotations

import contextlib
import io
import json
import signal
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
import fetch_yahoo_finance as subject  # noqa: E402


class YahooAdapterUtilityTests(unittest.TestCase):
    def test_epoch_raw_safe_and_source_helpers_cover_edge_values(self) -> None:
        self.assertIsNone(subject.epoch_to_iso(True))
        self.assertIsNone(subject.epoch_to_iso("not-a-number"))
        self.assertEqual(subject.epoch_to_iso(0), "1970-01-01T00:00:00Z")
        self.assertEqual(
            subject.raw_value({"value": {"raw": 2}, "rows": [{"raw": 3}, 4]}),
            {"value": 2, "rows": [3, 4]},
        )
        self.assertIsNone(subject.safe_value("not-a-list", 0))
        self.assertIsNone(subject.safe_value([1], 1))
        self.assertEqual(subject.safe_value([{"raw": 7}], 0), 7)
        self.assertIn("%5EGSPC", subject.source_url("^GSPC", "chart"))
        self.assertEqual(subject.source_ref("***", "chart", "2026-01-02T03:04:05Z"), "yf-chart-instrument-20260102030405")

    def test_epoch_to_iso_unrepresentable_values_fail_closed(self) -> None:
        for value in (10**1000, float("inf"), float("-inf"), float("nan")):
            with self.subTest(value=value):
                self.assertIsNone(subject.epoch_to_iso(value))

    def test_provider_deadline_disabled_and_timeout_handler(self) -> None:
        with subject.provider_deadline(0):
            pass
        with (
            mock.patch.object(subject.signal, "getsignal", return_value="previous"),
            mock.patch.object(subject.signal, "signal") as signal_mock,
            mock.patch.object(subject.signal, "setitimer") as timer_mock,
        ):
            with self.assertRaises(subject.ProviderTimeoutError):
                with subject.provider_deadline(1.25):
                    handler = signal_mock.call_args_list[0].args[1]
                    handler(signal.SIGALRM, None)
            self.assertEqual(timer_mock.call_args_list[0].args, (signal.ITIMER_REAL, 1.25))
            self.assertEqual(timer_mock.call_args_list[-1].args, (signal.ITIMER_REAL, 0))
            self.assertEqual(signal_mock.call_args_list[-1].args, (signal.SIGALRM, "previous"))

    def test_write_json_stdout_and_atomic_file_output(self) -> None:
        payload = {"status": "ok", "value": "测试"}
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            subject.write_json(None, payload)
        self.assertEqual(json.loads(buffer.getvalue()), payload)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "artifact.json"
            subject.write_json(path, payload)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)

    def test_rate_limit_disabled_invalid_state_and_sleeping_state(self) -> None:
        with mock.patch.object(subject.time, "sleep") as sleep_mock:
            subject.wait_for_rate_limit(0)
            sleep_mock.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            state.write_text("invalid\n", encoding="utf-8")
            with mock.patch.object(subject.time, "time", side_effect=[100.0, 100.0]), mock.patch.object(
                subject.time, "sleep"
            ) as sleep_mock:
                subject.wait_for_rate_limit(1.0, state)
            sleep_mock.assert_not_called()
            self.assertEqual(state.read_text(encoding="utf-8"), "100.000000\n")
            state.write_text("100.0\n", encoding="utf-8")
            with mock.patch.object(subject.time, "time", side_effect=[100.25, 100.25]), mock.patch.object(
                subject.time, "sleep"
            ) as sleep_mock:
                subject.wait_for_rate_limit(1.0, state)
            sleep_mock.assert_called_once_with(0.75)

    def test_load_client_class_missing_runtime_and_import_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with mock.patch.object(subject, "RUNTIME_DIR", missing):
                client, error = subject.load_client_class()
            self.assertIsNone(client)
            self.assertIn("runtime not found", error)

            runtime = Path(directory) / "runtime"
            runtime.mkdir()
            original_import = __import__

            def reject_data_api(name: str, *args, **kwargs):
                if name == "data_api":
                    raise ImportError("unavailable")
                return original_import(name, *args, **kwargs)

            with mock.patch.object(subject, "RUNTIME_DIR", runtime), mock.patch("builtins.__import__", side_effect=reject_data_api):
                client, error = subject.load_client_class()
            self.assertIsNone(client)
            self.assertIn("Unable to import", error)


class YahooQueryAndNormalizerTests(unittest.TestCase):
    @staticmethod
    def args(*values: str):
        return subject.build_parser().parse_args(list(values))

    def test_build_query_accepts_periods_region_language_and_prepost(self) -> None:
        args = self.args(
            "chart",
            "--symbol",
            "  AAPL  ",
            "--region",
            "US",
            "--lang",
            "en-US",
            "--interval",
            "1h",
            "--period1",
            "1",
            "--period2",
            "2",
            "--include-pre-post",
            "--timeout",
            "120",
            "--min-interval",
            "60",
        )
        self.assertEqual(
            subject.build_query(args),
            {
                "symbol": "AAPL",
                "region": "US",
                "lang": "en-US",
                "interval": "1h",
                "period1": 1,
                "period2": 2,
                "includePrePost": True,
                "includeAdjustedClose": True,
            },
        )

    def test_build_query_rejects_all_parameter_boundaries(self) -> None:
        cases = [
            (("chart", "--symbol", ""), "--symbol"),
            (("chart", "--symbol", "A" * 65), "--symbol"),
            (("chart", "--symbol", "BAD SYMBOL"), "--symbol"),
            (("chart", "--symbol", "AAPL", "--timeout", "0"), "--timeout"),
            (("chart", "--symbol", "AAPL", "--timeout", "121"), "--timeout"),
            (("chart", "--symbol", "AAPL", "--min-interval", "-1"), "--min-interval"),
            (("chart", "--symbol", "AAPL", "--min-interval", "61"), "--min-interval"),
            (("profile", "--symbol", "AAPL", "--region", "U5"), "--region"),
            (("profile", "--symbol", "AAPL", "--lang", "en_US"), "--lang"),
            (("chart", "--symbol", "AAPL", "--interval", ""), "--interval"),
            (("chart", "--symbol", "AAPL", "--period1", "1"), "both --period1 and --period2"),
            (("chart", "--symbol", "AAPL", "--period1", "-1", "--period2", "2"), "timestamps"),
            (("chart", "--symbol", "AAPL", "--period1", "2", "--period2", "2"), "timestamps"),
            (("chart", "--symbol", "AAPL", "--range", ""), "--range"),
        ]
        for argv, fragment in cases:
            with self.subTest(argv=argv):
                with self.assertRaisesRegex(ValueError, fragment):
                    subject.build_query(self.args(*argv))

    def test_provider_error_and_first_result_shapes(self) -> None:
        self.assertEqual(subject.provider_error([])["code"], "invalid_response")
        self.assertEqual(subject.provider_error({"error": "direct"})["code"], "provider_error")
        for name in ("chart", "quoteSummary", "finance"):
            self.assertEqual(subject.provider_error({name: {"error": "nested"}})["code"], "provider_error")
        self.assertIsNone(subject.provider_error({"chart": {"error": None}}))
        self.assertEqual(subject.first_result({"chart": {"result": [{"x": 1}]}}, ("chart",)), {"x": 1})
        self.assertEqual(subject.first_result({"chart": {"result": {"x": 2}}}, ("chart",)), {"x": 2})
        self.assertEqual(subject.first_result({"result": [{"x": 3}]}, ("chart",)), {"x": 3})
        self.assertEqual(subject.first_result({"result": {"x": 4}}, ("chart",)), {"x": 4})
        self.assertIsNone(subject.first_result({"result": []}, ("chart",)))

    def test_chart_normalizer_empty_partial_and_event_list_branches(self) -> None:
        normalized, observed, warnings = subject.normalize_chart({})
        self.assertIsNone(normalized)
        self.assertIsNone(observed)
        self.assertTrue(warnings)
        response = {
            "chart": {
                "result": {
                    "meta": {},
                    "timestamp": [0],
                    "indicators": {"quote": [{"close": [None]}]},
                    "events": {
                        "capitalGains": [{"amount": {"raw": 1}, "date": {"raw": 0}}, "drop"],
                        "splits": {"s1": {"date": {"raw": 0}, "splitRatio": "2:1"}},
                    },
                }
            }
        }
        normalized, observed, warnings = subject.normalize_chart(response)
        self.assertEqual(observed, "1970-01-01T00:00:00Z")
        self.assertTrue(any("missing close" in warning for warning in warnings))
        self.assertEqual(normalized["events"]["capitalGains"][0], {"amount": 1, "date": 0})
        self.assertEqual(normalized["events"]["splits"]["s1"], {"date": 0, "splitRatio": "2:1"})

    def test_other_normalizers_cover_no_result_empty_and_undated_paths(self) -> None:
        for normalizer in (
            subject.normalize_profile,
            subject.normalize_holders,
            subject.normalize_insights,
            subject.normalize_filings,
        ):
            normalized, observed, warnings = normalizer({})
            self.assertIsNone(normalized)
            self.assertIsNone(observed)
            self.assertTrue(warnings)

        normalized, observed, warnings = subject.normalize_profile({"quoteSummary": {"result": {"summaryProfile": {}}}})
        self.assertIsNone(normalized)
        self.assertIsNone(observed)
        self.assertIn("no approved fields", warnings[0])

        holders_response = {"quoteSummary": {"result": {"majorHoldersBreakdown": {"institutionsCount": 1}}}}
        normalized, observed, warnings = subject.normalize_holders(holders_response)
        self.assertEqual(normalized["major_holders"], {"institutionsCount": 1})
        self.assertIsNone(observed)
        self.assertTrue(any("timestamp" in warning for warning in warnings))
        empty_holders = {"quoteSummary": {"result": {"institutionOwnership": {"ownershipList": ["drop"]}}}}
        self.assertIsNone(subject.normalize_holders(empty_holders)[0])

        insights_response = {"finance": {"result": {"companySnapshot": {"sectorInfo": "Technology"}, "events": ["drop"]}}}
        normalized, observed, warnings = subject.normalize_insights(insights_response)
        self.assertEqual(normalized["company_snapshot"]["sector_info"], "Technology")
        self.assertIsNone(observed)
        self.assertTrue(any("timestamp" in warning for warning in warnings))
        self.assertIsNone(subject.normalize_insights({"finance": {"result": {}}})[0])

        filings_response = {
            "quoteSummary": {
                "result": {
                    "secFilings": {
                        "filings": ["drop", {"date": "2026-01-01", "exhibits": ["drop", {"type": "EX-1"}]}]
                    }
                }
            }
        }
        normalized, observed, warnings = subject.normalize_filings(filings_response)
        self.assertEqual(normalized["filings"][0]["exhibits"], [{"type": "EX-1"}])
        self.assertIsNone(observed)
        self.assertTrue(any("timestamp" in warning for warning in warnings))
        self.assertIsNone(subject.normalize_filings({"quoteSummary": {"result": {"secFilings": {"filings": ["drop"]}}}})[0])

    def test_normalize_response_dispatches_every_operation_and_unknown(self) -> None:
        with mock.patch.object(subject, "normalize_chart", return_value=({"x": 1}, None, [])) as chart_mock:
            self.assertEqual(subject.normalize_response({}, "chart")[0], {"x": 1})
            chart_mock.assert_called_once()
        for operation, name in (
            ("profile", "normalize_profile"),
            ("holders", "normalize_holders"),
            ("insights", "normalize_insights"),
            ("filings", "normalize_filings"),
        ):
            with self.subTest(operation=operation), mock.patch.object(subject, name, return_value=({"x": 1}, None, [])) as target:
                self.assertEqual(subject.normalize_response({}, operation)[0], {"x": 1})
                target.assert_called_once()
        normalized, observed, warnings = subject.normalize_response({}, "unknown")
        self.assertIsNone(normalized)
        self.assertIsNone(observed)
        self.assertIn("Unsupported", warnings[0])


class YahooFetchStateMachineTests(unittest.TestCase):
    @staticmethod
    def args(*values: str):
        return subject.build_parser().parse_args(list(values))

    def chart_args(self):
        return self.args("chart", "--symbol", "AAPL", "--min-interval", "0", "--timeout", "1")

    @staticmethod
    def complete_chart() -> dict:
        return {
            "chart": {
                "result": {
                    "meta": {"regularMarketTime": {"raw": 1720000000}},
                    "timestamp": [1720000000],
                    "indicators": {
                        "quote": [{"open": [1], "high": [2], "low": [0.5], "close": [1.5], "volume": [10]}]
                    },
                }
            }
        }

    def test_runtime_unavailable_and_initialization_failure(self) -> None:
        with mock.patch.object(subject, "load_client_class", return_value=(None, "missing runtime")):
            artifact = subject.fetch(self.chart_args())
        self.assertEqual(artifact["status"], "blocked")
        self.assertEqual(artifact["error"]["code"], "runtime_unavailable")

        class BrokenClient:
            def __init__(self) -> None:
                raise RuntimeError("initialization failed")

        artifact = subject.fetch(self.chart_args(), client_class=BrokenClient)
        self.assertEqual(artifact["status"], "blocked")
        self.assertEqual(artifact["error"]["code"], "runtime_initialization_failed")

    def test_provider_call_failures_provider_errors_and_invalid_response(self) -> None:
        class RaisingClient:
            def call_api(self, _operation: str, query: dict) -> dict:
                raise RuntimeError("network failed")

        artifact = subject.fetch(self.chart_args(), client_class=RaisingClient)
        self.assertEqual(artifact["error"]["code"], "provider_call_failed")

        responses = [
            {"error": "direct"},
            {"chart": {"error": "nested"}},
            ["not-an-object"],
        ]
        for response in responses:
            class Client:
                def call_api(self, _operation: str, query: dict):
                    return response

            with self.subTest(response=response):
                artifact = subject.fetch(self.chart_args(), client_class=Client)
                self.assertEqual(artifact["status"], "failed")
                self.assertIn(artifact["error"]["code"], {"provider_error", "invalid_response"})

    def test_empty_partial_and_ok_statuses(self) -> None:
        responses = [
            ({"chart": {"result": []}}, "failed", "empty_result"),
            ({"chart": {"result": {"meta": {}}}}, "partial", None),
            (self.complete_chart(), "ok", None),
        ]
        for response, expected_status, expected_error in responses:
            class Client:
                def call_api(self, _operation: str, query: dict):
                    return response

            with self.subTest(expected_status=expected_status):
                artifact = subject.fetch(self.chart_args(), client_class=Client)
                self.assertEqual(artifact["status"], expected_status)
                if expected_error:
                    self.assertEqual(artifact["error"]["code"], expected_error)
                else:
                    self.assertIsNone(artifact["error"])

    def test_invalid_symbol_fallback_and_equity_only_boundary(self) -> None:
        artifact = subject.fetch(self.args("chart", "--symbol", "A" * 65), client_class=mock.Mock)
        self.assertEqual(artifact["symbol"], "invalid-symbol")
        self.assertEqual(artifact["error"]["code"], "invalid_request")
        artifact = subject.fetch(
            self.args("filings", "--symbol", "BTC-USD", "--asset-class", "crypto", "--min-interval", "0"),
            client_class=mock.Mock,
        )
        self.assertEqual(artifact["error"]["code"], "unsupported_asset_operation")

    def test_main_maps_status_and_writes_output(self) -> None:
        for status, expected in (("ok", 0), ("partial", 0), ("failed", 1), ("blocked", 2), ("unknown", 1)):
            with self.subTest(status=status), mock.patch.object(subject, "fetch", return_value={"status": status}), mock.patch.object(
                subject, "write_json"
            ) as write_mock:
                code = subject.main(["chart", "--symbol", "AAPL", "--output", "artifact.json"])
                self.assertEqual(code, expected)
                self.assertEqual(write_mock.call_args.args[0], Path("artifact.json"))


if __name__ == "__main__":
    unittest.main()
