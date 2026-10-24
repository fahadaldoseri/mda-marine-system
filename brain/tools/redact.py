#!/usr/bin/env python3
"""إخفاء الأسرار من أي نص يُكتب في سجل أو يُدفع أو يُرسل.

الغرض: لا يظهر سرّ في أي سجل تشغيل، ولا في أي مخرج يُحفظ أو يُدفع.
الاستخدام:
  python3 tools/redact.py < ملف   → يطبع النص بعد الإخفاء
  from redact import redact       → للاستخدام داخل الأدوات
"""
from __future__ import annotations

import os
import re
import sys

# ── أنماط الأسرار المعروفة (تُخفى دائمًا) ──
PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"), "<رمز-بوت-محجوب>"),
    (re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}\b"), "<مفتاح-محجوب>"),
    (re.compile(r"\b(?:ghp|gho|ghs|ghr)_[A-Za-z0-9]{20,}\b"), "<رمز-github-محجوب>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<مفتاح-aws-محجوب>"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"), "<مفتاح-google-محجوب>"),
    (re.compile(r"(?i)\b(token|api_key|apikey|secret|password|passwd|bot_token|access_key)\b"
                r"(\s*[=:]\s*)([\"']?)([A-Za-z0-9_\-]{16,})"),
     r"\1\2\3<محجوب>"),
    (re.compile(r"(?i)(bot)(\d{6,12}):([A-Za-z0-9_-]{20,})"), r"\1\2:<محجوب>"),
]

_ENV_NAME = re.compile(r"(TOKEN|SECRET|API_KEY|APIKEY|PASSWORD|PASSWD|KEY)$")


def secret_values() -> list[str]:
    """قيم الأسرار الفعلية الموجودة في البيئة، لإخفائها إن ظهرت حرفيًا في نص."""
    vals: list[str] = []
    for name, value in os.environ.items():
        if not value or len(value) < 12:
            continue
        if _ENV_NAME.search(name.upper()):
            vals.append(value)
    return sorted(set(vals), key=len, reverse=True)


def redact(text: str) -> str:
    """يعيد النص بعد إخفاء كل سرّ فيه."""
    if not text:
        return text
    out = text
    for value in secret_values():
        if value in out:
            out = out.replace(value, "<سرّ-محجوب>")
    for pattern, repl in PATTERNS:
        out = pattern.sub(repl, out)
    return out


def redact_lines(lines: list[str]) -> list[str]:
    return [redact(line) for line in lines]


def main() -> int:
    sys.stdout.write(redact(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())