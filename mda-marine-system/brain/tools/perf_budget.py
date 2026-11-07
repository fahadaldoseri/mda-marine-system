#!/usr/bin/env python3
"""قِس أزمنة خطوات البوابات من سجلات المحرّك وقارنها بميزانية حاكمة.

رموز الخروج: 0 داخل الميزانية · 2 تجاوز أو غياب قياس أو عقد فاسد.
لا تُخمّن الأرقام: السجل بلا علامة زمن صريحة مخالفة مانعة.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


DURATION_PATTERNS = (
    re.compile(r"elapsed_seconds\s*=\s*([0-9]+(?:\.[0-9]+)?)"),
    re.compile(r"(?i)\b(?:elapsed|duration|took)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*s\b"),
    re.compile(r"(?i)\b(?:passed|failed)\s+in\s+([0-9]+(?:\.[0-9]+)?)\s*s\b"),
)


def _fmt_seconds(value: float) -> str:
    """اعرض القياس بدقة مفيدة، مع إبقاء 1.0 واضحًا في سجل العقد."""
    return f"{value:.1f}" if value.is_integer() else f"{value:g}"


def _positive_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} يجب أن يكون رقمًا موجبًا")
    number = float(value)
    if number <= 0:
        raise ValueError(f"{label} يجب أن يكون أكبر من صفر")
    return number


def load_budget(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"تعذّر قراءة عقد الميزانية: {type(exc).__name__}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("عقد الميزانية يجب أن يكون كائن JSON")
    if data.get("version") != 1:
        raise ValueError("إصدار عقد الميزانية غير معروف؛ المطلوب version=1")
    default = _positive_number(data.get("default_seconds"), "default_seconds")
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, dict) or not raw_steps:
        raise ValueError("عقد الميزانية يحتاج إلى steps غير فارغة")
    steps: dict[str, dict[str, Any]] = {}
    for step_id, spec in raw_steps.items():
        if not isinstance(step_id, str) or not step_id.strip():
            raise ValueError("معرّف خطوة فارغ في عقد الميزانية")
        if not isinstance(spec, dict):
            raise ValueError(f"عقد الميزانية للخطوة {step_id} ليس كائنًا")
        limit = _positive_number(spec.get("max_seconds", default), f"{step_id}.max_seconds")
        basis = spec.get("basis")
        if not isinstance(basis, str) or not basis.strip():
            raise ValueError(f"{step_id}: أساس الحد مفقود؛ لا تُفترض الأرقام")
        steps[step_id] = {"max_seconds": limit, "basis": basis.strip()}
    return {"version": 1, "default_seconds": default, "steps": steps}


def durations_from_log(path: Path) -> list[float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    explicit = [float(match) for match in DURATION_PATTERNS[0].findall(text)]
    if explicit:
        return explicit
    values: list[float] = []
    for pattern in DURATION_PATTERNS[1:]:
        values.extend(float(match) for match in pattern.findall(text))
    return values


def measure(root: Path, date: str, budget: dict[str, Any]) -> dict[str, Any]:
    log_root = root / "logs" / "runbook" / date
    measured: dict[str, dict[str, Any]] = {}
    violations: list[str] = []
    for step_id, spec in budget["steps"].items():
        log_path = log_root / f"{step_id}.log"
        entry: dict[str, Any] = {
            "log": str(log_path.relative_to(root)),
            "max_seconds": spec["max_seconds"],
            "basis": spec["basis"],
        }
        if not log_path.is_file():
            entry["status"] = "missing_log"
            violations.append(f"{step_id}: سجل الخطوة غائب، فشل مغلق")
            measured[step_id] = entry
            continue
        values = durations_from_log(log_path)
        if not values:
            entry["status"] = "missing_duration"
            violations.append(f"{step_id}: لا يوجد زمن مقيس صريح في السجل، فشل مغلق")
            measured[step_id] = entry
            continue
        # elapsed_seconds هو القياس الحاكم إن وُجد، وإلا نستخدم آخر قياس أداة صريح.
        seconds = values[-1]
        entry["measured_seconds"] = seconds
        entry["status"] = "pass" if seconds <= spec["max_seconds"] else "over_budget"
        if seconds > spec["max_seconds"]:
            violations.append(
                f"{step_id}: تجاوز ميزانية الأداء — الزمن المقيس {_fmt_seconds(seconds)}s > "
                f"الحد {_fmt_seconds(spec['max_seconds'])}s"
            )
        measured[step_id] = entry
    return {
        "version": 1,
        "date": date,
        "measured_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass" if not violations else "fail_closed",
        "steps": measured,
        "violations": violations,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="قياس ميزانية أداء خطوات البوابات من سجلات runbook")
    parser.add_argument("--root", default=".", help="جذر brain")
    parser.add_argument("--date", required=True, help="تاريخ الجولة YYYY-MM-DD")
    parser.add_argument("--budget", default="runbook/perf-budget.json", help="ملف عقد الميزانية")
    parser.add_argument("--out", default="", help="مسار JSON الناتج")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    budget_path = Path(args.budget).expanduser()
    if not budget_path.is_absolute():
        budget_path = root / budget_path
    try:
        budget = load_budget(budget_path)
        result = measure(root, args.date, budget)
    except (OSError, ValueError) as exc:
        print(f"✘ فشل مغلق — عقد ميزانية الأداء غير قابل للقياس: {exc}")
        return 2
    if args.out:
        out = Path(args.out).expanduser()
        if not out.is_absolute():
            out = root / out
        _write_json(out, result)
    for step_id, entry in result["steps"].items():
        if entry.get("measured_seconds") is not None:
            print(
                f"{step_id}: الزمن المقيس {_fmt_seconds(entry['measured_seconds'])}s · "
                f"الحد {_fmt_seconds(entry['max_seconds'])}s · {entry['status']}"
            )
        else:
            print(f"{step_id}: {entry['status']} · فشل مغلق")
    if result["violations"]:
        print("✘ ميزانية الأداء تمنع الجولة:")
        for violation in result["violations"]:
            print(f"  - {violation}")
        return 2
    print(f"✔ ميزانية الأداء: {len(result['steps'])} خطوة داخل الحدود")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
