#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""جدول ادعاءات فاشل مغلقًا.

مخطط الإدخال المقبول:
{"claims": [{"id": "C-1", "claim": "...", "status": "confirmed",
  "measurement": {"command": "...", "exit_code": 0}}]}

القياس صالح فقط إذا جمع أمرًا غير فارغ مع رمز خروج رقمي أو رقم قياس.
النتيجة المعلنة «confirmed» بلا قياس لا تُقبل، وتُخرج العملية الرمز 2.
رمز 0 = كل صفوف الادعاءات قابلة للتصنيف بلا مخالفة، 2 = ادعاء confirmed
بلا قياس أو تنبيه فاشل، 3 = ملف إدخال غير صالح.
"""
from __future__ import annotations

import argparse
import json
import math
import operator
import sys
from pathlib import Path
from typing import Any

CONFIRMED = "مؤكد بقياس"
REJECTED = "مرفوض بقياس"
UNVERIFIED = "لم يُتحقق"


def _load(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        claims = data
    elif isinstance(data, dict) and isinstance(data.get("claims"), list):
        claims = data["claims"]
    else:
        raise ValueError("يجب أن يكون JSON قائمة أو كائنًا يحوي claims[]")
    if not all(isinstance(x, dict) for x in claims):
        raise ValueError("كل عنصر في claims[] يجب أن يكون كائنًا")
    return claims


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    try:
        n = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def _status(value: Any) -> str | None:
    if isinstance(value, bool):
        return "confirmed" if value else "rejected"
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in {"confirmed", "confirm", "pass", "passed", "ok", "true", "مؤكد", "مؤكد بقياس", "ناجح"}:
        return "confirmed"
    if s in {"rejected", "reject", "fail", "failed", "false", "مرفوض", "مرفوض بقياس", "فاشل"}:
        return "rejected"
    if s in {"unverified", "unknown", "pending", "لم يتحقق", "لم يُتحقق", "غير متحقق"}:
        return "unverified"
    return None


def _compare(actual: float, expected: float, op: str) -> bool | None:
    ops = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le,
           "==": operator.eq, "=": operator.eq, "!=": operator.ne}
    fn = ops.get(op.strip())
    return fn(actual, expected) if fn else None


def _measurement_result(measurement: Any) -> tuple[str | None, bool, str]:
    """Return outcome, valid-measurement flag, and compact evidence."""
    if not isinstance(measurement, dict):
        return None, False, "لا يوجد كائن قياس"
    command = str(measurement.get("command", "")).strip()
    exit_code = _number(measurement.get("exit_code"))
    actual = _number(measurement.get("value", measurement.get("actual", measurement.get("number"))))
    metric_present = exit_code is not None or actual is not None
    if not command or not metric_present:
        return None, False, "ينقص الأمر أو رمز الخروج/الرقم"

    explicit = _status(measurement.get("status", measurement.get("outcome")))
    if explicit in {"confirmed", "rejected"}:
        outcome = explicit
    elif exit_code is not None:
        outcome = "confirmed" if int(exit_code) == 0 else "rejected"
    else:
        expected = _number(measurement.get("expected", measurement.get("threshold")))
        op = str(measurement.get("operator", "")).strip()
        compared = _compare(actual, expected, op) if actual is not None and expected is not None and op else None
        if compared is None:
            return None, True, f"{command} · رقم={actual:g} بلا مقارنة حاسمة"
        outcome = "confirmed" if compared else "rejected"

    metric = f"exit={int(exit_code)}" if exit_code is not None else f"value={actual:g}"
    return outcome, True, f"{command} · {metric}"


def _measurements(claim: dict[str, Any]) -> list[Any]:
    value = claim.get("measurements", claim.get("measurement"))
    if isinstance(value, list):
        return value
    return [value] if value is not None else []


def _declared_confirmed(claim: dict[str, Any]) -> bool:
    direct = claim.get("confirmed")
    if direct is True:
        return True
    return _status(claim.get("status", claim.get("classification"))) == "confirmed"


def classify(claim: dict[str, Any]) -> tuple[str, str, bool]:
    outcomes: list[str] = []
    evidence: list[str] = []
    valid_count = 0
    for raw in _measurements(claim):
        outcome, valid, detail = _measurement_result(raw)
        evidence.append(detail)
        if valid:
            valid_count += 1
        if outcome in {"confirmed", "rejected"}:
            outcomes.append(outcome)
    if outcomes and len(set(outcomes)) == 1 and valid_count == len(outcomes):
        category = CONFIRMED if outcomes[0] == "confirmed" else REJECTED
    else:
        category = UNVERIFIED
    violation = _declared_confirmed(claim) and valid_count == 0
    return category, " ؛ ".join(evidence) if evidence else "لا يوجد قياس", violation


def _clip(text: Any, width: int = 48) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= width else s[: width - 1] + "…"


def main() -> int:
    parser = argparse.ArgumentParser(description="صنّف ادعاءات JSON بقياس قابل للتكرار")
    parser.add_argument("claims", type=Path, help="ملف JSON يحوي claims[]")
    args = parser.parse_args()
    try:
        claims = _load(args.claims)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"خطأ في ملف الادعاءات: {exc}", file=sys.stderr)
        return 3

    rows = []
    violations = 0
    for index, claim in enumerate(claims, 1):
        category, evidence, violation = classify(claim)
        violations += int(violation)
        if violation:
            evidence += " · مخالفة: confirmed بلا مقياس"
        rows.append((str(claim.get("id", index)), _clip(claim.get("claim", "")), category, _clip(evidence, 72)))

    headers = ("المعرّف", "الادعاء", "التصنيف", "دليل القياس")
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i]) for i in range(4)]
    sep = "-+-".join("-" * w for w in widths)
    print(" | ".join(headers[i].ljust(widths[i]) for i in range(4)))
    print(sep)
    for row in rows:
        print(" | ".join(row[i].ljust(widths[i]) for i in range(4)))
    print(f"\nالملخص: {len(rows)} ادعاء · مخالفات القياس: {violations}")
    return 2 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
