from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import _bootstrap  # noqa: E402,F401
import fetch_yahoo_finance as fetcher  # noqa: E402
import validate_yahoo_source as validator  # noqa: E402
from ensure_runtime import RuntimePreparationError  # noqa: E402


class YahooValidatorSemanticEdgeTests(unittest.TestCase):
    retrieved_at = "2026-07-29T08:00:00Z"
    data_as_of = "2026-07-29T07:59:00Z"

    def artifact(
        self,
        operation: str,
        data: object,
        *,
        status: str = "ok",
        warnings: list[str] | None = None,
        data_as_of: str | None = data_as_of,
    ) -> dict:
        return fetcher.base_artifact(
            status=status,
            symbol="AAPL",
            operation=operation,
            query={"symbol": "AAPL"},
            retrieved_at=self.retrieved_at,
            data_as_of=data_as_of,
            data=data,  # type: ignore[arg-type]
            warnings=[] if warnings is None else warnings,
            error=None,
        )

    def assert_error(self, errors: list[str], fragment: str) -> None:
        self.assertTrue(any(fragment in error for error in errors), (fragment, errors))

    def test_json_and_recursive_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            object_path = root / "object.json"
            object_path.write_text('{"ok": true}', encoding="utf-8")
            self.assertEqual(validator.load_json(object_path), {"ok": True})
            list_path = root / "list.json"
            list_path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                validator.load_json(list_path)
        self.assertEqual(validator.unexpected_keys([], {"a"}), [])
        self.assertEqual(validator.unexpected_keys({"b": 1, "a": 2}, {"a"}), ["b"])
        self.assertEqual(validator.recursive_keys({"a": [{"b": 1}, {"c": {"d": 2}}]}), {"a", "b", "c", "d"})
        errors: list[str] = []
        validator.append_unexpected(errors, {"bad": 1}, {"good"}, "data")
        self.assertEqual(errors, ["data contains non-whitelisted fields: bad."])

    def test_generic_status_time_query_and_source_rules(self) -> None:
        partial = self.artifact("chart", None, status="partial", warnings=[], data_as_of=None)
        partial["query"]["symbol"] = "MSFT"
        partial["source_manifest_entry"].update(
            {"title": "wrong title", "retrieved_at": "2020-01-01T00:00:00Z", "data_as_of": "2020-01-01T00:00:00Z"}
        )
        errors = validator.semantic_errors(partial)
        for fragment in (
            "partial artifact must include",
            "missing observation time",
            "query.symbol",
            "title must identify",
            "retrieved_at must match",
            "data_as_of must match",
            "chart artifact must contain an object",
        ):
            self.assert_error(errors, fragment)

        failed = self.artifact("profile", {"profile": {}}, status="failed")
        self.assert_error(validator.semantic_errors(failed), "must set data to null")

        explained = self.artifact(
            "profile",
            {"profile": {}, "price": {}, "quote_type": {}, "summary": {}},
            status="partial",
            warnings=["Provider omitted the observation timestamp."],
            data_as_of=None,
        )
        errors = validator.semantic_errors(explained)
        self.assertFalse(any("missing observation time" in error for error in errors), errors)

    def test_chart_contract_catches_meta_bars_events_and_unknown_fields(self) -> None:
        data = {
            "meta": {"symbol": "AAPL", "unknownMeta": 1},
            "bars": [{"timestamp": 1, "close": 100, "unknownBar": 2}],
            "events": {
                "dividends": {"1": {"amount": 0.2, "date": 1, "issuer": "bad"}},
                "splits": [{"date": 1, "splitRatio": "2:1", "note": "bad"}],
                "unknownEvent": {},
            },
            "unknownData": 3,
        }
        errors = validator.semantic_errors(self.artifact("chart", data))
        for fragment in ("unknownData", "unknownMeta", "unknownBar", "unknownEvent", "issuer", "note"):
            self.assert_error(errors, fragment)

        empty = self.artifact("chart", {"meta": {}, "bars": [], "events": None})
        errors = validator.semantic_errors(empty)
        self.assert_error(errors, "data.meta.symbol")
        self.assert_error(errors, "at least one OHLCV bar")

    def test_profile_contract_catches_top_level_and_nested_unknown_fields(self) -> None:
        errors = validator.semantic_errors(self.artifact("profile", []))
        self.assert_error(errors, "profile artifact must contain an object")
        data = {
            "profile": {"sector": "Technology", "phone": "bad"},
            "price": {"symbol": "AAPL", "secret": 1},
            "quote_type": {"symbol": "AAPL", "extra": 1},
            "summary": {"volume": 1, "extraSummary": 1},
            "extraData": 1,
        }
        errors = validator.semantic_errors(self.artifact("profile", data))
        for fragment in ("phone", "secret", "extra", "extraSummary", "extraData"):
            self.assert_error(errors, fragment)

    def test_holders_contract_catches_row_whitelists_and_personal_identifiers(self) -> None:
        errors = validator.semantic_errors(self.artifact("holders", []))
        self.assert_error(errors, "holders artifact must contain an object")
        private_email = "private" + "@" + "example.com"
        data = {
            "major_holders": {"institutionsCount": 1, "extra": 2},
            "institutional_holders": [{"organization": "Fund", "name": "Private", "extra": 1}],
            "fund_holders": [{"organization": "Fund", "address": "Private"}],
            "insider_positions": [{"relation": "Director", "email": private_email, "extra": 1}],
            "unknown": 1,
        }
        errors = validator.semantic_errors(self.artifact("holders", data))
        for fragment in ("data contains non-whitelisted", "data.major_holders", "institutional_holders", "fund_holders", "insider_positions"):
            self.assert_error(errors, fragment)
        self.assert_error(errors, "personal identifiers")
        self.assert_error(errors, "email")
        self.assert_error(errors, "name")

    def test_insights_contract_catches_all_nested_whitelists_and_report_metadata(self) -> None:
        errors = validator.semantic_errors(self.artifact("insights", []))
        self.assert_error(errors, "insights artifact must contain an object")
        data = {
            "instrument_info": {
                "key_technicals": {"provider": "P", "extraKey": 1},
                "technical_events": {
                    "provider": "P",
                    "shortTermOutlook": {"direction": "Bullish", "analystName": "Private"},
                    "intermediateTermOutlook": {"score": 1, "extraOutlook": 1},
                    "longTermOutlook": {"stateDescription": "Stable"},
                    "extraTechnical": 1,
                },
                "valuation": {"provider": "P", "reportTitle": "Private report"},
                "extraInstrument": 1,
            },
            "company_snapshot": {
                "company": {"hiring": 1, "extraScore": 2},
                "sector": {"hiring": 1, "extraSector": 2},
                "sector_info": "Tech",
                "extraSnapshot": 1,
            },
            "recommendation": {"rating": "BUY", "author": "Private"},
            "events": [{"eventType": "PriceCross", "title": "Private report"}],
            "reports": [{"headHtml": "full text"}],
        }
        errors = validator.semantic_errors(self.artifact("insights", data))
        for fragment in (
            "extraKey",
            "extraTechnical",
            "extraOutlook",
            "extraInstrument",
            "extraScore",
            "extraSector",
            "extraSnapshot",
            "data.recommendation",
            "data.events[0]",
            "report text and report metadata",
        ):
            self.assert_error(errors, fragment)

    def test_filings_contract_catches_empty_rows_and_exhibit_fields(self) -> None:
        errors = validator.semantic_errors(self.artifact("filings", []))
        self.assert_error(errors, "filings artifact must contain an object")
        empty_errors = validator.semantic_errors(self.artifact("filings", {"filings": []}))
        self.assert_error(empty_errors, "at least one filing row")
        data = {
            "filings": [
                {
                    "date": "2026-07-01",
                    "type": "10-Q",
                    "title": "Quarterly report",
                    "edgarUrl": "https://www.sec.gov/example",
                    "rawText": "bad",
                    "exhibits": [{"type": "EX-99", "url": "https://www.sec.gov/exhibit", "description": "bad"}],
                }
            ],
            "extra": 1,
        }
        errors = validator.semantic_errors(self.artifact("filings", data))
        for fragment in ("data contains non-whitelisted", "data.filings[0]", "data.filings[0].exhibits[0]"):
            self.assert_error(errors, fragment)


class YahooValidatorCliEdgeTests(unittest.TestCase):
    def test_load_jsonschema_prepares_runtime(self) -> None:
        with mock.patch.object(validator, "ensure_runtime") as ensure:
            module = validator.load_jsonschema()
        ensure.assert_called_once_with()
        self.assertTrue(hasattr(module, "Draft202012Validator"))

    def run_main(self, result_or_error: object) -> tuple[int, dict]:
        output = io.StringIO()
        side_effect = result_or_error if isinstance(result_or_error, BaseException) else None
        return_value = None if side_effect else result_or_error
        with mock.patch.object(validator, "validate", return_value=return_value, side_effect=side_effect), contextlib.redirect_stdout(output):
            code = validator.main(["artifact.json"])
        return code, json.loads(output.getvalue())

    def test_main_valid_invalid_blocked_and_unexpected_error_exit_codes(self) -> None:
        code, payload = self.run_main({"status": "valid", "artifact": "artifact.json", "errors": [], "warnings": []})
        self.assertEqual((code, payload["status"]), (0, "valid"))
        code, payload = self.run_main({"status": "invalid", "artifact": "artifact.json", "errors": ["bad"], "warnings": []})
        self.assertEqual((code, payload["status"]), (1, "invalid"))
        code, payload = self.run_main(RuntimePreparationError("runtime unavailable"))
        self.assertEqual((code, payload["status"]), (2, "blocked"))
        code, payload = self.run_main(ValueError("malformed artifact"))
        self.assertEqual((code, payload["status"]), (1, "invalid"))
        self.assertIn("malformed artifact", payload["errors"][0])

    def test_validate_merges_schema_and_semantic_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "artifact.json"
            path.write_text('{"status": "partial"}', encoding="utf-8")

            class SchemaError:
                message = "schema failure"
                path: list[str] = []

            schema_api = mock.Mock()
            schema_api.FormatChecker.return_value = object()
            schema_api.Draft202012Validator.return_value.iter_errors.return_value = [SchemaError()]
            with mock.patch.object(validator, "SCHEMA_PATH", path), mock.patch.object(validator, "load_jsonschema", return_value=schema_api):
                result = validator.validate(path)
            self.assertEqual(result["status"], "invalid")
            self.assertIn("schema failure", result["errors"])
            self.assertTrue(any("partial artifact" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
