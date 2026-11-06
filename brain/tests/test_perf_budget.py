#!/usr/bin/env python3
"""اختبارات عقد ميزانية زمن البوابات: موجب وسالب وفشل مغلق للزمن المفقود."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "perf_budget.py"
RUNBOOK = ROOT / "tools" / "runbook.py"


def _fixture(tmp_path: Path, elapsed: str | None, limit: float = 1.0) -> tuple[Path, Path, Path]:
    logs = tmp_path / "logs" / "runbook" / "2026-11-07"
    logs.mkdir(parents=True)
    body = "✔ خطوة اختبار\n"
    if elapsed is not None:
        body += f"elapsed_seconds={elapsed}\n"
    (logs / "G057.log").write_text(body, encoding="utf-8")
    budget = tmp_path / "perf-budget.json"
    budget.write_text(
        json.dumps(
            {
                "version": 1,
                "default_seconds": limit,
                "steps": {"G057": {"max_seconds": limit, "basis": "اختبار عقد"}},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "perf.json"
    return logs, budget, output


def _run(tmp_path: Path, elapsed: str | None, limit: float = 1.0) -> subprocess.CompletedProcess[str]:
    _, budget, output = _fixture(tmp_path, elapsed, limit)
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--root",
            str(tmp_path),
            "--date",
            "2026-11-07",
            "--budget",
            str(budget),
            "--out",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_elapsed_inside_budget_passes_and_is_saved(tmp_path: Path) -> None:
    result = _run(tmp_path, "0.25")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "G057" in result.stdout
    saved = json.loads((tmp_path / "perf.json").read_text(encoding="utf-8"))
    assert saved["steps"]["G057"]["measured_seconds"] == 0.25
    assert saved["status"] == "pass"


def test_over_budget_fails_closed_and_names_step(tmp_path: Path) -> None:
    result = _run(tmp_path, "1.25")
    assert result.returncode == 2
    assert "G057" in result.stdout
    assert "1.25" in result.stdout
    assert "1.0" in result.stdout
    assert "تجاوز" in result.stdout


def test_missing_elapsed_fails_closed_and_names_step(tmp_path: Path) -> None:
    result = _run(tmp_path, None)
    assert result.returncode == 2
    assert "G057" in result.stdout
    assert "زمن" in result.stdout
    assert "فشل مغلق" in result.stdout


def test_runbook_records_elapsed_seconds(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    (tmp_path / "runbook").mkdir()
    shutil.copy2(RUNBOOK, tmp_path / "tools" / "runbook.py")
    (tmp_path / "runbook" / "runbook.json").write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "id": "GTEST",
                        "title": "اختبار الزمن",
                        "kind": "script",
                        "phase": "gates",
                        "command": [sys.executable, "-c", "print('ok')"],
                        "assert": [],
                        "on_fail": "stop",
                        "ok_rc": [0],
                        "warn_rc": [],
                    }
                ],
                "gate_phases": ["gates"],
                "ledger_dir": "logs/runbook",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(tmp_path / "tools" / "runbook.py"), "run", "--date", "2026-11-07", "--root", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    log = (tmp_path / "logs" / "runbook" / "2026-11-07" / "GTEST.log").read_text(encoding="utf-8")
    assert "elapsed_seconds=" in log


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
