#!/usr/bin/env python3
"""حاجز G036: الصياغة اليومية المعتمدة تمرّ وعودة اللفظ المرفوض تُمنع."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validators" / "check_vocabulary.py"
DAY = os.environ.get("D") or sorted(p.name[:10] for p in (ROOT / "reports").glob("????-??-??-sectioned.md"))[-1]
REPORT = ROOT / "reports" / f"{DAY}-sectioned.md"
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


@pytest.mark.parametrize("state,expected", [
    ("rejected", 0), ("watch", 1), ("proposed", 1), ("approved", 2), ("unknown", 2),
])
def test_g036_respects_individual_entry_status(tmp_path, monkeypatch, capsys, state, expected):
    spec = importlib.util.spec_from_file_location("g036_status_probe", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"status": "canonical", "entries": [
        {"term": "لا تؤكد", "plain": ["لم تؤكد"], "status": state},
    ]}, ensure_ascii=False), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text("لا تؤكد المادة وقوع الحادث.\n", encoding="utf-8")
    monkeypatch.setattr(module, "VOCAB", registry)
    monkeypatch.setattr(sys, "argv", [str(VALIDATOR), "--md", str(report)])
    assert module.main() == expected
    output = capsys.readouterr().out
    if state == "unknown":
        assert "حالة غير معروفة" in output
    elif state == "rejected":
        assert "البديل اليومي" not in output


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__]))
