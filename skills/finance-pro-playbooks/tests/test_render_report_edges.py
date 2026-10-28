"""Edge and CLI coverage for the deterministic Markdown report renderer."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

TEST_ROOT = Path(__file__).resolve().parent
SCRIPT_ROOT = TEST_ROOT.parent / "scripts"
for path in (SCRIPT_ROOT, TEST_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import _bootstrap  # noqa: E402,F401
import render_report as subject  # noqa: E402
from result_fixtures import valid_result  # noqa: E402


def materials_review() -> dict:
    return {
        "task_type": "pre-ic-consistency-review",
        "materials_reviewed": [
            {"source_ref": "src-1", "role": "primary model", "version_or_date": "2026-07-29"}
        ],
        "verified_fact_refs": ["src-1"],
        "scorecard": {"overall": 82, "scale": 100},
        "inconsistencies": [
            {
                "topic": "Revenue",
                "sources": ["src-1", "src-2"],
                "description": "Versions differ",
                "severity": "medium",
                "recommended_resolution": "Reconcile against signed statements",
            }
        ],
        "red_flags": [
            {"flag": "Unverified forecast", "evidence_refs": ["src-1"], "impact": "Valuation uncertainty", "status": "open"}
        ],
        "open_questions": [
            {"question": "Which forecast is approved?", "owner": "Deal team", "due": "2026-08-01", "priority": "high"}
        ],
        "deliverables": [
            {"name": "Consistency review", "format": "markdown", "path": "artifacts/review.md", "status": "draft"}
        ],
        "publication_status": "draft",
    }


class MaterialsReviewRenderingTests(unittest.TestCase):
    def test_optional_materials_review_renders_all_sections_and_escapes_tables(self) -> None:
        result = valid_result("corporate-finance")
        review = materials_review()
        review["inconsistencies"][0]["topic"] = "Revenue | EBITDA"
        rendered = "\n".join(subject._render_materials_review(review, result))
        for heading in (
            "Existing Materials Handling",
            "Materials Reviewed",
            "Verified Facts",
            "Scoring and Screening Conclusions",
            "Document Inconsistencies",
            "Red Flags",
            "Open Questions and Follow-up Due Diligence",
            "Deliverables",
            "Publication Status and Authorization",
        ):
            self.assertIn(heading, rendered)
        self.assertIn("Revenue \\| EBITDA", rendered)
        self.assertIn("external_side_effect", rendered.lower().replace(" ", "_"))

    def test_corporate_renderer_appends_materials_review_only_when_present(self) -> None:
        without_review = valid_result("corporate-finance")
        self.assertNotIn("Existing Materials Handling", "\n".join(subject._render_corporate_finance(without_review)))
        with_review = deepcopy(without_review)
        with_review["payload"]["materials_review"] = materials_review()
        rendered = "\n".join(subject._render_corporate_finance(with_review))
        self.assertIn("Existing Materials Handling", rendered)
        self.assertIn("pre-ic-consistency-review", rendered)


class RenderReportTemplateTests(unittest.TestCase):
    def test_missing_template_raises_file_not_found(self) -> None:
        result = valid_result("equity-research")
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(subject, "ROOT", Path(directory)), mock.patch.object(
            subject, "ensure_runtime"
        ):
            with self.assertRaisesRegex(FileNotFoundError, "missing template"):
                subject.render_report(result)

    def test_template_missing_required_heading_is_rejected(self) -> None:
        result = valid_result("equity-research")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "templates" / "equity-research.md"
            template.parent.mkdir(parents=True)
            template.write_text(subject.IMPORTANT_NOTICE_BLOCK + "\n", encoding="utf-8")
            with mock.patch.object(subject, "ROOT", root), mock.patch.object(subject, "ensure_runtime"):
                with self.assertRaisesRegex(ValueError, "template missing required heading"):
                    subject.render_report(result)

    def test_valid_report_is_deterministic_and_ends_with_canonical_notice(self) -> None:
        result = valid_result("corporate-finance")
        result["payload"]["materials_review"] = materials_review()
        with mock.patch.object(subject, "ensure_runtime"):
            first = subject.render_report(result)
            second = subject.render_report(result)
        self.assertEqual(first, second)
        self.assertTrue(first.rstrip().endswith(subject.IMPORTANT_NOTICE_BLOCK))
        self.assertIn("Existing Materials Handling", first)


class RenderReportCliTests(unittest.TestCase):
    @staticmethod
    def run_main(argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", ["render_report.py", *argv]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = subject.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_main_stdout_and_validation_output_success(self) -> None:
        data = valid_result("equity-research")
        report = {"status": "passed", "errors": [], "warnings": []}
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(subject, "_load_json", return_value=data), mock.patch.object(
            subject, "validate_result", return_value=report
        ), mock.patch.object(subject, "render_report", return_value="# Report\n"):
            validation = Path(directory) / "validation.json"
            code, stdout, stderr = self.run_main(["result.json", "--validation-output", str(validation)])
            written_report = json.loads(validation.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "# Report\n")
        self.assertEqual(stderr, "")
        self.assertEqual(written_report, report)

    def test_main_writes_nested_output_path(self) -> None:
        data = valid_result("equity-research")
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(subject, "_load_json", return_value=data), mock.patch.object(
            subject, "validate_result", return_value={"status": "passed"}
        ), mock.patch.object(subject, "render_report", return_value="# Report\n"):
            destination = Path(directory) / "nested" / "report.md"
            code, stdout, stderr = self.run_main(["result.json", "--output", str(destination)])
            self.assertEqual(destination.read_text(encoding="utf-8"), "# Report\n")
        self.assertEqual((code, stdout, stderr), (0, "", ""))

    def test_main_stops_on_validation_failure(self) -> None:
        failed = {"status": "failed", "errors": ["bad result"]}
        with mock.patch.object(subject, "_load_json", return_value={}), mock.patch.object(
            subject, "validate_result", return_value=failed
        ), mock.patch.object(subject, "render_report") as render_mock:
            code, stdout, stderr = self.run_main(["result.json"])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr), failed)
        render_mock.assert_not_called()

    def test_main_maps_runtime_block_and_generic_failure_to_exit_two(self) -> None:
        runtime_error = subject.RuntimePreparationError("runtime unavailable", state={"status": "blocked"})
        with mock.patch.object(subject, "_load_json", return_value={}), mock.patch.object(
            subject, "validate_result", return_value={"status": "passed"}
        ), mock.patch.object(subject, "render_report", side_effect=runtime_error):
            code, stdout, stderr = self.run_main(["result.json"])
        self.assertEqual((code, stdout), (2, ""))
        runtime_payload = json.loads(stderr)
        self.assertEqual(runtime_payload["status"], "blocked")
        self.assertEqual(runtime_payload["runtime"]["status"], "blocked")

        with mock.patch.object(subject, "_load_json", side_effect=ValueError("invalid input")):
            code, stdout, stderr = self.run_main(["result.json"])
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("render failed: invalid input", stderr)


if __name__ == "__main__":
    unittest.main()
