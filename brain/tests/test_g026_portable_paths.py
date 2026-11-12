#!/usr/bin/env python3
"""انحدار G026: النقل الفعلي يمر، وجذر التشغيل الثابت يُمنع."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def site_root() -> Path:
    if os.environ.get("SITE_DIR"):
        return Path(os.environ["SITE_DIR"])
    for base in (ROOT.parent, ROOT.parent.parent):
        if (base / "seawatch" / "generator").is_dir():
            return base / "seawatch"
    return ROOT.parent / "site"


def validator(brain: Path, site: Path):
    with patch.dict(os.environ, {"BRAIN_DIR": str(brain), "SITE_DIR": str(site)}):
        spec = importlib.util.spec_from_file_location("portable_gate_fixture", ROOT / "validators/check_portable_paths.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class PortablePathContractTest(unittest.TestCase):
    def test_current_runtime_trees_pass_real_scanner(self) -> None:
        gate = validator(ROOT, site_root())
        self.assertEqual([], gate.scan(), "جذور ثابتة في أشجار التشغيل")

    def test_fixed_root_is_rejected_and_environment_root_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            brain, site = Path(td) / "brain", Path(td) / "site"
            brain.mkdir()
            site.mkdir()
            source = brain / "probe.py"
            source.write_text('import os\nSITE = os.environ["SITE_DIR"]\n', encoding="utf-8")
            gate = validator(brain, site)
            self.assertEqual([], gate.scan())
            # تُركب القيمة كي لا تحمل شيفرة الاختبار نفسها المسار الثابت.
            source.write_text('SITE = ' + repr(str(Path.home() / "seawatch")) + '\n', encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(2, gate.main())
            self.assertIn("brain/probe.py:1", out.getvalue())

    def test_relocated_evidence_checker_selects_local_page_without_env(self) -> None:
        for source in (ROOT / "tests/test_reliability_and_evidence_anchor.py", site_root() / "tests/test_reliability_and_evidence_anchor.py"):
            with self.subTest(source=str(source)), tempfile.TemporaryDirectory() as td:
                site = Path(td) / "site"
                tests = site / "tests"
                tests.mkdir(parents=True)
                script = tests / source.name
                shutil.copy2(source, script)
                page = site / "dist/reports/2026-11-12.html"
                page.parent.mkdir(parents=True)
                page.write_text('<span data-source-reliability="A/2" data-analytic-confidence="low"></span><a class="ev-link" href="https://example.org/evidence#id">دليل</a>', encoding="utf-8")
                env = dict(os.environ)
                for key in ("SITE", "SITE_DIR", "BRAIN_DIR"):
                    env.pop(key, None)
                result = subprocess.run([sys.executable, str(script)], cwd=td, env=env, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertIn(str(page), result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
