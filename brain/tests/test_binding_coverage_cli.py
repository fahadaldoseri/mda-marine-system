#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""عقد CLI: binding_coverage يقبل --root كما في أوامر التشغيل المعتمدة."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "binding_coverage.py"


class BindingCoverageCliTests(unittest.TestCase):
    def test_root_alias_is_accepted(self) -> None:
        result = subprocess.run(
            [sys.executable, str(TOOL), "--root", str(ROOT), "--show", "0"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("تغطية الربط", result.stdout)


if __name__ == "__main__":
    unittest.main()
