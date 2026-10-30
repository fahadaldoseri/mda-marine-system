#!/usr/bin/env python3
"""Regression test for closed tracking of evidence files."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRAY = ROOT / "evidence" / "__stray-test.txt"


def test_txt_evidence_stray_is_rejected_by_verify() -> None:
    STRAY.write_text("deliberate stray evidence\n", encoding="utf-8")
    try:
        result = subprocess.run(
            ["python3", "tools/runbook.py", "verify"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 2, output
        assert "evidence/__stray-test.txt" in output
    finally:
        STRAY.unlink(missing_ok=True)
