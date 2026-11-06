#!/usr/bin/env python3
"""Measure literal and near-duplicate overlap between skill SKILL.md files."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

TOKEN_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)


def resolve_skill(path: Path) -> Path:
    """Accept either a skill directory or a SKILL.md path."""
    candidate = path / "SKILL.md" if path.is_dir() else path
    if not candidate.is_file():
        raise FileNotFoundError(f"SKILL.md غير موجود: {candidate}")
    return candidate


def normalize_line(line: str) -> str:
    return " ".join(line.casefold().split())


def read_lines(path: Path) -> list[str]:
    return [normalized for raw in path.read_text(encoding="utf-8").splitlines() if (normalized := normalize_line(raw))]


def similar_matches(left: list[str], right: list[str], threshold: float) -> tuple[int, int]:
    """Match each shorter-file line to at most one line in the other file."""
    if len(left) > len(right):
        left, right = right, left
    unused = set(range(len(right)))
    matches = 0
    for line in left:
        best_index = None
        best_score = threshold
        for index in unused:
            score = SequenceMatcher(None, line, right[index]).ratio()
            if score >= best_score:
                best_score = score
                best_index = index
        if best_index is not None:
            unused.remove(best_index)
            matches += 1
    return matches, len(left)


def phrases(lines: list[str], size: int = 3) -> set[str]:
    found: set[str] = set()
    for line in lines:
        tokens = TOKEN_RE.findall(line)
        found.update(" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1))
    return found


def pair_report(left_path: Path, right_path: Path, line_threshold: float, max_phrases: int) -> tuple[float, str]:
    left = read_lines(left_path)
    right = read_lines(right_path)
    left_counter = Counter(left)
    right_counter = Counter(right)
    exact = sum((left_counter & right_counter).values())
    matched, denominator = similar_matches(left, right, line_threshold)
    exact_pct = (exact / denominator * 100) if denominator else 0.0
    similar_pct = (matched / denominator * 100) if denominator else 0.0
    shared = sorted(phrases(left) & phrases(right))
    shown = shared[:max_phrases]
    phrase_text = ", ".join(repr(item) for item in shown) if shown else "(لا توجد)"
    report = (
        f"مقارنة: {left_path} <> {right_path}\n"
        f"  الأسطر غير الفارغة: {len(left)} <> {len(right)}؛ المقام: {denominator}\n"
        f"  الأسطر المكررة حرفيًا: {exact}؛ النسبة من الأصغر: {exact_pct:.2f}%\n"
        f"  الأسطر المتشابهة/المكررة (عتبة {line_threshold:.2f}): {matched}؛ النسبة من الأصغر: {similar_pct:.2f}%\n"
        f"  العبارات المشتركة (3 رموز فأكثر): {len(shared)}؛ المعروض: {phrase_text}"
    )
    return similar_pct, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="قِس التداخل الحرفي والوظيفي بين مهارتين أو أكثر قراءةً فقط."
    )
    parser.add_argument("skills", nargs="+", type=Path, help="مسارات مجلدات المهارات أو ملفات SKILL.md")
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="عتبة التداخل كنسبة من أصغر ملف (افتراضي: 20.0)؛ تجاوزها يعيد 1",
    )
    parser.add_argument(
        "--line-threshold",
        type=float,
        default=0.85,
        help="عتبة تشابه السطر بين 0 و1 (افتراضي: 0.85)",
    )
    parser.add_argument("--max-phrases", type=int, default=10, help="عدد العبارات المعروضة لكل مقارنة (افتراضي: 10)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if len(args.skills) < 2:
        parser.error("مرّر مساري مهارتين على الأقل")
    if not 0 <= args.line_threshold <= 1:
        parser.error("--line-threshold يجب أن يكون بين 0 و1")
    if args.threshold < 0 or args.max_phrases < 0:
        parser.error("--threshold و--max-phrases لا يقبلان قيمة سالبة")

    try:
        paths = [resolve_skill(path) for path in args.skills]
    except (OSError, FileNotFoundError) as error:
        print(f"خطأ: {error}", file=sys.stderr)
        return 2

    exceeded = False
    print(f"العتبة الكلية: {args.threshold:.2f}%؛ عتبة السطر: {args.line_threshold:.2f}")
    for left, right in combinations(paths, 2):
        overlap, report = pair_report(left, right, args.line_threshold, args.max_phrases)
        print(report)
        if overlap > args.threshold:
            exceeded = True
            print(f"  الحكم: تجاوز العتبة ({overlap:.2f}% > {args.threshold:.2f}%)")
        else:
            print(f"  الحكم: دون العتبة ({overlap:.2f}% <= {args.threshold:.2f}%)")
    return 1 if exceeded else 0


if __name__ == "__main__":
    raise SystemExit(main())
