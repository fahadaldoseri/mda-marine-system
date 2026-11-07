#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة سجل الأحداث الحي وسطح الأقسام المنقولة.

تتحقق البوابة من دفتر الفترة المنسوخ إلى الموقع ومن الأسطح المبنية:
- كل سجلات دفتر اليوم في الفترة تظهر كبطاقات في «سجل الأحداث».
- كل سجل معلّم كتحديث/امتداد وله مرجع يظهر له فرع سابق مكتوب؛ لا استنتاج من تشابه النص.
- لا يوجد مرجع فرع معلّق بلا هدف.
- الأقسام الخمسة المنقولة كاملة في «إضافات» وغائبة من التقرير اليومي.
- «سجل IMO والحوادث المؤكدة» يسبق أي عنوان وقائع/أحداث إن ظهر كلاهما في الإضافات.

الاستعمال:
  python3 validators/check_daily_event_surface.py --date 2026-10-31
  python3 validators/check_daily_event_surface.py --date 2026-10-31 --site "$SITE_DIR"

رموز الخروج: 0 نجاح · 2 مخالفة مانعة · 70 انهيار المدقق.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVED_SECTIONS = (
    "حالة المصادر والإفصاح",
    "الاحتمالات ونسبة الحوادث إلى جهات",
    "التحذيرات والتنبيهات النشطة",
    "المراقبة المستمرة",
    "سجل IMO والحوادث المؤكدة",
)
EVENT_TITLES = ("سجل الأحداث", "الوقائع الجديدة")


def _root(env: str, base: Path, *names: str) -> Path:
    value = os.environ.get(env)
    if value:
        return Path(value)
    for name in names:
        candidate = base / name
        if candidate.is_dir():
            return candidate
    return base / names[0]


HOME = ROOT.parent
DEFAULT_BRAIN = _root("BRAIN_DIR", HOME, "brain-marine-news", "brain")
DEFAULT_SITE = _root("SITE_DIR", HOME, "seawatch", "site")


def _text(value) -> str:
    if isinstance(value, list):
        return " · ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").strip()


def _code(event: dict) -> str:
    return _text(event.get("code") or event.get("display_code") or event.get("event_id"))


def _date(event: dict) -> str:
    return _text(event.get("date") or event.get("date_start") or event.get("date_label"))


def _is_cumulative_update(event: dict) -> bool:
    """سجل تحديث تراكمي يبقى في الدفتر ولا يظهر كبطاقة واقعة."""
    return _text(event.get("event_kind")).strip().lower() == "تحديث بيانات"


def _relation_marker(event: dict, known: set[str]) -> tuple[bool, str]:
    kind = _text(event.get("event_kind")).lower()
    marked = bool(kind and any(token in kind for token in (
        "update", "extension", "follow", "duplicate", "تحديث", "امتداد", "تابع", "نسخة"
    )))
    for key in ("update_of", "parent_id", "duplicate_of"):
        ref = _text(event.get(key))
        if ref:
            return True, ref
    link = _text(event.get("link"))
    if link and link in known:
        return True, link
    return marked, ""


def _load_events(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"دفتر الأحداث ليس قائمة سجلات: {path}")
    return data


def _known_ids(site: Path, daily: list[dict]) -> set[str]:
    known = {_code(event) for event in daily if _code(event)}
    ledger = site / "sources" / "ledger.json"
    if ledger.is_file():
        try:
            data = json.loads(ledger.read_text(encoding="utf-8"))
            events = data.get("events") if isinstance(data, dict) else data
            if isinstance(events, list):
                for event in events:
                    if isinstance(event, dict):
                        for key in ("code", "display_code", "event_id"):
                            value = _text(event.get(key))
                            if value:
                                known.add(value)
        except (OSError, json.JSONDecodeError):
            pass
    return known


def _headings(page: str) -> list[str]:
    return [html.unescape(re.sub(r"<[^>]+>", "", value)).strip()
            for value in re.findall(r"<h2[^>]*>(.*?)</h2>", page, re.S)]


def _section_payload(page: str, title: str) -> str:
    """Return the payload from the section whose DOM heading has ``title``.

    Rendered headings may isolate a Latin token such as ``IMO`` in ``span.ltr``.
    Matching the raw HTML title therefore produces a false empty payload even
    though ``_headings`` can read the same heading.  Keep the section boundary
    strict, but compare the heading after stripping markup just like the
    heading counter does.
    """
    for section_match in re.finditer(r"<section\b[^>]*>(.*?)</section>", page, re.S):
        section = section_match.group(1)
        heading_match = re.search(r"<h2\b[^>]*>(.*?)</h2>", section, re.S)
        if not heading_match:
            continue
        heading = html.unescape(re.sub(r"<[^>]+>", "", heading_match.group(1))).strip()
        if title not in heading:
            continue
        payload = section[heading_match.end():]
        visible = html.unescape(re.sub(r"<[^>]+>", "", payload)).strip()
        return payload if visible else ""
    return ""


def _event_cards(page: str) -> list[tuple[str, str]]:
    return re.findall(
        r'<article\b[^>]*\bdata-event-code="([^"]+)"[^>]*>(.*?)</article>', page, re.S
    )


def validate_documents(*, daily: list[dict], report: str, additions: str, site: Path,
                       policy: dict | None = None) -> list[str]:
    errors: list[str] = []
    policy = policy or {}
    moved_config = policy.get("required_in_additions")
    moved = tuple(moved_config) if moved_config is not None else MOVED_SECTIONS
    required_report = tuple(policy.get("required_in_report") or ())

    report_heads = _headings(report)
    additions_heads = _headings(additions)
    for title in moved:
        add_count = sum(1 for heading in additions_heads if title in heading)
        report_count = sum(1 for heading in report_heads if title in heading)
        if add_count != 1:
            errors.append(f"القسم المنقول «{title}» في الإضافات عدده {add_count} لا يساوي 1")
        if report_count:
            errors.append(f"القسم المنقول «{title}» ما زال ظاهرًا في التقرير اليومي ({report_count})")
        if not _section_payload(additions, title).strip():
            errors.append(f"القسم المنقول «{title}» بلا متن ظاهر في الإضافات")
    for title in required_report:
        if title in moved:
            continue
        if not any(title in heading for heading in report_heads):
            errors.append(f"قسم التقرير الباقي «{title}» غائب عن التقرير اليومي")

    imo_positions = [i for i, heading in enumerate(additions_heads) if "سجل IMO والحوادث المؤكدة" in heading]
    event_positions = [i for i, heading in enumerate(additions_heads)
                       if any(key in heading for key in EVENT_TITLES)]
    if imo_positions and event_positions and min(imo_positions) > min(event_positions):
        errors.append("ترتيب الإضافات مخالف: سجل IMO يجب أن يسبق أي قسم وقائع/أحداث")

    grid_match = re.search(r'<div\b[^>]*\bev-grid\b[^>]*>', report, re.S)
    if not grid_match:
        return errors + ["حاوية سجل الأحداث الحي مفقودة من التقرير اليومي"]
    attrs = grid_match.group(0)
    def attr_int(name: str) -> int | None:
        match = re.search(rf'\b{re.escape(name)}="(\d+)"', attrs)
        return int(match.group(1)) if match else None

    cards = _event_cards(report)
    renderable_daily = [event for event in daily if not _is_cumulative_update(event)]
    expected_codes = [_code(event) for event in renderable_daily]
    actual_codes = [code for code, _ in cards]
    source_count = attr_int("data-source-count")
    rendered_count = attr_int("data-count")
    if source_count != len(renderable_daily):
        errors.append(f"عداد مصدر سجل الأحداث={source_count}، والسجلات القابلة للعرض={len(renderable_daily)}")
    if rendered_count != len(renderable_daily) or len(cards) != len(renderable_daily):
        errors.append(f"عدد بطاقات سجل الأحداث={len(cards)}، والسجلات القابلة للعرض={len(renderable_daily)}")
    if actual_codes != expected_codes:
        errors.append("رموز سجل الأحداث الظاهرة لا تطابق ترتيب/سجلات دفتر الفترة")

    known = _known_ids(site, daily)
    expected_relations = {}
    for event in renderable_daily:
        marked, ref = _relation_marker(event, known)
        if marked:
            expected_relations[_code(event)] = ref
    branch_count = attr_int("data-branch-count")
    unresolved_count = attr_int("data-unresolved-branch-count")
    shown_branches = len(re.findall(r'data-branch-status="shown"', report))
    missing_branches = len(re.findall(r'data-branch-status="(?:missing-target|missing-ref)"', report))
    if branch_count != shown_branches:
        errors.append(f"عداد الفروع={branch_count}، والفروع المكتوبة={shown_branches}")
    if unresolved_count != missing_branches:
        errors.append(f"عداد فجوات الفروع={unresolved_count}، والفجوات الظاهرة={missing_branches}")
    if missing_branches:
        errors.append("يوجد فرع معلّم بلا هدف أو بلا مرجع")
    for code, ref in expected_relations.items():
        card = next((body for card_code, body in cards if card_code == code), "")
        if not ref:
            errors.append(f"الحدث {code} معلّم كتحديث/امتداد بلا مرجع حاكم")
        elif not re.search(r'data-branch-status="shown"', card):
            errors.append(f"الحدث {code} لا يعرض فرعه السابق الموثق")
        elif not re.search(rf'data-parent-ref="{re.escape(html.escape(ref))}"', card):
            errors.append(f"مرجع فرع الحدث {code} لا يطابق {ref}")
        elif ref not in known:
            errors.append(f"مرجع فرع الحدث {code} لا يملك هدفًا في الدفتر: {ref}")
    if not expected_relations and shown_branches:
        errors.append("ظهر فرع تابع رغم عدم وجود حقل ربط في دفتر الفترة")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--site", default=str(DEFAULT_SITE))
    parser.add_argument("--brain", default=str(DEFAULT_BRAIN))
    args = parser.parse_args()
    site = Path(args.site)
    brain = Path(args.brain)
    daily_path = site / "sources" / "daily-events" / f"{args.date}.json"
    if not daily_path.is_file():
        daily_path = brain / "cumulative-2026" / "daily" / f"{args.date}.json"
    report_path = site / "dist" / "reports" / f"{args.date}.html"
    additions_path = site / "dist" / "additions.html"
    policy_path = brain / "appendices" / "report-sections-policy.json"
    required = (daily_path, report_path, additions_path, policy_path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print("✘ ملفات البوابة مفقودة: " + " · ".join(missing))
        return 2
    try:
        daily = _load_events(daily_path)
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"✘ تعذر تحميل مدخلات البوابة: {exc}")
        return 2
    errors = validate_documents(
        daily=daily,
        report=report_path.read_text(encoding="utf-8"),
        additions=additions_path.read_text(encoding="utf-8"),
        site=site,
        policy=policy,
    )
    print(f"دفتر الفترة: {len(daily)} سجلًا · التقرير: {_headings(report_path.read_text(encoding='utf-8')).count('سجل الأحداث')} سجل أحداث")
    if errors:
        for error in errors:
            print("✘", error)
        print("النتيجة: مخالف — فشل مغلق")
        return 2
    print("✔ عدّاد الفترة والفروع والأسطح المنقولة والمراسي سليمة")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
