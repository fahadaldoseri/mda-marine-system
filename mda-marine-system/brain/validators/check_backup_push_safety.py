#!/usr/bin/env python3
"""حاجز فشل مغلق يمنع دفع النسخة الاحتياطية مباشرة إلى main."""
from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path


_PUSH = re.compile(r"(?<![\w-])git[ \t]+push(?:[ \t]+|$)(.*)$")
_MAIN_REF = re.compile(r"(?:^|/|:)main$")


def _strip_comment(line: str) -> str:
    """احذف تعليق shell خارج علامات الاقتباس دون تغيير الأوامر."""
    quote = ""
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote != "'":
            escaped = True
            continue
        if char in "'\"":
            if not quote:
                quote = char
            elif quote == char:
                quote = ""
            continue
        if char == "#" and not quote:
            return line[:index]
    return line


def _logical_lines(text: str):
    pending = ""
    start = 1
    for number, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw).rstrip()
        if not pending:
            start = number
        pending += line.lstrip()
        if pending.endswith("\\"):
            pending = pending[:-1]
            continue
        yield start, pending
        pending = ""
    if pending:
        yield start, pending


def direct_main_pushes(text: str) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    for line_number, line in _logical_lines(text):
        match = _PUSH.search(line)
        if not match:
            continue
        try:
            args = shlex.split(match.group(1), posix=True)
        except ValueError as exc:
            findings.append((line_number, f"تعذر تحليل أمر git push: {exc}"))
            continue
        for token in args:
            if token.startswith("-"):
                continue
            if _MAIN_REF.search(token):
                findings.append((line_number, f"وجهة دفع مباشرة محظورة: {token}"))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        text = args.script.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"✘ فشل مغلق: تعذر قراءة {args.script}: {exc}", file=sys.stderr)
        return 2
    findings = direct_main_pushes(text)
    if findings:
        print(f"✘ فشل مغلق: {len(findings)} دفعًا مباشرًا إلى main في {args.script}")
        for line, detail in findings:
            print(f"  السطر {line}: {detail}")
        return 2
    print(f"✔ آمن: لا يوجد git push مباشر إلى main في {args.script}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
