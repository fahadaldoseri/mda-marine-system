#!/usr/bin/env python3
"""حاجز G030: رموز EST في تقرير التشغيل مسجلة، ذات معنى موحد، والرموز المجهولة تُمنع."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
# اليوم إن وُجد متنه (تشغيل الخادم بعد كتابة التقرير)، وإلا أحدث متن محفوظ؛ كان الاختبار
# يفشل في كل بيئة لا تحمل تقرير اليوم (GitHub Actions والجلسات السحابية) لا لعيب في الرموز.
_TODAY = datetime.now(timezone.utc).date().isoformat()
_REPORTS = Path(__file__).resolve().parents[1] / "reports"
DATE = os.environ.get("D") or (
    _TODAY if (_REPORTS / f"{_TODAY}-sectioned.md").is_file()
    else sorted(p.name[:10] for p in _REPORTS.glob("????-??-??-sectioned.md"))[-1]
)
VALIDATOR = ROOT / "validators" / "check_code_spaces.py"
REPORT = ROOT / "reports" / f"{DATE}-sectioned.md"
META = ROOT / "web" / "meta" / f"{DATE}.json"
CODE_MAP = ROOT / "appendices" / "estimate-code-map.json"


def run_validator(*, report: Path | None = None, meta: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(VALIDATOR), "--date", DATE]
    if report is not None:
        command.extend(["--report", str(report)])
    if meta is not None:
        command.extend(["--meta", str(meta)])
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def test_current_report_has_registered_estimates() -> None:
    result = run_validator()
    assert result.returncode in (0, 1), result.stdout + result.stderr
    assert not ("EST-" in result.stdout and "غير مسجَّل" in result.stdout), result.stdout


def test_current_estimates_have_one_registered_meaning() -> None:
    report = REPORT.read_text(encoding="utf-8")
    meta = json.loads(META.read_text(encoding="utf-8"))
    code_map = json.loads(CODE_MAP.read_text(encoding="utf-8"))["codes"]
    used = sorted(
        code
        for code in set(re.findall(r"EST-\d{4}-\d{2}-\d{2}-\d{2}", report))
        if code.startswith(f"EST-{DATE}-")
    )
    for code in used:
        assert code in code_map, f"غير مسجل: {code}"
        lines = [line for line in report.splitlines() if code in line]
        assert len(lines) == 1, f"معانٍ/مواضع متعددة للرمز {code}: {lines}"
        statement = str(code_map[code].get("statement", "")).strip()
        assert statement and statement in lines[0], f"معنى السجل لا يطابق موضع {code}: {statement!r}"
        hypotheses = [h for h in meta.get("hypotheses", []) if h.get("est") == code]
        if hypotheses:
            assert len(hypotheses) == 1, f"تكرار معنى {code} في ملف الواجهة"
            assert hypotheses[0].get("statement") == statement, f"ملف الواجهة لا يطابق السجل للرمز {code}"


def test_day_without_new_estimates_is_valid(tmp_path: Path, monkeypatch) -> None:
    report, meta, code_map = [tmp_path / name for name in ("report.md", "meta.json", "map.json")]
    report.write_text("# تقرير بلا تقدير جديد\n", encoding="utf-8")
    meta.write_text('{"hypotheses": []}', encoding="utf-8")
    code_map.write_text('{"codes": {}}', encoding="utf-8")
    monkeypatch.setitem(globals(), "REPORT", report)
    monkeypatch.setitem(globals(), "META", meta)
    monkeypatch.setitem(globals(), "CODE_MAP", code_map)
    test_current_estimates_have_one_registered_meaning()


def test_g030_unknown_estimate_remains_blocking(tmp_path: Path) -> None:
    report = tmp_path / "unknown.md"
    report.write_text("# اختبار\n\nEST-2099-01-01-99\n", encoding="utf-8")
    result = run_validator(report=report, meta=META)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "EST-2099-01-01-99" in result.stdout


def test_w010_cannot_complete_without_registration(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    (root / "tools").mkdir(parents=True)
    (root / "runbook").mkdir()
    (root / "reports").mkdir()
    (root / "appendices").mkdir()
    (root / "logs" / "runbook").mkdir(parents=True)
    shutil.copy2(ROOT / "tools" / "register_estimate.py", root / "tools" / "register_estimate.py")
    code = "EST-2099-01-01-01"
    date = "2099-01-01"
    step = {
        "id": "W010",
        "title": "اختبار تسجيل التقدير",
        "kind": "agent",
        "assert": [{"type": "cmd", "command": ["python3", "tools/register_estimate.py", "--check", "--date", "{date}"]}],
        "writes": ["appendices/estimate-code-map.json"],
    }
    (root / "runbook" / "runbook.json").write_text(json.dumps({"steps": [step]}, ensure_ascii=False), encoding="utf-8")
    (root / "appendices" / "estimate-code-map.json").write_text(json.dumps({"codes": {}}), encoding="utf-8")
    (root / "reports" / f"{date}-sectioned.md").write_text(f"تقدير {code}\n", encoding="utf-8")
    ledger = root / "logs" / "runbook" / f"{date}.jsonl"
    ledger.write_text(json.dumps({"step": "W010", "status": "waiting_agent"}) + "\n", encoding="utf-8")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    engine = ROOT / "tools" / "runbook.py"
    complete = [sys.executable, str(engine), "complete", "W010", "--date", date, "--root", str(root)]

    blocked = subprocess.run(complete, cwd=root, env=env, capture_output=True, text=True, check=False)
    assert blocked.returncode == 2, blocked.stdout + blocked.stderr
    assert "فحص فشل" in blocked.stdout

    registered = subprocess.run(
        [sys.executable, str(root / "tools" / "register_estimate.py"), "--date", date, "--seq", "1",
         "--section", "اختبار", "--statement", "فرضية اختبارية", "--confidence", "منخفضة",
         "--reliability", "اختبار", "--support", "مصدر اختبار"],
        cwd=root, env=env, capture_output=True, text=True, check=False,
    )
    assert registered.returncode == 0, registered.stdout + registered.stderr
    accepted = subprocess.run(complete, cwd=root, env=env, capture_output=True, text=True, check=False)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr


def test_g030_is_connected_to_manifest_and_g001_runner() -> None:
    manifest = json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))
    g030 = next(item for item in manifest["steps"] if item["id"] == "G030")
    assert "tests/test_g030_code_spaces.py" in g030["links"]["tests"]
    assert "validators/check_code_spaces.py" in g030["links"]["files"]
    assert "appendices/estimate-code-map.json" in g030["links"]["files"]
    w010 = next(item for item in manifest["steps"] if item["id"] == "W010")
    assert any(a.get("type") == "cmd" and a.get("command") == ["python3", "tools/register_estimate.py", "--check", "--date", "{date}"] for a in w010.get("assert", []))
    runner = (ROOT / "tests" / "run_checks.sh").read_text(encoding="utf-8")
    assert "tests/test_g030_code_spaces.py" in runner, "اختبار G030 ليس موصولًا فعليًا ببوابة G001"


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__]))
