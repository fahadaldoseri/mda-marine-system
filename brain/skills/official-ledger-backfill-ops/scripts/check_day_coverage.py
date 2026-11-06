#!/usr/bin/env python3
"""حارس اكتمال تغطية الأيام في دفتر أحداث تراكمي.

القاعدة: لكل يوم في المدى سجل واحد؛ إما مادة فعلية، وإما سجل «لا واقعة»
يحمل قائمة المصادر التي فُحصت فعلًا ووقت الجلب. أي يوم بلا ملف، أو بلا دليل
فحص، أو ببنية غير مفهومة => فشل مغلق برمز الخروج 2.

استعمال:
  check_day_coverage.py --ledger-dir DIR --start YYYY-MM-DD --end YYYY-MM-DD
                        [--min-sources 1] [--json]

المخرجات: جدول موجز + قائمة الثغرات. رمز الخروج: 0 سليم · 2 ثغرة.
لا يحتاج أي مكتبة خارجية.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

# مفاتيح محتملة لأسماء الحقول، لتقبل مخططات مشاريع مختلفة بلا تعديل الكود.
RECORD_KEYS = ("records", "events", "items", "incidents", "rows", "entries")
STATUS_KEYS = ("status", "kind", "day_kind", "state", "event_kind", "record_type")
NO_INCIDENT_VALUES = ("no_incident", "no-incident", "noincident", "لا واقعة")
SOURCES_KEYS = ("sources_checked", "consulted_sources", "sources", "checked_sources", "sources_consulted")
RETRIEVED_KEYS = ("retrieved_at", "fetched_at", "checked_at", "collected_at")


def daterange(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def find_day_file(ledger_dir: pathlib.Path, date_str: str):
    """يبحث عن ملف اليوم مباشرة أو في مجلد فرعي واحد."""
    direct = ledger_dir / f"{date_str}.json"
    if direct.is_file():
        return direct
    for sub in sorted(ledger_dir.iterdir()):
        if sub.is_dir():
            cand = sub / f"{date_str}.json"
            if cand.is_file():
                return cand
    return None


def as_records(data):
    """يعيد قائمة السجلات إن وُجدت، أو None."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in RECORD_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                return value
        # مخطط مفهرس بالتواريخ: { "2026-03-01": [ ... ] }
        collected = []
        for value in data.values():
            if isinstance(value, list):
                collected.extend(value)
        return collected or None
    return None


def status_of(data):
    """يستخرج حالة اليوم إن أعلنها الملف."""
    if not isinstance(data, dict):
        return None
    for key in STATUS_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    if data.get("no_incident") is True:
        return "no_incident"
    return None


def declared_sources(data):
    if not isinstance(data, dict):
        return []
    for key in SOURCES_KEYS:
        value = data.get(key)
        if isinstance(value, list):
            return [str(v) for v in value if str(v).strip()]
        if isinstance(value, dict):
            return [str(k) for k in value.keys() if str(k).strip()]
    return []


def retrieved_at(data):
    if not isinstance(data, dict):
        return None
    for key in RETRIEVED_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def row_is_no_incident(row) -> bool:
    """هل الصف نفسه صف «لا واقعة»؟"""
    if not isinstance(row, dict):
        return False
    if row.get("no_incident") is True:
        return True
    for key in STATUS_KEYS + ("class", "event_kind", "record_class"):
        value = row.get(key)
        if isinstance(value, str) and value.strip().lower() in NO_INCIDENT_VALUES:
            return True
    return False


def row_sources(row):
    """قائمة المصادر المفحوصة في صف واحد."""
    if not isinstance(row, dict):
        return []
    for key in SOURCES_KEYS:
        value = row.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value.values())
    return []


def sources_ok(sources, min_sources: int):
    """يتحقق أن كل مصدر مفحوص يحمل رابطًا ووقت جلب، وأن العدد كافٍ."""
    if len(sources) < min_sources:
        return False, f"عدد المصادر المفحوصة {len(sources)} أقل من {min_sources}"
    for index, item in enumerate(sources, 1):
        if isinstance(item, str):
            if not item.strip():
                return False, f"المصدر #{index} فارغ"
            continue
        if not isinstance(item, dict):
            return False, f"المصدر #{index} بصيغة غير مفهومة"
        url = item.get("url") or item.get("link") or item.get("source_url") or item.get("endpoint")
        when = item.get("retrieved_at") or item.get("fetched_at") or item.get("checked_at")
        if not url:
            return False, f"المصدر #{index} بلا رابط"
        if not when:
            return False, f"المصدر #{index} بلا وقت جلب"
    return True, f"{len(sources)} مصدرًا مفحوصًا"


def classify(path: pathlib.Path, min_sources: int):
    """يعيد (الحالة, السبب). الحالة: material | no_incident | gap"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # ملف تالف => فشل مغلق
        return "gap", f"ملف غير قابل للقراءة: {exc}"

    rows = as_records(data)
    if rows is None:
        return "gap", "بنية ملف غير مفهومة (لا قائمة سجلات ولا إعلان «لا واقعة»)"

    material_rows = [row for row in rows if not row_is_no_incident(row)]
    if material_rows:
        return "material", f"{len(material_rows)} سجلًا"

    noinc_rows = [row for row in rows if row_is_no_incident(row)]
    if noinc_rows:
        for row in noinc_rows:
            ok, reason = sources_ok(row_sources(row), min_sources)
            if not ok:
                return "gap", f"«لا واقعة» بلا دليل فحص كافٍ: {reason}"
            if not (row.get("retrieved_at") or retrieved_at(row)):
                return "gap", "«لا واقعة» بلا وقت جلب على الصف (retrieved_at)"
        return "no_incident", f"{len(noinc_rows)} صف «لا واقعة» موثّق"

    # إعلان «لا واقعة» على مستوى الملف (قاموس بلا صفوف)
    status = status_of(data)
    if status in NO_INCIDENT_VALUES:
        ok, reason = sources_ok(declared_sources(data), min_sources)
        if not ok:
            return "gap", f"«لا واقعة» بلا دليل فحص كافٍ: {reason}"
        when = retrieved_at(data)
        if not when:
            return "gap", "«لا واقعة» بلا وقت جلب (retrieved_at)"
        return "no_incident", f"ملف معلن «لا واقعة» · {when}"

    return "gap", "سجل بلا مادة ولا إعلان «لا واقعة»"


def main() -> int:
    parser = argparse.ArgumentParser(description="حارس اكتمال تغطية أيام الدفتر")
    parser.add_argument("--ledger-dir", required=True, help="مجلد ملفات الأيام (YYYY-MM-DD.json)")
    parser.add_argument("--start", required=True, help="أول يوم في المدى")
    parser.add_argument("--end", required=True, help="آخر يوم في المدى")
    parser.add_argument("--min-sources", type=int, default=1, help="أدنى عدد مصادر مفحوصة في سجل «لا واقعة»")
    parser.add_argument("--json", action="store_true", help="إخراج JSON بدل نص")
    args = parser.parse_args()

    ledger_dir = pathlib.Path(args.ledger_dir).expanduser().resolve()
    if not ledger_dir.is_dir():
        print(f"✘ مجلد الدفتر غير موجود: {ledger_dir}", file=sys.stderr)
        return 2

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    if end < start:
        print("✘ نهاية المدى قبل بدايته", file=sys.stderr)
        return 2

    material = no_incident = 0
    gaps = []
    no_incident_days = []

    for day in daterange(start, end):
        date_str = day.isoformat()
        path = find_day_file(ledger_dir, date_str)
        if path is None:
            gaps.append({"date": date_str, "reason": "لا ملف لليوم"})
            continue
        state, reason = classify(path, args.min_sources)
        if state == "material":
            material += 1
        elif state == "no_incident":
            no_incident += 1
            no_incident_days.append(date_str)
        else:
            gaps.append({"date": date_str, "reason": reason})

    total = (end - start).days + 1
    covered = material + no_incident

    if args.json:
        print(json.dumps({
            "start": start.isoformat(), "end": end.isoformat(), "total_days": total,
            "material": material, "no_incident": no_incident, "gaps": gaps,
            "no_incident_days": no_incident_days,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"   المدى: {start.isoformat()} → {end.isoformat()} · {total} يومًا")
        print(f"   مادة: {material} · «لا واقعة» موثّقة: {no_incident} · مغطّى: {covered}/{total}")
        if gaps:
            print(f"   ✘ ثغرات: {len(gaps)}")
            for gap in gaps[:50]:
                print(f"      - {gap['date']}: {gap['reason']}")
            if len(gaps) > 50:
                print(f"      … و{len(gaps) - 50} أخرى")
        else:
            print("   ✔ استمرارية الدفتر مكتملة: لا يوم بلا سجل")

    return 0 if not gaps else 2


if __name__ == "__main__":
    sys.exit(main())
