#!/usr/bin/env python3
"""حاجز G036: الصياغة اليومية المعتمدة تمرّ وعودة اللفظ المرفوض تُمنع."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validators" / "check_vocabulary.py"
REPORT = ROOT / "reports" / "2026-11-07-sectioned.md"
TERM = "بلاغ ملاحي مستقل"


def run_validator(report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--md", str(report)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_g036_current_report_uses_approved_daily_term() -> None:
    result = run_validator(REPORT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert TERM not in result.stdout


def test_g036_rejects_reintroduced_approved_term(tmp_path: Path) -> None:
    report = tmp_path / "reintroduced.md"
    report.write_text(f"# اختبار\n\n{TERM}\n", encoding="utf-8")
    result = run_validator(report)
    assert result.returncode == 2, result.stdout + result.stderr
    assert TERM in result.stdout


def test_g036_is_connected_to_runbook() -> None:
    manifest = json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))
    step = next(item for item in manifest["steps"] if item["id"] == "G036")
    assert "tests/test_g036_vocabulary_contract.py" in step["links"]["tests"]
    assert "appendices/simplified-vocabulary.json" in step["links"]["files"]


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__]))
