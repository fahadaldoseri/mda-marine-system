#!/usr/bin/env python3
"""بوابة قابلة للتخصيص لربط الأرقام المنشورة بملفاتها الحاكمة."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Mapping, Sequence


# عدّل هذه القائمة في نسخة المشروع المضيف. لا تضع قيمة متوقعة يدويًا في الربط.
@dataclass(frozen=True)
class NumberRecord:
    approved: int
    qualified: Mapping[str, int] = field(default_factory=dict)
    unit_terms: tuple[str, ...] = ()
    approved_terms: tuple[str, ...] = ()


def _json_record(path: Path, default_units: Sequence[str]) -> NumberRecord:
    """استخرج السجل من JSON حاكم؛ يمكن استبدال هذه الدالة بملف Markdown أو قاعدة بيانات."""
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict) or "approved" not in data:
        raise ValueError(f"ملف المالك لا يحتوي على approved: {path}")
    approved = data["approved"]
    if not isinstance(approved, int) or isinstance(approved, bool) or approved < 0:
        raise ValueError(f"قيمة approved غير صالحة في: {path}")
    raw_qualified = data.get("qualified", {})
    if not isinstance(raw_qualified, dict):
        raise ValueError(f"qualified يجب أن يكون كائنًا في: {path}")
    qualified: dict[str, int] = {}
    for qualifier, value in raw_qualified.items():
        if not isinstance(qualifier, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"قيمة مؤهلة غير صالحة في: {path}")
        qualified[qualifier] = value
    raw_units = data.get("unit_terms", list(default_units))
    raw_approved_terms = data.get("approved_terms", [])
    if not isinstance(raw_units, list) or not all(isinstance(item, str) for item in raw_units):
        raise ValueError(f"unit_terms غير صالحة في: {path}")
    if not isinstance(raw_approved_terms, list) or not all(isinstance(item, str) for item in raw_approved_terms):
        raise ValueError(f"approved_terms غير صالحة في: {path}")
    return NumberRecord(
        approved=approved,
        qualified=qualified,
        unit_terms=tuple(raw_units),
        approved_terms=tuple(raw_approved_terms),
    )


# دوال استخراج نموذجية: استبدلها بما يلائم ملفات المالك الفعلية.
def extract_sources(path: Path) -> NumberRecord:
    return _json_record(path, ("مصدر", "مصادر"))


def extract_imo_attacks(path: Path) -> NumberRecord:
    return _json_record(path, ("هجمة", "هجمات", "IMO"))


def extract_sailor_deaths(path: Path) -> NumberRecord:
    return _json_record(path, ("وفاة", "وفيات", "بحار", "البحارة"))


# كل ربط = (اسم الرقم، ملف المالك، دالة استخراج، السطح المنشور، ملف المقارنة).
# تفحص البوابة السطح المنشور وملف المقارنة بوصفهما سطحين حاليين صريحين.
BINDINGS: list[tuple[str, str, Callable[[Path], NumberRecord], str, str]] = [
    (
        "عدد المصادر المعتمد",
        "owners/sources.json",
        extract_sources,
        "current/report.md",
        "current/runbook/runbook.json",
    ),
    (
        "عداد هجمات IMO المعتمد",
        "owners/imo_attacks.json",
        extract_imo_attacks,
        "current/report.md",
        "current/runbook/runbook.json",
    ),
    (
        "عداد وفيات البحارة المعتمد",
        "owners/sailor_deaths.json",
        extract_sailor_deaths,
        "current/report.md",
        "current/runbook/runbook.json",
    ),
]


NUMBER_RE = re.compile(r"(?<![\w])(?P<number>\d+)(?![\w])")
ARCHIVE_MARKERS = {
    "archive",
    "archives",
    "historical",
    "history",
    "old",
    "previous",
    "أرشيف",
    "الأرشيف",
    "تاريخي",
    "التاريخي",
}
QUALIFIER_MARKERS: dict[str, tuple[str, ...]] = {
    "approved": ("معتمد", "معتمدة", "المعتمد", "المعتمدة", "approved"),
    "checked": ("مفحوص", "مفحوصًا", "فحص", "checked"),
    "cited": ("مستشهد", "مستشهدًا", "مستند", "مستشهد به", "cited"),
    "at_time": ("آنذاك", "ذلك التشغيل", "في ذلك التشغيل", "at_time"),
}


@dataclass(frozen=True)
class Claim:
    number: int
    kind: str
    context: str


def _resolve_under_brain(brain: Path, relative: str, role: str) -> Path:
    if not relative or relative in {"-", "none", "None"}:
        raise ValueError(f"مسار {role} فارغ")
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValueError(f"مسار {role} يجب أن يكون نسبيًا إلى brain: {relative}")
    root = brain.resolve()
    resolved = (root / candidate).resolve()
    try:
        relative_parts = resolved.relative_to(root).parts
    except ValueError as exc:
        raise ValueError(f"مسار {role} يخرج من brain: {relative}") from exc
    lowered = {part.casefold() for part in relative_parts}
    if role != "المالك" and lowered.intersection(ARCHIVE_MARKERS):
        raise ValueError(f"النطاق الحالي لا يشمل الأرشيف: {relative}")
    return resolved


def _nearest_kind(text: str, start: int, end: int, record: NumberRecord) -> str | None:
    window_start = max(0, start - 32)
    window_end = min(len(text), end + 32)
    marker_candidates: list[tuple[int, str]] = []
    markers = dict(QUALIFIER_MARKERS)
    if record.approved_terms:
        markers["approved"] = markers["approved"] + record.approved_terms
    for kind, values in markers.items():
        for marker in values:
            cursor = window_start
            while True:
                index = text.find(marker, cursor, window_end)
                if index < 0:
                    break
                marker_center = index + (len(marker) / 2)
                number_center = start + ((end - start) / 2)
                marker_candidates.append((int(abs(marker_center - number_center)), kind))
                cursor = index + max(1, len(marker))
    if not marker_candidates:
        return None
    marker_candidates.sort(key=lambda item: item[0])
    return marker_candidates[0][1]


def _claims_in_text(text: str, record: NumberRecord) -> list[Claim]:
    claims: list[Claim] = []
    for match in NUMBER_RE.finditer(text):
        start, end = match.span("number")
        context_start = max(0, start - 48)
        context_end = min(len(text), end + 48)
        context = text[context_start:context_end]
        kind = _nearest_kind(text, start, end, record)
        unit_start = max(0, start - 16)
        unit_end = min(len(text), end + 16)
        unit_context = text[unit_start:unit_end]
        has_unit = any(term and term in unit_context for term in record.unit_terms)
        # لا تكفي كلمة مؤهل بعيدة؛ يجب أن تكون الوحدة ملاصقة للرقم حتى لا تختلط
        # أرقام عدادات مختلفة في السطح نفسه.
        if not has_unit:
            continue
        claims.append(Claim(number=int(match.group("number")), kind=kind or "plain", context=" ".join(context.split())))
    return claims


def _surface_paths(brain: Path, surface: str, comparison: str) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for label, relative in (("السطح", surface), ("المقارنة", comparison)):
        resolved = _resolve_under_brain(brain, relative, label)
        if resolved in seen:
            continue
        seen.add(resolved)
        paths.append((label, resolved))
    return paths


def _check_binding(brain: Path, binding: tuple[str, str, Callable[[Path], NumberRecord], str, str]) -> tuple[str, int, list[int], list[str]]:
    name, owner_relative, extractor, surface_relative, comparison_relative = binding
    owner = _resolve_under_brain(brain, owner_relative, "المالك")
    if not owner.is_file():
        raise FileNotFoundError(f"ملف المالك غير موجود: {owner_relative}")
    record = extractor(owner)
    if not isinstance(record, NumberRecord):
        raise TypeError(f"دالة الاستخراج لم تُعد NumberRecord: {name}")
    observed: list[int] = []
    problems: list[str] = []
    for label, surface_path in _surface_paths(brain, surface_relative, comparison_relative):
        if not surface_path.is_file():
            problems.append(f"{label} غير موجود: {surface_path.relative_to(brain.resolve())}")
            continue
        text = surface_path.read_text(encoding="utf-8")
        claims = _claims_in_text(text, record)
        observed.extend(claim.number for claim in claims)
        approved_claims = [claim.number for claim in claims if claim.kind == "approved"]
        if record.approved not in approved_claims:
            shown = ", ".join(str(value) for value in approved_claims) or "لا يوجد"
            problems.append(
                f"{label} لا يثبت ادعاء المعتمد {record.approved}؛ القيم المصنفة المعتمدة: {shown}"
            )
        for claim in claims:
            if claim.kind == "plain" and any(term and term in claim.context for term in record.unit_terms):
                if claim.number != record.approved:
                    problems.append(
                        f"{label} يحتوي كمية غير مؤهلة {claim.number} بدل المعتمد {record.approved}"
                    )
            elif claim.kind in QUALIFIER_MARKERS and claim.kind != "approved":
                if claim.kind not in record.qualified:
                    problems.append(
                        f"{label} يحتوي مؤهلًا بلا مالك: {claim.kind}={claim.number}"
                    )
                elif claim.number != record.qualified[claim.kind]:
                    problems.append(
                        f"{label} يخالف الكمية {claim.kind}: {claim.number} بدل {record.qualified[claim.kind]}"
                    )
    return name, record.approved, observed, problems


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="افحص ربط الأرقام المنشورة بملفاتها الحاكمة على الأسطح الحالية فقط."
    )
    parser.add_argument(
        "--brain",
        default=".",
        help="جذر نسخة الدماغ/البيانات المعزولة؛ الافتراضي هو المجلد الحالي.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="تاريخ القياس بصيغة YYYY-MM-DD، ويظهر في جدول القياس.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    brain = Path(args.brain)
    rows: list[tuple[str, str, str, str, str]] = []
    problems: list[str] = []
    try:
        if not brain.is_dir():
            raise NotADirectoryError(f"brain ليس مجلدًا: {brain}")
        if not BINDINGS:
            raise ValueError("BINDINGS فارغة؛ الفشل مغلق")
        for binding in BINDINGS:
            name = binding[0] if binding else "ربط بلا اسم"
            try:
                checked_name, expected, observed, binding_problems = _check_binding(brain, binding)
                status = "اجتاز" if not binding_problems else "فشل"
                rows.append(
                    (
                        checked_name,
                        str(expected),
                        ",".join(str(value) for value in observed) or "لا يوجد",
                        status,
                        "; ".join(binding_problems) or "-",
                    )
                )
                problems.extend(f"{checked_name}: {problem}" for problem in binding_problems)
            except Exception as exc:  # اجعل كل خطأ فشلًا مغلقًا دون traceback للمشغّل.
                rows.append((name, "؟", "؟", "فشل", str(exc)))
                problems.append(f"{name}: {exc}")
    except Exception as exc:
        problems.append(str(exc))

    print(f"جدول القياس | التاريخ: {args.date} | brain: {brain}")
    print("الرقم | المتوقع المعتمد | المرصود | الحالة | الملاحظة")
    print("--- | ---: | --- | --- | ---")
    if rows:
        for name, expected, observed, status, note in rows:
            print(f"{name} | {expected} | {observed} | {status} | {note}")
    else:
        print("لا توجد قياسات | ؟ | ؟ | فشل | لم يمكن بناء أي ربط")
    if problems:
        print("الأخطاء:")
        for problem in problems:
            print(f"- {problem}")
    verdict = "PASS" if not problems and rows else "FAIL"
    print(f"VERDICT: {verdict}")
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
