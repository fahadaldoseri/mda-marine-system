#!/usr/bin/env python3
"""دمج مصادر السجل المرتبطة بالواقعة نفسها دون إسقاط مقتطف أي مصدر.

المخرج يحافظ على الصفوف الأصلية، ويجمع المصادر في الصف الجذر الذي تشير إليه
`duplicate_of`. الحقل `source` يبقى سطرًا واحدًا بأسماء فريدة مفصولة بفواصل،
والحقل `sources` يحفظ مقتطفًا لكل اسم. لا تُعدّل الأداة العنوان؛ بل تعيد مؤشرًا
صريحًا لتوليده فقط عندما أضيفت معلومة نصية جديدة فعلية.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

SOURCE_SEPARATOR = ", "
_SPLIT_SOURCES = re.compile(r"\s*(?:,|،|؛|;|·)\s*")
_TOKEN = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)


class MergeEventSourcesError(ValueError):
    """خطأ عقدي يمنع إخراج سجل مصادر ناقص أو ملتبس."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MergeEventSourcesError(f"{field} يجب أن يكون نصًا غير فارغًا")
    return " ".join(value.split())


def _key(value: str) -> str:
    return " ".join(value.casefold().split())


def _tokens(value: str) -> set[str]:
    return {m.group(0).casefold() for m in _TOKEN.finditer(value)}


def _entry(name: Any, excerpt: Any) -> dict[str, str]:
    return {"name": _text(name, "اسم المصدر"), "excerpt": _text(excerpt, "مقتطف المصدر")}


def _row_entries(row: dict[str, Any]) -> list[dict[str, str]]:
    """اقرأ الشكل الجديد أو الشكل القديم إلى قائمة اسم/مقتطف موحّدة."""
    if isinstance(row.get("sources"), list):
        entries: list[dict[str, str]] = []
        for item in row["sources"]:
            if not isinstance(item, dict):
                raise MergeEventSourcesError("كل عنصر في sources يجب أن يكون كائنًا")
            name = item.get("name", item.get("source"))
            excerpt = item.get("excerpt", item.get("source_excerpt"))
            entries.append(_entry(name, excerpt))
    else:
        source = row.get("source")
        if isinstance(source, list):
            names = source
        else:
            source_text = _text(source, "source")
            names = [n for n in _SPLIT_SOURCES.split(source_text) if n.strip()]
        excerpt = row.get("source_excerpt")
        excerpts = row.get("source_excerpts")
        entries = []
        for name in names:
            selected = excerpts.get(name) if isinstance(excerpts, dict) else excerpt
            entries.append(_entry(name, selected))
    if not entries:
        raise MergeEventSourcesError("لا يجوز أن تكون قائمة المصادر فارغة")
    return entries


def _merge_entry(target: list[dict[str, str]], incoming: dict[str, str]) -> tuple[bool, bool]:
    """أضف مصدرًا؛ أعد (أضيف اسم جديد، أضيفت معلومة نصية جديدة)."""
    incoming_key = _key(incoming["name"])
    for current in target:
        if _key(current["name"]) != incoming_key:
            continue
        old_excerpt = current["excerpt"]
        if _key(old_excerpt) == _key(incoming["excerpt"]):
            return False, False
        old_tokens = _tokens(old_excerpt)
        new_tokens = _tokens(incoming["excerpt"])
        if incoming["excerpt"] not in old_excerpt and old_excerpt not in incoming["excerpt"]:
            current["excerpt"] = f"{old_excerpt} / {incoming['excerpt']}"
        return False, bool(new_tokens - old_tokens)
    target.append(copy.deepcopy(incoming))
    existing_tokens = set().union(*(_tokens(x["excerpt"]) for x in target[:-1])) if len(target) > 1 else set()
    return True, bool(_tokens(incoming["excerpt"]) - existing_tokens)


def _root_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    by_code: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise MergeEventSourcesError("كل سجل واقعة يجب أن يكون كائنًا")
        code = _text(row.get("code"), "code")
        if code in by_code:
            raise MergeEventSourcesError(f"رمز واقعة مكرر: {code}")
        by_code[code] = row
    roots: dict[str, str] = {}
    for code in by_code:
        seen: set[str] = set()
        current = code
        while by_code[current].get("duplicate_of"):
            if current in seen:
                raise MergeEventSourcesError(f"دورة duplicate_of عند {code}")
            seen.add(current)
            target = _text(by_code[current]["duplicate_of"], "duplicate_of")
            if target not in by_code:
                raise MergeEventSourcesError(f"هدف duplicate_of غير موجود: {target}")
            current = target
        roots[code] = current
    return roots


def merge_event_records(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """ادمج مصادر كل مجموعة duplicate_of وأعد الصفوف والتقرير القابل للتدقيق."""
    result = copy.deepcopy(rows)
    roots = _root_map(result)
    entries_by_root: dict[str, list[dict[str, str]]] = {}
    title_codes: set[str] = set()
    for row in result:
        code = _text(row.get("code"), "code")
        if roots[code] != code:
            continue
        base_entries: list[dict[str, str]] = []
        for incoming in _row_entries(row):
            _merge_entry(base_entries, incoming)
        entries_by_root[code] = base_entries
    for row in result:
        code = _text(row.get("code"), "code")
        root = roots[code]
        if code == root:
            continue
        for incoming in _row_entries(row):
            _, extra_fact = _merge_entry(entries_by_root[root], incoming)
            if extra_fact:
                title_codes.add(root)
    for row in result:
        code = _text(row.get("code"), "code")
        if roots[code] != code:
            continue
        entries = entries_by_root[code]
        row["source"] = SOURCE_SEPARATOR.join(item["name"] for item in entries)
        row["sources"] = entries
    report = {
        "merged_groups": len(entries_by_root),
        "title_regeneration_required_codes": sorted(title_codes),
        "source_separator": SOURCE_SEPARATOR,
    }
    return result, report

# اسم مختصر مريح للاستخدام من الأدوات الخارجية.
merge_event_sources = merge_event_records


def _indent_of(text: str) -> int:
    for line in text.splitlines()[1:3]:
        stripped = line.lstrip(" ")
        if stripped and len(line) != len(stripped):
            return len(line) - len(stripped)
    return 2


def merge_ledger(daily_dir: Path, apply: bool) -> dict[str, Any]:
    """الدمج على الدفتر اليومي كله (S074): مجموعات duplicate_of تعبر الأيام.

    لا يُلمس إلا صف جذر له تكرار واحد على الأقل، ولا يُكتب فيه إلا `sources`
    و`sources_basis`. الحقل `source` يبقى كما هو لأن مدققات سجل المصادر تقرؤه.
    """
    files: list[tuple[Path, str, list[dict[str, Any]]]] = []
    rows: list[dict[str, Any]] = []
    for f in sorted(daily_dir.glob("*.json")):
        text = f.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, list):
            continue
        data = [r for r in data if isinstance(r, dict)]
        files.append((f, text, data))
        rows.extend(r for r in data if r.get("code"))
    seen: set[str] = set()
    unique = []
    for r in rows:  # رمز مكرر عبر ملفين لا يُسقط الدمج كله: الأول يحكم
        if r["code"] in seen:
            continue
        seen.add(r["code"])
        unique.append(r)
    codes = {r["code"] for r in unique}
    usable = [r for r in unique if not r.get("duplicate_of") or r["duplicate_of"] in codes]
    # تكرار يشير إلى الدفتر المجمّد أو سجل IMO خارج اليومي: يبقى بلا دمج
    usable_codes = {r["code"] for r in usable}
    usable = [dict(r, duplicate_of=r.get("duplicate_of") if r.get("duplicate_of") in usable_codes else None)
              for r in usable]
    roots = _root_map(usable)
    grouped = {roots[c] for c in roots if roots[c] != c}
    new_sources: dict[str, list[dict[str, str]]] = {}
    skipped: list[dict[str, str]] = []
    titles: list[str] = []
    for root in sorted(grouped):  # كل مجموعة وحدها: صف بلا مقتطف يُسجَّل ولا يُسقط بقية الدفتر
        members = [r for r in usable if roots[r["code"]] == root]
        try:
            merged, report = merge_event_records(members)
        except MergeEventSourcesError as exc:
            skipped.append({"root": root, "reason": str(exc)})
            continue
        new_sources[root] = next(r["sources"] for r in merged if r["code"] == root)
        titles += report["title_regeneration_required_codes"]
    changed_files = []
    for f, text, data in files:
        touched = False
        for r in data:
            code = r.get("code")
            if code in new_sources and r.get("sources") != new_sources[code]:
                members = sorted(c for c in roots if roots[c] == code and c != code)
                r["sources"] = new_sources[code]
                r["sources_basis"] = "دمج مصادر الواقعة من صفوف duplicate_of: " + "، ".join(members)
                touched = True
        if touched:
            changed_files.append(f.name)
            if apply:
                f.write_text(json.dumps(data, ensure_ascii=False, indent=_indent_of(text)) + "\n",
                             encoding="utf-8")
    return {"groups": len(grouped), "roots": sorted(new_sources), "changed_files": changed_files,
            "skipped": skipped, "applied": apply, "title_regeneration_required_codes": titles}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="ملف JSON للقائمة")
    parser.add_argument("--output", type=Path, help="ملف JSON الناتج")
    parser.add_argument("--ledger", type=Path, help="مجلد الدفتر اليومي cumulative-2026/daily (وضع S074)")
    parser.add_argument("--apply", action="store_true", help="مع --ledger: اكتب الصفوف الجذر")
    args = parser.parse_args(argv)
    if args.ledger:
        try:
            print(json.dumps(merge_ledger(args.ledger, args.apply), ensure_ascii=False))
            return 0
        except (OSError, json.JSONDecodeError, MergeEventSourcesError) as exc:
            print(f"فشل دمج مصادر الدفتر: {exc}", file=sys.stderr)
            return 2
    if not (args.input and args.output):
        parser.error("--input و--output مطلوبان بلا --ledger")
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise MergeEventSourcesError("المدخل الجذري يجب أن يكون قائمة")
        merged, report = merge_event_records(payload)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"events": merged, "merge_report": report}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, MergeEventSourcesError) as exc:
        print(f"فشل دمج مصادر الواقعة: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
