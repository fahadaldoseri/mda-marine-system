#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة حقول علاقة دفتر الوقائع — فشل مغلق.

تتحقق من أن نوع العلاقة يطابق حقله، وأن المرجع يشير إلى رمز أقدم موجود، وأن
العلاقة موثقة بأساس ودليل، وأن السطح المبني لا يعرض عبارات غياب العلاقة.

الاستعمال:
  python3 validators/check_ledger_links.py --date 2026-11-02 --brain . --site ../seawatch

رموز الخروج: 0 = مطابق · 2 = منع · 70 = انهيار المدقق.
"""
from __future__ import annotations

import argparse
import datetime as _datetime
import json
import pathlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELATION_FIELDS = ("update_of", "parent_id", "duplicate_of")
KIND_TO_FIELD = {"تحديث": "update_of", "تكرار": "duplicate_of", "فرع تابع": "parent_id"}

# ك-507: مصدر واحد للأنواع المعتمدة = مخطط الدفتر نفسه. وصنف «تحديث بيانات» معتمد
# بقرار المالك: صف يعلن تحديث أرقام تراكمية من مصدر رسمي، ليس واقعة ولا فرعًا تابعًا،
# ولذلك لا يُطلب له حقل علاقة — ويُستبعد من سطح سجل الأحداث عند العرض.
_SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[1] / "schemas" / "daily-events.schema.json"
RELATION_FREE_KINDS = {"جديد", "تحديث بيانات", "no_incident", "incident", "legacy_projection"}


def _schema_event_kinds(fallback: tuple) -> tuple:
    try:
        spec = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        enum = spec["$defs"]["material_record"]["properties"]["event_kind"]["enum"]
    except (OSError, ValueError, KeyError, TypeError):
        return fallback
    return tuple(enum) if isinstance(enum, list) and enum else fallback


ALLOWED_KINDS = set(_schema_event_kinds(("جديد", "تحديث", "تكرار", "فرع تابع", "تحديث بيانات")))
ABSENCE_RELATION_RE = re.compile(
    r"لا\s+فرع\s+تابع|فجوة\s+(?:بيانات\s+)?الربط|لم\s+تُنشأ\s+علاقة|"
    r"لا\s+توجد[^\n.]{0,100}علاقة|لم\s+يُعثر\s+على\s+الواقعة\s+السابقة"
)
CODE_SEQ_RE = re.compile(r"-(\d+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_FIELDS = ("official_ref", "title", "source_excerpt", "imo_number", "source")
_DIGIT_TRANSLATION = str.maketrans(
    {ord(chr(start + i)): ord(str(i)) for start in (0x0660, 0x06F0) for i in range(10)}
)
_PUNCT_TRANSLATION = str.maketrans({
    "؛": ";", "﹔": ";", "،": ",", "﹐": ",", "：": ":", "﹕": ":",
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    "／": "/", "⁄": "/", "＿": "_",
})
_FORMAT_MARKS = str.maketrans({ch: None for ch in "\u200b\u200c\u200d\ufeff"})


def _text(value) -> str:
    return str(value or "").strip()


def _normalize_literal(value: str) -> str:
    """Normalize only representation, never meaning, before literal matching."""
    text = _text(value).translate(_DIGIT_TRANSLATION)
    text = text.translate(_PUNCT_TRANSLATION).translate(_FORMAT_MARKS)
    return " ".join(text.casefold().split())


def _source_text_fields(row: dict) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for field in SOURCE_FIELDS:
        value = row.get(field)
        if isinstance(value, list):
            fields.extend((f"{field}[{index}]", _text(item)) for index, item in enumerate(value))
        else:
            text = _text(value)
            if field == "source" and re.match(r"(?i)^https?://", text):
                continue
            fields.append((field, text))
    return [(field, text) for field, text in fields if text]


def _check_literal_evidence(item: dict, target: dict | None, problems: list[str]) -> None:
    row = item["row"]
    code = _text(row.get("code"))
    raw_evidence = _text(row.get("link_evidence"))
    if not raw_evidence:
        return
    if ";" in raw_evidence:
        problems.append(
            f"دليل العلاقة ليس بصيغة الفاصل العربي في {code}: "
            f"المكوّنات يجب أن تفصل بـ«؛» لا «;»"
        )
    components = [part.strip() for part in raw_evidence.split("؛")]
    if any(not component for component in components):
        problems.append(f"دليل العلاقة يحوي مكوّنًا فارغًا في {code}: {raw_evidence}")
        components = [component for component in components if component]
    search_rows: list[tuple[str, dict]] = [("حقول الصف المصدر", row)]
    basis = _text(row.get("link_basis"))
    if target is not None and basis.startswith("معرّف رسمي مشترك بين مصدرين"):
        search_rows.append(("حقول الصف الهدف (قاعدة المعرّف الرسمي المشترك)", target["row"]))
    for component in components:
        normalized_component = _normalize_literal(component)
        if not normalized_component:
            continue
        found = False
        for _place, search_row in search_rows:
            for _field, value in _source_text_fields(search_row):
                if normalized_component in _normalize_literal(value):
                    found = True
                    break
            if found:
                break
        if not found:
            places = " أو ".join(place for place, _search_row in search_rows)
            problems.append(
                f"دليل العلاقة غير حرفي في {code}: المكوّن «{component}» "
                f"غير موجود؛ مكان البحث: {places}"
            )


def _record_date(row: dict, file_date: str) -> str:
    for key in ("date", "date_start", "occurred_on"):
        value = _text(row.get(key))
        if value:
            return value[:10]
    return file_date


def _chronology(row: dict, file_date: str) -> tuple[_datetime.date, int] | None:
    raw_date = _record_date(row, file_date)
    if not DATE_RE.fullmatch(raw_date):
        return None
    try:
        day = _datetime.date.fromisoformat(raw_date)
    except ValueError:
        return None
    code = _text(row.get("code"))
    match = CODE_SEQ_RE.search(code)
    return day, int(match.group(1)) if match else -1


def _load_records(brain: Path) -> tuple[list[dict], list[str]]:
    daily = brain / "cumulative-2026" / "daily"
    records: list[dict] = []
    problems: list[str] = []
    if not daily.is_dir():
        return [], [f"مجلد الدفتر اليومي مفقود: {daily}"]
    for path in sorted(daily.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            problems.append(f"ملف دفتر غير صالح: {path.name}: {exc}")
            continue
        if not isinstance(data, list):
            problems.append(f"ملف دفتر ليس قائمة سجلات: {path.name}")
            continue
        for index, row in enumerate(data, 1):
            if not isinstance(row, dict):
                problems.append(f"سجل غير كائن: {path.name}:{index}")
                continue
            code = _text(row.get("code"))
            if not code:
                problems.append(f"سجل بلا code: {path.name}:{index}")
                continue
            records.append({"row": row, "file": path, "file_date": path.stem})
    return records, problems


def _selected(records: list[dict], date: str) -> list[dict]:
    if not date:
        return records
    name = f"{date}.json"
    return [item for item in records if item["file"].name == name]


def _check_schema(item: dict, codes: dict[str, dict], problems: list[str]) -> tuple[str, str] | None:
    row = item["row"]
    code = _text(row.get("code"))
    kind = _text(row.get("event_kind"))
    values = {field: _text(row.get(field)) for field in RELATION_FIELDS}
    present = {field for field, value in values.items() if value}
    if kind and kind not in ALLOWED_KINDS:
        problems.append(f"event_kind غير معروف: {code} — {kind}")
        return None
    expected = KIND_TO_FIELD.get(kind)
    if kind in RELATION_FREE_KINDS and present:
        problems.append(f"event_kind جديد مع حقل علاقة: {code} — {', '.join(sorted(present))}")
    elif expected and expected not in present:
        problems.append(f"event_kind بلا الحقل المقابل: {code} — {kind} يحتاج {expected}")
    for field in sorted(present):
        if not kind:
            problems.append(f"حقل علاقة بلا event_kind مطابق: {code} — {field}")
        elif field != expected:
            problems.append(f"حقل علاقة لا يطابق event_kind: {code} — {field} مع {kind}")
    if not present or not expected or expected not in present:
        return None
    return expected, values[expected]


def _check_target(item: dict, field: str, target_code: str, code_items: dict[str, dict], problems: list[str]) -> None:
    row = item["row"]
    code = _text(row.get("code"))
    if not _text(row.get("link_basis")):
        problems.append(f"علاقة بلا link_basis: {code}")
    if not _text(row.get("link_evidence")):
        problems.append(f"علاقة بلا link_evidence: {code}")
    target = code_items.get(target_code)
    _check_literal_evidence(item, target, problems)
    if target is None:
        problems.append(f"معرّف معلّق في {field}: {code} ← {target_code}")
        return
    if target_code == code:
        problems.append(f"العلاقة تشير إلى الصف نفسه: {code} ← {target_code}")
        return
    source_key = _chronology(row, item["file_date"])
    target_item = target
    target_key = _chronology(target_item["row"], target_item["file_date"])
    if source_key is None or target_key is None:
        problems.append(f"تاريخ غير صالح للتحقق من قدم العلاقة: {code} ← {target_code}")
    elif target_key >= source_key:
        problems.append(f"هدف العلاقة أحدث أو مساوٍ زمنيًا: {code} ← {target_code}")


def _find_cycles(edges: dict[str, str]) -> list[str]:
    cycles: list[str] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        target = edges.get(node)
        if target:
            if state.get(target) == 1:
                start = stack.index(target)
                cycles.append(" → ".join(stack[start:] + [target]))
            elif state.get(target, 0) == 0:
                visit(target)
        stack.pop()
        state[node] = 2

    for node in edges:
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def _check_built_pages(site: Path, problems: list[str]) -> int:
    pages = sorted(site.rglob("*.html")) if site.is_dir() else []
    hits = 0
    for page in pages:
        try:
            text = page.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            problems.append(f"تعذر قراءة الصفحة المبنية {page}: {exc}")
            continue
        if ABSENCE_RELATION_RE.search(text):
            hits += 1
            problems.append(f"عبارة غياب علاقة في صفحة مبنية: {page}")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="بوابة حقول علاقة دفتر الوقائع (فشل مغلق)",
                                     allow_abbrev=False)
    parser.add_argument("--date", required=True, help="ملف اليوم المستهدف YYYY-MM-DD")
    parser.add_argument("--brain", default=str(ROOT), help="جذر brain")
    parser.add_argument("--site", default=None, help="جذر seawatch؛ اختياري لفحص HTML المبني")
    args = parser.parse_args()

    brain = Path(args.brain).resolve()
    site = Path(args.site).resolve() if args.site else brain.parent / "seawatch"
    records, problems = _load_records(brain)
    selected = _selected(records, args.date)
    if not selected:
        problems.append(f"لا توجد سجلات في دفتر اليوم: {args.date}")

    code_items: dict[str, dict] = {}
    for item in records:
        code = _text(item["row"].get("code"))
        code_items.setdefault(code, item)

    edges: dict[str, str] = {}
    for item in records:
        code = _text(item["row"].get("code"))
        for field in RELATION_FIELDS:
            target = _text(item["row"].get(field))
            if target:
                edges.setdefault(code, target)
    relation_count = 0
    for item in selected:
        relation = _check_schema(item, code_items, problems)
        if relation is None:
            continue
        field, target_code = relation
        relation_count += 1
        code = _text(item["row"].get("code"))
        _check_target(item, field, target_code, code_items, problems)
        edges[code] = target_code

    for cycle in _find_cycles(edges):
        problems.append(f"سلسلة علاقة دائرية: {cycle}")

    page_hits = _check_built_pages(site, problems)
    print("   ══ بوابة حقول علاقة دفتر الوقائع ══")
    print(f"   اليوم: {args.date} · سجلات الدفتر: {len(records)} · العلاقات المفحوصة: {relation_count} · صفحات HTML: {page_hits}")
    if problems:
        print(f"   ✘ مشكلات: {len(problems)}")
        for problem in problems[:40]:
            print(f"      - {problem}")
        print("   النتيجة: منع — فشل مغلق")
        return 2
    print("   ✔ اجتاز: حقول العلاقة متسقة، الأهداف أقدم، والأدلة والأسطح سليمة")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
