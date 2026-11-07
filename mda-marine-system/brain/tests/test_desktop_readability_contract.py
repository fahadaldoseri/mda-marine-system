#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""عقد متصفح حي لحارس وضوح سطح الحاسوب: موجب وسالب."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "validators" / "check_desktop_readability.py"
DATE = "2026-11-06"


class DesktopReadabilityContractTests(unittest.TestCase):
    def _run(self, css: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="desktop-readability-") as td:
            site = Path(td)
            page = site / "dist" / "reports" / f"{DATE}.html"
            page.parent.mkdir(parents=True)
            page.write_text(
                "<!doctype html><html><head><meta charset='utf-8'>"
                f"<style>{css}</style></head><body>"
                "<main><h1>اختبار وضوح الشاشة</h1><p>نص قياس حقيقي داخل صفحة محلية.</p></main>"
                "</body></html>",
                encoding="utf-8",
            )
            return subprocess.run(
                [
                    sys.executable,
                    str(GUARD),
                    "--site",
                    str(site),
                    "--date",
                    DATE,
                    "--widths",
                    "1440",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_readable_page_passes(self) -> None:
        result = self._run("body { font-size: 16px; color: #111; background: #fff; }")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("✔ سطح الحاسوب", result.stdout)

    def test_small_text_fails_closed_and_names_reason(self) -> None:
        result = self._run("body { font-size: 10px; color: #111; background: #fff; }")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("خط<12", result.stdout)
        self.assertIn("فشل مغلق", result.stdout)


if __name__ == "__main__":
    unittest.main()
