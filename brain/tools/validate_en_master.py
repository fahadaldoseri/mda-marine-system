#!/usr/bin/env python3
"""تحقق fail-closed من تطابق بنية الأصل الإنجليزي وأرقامه مع التقرير العربي."""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import sys

ARABIC_SCRIPT = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
HEADING = re.compile(r"^(#{1,6})\s+")
LIST_ITEM = re.compile(r"^[-*+]\s+")


def line_kind(line: str) -> str:
    """تصنيف نوع السطر، مع تضمين عدد خلايا صف الجدول في العقد البنيوي."""
    value = line.strip()
    if value.startswith("|"):
        return f"table/{len(value.strip('|').split('|'))}"
    heading = HEADING.match(value)
    if heading:
        return f"h{len(heading.group(1))}"
    if LIST_ITEM.match(value):
        return "list"
    if value.startswith(">"):
        return "quote"
    return "text"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(ar_path: pathlib.Path, en_path: pathlib.Path) -> tuple[list[str], dict[str, int | str]]:
    problems: list[str] = []
    try:
        ar_text = ar_path.read_text(encoding="utf-8")
        en_text = en_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"SOURCE_READ_ERROR: {exc}"], {}

    ar_lines = [line for line in ar_text.splitlines() if line.strip()]
    en_lines = [line for line in en_text.splitlines() if line.strip()]
    if len(ar_lines) != len(en_lines):
        problems.append(
            f"STRUCTURE_MISMATCH: nonempty_lines Arabic={len(ar_lines)} English={len(en_lines)}"
        )

    for index, (ar_line, en_line) in enumerate(zip(ar_lines, en_lines), start=1):
        ar_kind = line_kind(ar_line)
        en_kind = line_kind(en_line)
        if ar_kind != en_kind:
            problems.append(
                f"STRUCTURE_MISMATCH: aligned_line={index} Arabic={ar_kind} English={en_kind}"
            )
        ar_numbers = NUMBER.findall(ar_line)
        en_numbers = NUMBER.findall(en_line)
        if ar_numbers != en_numbers:
            problems.append(
                f"NUMBER_MISMATCH: aligned_line={index} Arabic={ar_numbers!r} English={en_numbers!r}"
            )

    arabic_chars = ARABIC_SCRIPT.findall(en_text)
    if arabic_chars:
        sample = "".join(arabic_chars[:12])
        problems.append(f"ARABIC_REMAINS: count={len(arabic_chars)} sample={sample!r}")

    table_rows = sum(1 for line in en_lines if line_kind(line).startswith("table/"))
    headings = sum(1 for line in en_lines if line_kind(line).startswith("h"))
    number_tokens = sum(len(NUMBER.findall(line)) for line in en_lines)
    metrics: dict[str, int | str] = {
        "bytes": en_path.stat().st_size,
        "nonempty_lines": len(en_lines),
        "headings": headings,
        "table_rows": table_rows,
        "number_tokens": number_tokens,
        "arabic_chars": len(arabic_chars),
        "sha256": sha256(en_path),
    }
    return problems, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arabic", required=True, type=pathlib.Path)
    parser.add_argument("--english", required=True, type=pathlib.Path)
    args = parser.parse_args()

    problems, metrics = validate(args.arabic, args.english)
    if problems:
        for problem in problems:
            print(f"✘ {problem}")
        if metrics:
            print(
                "EN_MASTER_MEASURE: "
                + " ".join(f"{key}={value}" for key, value in metrics.items())
            )
        return 2

    print("✔ EN_MASTER_STRUCTURE=PASS")
    print("EN_MASTER_MEASURE: " + " ".join(f"{key}={value}" for key, value in metrics.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
