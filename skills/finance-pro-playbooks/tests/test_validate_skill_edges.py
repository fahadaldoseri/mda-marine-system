from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import _bootstrap  # noqa: E402,F401
import validate_skill as subject  # noqa: E402


class FrontmatterAndScanTests(unittest.TestCase):
    def test_parse_frontmatter_success_and_failures(self) -> None:
        metadata, body = subject.parse_frontmatter("---\nname: 'skill'\ndescription: \"desc\"\n---\nBody\n")
        self.assertEqual(metadata, {"name": "skill", "description": "desc"})
        self.assertEqual(body, "Body\n")
        for text, fragment in (
            ("name: skill\n", "must start"),
            ("---\nname: skill\n", "not closed"),
            ("---\ninvalid\n---\n", "invalid frontmatter line"),
        ):
            with self.subTest(fragment=fragment), self.assertRaisesRegex(ValueError, fragment):
                subject.parse_frontmatter(text)

    def test_read_json_records_invalid_and_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            bad = root / "bad.json"
            bad.write_text("{", encoding="utf-8")
            for path in (bad, root / "missing.json"):
                errors: list[str] = []
                self.assertIsNone(subject._read_json(path, errors, root))
                self.assertTrue(errors)

    def test_scan_file_detects_secret_email_syntax_and_link_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            existing = root / "existing.md"
            existing.write_text("# Existing\n", encoding="utf-8")
            python_file = root / "bad.py"
            assignment_name = "to" + "ken"
            assignment_value = "abcdefghijkl" + "mnop"
            python_file.write_text(f"{assignment_name} = '{assignment_value}'\ndef broken(:\n", encoding="utf-8")
            email = "test" + "@" + "example.com"
            mail_target = "a" + "@" + "example.com"
            markdown = root / "doc.md"
            markdown.write_text(
                f"Contact {email}\n"
                "[good](existing.md) [broken](missing.md) [escape](../outside.md)\n"
                f"[web](https://example.com) [mail](mailto:{mail_target}) [anchor](#section)\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            warnings: list[str] = []
            subject._scan_file(python_file, root, errors, warnings)
            subject._scan_file(markdown, root, errors, warnings)
            rendered = "\n".join(errors)
            self.assertIn("possible hardcoded secret", rendered)
            self.assertIn("Python syntax error", rendered)
            self.assertIn("broken local link", rendered)
            self.assertIn("link escapes Skill root", rendered)
            self.assertTrue(any(email in warning for warning in warnings))

    def test_scan_file_ignores_unreadable_content(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        path = mock.Mock(spec=Path)
        path.read_text.side_effect = OSError("unreadable")
        subject._scan_file(path, Path("/tmp"), errors, warnings)
        self.assertEqual((errors, warnings), ([], []))


class DomainAndCatalogTests(unittest.TestCase):
    def test_domain_document_reports_structure_dependency_and_marker_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            refs = Path(temporary_directory)
            (refs / "equity-research.md").write_text(
                "# Equity\n"
                "## Common Dependency Declaration\n"
                "## Output Contract\n"
                "| Required | [`extra.md`](extra.md) |\n"
                "| Conditional | [`wrong.md`](wrong.md) |\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            with mock.patch.object(subject, "DOMAIN_REQUIRED_REFERENCES", {"equity-research.md": {"required.md"}}), mock.patch.object(
                subject, "DOMAIN_CONDITIONAL_REFERENCES", {"equity-research.md": {"conditional.md"}}
            ):
                self.assertEqual(subject._validate_domain_documents(refs, errors), 1)
            rendered = "\n".join(errors)
            for fragment in (
                "duplicate output contract",
                "output format section",
                "missing required dependency",
                "unexpected required dependency",
                "missing conditional dependency",
                "unexpected conditional dependency",
                "missing output format marker",
            ):
                self.assertIn(fragment, rendered)

    def make_catalog_root(self, root: Path) -> Path:
        plugin = root / "references" / "corporate-finance"
        playbooks = plugin / "playbooks" / "g"
        playbooks.mkdir(parents=True)
        (playbooks / "_overview.md").write_text("# Overview\n", encoding="utf-8")
        (playbooks / "task.md").write_text("# Test Task\n", encoding="utf-8")
        (root / "references" / "format.md").write_text("# Format\n", encoding="utf-8")
        catalog = {
            "catalog_version": "1.0",
            "primary_module": "corporate-finance",
            "format_registry": {"excel": "references/format.md"},
            "tasks": [
                {
                    "id": "task",
                    "label": "Test Task",
                    "group": "g",
                    "playbook": "references/corporate-finance/playbooks/g/task.md",
                    "playbook_overview": "references/corporate-finance/playbooks/g/_overview.md",
                    "formats": ["excel"],
                    "artifacts": ["model"],
                    "patterns": ["test task"],
                }
            ],
        }
        (plugin / "task-catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
        return plugin / "task-catalog.json"

    def test_task_catalog_minimal_valid_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.make_catalog_root(root)
            errors: list[str] = []
            warnings: list[str] = []
            with mock.patch.object(subject, "EXPECTED_TASK_COUNT", 1), mock.patch.object(
                subject, "EXPECTED_PLUGIN_GROUPS", {"g"}
            ), mock.patch.object(subject, "EXPECTED_FORMAT_KEYS", {"excel"}):
                result = subject._validate_task_catalog(root, errors, warnings)
            self.assertEqual(result, (1, 1, 1, {"task"}))
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_task_catalog_reports_all_malformed_task_branches_and_orphans(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            catalog_path = self.make_catalog_root(root)
            orphan = root / "references" / "corporate-finance" / "playbooks" / "g" / "orphan.md"
            orphan.write_text("# Orphan\n", encoding="utf-8")
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog.update({"catalog_version": "bad", "primary_module": "bad", "format_registry": {"unknown": 1}})
            catalog["tasks"] = [
                "not-an-object",
                {"id": "missing-fields"},
                {
                    "id": "Bad ID",
                    "label": "Missing Label",
                    "group": "bad-group",
                    "playbook": "wrong.md",
                    "playbook_overview": "wrong-overview.md",
                    "formats": ["mystery"],
                    "artifacts": [],
                    "patterns": ["("],
                },
            ]
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            errors: list[str] = []
            warnings: list[str] = []
            with mock.patch.object(subject, "EXPECTED_TASK_COUNT", 1), mock.patch.object(
                subject, "EXPECTED_PLUGIN_GROUPS", {"g"}
            ), mock.patch.object(subject, "EXPECTED_FORMAT_KEYS", {"excel"}):
                subject._validate_task_catalog(root, errors, warnings)
            rendered = "\n".join(errors)
            for fragment in (
                "catalog_version",
                "primary_module",
                "format registry",
                "format resource missing",
                "task count",
                "must be an object",
                "missing fields",
                "lowercase kebab-case",
                "playbook must be task-level",
                "playbook_overview",
                "unknown keys",
                "non-empty string array",
                "invalid route pattern",
                "groups mismatch",
                "not referenced by task catalog",
            ):
                self.assertIn(fragment, rendered)

    def test_task_catalog_missing_invalid_and_non_list_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            errors: list[str] = []
            self.assertEqual(subject._validate_task_catalog(root, errors, []), (0, 0, 0, set()))
            self.assertIn("catalog is missing", errors[0])
            catalog = root / "references" / "corporate-finance" / "task-catalog.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text("[]", encoding="utf-8")
            errors = []
            self.assertEqual(subject._validate_task_catalog(root, errors, []), (0, 0, 0, set()))
            catalog.write_text(json.dumps({"format_registry": {}, "tasks": {}}), encoding="utf-8")
            errors = []
            subject._validate_task_catalog(root, errors, [])
            self.assertTrue(any("tasks must be a list" in error for error in errors))


class SchemaModuleAndAuthorityTests(unittest.TestCase):
    def test_schema_missing_and_mismatch_branches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            schema = root / "schema.json"
            errors: list[str] = []
            subject._validate_schema(schema, {"a"}, {"task"}, errors, root)
            self.assertIn("Schema is missing", errors[0])
            schema.write_text(
                json.dumps(
                    {
                        "properties": {"schema_version": {"const": "bad"}},
                        "allOf": [],
                        "$defs": {"module": {"enum": ["wrong"]}, "corporateFinanceTaskId": {"enum": ["wrong"]}},
                    }
                ),
                encoding="utf-8",
            )
            errors = []
            subject._validate_schema(schema, {"a"}, {"task"}, errors, root)
            rendered = "\n".join(errors)
            for fragment in ("schema version", "map exactly nine", "module enum", "task IDs", "corporateFinancePayload"):
                self.assertIn(fragment, rendered)

    def test_metric_authority_missing_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            errors: list[str] = []
            subject._validate_metric_authority(root, errors)
            self.assertTrue(any("metric authority files missing" in error for error in errors))
            appendix = root / "references" / "corporate-finance" / "formats" / "metric_disambiguation.md"
            appendix.parent.mkdir(parents=True)
            appendix.write_text("# Appendix\n\n## Section A\nNo authority link.\n", encoding="utf-8")
            dictionary = root / "references" / "metric-dictionary.md"
            dictionary.write_text("# Dictionary\n", encoding="utf-8")
            errors = []
            subject._validate_metric_authority(root, errors)
            rendered = "\n".join(errors)
            self.assertIn("normative section", rendered)
            self.assertIn("lacks authority link", rendered)

    def test_module_catalog_invalid_shapes_and_cross_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            catalog_path = root / "references" / "module-catalog.json"
            catalog_path.parent.mkdir(parents=True)
            catalog = {
                "modules": {
                    "equity-research": {
                        "reference": "missing.md",
                        "patterns": ["("],
                        "required_references": ["missing.md"],
                        "conditional_references": {"unknown": ["missing.md"]},
                    },
                    "fund-etf": "not-an-object",
                },
                "dependency_order": [],
                "primary_priority": "bad",
                "merge_rules": {},
                "out_of_scope_patterns": "bad",
            }
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            errors: list[str] = []
            with mock.patch.object(subject, "REQUIRED_TEMPLATES", {"equity-research.md", "fund-etf.md"}):
                self.assertEqual(subject._validate_module_catalog(root, errors), 2)
            rendered = "\n".join(errors)
            for fragment in (
                "dependency_order",
                "primary_priority",
                "boundary_rule",
                "out_of_scope_patterns",
                "reference is missing",
                "invalid module pattern",
                "required_references contains missing",
                "unknown condition flag",
                "conditional_references.unknown contains missing",
                "diverges from domain declaration",
                "must be an object",
            ):
                self.assertIn(fragment, rendered)

    def test_module_catalog_missing_invalid_and_modules_not_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            errors: list[str] = []
            self.assertEqual(subject._validate_module_catalog(root, errors), 0)
            catalog = root / "references" / "module-catalog.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text("[]", encoding="utf-8")
            errors = []
            self.assertEqual(subject._validate_module_catalog(root, errors), 0)
            catalog.write_text(json.dumps({"modules": []}), encoding="utf-8")
            errors = []
            self.assertEqual(subject._validate_module_catalog(root, errors), 0)
            self.assertTrue(any("modules must be an object" in error for error in errors))

    def test_field_contract_consistency_detects_deprecated_and_orphan_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            refs = root / "references"
            (refs / "schemas").mkdir(parents=True)
            (refs / "domain.md").write_text("`depth`: quick\n", encoding="utf-8")
            (root / "SKILL.md").write_text("audience: executive|alien\ndetail_level: brief|huge\n", encoding="utf-8")
            (refs / "schemas" / "finance-analysis-result.schema.json").write_text(
                json.dumps(
                    {
                        "$defs": {
                            "presentation": {
                                "properties": {
                                    "audience": {"enum": ["executive"]},
                                    "detail_level": {"enum": ["brief"]},
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            errors: list[str] = []
            subject._validate_field_contract_consistency(root, errors)
            rendered = "\n".join(errors)
            self.assertIn("deprecated field contract", rendered)
            self.assertIn("audience values missing", rendered)
            self.assertIn("detail_level values missing", rendered)


class NavigationAndTaskIndexTests(unittest.TestCase):
    def fake_nav(self, load_error: Exception | None = None) -> types.SimpleNamespace:
        pattern = re.compile(r"<!-- nav:start -->.*?<!-- nav:end -->\n?", re.DOTALL)
        if load_error:
            load_catalog = mock.Mock(side_effect=load_error)
        else:
            load_catalog = mock.Mock(return_value=({}, {}))
        return types.SimpleNamespace(
            load_catalog=load_catalog,
            build_nav=lambda _text, _task, _registry: "<!-- nav:start -->\nEXPECTED\n<!-- nav:end -->",
            NAV_BLOCK=pattern,
        )

    def test_nav_validation_missing_stale_and_catalog_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            playbooks = root / "references" / "corporate-finance" / "playbooks" / "g"
            playbooks.mkdir(parents=True)
            (playbooks / "_overview.md").write_text("# Overview\n", encoding="utf-8")
            task = playbooks / "task.md"
            task.write_text("# Task\n", encoding="utf-8")
            errors: list[str] = []
            with mock.patch.dict(sys.modules, {"gen_nav_headers": self.fake_nav()}):
                subject._validate_nav_headers(root, errors)
            self.assertTrue(any("missing nav header" in error for error in errors))
            task.write_text("# Task\n<!-- nav:start -->\nSTALE\n<!-- nav:end -->\n", encoding="utf-8")
            errors = []
            with mock.patch.dict(sys.modules, {"gen_nav_headers": self.fake_nav()}):
                subject._validate_nav_headers(root, errors)
            self.assertTrue(any("stale nav header" in error for error in errors))
            errors = []
            with mock.patch.dict(sys.modules, {"gen_nav_headers": self.fake_nav(ValueError("bad catalog"))}):
                subject._validate_nav_headers(root, errors)
            self.assertTrue(any("cannot load task catalog" in error for error in errors))

    def make_task_index_root(self, root: Path) -> None:
        catalog = root / "references" / "corporate-finance" / "task-catalog.json"
        catalog.parent.mkdir(parents=True)
        catalog.write_text(
            json.dumps(
                {
                    "tasks": [
                        {"id": "z-task", "group": "b", "playbook": "z.md"},
                        {"id": "a-task", "group": "a", "playbook": "a.md"},
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_task_index_build_sync_validate_and_error_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.make_task_index_root(root)
            expected = subject._build_task_index(root)
            self.assertLess(expected.index("**a**"), expected.index("**b**"))
            skill = root / "SKILL.md"
            skill.write_text(f"Before\n{subject.TASK_INDEX_START}\nSTALE\n{subject.TASK_INDEX_END}\nAfter\n", encoding="utf-8")
            self.assertTrue(subject._sync_task_index(root))
            self.assertFalse(subject._sync_task_index(root))
            errors: list[str] = []
            subject._validate_task_index(root, errors)
            self.assertEqual(errors, [])
            skill.write_text("No markers\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no task-index markers"):
                subject._sync_task_index(root)
            errors = []
            subject._validate_task_index(root, errors)
            self.assertTrue(any("missing the inline task index" in error for error in errors))
            skill.write_text(f"{subject.TASK_INDEX_START}\nSTALE\n{subject.TASK_INDEX_END}\n", encoding="utf-8")
            errors = []
            subject._validate_task_index(root, errors)
            self.assertTrue(any("index is stale" in error for error in errors))
            catalog = root / "references" / "corporate-finance" / "task-catalog.json"
            catalog.write_text("{", encoding="utf-8")
            errors = []
            subject._validate_task_index(root, errors)
            self.assertTrue(any("cannot load task catalog" in error for error in errors))


class ValidateSkillCliTests(unittest.TestCase):
    def test_validate_missing_skill_file_short_circuits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = subject.validate(Path(temporary_directory))
        self.assertEqual(result, {"status": "failed", "errors": ["SKILL.md is missing"], "warnings": []})

    def test_main_stdout_output_file_sync_and_exit_codes(self) -> None:
        passed = {"status": "passed", "errors": [], "warnings": []}
        failed = {"status": "failed", "errors": ["bad"], "warnings": []}
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "report.json"
            with mock.patch.object(subject, "validate", return_value=passed), mock.patch.object(
                subject, "_sync_task_index", return_value=True
            ) as sync, mock.patch.object(
                sys, "argv", ["validate_skill.py", str(root), "--sync-index", "--output", str(output_path)]
            ), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(subject.main(), 0)
            sync.assert_called_once_with(root.resolve())
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["status"], "passed")

            stdout = io.StringIO()
            with mock.patch.object(subject, "validate", return_value=failed), mock.patch.object(
                sys, "argv", ["validate_skill.py", str(root)]
            ), contextlib.redirect_stdout(stdout):
                self.assertEqual(subject.main(), 2)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "failed")


if __name__ == "__main__":
    unittest.main()
