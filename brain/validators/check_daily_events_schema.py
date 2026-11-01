#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة مخطط دفتر الوقائع (فشل مغلق).

تتحقق من كل سجل في ``cumulative-2026/daily/{date}.json`` مقابل
``schemas/daily-events.schema.json`` وعقد العرض ``appendices/event-card-contract.md``:

- الحقول المطلوبة والأنماط: رمز الواقعة · التاريخ · التوقيت · رقم IMO.
- القوائم المغلقة: درجة الموثوقية · القطاع · منشأ السجل · نوع الدليل · نطاق الإصابات.
- الروابط: https مباشر بلا مختصر ولا معطيات تتبّع.
- معرّفات الربط: لا مرجع معلّق بلا هدف في الدفتر التراكمي.
- النطاق الحيّ (2026-10-31 وما بعده): المقتطف وسنده والموضع مطلوبة.

الغياب مسموح ويُعرض بنصّ الغياب في البطاقة؛ أما القيمة المشوّهة أو خارج
القائمة المغلقة أو الملف المفقود أو غير المقروء فمخالفة مانعة.

الاستعمال:
  python3 validators/check_daily_events_schema.py --date 2026-11-01
  python3 validators/check_daily_events_schema.py --all
  python3 validators/check_daily_events_schema.py --file path/to/2026-11-01.json --json

رموز الخروج: 0 مطابق · 2 منع (فشل مغلق) · 70 انهيار المدقق.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_FROM = "2026-10-31"
ABSENCE_VALUES = {"غير متاح", "غير مقيّمة", "غير مدرج", "لا يوجد", "غير معروف", "-", "—"}

CONFIDENCE = ("عالية", "متوسطة", "منخفضة")
SECTOR_IDS = ("Z1", "Z2", "Z3", "Z4")
EVENT_KINDS = ("جديد", "legacy_projection", "incident")
EVIDENCE_KINDS = ("imo_confirmed_incidents", "official_source")
CLASSIFICATIONS = ("imo_confirmed_incidents",)
CASUALTY_SCOPES = ("not_announced", "seafarer", "shipyard_worker", "عامل حوض سفن")
TARGETS = ("سفينة",)
TIME_KINDS = ("وقوع", "نشر")
RELIABILITY_FLAGS = ("مصدر غير موثوق",)
INCIDENT_KINDS = ("هجوم", "حريق", "ألغام", "تسرب", "إغلاق", "تهديد", "اختطاف", "عطل", "جنوح",
                  "نشاط مشبوه", "لا ينطبق")

# النطاق الحيّ يلزمه رمز «MN-YYYY-MM-DD-NN»؛ الأرشيف يحمل بادئات موثّقة
# (COVER · IMO · BF) ولا تُعاد تسميتها لأنها مراجع تاريخية.
CODE_RE = re.compile(r"^[A-Z]{2,6}-\d{4}-\d{2}-\d{2}-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
LIVE_CODE_RE = re.compile(r"^MN-\d{4}-\d{2}-\d{2}-\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{4}Z$")
# سبعة أرقام هي الصيغة القياسية؛ وتُقبل ثمانية عندما ينقلها المصدر الرسمي
# نفسه بهذه الصورة (لا تصحيح بلا تأكيد رسمي).
IMO_RE = re.compile(r"^\d{7,8}$")
URL_RE = re.compile(r"^https://[^\s]+$")
SHORTENERS = ("t.co/", "bit.ly/", "lnkd.in/", "tinyurl.com/", "goo.gl/", "ow.ly/",
              "buff.ly/", "is.gd/", "cutt.ly/", "rb.gy/")
TRACKING = ("utm_", "fbclid=", "gclid=", "mc_eid=")
RELATION_KEYS = ("update_of", "parent_id", "duplicate_of")
REQUIRED = ("code", "date", "title", "source", "class", "confidence")


def _text(value) -> str:
    if isinstance(value, list):
        return " · ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").strip()


def _rows(value) -> list[dict]:
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict):
        rows = next((value.get(k) for k in ("events", "items", "rows")
                     if isinstance(value.get(k), list)), None)
        if rows is None:
            raise ValueError("بنية دفتر غير معروفة: لا قائمة سجلات في الجذر")
    else:
        raise ValueError("بنية دفتر غير معروفة: الجذر ليس قائمة ولا كائنًا")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("صف غير صالح: عنصر ليس كائنًا")
    return rows


def _is_no_incident(row: dict) -> bool:
    return bool(row.get("no_incident")) or row.get("event_kind") == "no_incident" \
        or row.get("class") == "no_incident"


def _check_url(value: str, where: str, errors: list[str]) -> None:
    if not URL_RE.match(value):
        errors.append(f"{where}: الرابط ليس https مباشرًا: {value[:60]}")
        return
    lowered = value.lower()
    if any(token in lowered for token in SHORTENERS):
        errors.append(f"{where}: رابط مختصر غير مسموح: {value[:60]}")
    if any(token in lowered for token in TRACKING):
        errors.append(f"{where}: معطى تتبّع في الرابط: {value[:60]}")


def violations(rows: list[dict], *, date_label: str, known_ids: set[str] | None = None,
               live_from: str = LIVE_FROM) -> list[str]:
    """يعيد قائمة المخالفات المانعة لملف يوم واحد. دالة نقية قابلة للاستيراد."""
    errors: list[str] = []
    if not rows:
        return [f"{date_label}: دفتر بلا سجلات (الغياب يُوثَّق بسجل no_incident لا بقائمة فارغة)"]
    known = known_ids if known_ids is not None else set()
    live = date_label >= live_from
    seen_codes: set[str] = set()
    for index, row in enumerate(rows, 1):
        where = f"{date_label}#{index}"
        if _is_no_incident(row):
            if not row.get("sources_checked"):
                errors.append(f"{where}: سجل لا واقعة بلا قائمة مصادر مفحوصة")
            if not _text(row.get("retrieved_at")):
                errors.append(f"{where}: سجل لا واقعة بلا وقت استرجاع")
            continue
        for key in REQUIRED:
            if not _text(row.get(key)) and live:
                errors.append(f"{where}: الحقل المطلوب «{key}» غائب أو فارغ")
        code = _text(row.get("code"))
        if code:
            if not CODE_RE.match(code):
                errors.append(f"{where}: نمط الرمز مخالف: {code}")
            elif live and not LIVE_CODE_RE.match(code):
                errors.append(f"{where}: رمز النطاق الحيّ يجب أن يكون MN-YYYY-MM-DD-NN: {code}")
            if code in seen_codes:
                errors.append(f"{where}: رمز مكرر داخل اليوم: {code}")
            seen_codes.add(code)
        date_value = _text(row.get("date"))
        if date_value:
            if not DATE_RE.match(date_value):
                errors.append(f"{where}: نمط التاريخ مخالف: {date_value}")
            elif DATE_RE.match(date_label) and date_value > date_label:
                errors.append(f"{where}: تاريخ الواقعة {date_value} بعد يوم الملف {date_label}")
            # تاريخ أسبق ليوم الملف مقبول: يوم الحادث لا يساوي يوم التقرير (بلاغ متأخر).
        confidence = _text(row.get("confidence"))
        if confidence and confidence not in CONFIDENCE:
            errors.append(f"{where}: درجة الموثوقية خارج القائمة المغلقة: {confidence}")
        for key, allowed in (("sector_id", SECTOR_IDS), ("event_kind", EVENT_KINDS),
                             ("evidence_kind", EVIDENCE_KINDS), ("classification", CLASSIFICATIONS),
                             ("casualty_scope", CASUALTY_SCOPES), ("target", TARGETS),
                             ("time_kind", TIME_KINDS), ("reliability_flag", RELIABILITY_FLAGS),
                             ("incident_kind", INCIDENT_KINDS)):
            value = _text(row.get(key))
            if value and value not in allowed:
                errors.append(f"{where}: قيمة «{key}» خارج القائمة المغلقة: {value}")
        time_value = _text(row.get("time"))
        if time_value and not TIME_RE.match(time_value):
            errors.append(f"{where}: صيغة التوقيت مخالفة (المتوقع DTG مثل 1859Z): {time_value}")
        imo = _text(row.get("imo_number"))
        if imo and live and not IMO_RE.match(imo):
            errors.append(f"{where}: رقم IMO ليس سبعة أرقام (أو ثمانية منقولة حرفيًّا): {imo}")
        url = _text(row.get("source_url"))
        if url:
            _check_url(url, where, errors)
        for key in ("area", "title", "source", "class", "source_excerpt"):
            value = _text(row.get(key))
            if value and value in ABSENCE_VALUES:
                errors.append(f"{where}: نصّ غياب مخزّن كقيمة في «{key}»؛ الغياب يُترك غيابًا")
        if live:
            for key in ("area", "source_excerpt", "source_excerpt_from"):
                if not _text(row.get(key)):
                    errors.append(f"{where}: الحقل «{key}» مطلوب في النطاق الحيّ وغائب")
        for key in RELATION_KEYS:
            ref = _text(row.get(key))
            if ref and known and ref not in known:
                errors.append(f"{where}: مرجع ربط معلّق بلا هدف في الدفتر: {key}={ref}")
    return errors


def historical_gaps(rows: list[dict], *, date_label: str,
                    live_from: str = LIVE_FROM) -> list[str]:
    """فجوات الأرشيف قبل النطاق الحيّ: تُعدّ وتُطبع ولا تُملأ بالتقدير."""
    if date_label >= live_from:
        return []
    gaps: list[str] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or _is_no_incident(row):
            continue
        where = f"{date_label}#{index}"
        for key in ("title", "class"):
            if not _text(row.get(key)):
                gaps.append(f"{where}: حقل عرض ناقص في الأرشيف: {key}")
        imo = _text(row.get("imo_number"))
        if imo and not IMO_RE.match(imo):
            gaps.append(f"{where}: رقم IMO خارج الصيغة: {imo}")
    return gaps


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(f"الملف مفقود: {path}")
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"تعذر قراءة {path}: {exc}") from exc


def known_ids(root: Path) -> set[str]:
    """كل معرّفات الوقائع في الدفتر اليومي والملف التراكمي، لمطابقة مراجع الربط."""
    ids: set[str] = set()
    for path in sorted((root / "cumulative-2026" / "daily").glob("*.json")):
        try:
            rows = _rows(load_json(path))
        except (RuntimeError, ValueError):
            continue
        for row in rows:
            for key in ("code", "event_id", "display_code"):
                value = _text(row.get(key))
                if value:
                    ids.add(value)
    master = root / "cumulative-2026" / "event-ledger-master.json"
    if master.is_file():
        try:
            value = load_json(master)
            rows = _rows(value) if isinstance(value, (list, dict)) else []
        except (RuntimeError, ValueError):
            rows = []
        for row in rows:
            for key in ("code", "event_id", "display_code"):
                value = _text(row.get(key))
                if value:
                    ids.add(value)
    return ids


def _targets(root: Path, site: Path | None, args) -> list[Path]:
    if args.file:
        return [Path(args.file)]
    if args.date:
        candidates = [root / "cumulative-2026" / "daily" / f"{args.date}.json"]
        if site is not None:
            candidates.append(site / "sources" / "daily-events" / f"{args.date}.json")
        for candidate in candidates:
            if candidate.is_file():
                return [candidate]
        return [candidates[0]]
    return sorted((root / "cumulative-2026" / "daily").glob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="بوابة مخطط دفتر الوقائع (فشل مغلق)",
                                     allow_abbrev=False)
    parser.add_argument("--date", default=None, help="يوم واحد بصيغة YYYY-MM-DD")
    parser.add_argument("--all", action="store_true", help="كل ملفات الدفتر اليومي")
    parser.add_argument("--file", default=None, help="ملف دفتر محدد")
    parser.add_argument("--brain", default=str(ROOT))
    parser.add_argument("--site", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.brain)
    site = Path(args.site) if args.site else None
    try:
        targets = _targets(root, site, args)
    except OSError as exc:
        print(f"✘ تعذر تحديد الملفات: {exc}")
        return 2
    if not targets:
        print("✘ منع: لا ملفات دفتر للقياس")
        return 2
    try:
        known = known_ids(root)
    except OSError as exc:
        print(f"✘ تعذر بناء فهرس المعرّفات: {exc}")
        return 2
    errors: list[str] = []
    gaps: list[str] = []
    checked = 0
    records = 0
    for path in targets:
        label = path.stem if DATE_RE.match(path.stem) else path.name
        try:
            rows = _rows(load_json(path))
        except (RuntimeError, ValueError) as exc:
            errors.append(f"{label}: {exc}")
            continue
        checked += 1
        records += len(rows)
        errors.extend(violations(rows, date_label=label, known_ids=known))
        gaps.extend(historical_gaps(rows, date_label=label))
    if args.json:
        print(json.dumps({"gate": "check_daily_events_schema", "status": "blocked" if errors else "ok",
                          "files": checked, "records": records,
                          "historical_gaps": gaps, "violations": errors},
                         ensure_ascii=False, indent=1))
        return 2 if errors else 0
    print(f"مخطط دفتر الوقائع: {checked} ملفًا · {records} سجلًا")
    if gaps:
        print(f"فجوات تاريخية موثّقة (قبل {LIVE_FROM}): {len(gaps)} — تُعدّ ولا تمنع، ولا تُملأ بالتقدير")
    if errors:
        for error in errors[:60]:
            print("✘", error)
        if len(errors) > 60:
            print(f"✘ … و{len(errors) - 60} مخالفة أخرى")
        print("النتيجة: منع — فشل مغلق")
        return 2
    print("النتيجة: مطابق")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
