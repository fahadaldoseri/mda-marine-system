#!/usr/bin/env python3
"""حاجز G030: رموز EST المسجلة تُقبل والرموز المجهولة تُرفض."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-11-07"
VALIDATOR = ROOT / "validators" / "check_code_spaces.py"


def run_validator(*, report: Path | None = None, meta: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(VALIDATOR), "--date", DATE]
    if report is not None:
        command.extend(["--report", str(report)])
    if meta is not None:
        command.extend(["--meta", str(meta)])
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def test_g030_current_report_has_registered_estimates() -> None:
    result = run_validator()
    assert result.returncode == 1, result.stdout + result.stderr
    assert "رموز تقديرات غير مسجَّلة" not in result.stdout
    assert "النتيجة: اجتياز مع تنبيهات." in result.stdout


def test_g030_unknown_estimate_remains_blocking(tmp_path: Path) -> None:
    report = tmp_path / "unknown.md"
    report.write_text("# اختبار\n\nEST-2099-01-01-99\n", encoding="utf-8")
    result = run_validator(report=report, meta=ROOT / "web" / "meta" / f"{DATE}.json")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "EST-2099-01-01-99" in result.stdout


def test_g030_is_connected_to_runbook() -> None:
    manifest = json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))
    step = next(item for item in manifest["steps"] if item["id"] == "G030")
    assert "tests/test_g030_code_spaces.py" in step["links"]["tests"]
    assert "validators/check_code_spaces.py" in step["links"]["files"]
    assert "appendices/estimate-code-map.json" in step["links"]["files"]


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__]))
