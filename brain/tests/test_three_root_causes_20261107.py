#!/usr/bin/env python3
"""حواجز ك-549/ك-550/ك-551: الجذر، تلغرام، واكتشاف جذر runbook."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TRACKING = load_module(ROOT / "validators" / "check_server_code_tracking.py", "tracking_root_contract")
TELEGRAM = load_module(ROOT / "tools" / "telegram_send.py", "telegram_target_contract")
RUNBOOK = ROOT / "tools" / "runbook.py"


class RepoRootContractTests(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(repo), *args], check=True,
                       text=True, capture_output=True)

    def test_git_root_is_measured_from_nested_brain(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "actual-repo"
            brain = repo / "brain"
            brain.mkdir(parents=True)
            self._git(repo, "init", "-q")
            self.assertEqual(TRACKING.default_repo_for(brain), repo.resolve())

    def test_missing_git_root_fails_closed_with_checked_path(self):
        with tempfile.TemporaryDirectory() as td:
            brain = Path(td) / "not-a-repo" / "brain"
            brain.mkdir(parents=True)
            with self.assertRaises(Exception) as ctx:
                TRACKING.default_repo_for(brain)
            self.assertIn(str(brain.parent), str(ctx.exception))

    def test_nested_duplicate_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "actual-repo"
            (repo / "brain").mkdir(parents=True)
            (repo / repo.name / "brain" / "secrets").mkdir(parents=True)
            self._git(repo, "init", "-q")
            with self.assertRaises(Exception) as ctx:
                TRACKING.default_repo_for(repo / "brain")
            self.assertIn("مضاعفة", str(ctx.exception))


class TelegramTargetContractTests(unittest.TestCase):
    def test_secret_numeric_id_overrides_non_numeric_file_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            targets = Path(td) / "targets.json"
            targets.write_text(json.dumps({"targets": [{
                "label": "المحادثة الشخصية", "chat_id": "بديل", "type": "private", "enabled": True
            }]}), encoding="utf-8")
            with patch.object(TELEGRAM, "TARGETS_FILE", targets), \
                 patch.object(TELEGRAM, "LEGACY_CHAT", Path(td) / "missing.json"), \
                 patch.dict(os.environ, {"TELEGRAM_OWNER_CHAT_ID": "-100123456789"}, clear=False):
                chosen = TELEGRAM.load_targets("primary")
            self.assertEqual(chosen[0]["chat_id"], "-100123456789")

    def test_non_numeric_enabled_fallback_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            targets = Path(td) / "targets.json"
            targets.write_text(json.dumps({"targets": [{
                "label": "المحادثة الشخصية", "chat_id": "بديل", "type": "private", "enabled": True
            }]}), encoding="utf-8")
            with patch.object(TELEGRAM, "TARGETS_FILE", targets), \
                 patch.object(TELEGRAM, "LEGACY_CHAT", Path(td) / "missing.json"), \
                 patch.dict(os.environ, {"TELEGRAM_OWNER_CHAT_ID": ""}, clear=False), \
                 patch.object(TELEGRAM, "_secret_from_env_file", return_value=""):
                with self.assertRaises(SystemExit) as ctx:
                    TELEGRAM.load_targets("primary")
            self.assertIn("غير رقمي", str(ctx.exception))

    def test_failure_log_contains_platform_error_fields(self):
        with tempfile.TemporaryDirectory() as td:
            targets = Path(td) / "targets.json"
            targets.write_text(json.dumps({"targets": [{
                "label": "المحادثة الشخصية", "chat_id": "123456789", "type": "private", "enabled": True
            }]}), encoding="utf-8")
            send_log = Path(td) / "telegram-sends.jsonl"
            with patch.object(TELEGRAM, "TARGETS_FILE", targets), \
                 patch.object(TELEGRAM, "LEGACY_CHAT", Path(td) / "missing.json"), \
                 patch.object(TELEGRAM, "SEND_LOG", send_log), \
                 patch.object(TELEGRAM, "send_text_direct", return_value='{"ok":false,"error_code":400,"description":"Bad Request"}'), \
                 patch.object(TELEGRAM, "curl", return_value='{"ok":false,"error_code":400,"description":"Bad Request"}'), \
                 patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}, clear=False):
                with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
                    fh.write("الفترة 2026-11-07 · و ب 1")
                    digest = fh.name
                try:
                    rc = TELEGRAM.main(["--daily-report", "--date", "2026-11-07", "--file", digest])
                finally:
                    Path(digest).unlink(missing_ok=True)
            self.assertEqual(rc, 1)
            records = [json.loads(line) for line in send_log.read_text(encoding="utf-8").splitlines()]
            failed = records[-1]
            self.assertEqual(failed["decision"], "failed")
            self.assertEqual(failed["error_code"], 400)
            self.assertEqual(failed["description"], "Bad Request")


class RunbookRootContractTests(unittest.TestCase):
    def _run(self, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(RUNBOOK), "status", "--date", "2026-11-07"],
                              cwd=cwd, text=True, capture_output=True, timeout=20)

    def test_status_discovers_brain_from_mirror_root_and_brain_root(self):
        mirror = ROOT.parent
        from_brain = self._run(ROOT)
        from_mirror = self._run(mirror)
        self.assertEqual(from_brain.returncode, 0, from_brain.stdout + from_brain.stderr)
        self.assertEqual(from_mirror.returncode, 0, from_mirror.stdout + from_mirror.stderr)
        self.assertIn("D070", from_mirror.stdout)

    def test_missing_manifest_error_lists_checked_paths(self):
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run([sys.executable, str(RUNBOOK), "status", "--date", "2026-11-07"],
                                    cwd=Path(td), text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 2)
            self.assertIn("المسارات المفحوصة", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
