from __future__ import annotations

import contextlib
import io
import json
import subprocess
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
import ensure_runtime as runtime  # noqa: E402
import gen_nav_headers as nav  # noqa: E402
import normalize_headings as headings  # noqa: E402


class NormalizeHeadingsEdgeTests(unittest.TestCase):
    def write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_legacy_headings_defaults_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = self.write(
                Path(temporary_directory),
                "legacy.md",
                "# Task\n\n### Workflow\nBody\n#### Detail\n### Defaults *(apply silently)*\n",
            )
            self.assertTrue(headings.normalize(path))
            normalized = path.read_text(encoding="utf-8")
            self.assertIn("## Workflow", normalized)
            self.assertIn("### Detail", normalized)
            self.assertIn("## Defaults\n\n**apply silently.**", normalized)
            self.assertFalse(headings.normalize(path))

    def test_existing_h2_preserves_h3_and_normalizes_annotated_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = self.write(
                Path(temporary_directory),
                "modern.md",
                "# Task\n\n## Workflow\n### Detail\n## Defaults *(disclose at delivery.)*\n",
            )
            self.assertTrue(headings.normalize(path))
            normalized = path.read_text(encoding="utf-8")
            self.assertIn("### Detail", normalized)
            self.assertIn("## Defaults\n\n**disclose at delivery.**", normalized)

    def test_unchanged_modern_file_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = self.write(Path(temporary_directory), "modern.md", "# Task\n\n## Workflow\nBody\n")
            before = path.read_text(encoding="utf-8")
            self.assertFalse(headings.normalize(path))
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_main_skips_overview_and_counts_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            playbooks = root / "references" / "corporate-finance" / "playbooks"
            overview = self.write(playbooks, "_overview.md", "# Overview\n\n### Keep\n")
            self.write(playbooks, "legacy.md", "# Task\n\n### Workflow\n")
            self.write(playbooks, "modern.md", "# Task\n\n## Workflow\n")
            output = io.StringIO()
            with mock.patch.object(headings, "ROOT", root), mock.patch.object(headings, "PLAYBOOKS", playbooks):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(headings.main(), 0)
            self.assertIn("normalized: references/corporate-finance/playbooks/legacy.md", output.getvalue())
            self.assertIn("total changed: 1", output.getvalue())
            self.assertIn("### Keep", overview.read_text(encoding="utf-8"))


class NavigationHeaderEdgeTests(unittest.TestCase):
    def test_build_nav_without_headings_task_or_gates(self) -> None:
        block = nav.build_nav("# Task\nBody\n", None, {})
        self.assertIn("**Sections**: (no sections)", block)
        self.assertNotIn("Must not skip", block)
        self.assertNotIn("Formats", block)

    def test_build_nav_orders_sections_gates_and_formats(self) -> None:
        text = "# Task\n\n## Workflow\n## Defaults\n## Interface\n"
        task = {"formats": ["excel", "unknown"]}
        block = nav.build_nav(text, task, {"excel": "references/formats/excel_standards.md"})
        self.assertIn("Workflow · Defaults · Interface", block)
        self.assertIn("Defaults · Interface — return here before delivery", block)
        self.assertIn("excel_standards.md · unknown", block)

    def test_apply_handles_missing_h1_insertion_refresh_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            no_h1 = root / "no-h1.md"
            no_h1.write_text("## Workflow\n", encoding="utf-8")
            with mock.patch.object(nav, "ROOT", root):
                self.assertEqual(nav.apply(no_h1, {}, {}), (False, False))

                path = root / "task.md"
                path.write_text("# Task\n\n## Workflow\n## Defaults\n", encoding="utf-8")
                self.assertEqual(nav.apply(path, {}, {}), (True, True))
                self.assertIn(nav.NAV_START, path.read_text(encoding="utf-8"))
                self.assertEqual(nav.apply(path, {}, {}), (False, False))

                stale = path.read_text(encoding="utf-8").replace("Workflow · Defaults", "Stale")
                path.write_text(stale, encoding="utf-8")
                self.assertEqual(nav.apply(path, {}, {}), (True, True))
                self.assertIn("Workflow · Defaults", path.read_text(encoding="utf-8"))

    def test_load_catalog_supports_object_and_string_registry_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            catalog = Path(temporary_directory) / "task-catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "tasks": [{"id": "t", "playbook": "references/task.md"}],
                        "format_registry": {
                            "excel": {"path": "references/excel.md"},
                            "memo": "references/memo.md",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(nav, "TASK_CATALOG", catalog):
                by_playbook, registry = nav.load_catalog()
            self.assertEqual(by_playbook["references/task.md"]["id"], "t")
            self.assertEqual(registry, {"excel": "references/excel.md", "memo": "references/memo.md"})

    def test_main_check_rewrite_and_clean_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            playbooks = root / "references" / "corporate-finance" / "playbooks"
            playbooks.mkdir(parents=True)
            task = playbooks / "task.md"
            task.write_text("# Task\n\n## Workflow\n## Scope Boundaries\n", encoding="utf-8")
            (playbooks / "_overview.md").write_text("# Overview\n", encoding="utf-8")
            catalog = root / "task-catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "tasks": [{"id": "t", "playbook": str(task.relative_to(root)), "formats": []}],
                        "format_registry": {},
                    }
                ),
                encoding="utf-8",
            )
            patches = (
                mock.patch.object(nav, "ROOT", root),
                mock.patch.object(nav, "PLAYBOOKS", playbooks),
                mock.patch.object(nav, "TASK_CATALOG", catalog),
            )
            with patches[0], patches[1], patches[2]:
                with mock.patch.object(sys, "argv", ["gen_nav_headers.py", "--check"]):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(nav.main(), 1)
                    self.assertIn("stale nav headers", output.getvalue())
                with mock.patch.object(sys, "argv", ["gen_nav_headers.py"]):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(nav.main(), 0)
                    self.assertIn("nav updated", output.getvalue())
                with mock.patch.object(sys, "argv", ["gen_nav_headers.py", "--check"]):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(nav.main(), 0)
                    self.assertIn("all nav headers up to date", output.getvalue())


class EnsureRuntimeEdgeTests(unittest.TestCase):
    def state(self, status: str, version: str | None = None) -> dict[str, object]:
        return {
            "runtime_contract": runtime.RUNTIME_CONTRACT,
            "status": status,
            "dependency": runtime.DEPENDENCY,
            "required": runtime.REQUIRED_SPECIFIER,
            "version": version,
        }

    def test_parse_release_and_supported_boundaries(self) -> None:
        self.assertEqual(runtime._parse_release("4.26.0rc1+local"), (4, 26, 1))
        self.assertTrue(runtime._is_supported("4.18.0"))
        self.assertFalse(runtime._is_supported("5.0.0"))
        with self.assertRaises(ValueError):
            runtime._parse_release("release")

    def test_probe_jsonschema_success_failure_and_exception(self) -> None:
        success = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        failure = subprocess.CompletedProcess([], 1, stdout="fallback", stderr="broken")
        with mock.patch.object(runtime.subprocess, "run", return_value=success):
            self.assertEqual(runtime._probe_jsonschema(), (True, None))
        with mock.patch.object(runtime.subprocess, "run", return_value=failure):
            self.assertEqual(runtime._probe_jsonschema(), (False, "broken"))
        with mock.patch.object(runtime.subprocess, "run", side_effect=OSError("unavailable")):
            self.assertEqual(runtime._probe_jsonschema(), (False, "unavailable"))

    def test_inspect_runtime_all_non_ready_states(self) -> None:
        with mock.patch.object(runtime.importlib.metadata, "version", side_effect=runtime.importlib.metadata.PackageNotFoundError):
            self.assertEqual(runtime.inspect_runtime()["status"], "missing")
        with mock.patch.object(runtime.importlib.metadata, "version", return_value="release"):
            self.assertEqual(runtime.inspect_runtime()["status"], "incompatible")
        with mock.patch.object(runtime.importlib.metadata, "version", return_value="5.0.0"):
            self.assertEqual(runtime.inspect_runtime()["status"], "incompatible")
        with mock.patch.object(runtime.importlib.metadata, "version", return_value="4.26.0"), mock.patch.object(
            runtime, "_probe_jsonschema", return_value=(False, "broken import")
        ):
            state = runtime.inspect_runtime()
            self.assertEqual(state["status"], "broken")
            self.assertEqual(state["detail"], "broken import")

    def test_lock_file_missing_and_missing_pin_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing.lock"
            with mock.patch.object(runtime, "LOCK_FILE", missing):
                with self.assertRaises(runtime.RuntimePreparationError):
                    runtime._validate_lock_file()
            invalid = Path(temporary_directory) / "requirements.lock"
            invalid.write_text("# comment\nother==1\n", encoding="utf-8")
            with mock.patch.object(runtime, "LOCK_FILE", invalid):
                with self.assertRaises(runtime.RuntimePreparationError):
                    runtime._validate_lock_file()

    def test_install_locked_records_runner_exception_then_uses_pip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            lock = Path(temporary_directory) / "requirements.lock"
            lock.write_text("jsonschema==4.26.0\n", encoding="utf-8")
            runner = mock.Mock(
                side_effect=[
                    OSError("uv unavailable"),
                    subprocess.CompletedProcess([], 0, stdout="installed", stderr=""),
                ]
            )
            with mock.patch.object(runtime, "LOCK_FILE", lock):
                result = runtime._install_locked(runner)
            self.assertEqual(result["installer"], "pip3")
            self.assertIsNone(result["attempts"][0]["returncode"])

    def test_check_only_and_disabled_value_variants_block_install(self) -> None:
        missing = self.state("missing")
        with mock.patch.object(runtime, "inspect_runtime", return_value=missing):
            with self.assertRaises(runtime.RuntimePreparationError) as context:
                runtime.ensure_runtime(allow_install=False)
        self.assertIn("check-only", str(context.exception))
        for value in ("true", "yes", "on"):
            with self.subTest(value=value), mock.patch.object(runtime, "inspect_runtime", return_value=missing), mock.patch.dict(
                runtime.os.environ, {runtime.DISABLE_AUTO_INSTALL_ENV: value}, clear=False
            ):
                with self.assertRaises(runtime.RuntimePreparationError):
                    runtime.ensure_runtime()

    def test_write_payload_to_stdout_and_nested_file(self) -> None:
        payload = {"status": "ready"}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            runtime._write_payload(payload, None)
        self.assertEqual(json.loads(output.getvalue()), payload)
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "nested" / "runtime.json"
            runtime._write_payload(payload, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)

    def test_main_success_and_blocked_output_contracts(self) -> None:
        ready = {**self.state("ready", "4.26.0"), "action": "none"}
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "runtime.json"
            with mock.patch.object(runtime, "ensure_runtime", return_value=ready), mock.patch.object(
                sys, "argv", ["ensure_runtime.py", "--check-only", "--output", str(path)]
            ):
                self.assertEqual(runtime.main(), 0)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "ready")

        error = runtime.RuntimePreparationError("blocked test", state={"status": "blocked", "detail": "offline"})
        output = io.StringIO()
        with mock.patch.object(runtime, "ensure_runtime", side_effect=error), mock.patch.object(
            sys, "argv", ["ensure_runtime.py", "--check-only"]
        ), contextlib.redirect_stdout(output):
            self.assertEqual(runtime.main(), 2)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("blocked test", payload["error"])


if __name__ == "__main__":
    unittest.main()
