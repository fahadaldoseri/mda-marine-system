#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build auditable cumulative metrics from the marine event ledger.

The master ledger's ``events`` list is the canonical event source.  Daily
files are also read and validated so a missing or unreadable day cannot be
silently turned into a zero.  The tool is deliberately stdlib-only and has
no dependency on the site, runbook, or report generators.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "cumulative-2026" / "daily"
MASTER_PATH = ROOT / "cumulative-2026" / "event-ledger-master.json"
OUTPUT_DIR = ROOT / "web" / "kpis-totals"
IMO_PATH = ROOT / "appendices" / "imo-incidents.json"
START_DATE = dt.date(2026, 2, 28)

SOURCE_DAILY = "cumulative-2026/daily/*.json"
SOURCE_MASTER = "cumulative-2026/event-ledger-master.json#events"

METRIC_TITLES = {
    "ukmto-reports": "بلاغات UKMTO المرصودة",
    "qualifying-incidents": "وقائع مستوفية لمعيار الاحتساب",
    "unconfirmed-narratives": "روايات لم تتأكد",
    "confirmed-incidents": "وقائع مؤكدة",
    "deaths": "الوفيات المسجّلة",
    "imo-confirmed-incidents": "سجل الحوادث المؤكدة من IMO",
    "imo-seafarer-deaths": "أعداد الوفيات من IMO",
    "fire-incidents": "حرائق السفن",
    "official-products": "منتجات UKMTO وJMIC المرصودة",
}

IMO_URL = "https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx"

# These are the governed maritime-event concepts used by the existing ledger
# classifier.  A hit is never enough by itself: a maritime or navigational
# target is also required, preventing land-only political/security reports
# from becoming maritime incidents.
QUALIFYING_MARKERS = (
    "هجوم",
    "استهداف",
    "إطلاق",
    "انفجار",
    "ألغام",
    "اصطدام بلغم",
    "اختطاف",
    "تفتيش قسري",
    "حريق",
    "اشتعال",
    "غرق",
    "إعاقة",
    "تعطيل ملاحي",
    "نشاط مشبوه",
    "إطفاء إشارات",
    "إخماد حريق",
    "attack",
    "targeting",
    "mine",
    "hijack",
    "fire",
    "sunk",
)
MARITIME_TARGET_MARKERS = (
    "سفينة",
    "سفن",
    "ناقلة",
    "ناقلات",
    "قارب",
    "زورق",
    "مركب",
    "باخرة",
    "يخت",
    "وحدة بحرية",
    "سفينة شحن",
    "حاملة",
    "رصيف",
    "ميناء",
    "ملاحة",
    "الملاحة",
    "ممر",
    "مضيق",
    "خليج",
    "كابلات",
    "بحري",
    "vessel",
    "ship",
    "tanker",
    "boat",
    "maritime",
)

NEGATIVE_EVENT_MARKERS = (
    "لا واقعة",
    "لا حادث",
    "لا هجوم",
    "لم يسجل هجوم",
    "لم تسجل هجمات",
    "لا يصف هجوم",
    "لا يثبت هجوم",
    "تحذير بلا حادثة",
    "لا واقعة بحرية جديدة",
)
FIRE_MARKERS = (
    "حريق",
    "اشتعال",
    "إخماد الحريق",
    "fire",
    "burning",
    "flames",
)
NARRATIVE_CLASS_MARKERS = ("رواية", "ادعاء منقول", "ادعاء طرف")
COUNTED_EVIDENCE_STATUSES = {
    "confirmed_effect_or_attack",
}
FIRE_ELIGIBLE_STATUSES = {
    "confirmed_effect_or_attack",
    "recorded_security_event",
    "military_interaction",
    "unresolved_incident",
}
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NON_SEAFARER_CASUALTY_SCOPES = {"shipyard_worker", "عامل حوض سفن"}


class LedgerError(Exception):
    """An input or integrity error that must stop the run."""


def fail(message: str) -> None:
    raise LedgerError(message)


def parse_iso_date(value: Any, label: str) -> dt.date:
    if not isinstance(value, str) or not ISO_DATE_RE.fullmatch(value):
        fail(f"{label} ليس تاريخ ISO صالحًا: {value!r}")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        fail(f"{label} ليس تاريخًا تقويميًا صالحًا: {value!r} ({exc})")
    raise AssertionError("unreachable")


def read_json(path: Path) -> Any:
    if not path.exists():
        fail(f"ملف الدفتر غير موجود: {path}")
    if not path.is_file():
        fail(f"مسار الدفتر ليس ملفًا: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        fail(f"تعذّرت قراءة JSON: {path}: {exc}")
    raise AssertionError("unreachable")


def expected_dates(target: dt.date) -> list[dt.date]:
    if target < START_DATE:
        fail(f"التاريخ المطلوب قبل بداية الدفتر {START_DATE.isoformat()}: {target.isoformat()}")
    days = (target - START_DATE).days + 1
    return [START_DATE + dt.timedelta(days=i) for i in range(days)]


def load_gap_days(target: dt.date) -> set[str]:
    """أيام فجوة النقل الموثقة بقرار المالك حتى التاريخ المطلوب (فشل مغلق عند خلل الملف)."""
    validators_dir = str(Path(__file__).resolve().parents[1] / "validators")
    if validators_dir not in sys.path:
        sys.path.insert(0, validators_dir)
    from _migration_gaps import load_gap_dates

    try:
        gaps = load_gap_dates(ROOT)
    except (RuntimeError, ValueError) as exc:
        fail(str(exc))
    return {day for day in gaps if day <= target.isoformat()}


def load_daily(target: dt.date) -> tuple[list[dict[str, Any]], int, list[str], list[str]]:
    if not DAILY_DIR.exists() or not DAILY_DIR.is_dir():
        fail(f"مجلد اليوميات غير موجود أو غير قابل للقراءة: {DAILY_DIR}")
    gap_days = load_gap_days(target)
    dates = [day for day in expected_dates(target) if day.isoformat() not in gap_days]
    conflicts = sorted(d for d in gap_days if (DAILY_DIR / f"{d}.json").exists())
    if conflicts:
        fail(f"يوم موثق فجوةَ نقل وله دفتر يومي (حدّث ملف الفجوة أو احذف الدفتر): {conflicts}")
    rows: list[dict[str, Any]] = []
    duplicate_codes: list[str] = []
    seen_codes: dict[str, dict[str, Any]] = {}
    for day in dates:
        path = DAILY_DIR / f"{day.isoformat()}.json"
        payload = read_json(path)
        if not isinstance(payload, list):
            fail(f"بنية دفتر اليوم ليست قائمة: {path}")
        for index, row in enumerate(payload):
            if not isinstance(row, dict):
                fail(f"صف غير كائن في {path} عند الفهرس {index}")
            code = row.get("code")
            row_date = row.get("date")
            if not isinstance(code, str) or not code.strip():
                fail(f"صف بلا code في {path} عند الفهرس {index}")
            parse_iso_date(row_date, f"date في {path} عند الفهرس {index}")
            if code in seen_codes:
                duplicate_codes.append(code)
                # A repeated code is one ledger event.  Conflicting copies are
                # unsafe because the metric could depend on file ordering.
                if json.dumps(seen_codes[code], ensure_ascii=False, sort_keys=True) != json.dumps(row, ensure_ascii=False, sort_keys=True):
                    fail(f"تعارض بين صفوف تحمل code نفسه: {code}")
                continue
            seen_codes[code] = row
            rows.append(row)
    return rows, len(dates), duplicate_codes, sorted(gap_days)


def load_master() -> tuple[list[dict[str, Any]], list[str]]:
    payload = read_json(MASTER_PATH)
    if not isinstance(payload, dict):
        fail(f"بنية الدفتر الرئيسي ليست كائنًا: {MASTER_PATH}")
    events = payload.get("events")
    if not isinstance(events, list):
        fail("الدفتر الرئيسي لا يحتوي قائمة events")
    counts = payload.get("counts")
    if isinstance(counts, dict) and isinstance(counts.get("total_records"), int):
        if counts["total_records"] != len(events):
            fail(
                "عدم تطابق الدفتر الرئيسي: counts.total_records="
                f"{counts['total_records']} مقابل events={len(events)}"
            )
    canonical: list[dict[str, Any]] = []
    excluded: list[str] = []
    seen: dict[str, dict[str, Any]] = {}
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            fail(f"واقعة غير كائنية في event-ledger-master.events عند الفهرس {index}")
        identity = event.get("display_code") or event.get("event_id")
        if not isinstance(identity, str) or not identity.strip():
            fail(f"واقعة في الدفتر الرئيسي بلا display_code أو event_id عند الفهرس {index}")
        event_date = event.get("date_start") or event.get("date")
        parse_iso_date(event_date, f"date_start للواقعة {identity}")
        if identity in seen:
            fail(f"هوية مكررة في الدفتر الرئيسي: {identity}")
        seen[identity] = event
        if event.get("counted") is False or event.get("duplicate_of"):
            excluded.append(identity)
            continue
        event["_identity"] = identity
        event["_event_date"] = event_date
        canonical.append(event)
    return canonical, excluded


def source_values(event: dict[str, Any]) -> list[str]:
    values: list[str] = []
    raw = event.get("sources")
    if isinstance(raw, list):
        values.extend(str(item) for item in raw if item not in (None, ""))
    elif raw not in (None, ""):
        values.append(str(raw))
    for key in ("source", "source_url", "evidence_ref"):
        value = event.get(key)
        if value not in (None, ""):
            values.append(str(value))
    return values


def source_text(event: dict[str, Any]) -> str:
    return " ".join(source_values(event))


def source_mentions(source: str, token: str) -> bool:
    """Match a governed source token despite handle/URL separators.

    Source records use both ``UKMTO`` and the official X handle ``UK_MTO``.
    Removing non-alphanumeric ASCII separators lets both spellings resolve to
    the same source without broadening the match to an unrelated Arabic word.
    """
    compact_source = re.sub(r"[^a-z0-9]+", "", str(source).casefold())
    compact_token = re.sub(r"[^a-z0-9]+", "", str(token).casefold())
    return bool(compact_token) and compact_token in compact_source


def event_text(event: dict[str, Any]) -> str:
    fields = (
        "title",
        "description",
        "classification",
        "operational_effect",
        "outcome",
        "source_description",
        "source_excerpt",
    )
    return " ".join(str(event.get(field, "")) for field in fields).strip()


def is_negative_event(event: dict[str, Any]) -> bool:
    text = event_text(event)
    classification = str(event.get("classification", ""))
    if event.get("event_kind") == "no_incident" or event.get("no_incident") is True:
        return True
    if classification == "no_incident":
        return True
    return any(marker in text for marker in NEGATIVE_EVENT_MARKERS)


def has_maritime_target(event: dict[str, Any]) -> bool:
    text = event_text(event).lower()
    return any(marker.lower() in text for marker in MARITIME_TARGET_MARKERS)


def qualifying(event: dict[str, Any]) -> bool:
    if is_negative_event(event):
        return False
    text = event_text(event).lower()
    if not any(marker.lower() in text for marker in QUALIFYING_MARKERS):
        return False
    return has_maritime_target(event)


# عطل ك-555 (جولة 2026-11-07): صفوف الدفتر اليومية تحمل مفردات `class` و`class_raw`
# و`proof_degree`، بينما كان المصنّف يقرأ `evidence_status` وحده، فسقطت رواية اليوم
# صامتًا وصار عدّاد «روايات لم تتأكد» صفرًا بينما المتن يعلن رواية واحدة.
# الحل: تُستخرج الحالة من الحقل القانوني إن وُجد، وإلا تُشتق من مفردات الدفتر المعلنة.
UNRESOLVED_STATUS_TOKENS = (
    "غير مؤكد", "غير مؤكدة", "رواية", "روايات", "unresolved", "unconfirmed",
)
CONFIRMED_STATUS_TOKENS = (
    "بلاغ رسمي", "مؤكد", "official", "confirmed",
)


def resolved_evidence_status(event: dict[str, Any]) -> str:
    raw = str(event.get("evidence_status") or "").strip()
    if raw:
        return raw
    vocabulary = " ".join(
        str(event.get(key, "")) for key in ("class", "class_raw", "proof_degree", "confidence")
    )
    folded = vocabulary.casefold()
    if any(token in vocabulary or token in folded for token in UNRESOLVED_STATUS_TOKENS):
        return "unresolved_incident"
    if any(token in vocabulary or token in folded for token in CONFIRMED_STATUS_TOKENS):
        return "official_confirmed"
    return ""


def unconfirmed_narrative(event: dict[str, Any]) -> bool:
    if is_negative_event(event):
        return False
    status = resolved_evidence_status(event)
    if status not in {"unresolved_incident", "unresolved_or_advisory"}:
        return False
    description = str(event.get("description") or event.get("title") or "").lstrip()
    classification = " ".join(str(event.get(k, "")) for k in ("classification", "class", "class_raw"))
    return (description.startswith(("رواية", "روايات"))
            or any(marker in classification for marker in NARRATIVE_CLASS_MARKERS))


def confirmed(event: dict[str, Any]) -> bool:
    return str(event.get("evidence_status", "")) in COUNTED_EVIDENCE_STATUSES


def fire(event: dict[str, Any]) -> bool:
    if str(event.get("evidence_status", "")) not in FIRE_ELIGIBLE_STATUSES:
        return False
    outcome = str(event.get("outcome", "")).lower()
    if outcome == "fire" or "حريق" in outcome:
        return True
    text = event_text(event).lower()
    if not any(marker.lower() in text for marker in FIRE_MARKERS):
        return False
    if any(negative in text for negative in ("لا حريق", "لا اشتعال", "no fire")):
        return False
    return has_maritime_target(event) or "حريق" in str(event.get("classification", ""))


def direct_ukmto(event: dict[str, Any]) -> bool:
    return source_mentions(source_text(event), "ukmto")


def official_product(event: dict[str, Any]) -> bool:
    source = source_text(event)
    return source_mentions(source, "ukmto") or source_mentions(source, "jmic")


def source_date(event: dict[str, Any]) -> dt.date | None:
    candidates: list[dt.date] = []
    for key in ("published_at", "retrieved_at", "date_start", "date"):
        value = event.get(key)
        if isinstance(value, str):
            match = re.match(r"^(\d{4}-\d{2}-\d{2})", value)
            if match:
                try:
                    candidates.append(dt.date.fromisoformat(match.group(1)))
                except ValueError:
                    pass
    return max(candidates) if candidates else None


def numeric_deaths(event: dict[str, Any]) -> int | None:
    value = event.get("deaths_confirmed")
    if isinstance(value, bool):
        return None
    # الصفر المعبأ آليًا عند غياب إعلان وفاة ليس رقمًا معلنًا؛ لا يدخل
    # مجموعة القياس، ولا يتحول غياب الإعلان إلى حصيلة صفرية.
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        return int(value)
    return None


def metric_sources() -> list[str]:
    return [SOURCE_DAILY, SOURCE_MASTER]


def make_metric(
    metric_id: str,
    rows: list[dict[str, Any]],
    today: dt.date,
    predicate,
    definition: str,
    basis: str,
    confidence: str,
) -> dict[str, Any]:
    selected = [event for event in rows if predicate(event)]
    today_rows = [event for event in selected if event["_event_date"] == today.isoformat()]
    dates = [source_date(event) for event in selected]
    dates = [value for value in dates if value is not None]
    updated = max(dates).isoformat() if dates else None
    updated_rule = " قاعدة updated: أعلى تاريخ من published_at أو retrieved_at أو date_start، مع استخدام تاريخ الواقعة عند غياب الحقلين الأولين."
    if not selected:
        return {
            "id": metric_id,
            "title": METRIC_TITLES[metric_id],
            "today": None,
            "cumulative": None,
            "updated": None,
            "definition": definition,
            "basis": basis + updated_rule + " لا يوجد سجل صالح لهذا المقياس في النطاق؛ لذلك القيمتان null.",
            "sources": metric_sources(),
            "confidence": "غير متاح",
        }
    return {
        "id": metric_id,
        "title": METRIC_TITLES[metric_id],
        "today": len(today_rows),
        "cumulative": len(selected),
        "updated": updated,
        "definition": definition,
        "basis": basis + updated_rule,
        "sources": metric_sources(),
        "confidence": confidence,
    }


def _load_imo_source() -> dict[str, Any] | None:
    if not IMO_PATH.exists():
        return None
    try:
        data = json.loads(IMO_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _imo_as_at_date(data: dict[str, Any]) -> dt.date | None:
    """تحويل source.as_at (مثل «3 November 2026») إلى تاريخ قابل للمقارنة."""
    raw = str((data.get("source") or {}).get("as_at") or "").strip()
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw)
    if not match:
        return None
    try:
        month = dt.datetime.strptime(match.group(2), "%B").month
        return dt.date(int(match.group(3)), month, int(match.group(1)))
    except (ValueError, TypeError):
        return None


def _imo_previous_total(data: dict[str, Any], key: str) -> int | None:
    previous = data.get("previous") or {}
    totals = previous.get("totals") if isinstance(previous, dict) else {}
    value = totals.get(key) if isinstance(totals, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def make_imo_attacks(today: dt.date) -> dict[str, Any]:
    """مقياس سجل الحوادث المؤكدة من القائمة الرسمية للمنظمة البحرية الدولية."""
    base = {
        "id": "imo-confirmed-incidents",
        "title": "سجل الحوادث المؤكدة من IMO",
        "today": None,
        "cumulative": None,
        "updated": None,
        "definition": "واقعة مؤكدة على سفينة تجارية مدرجة في قائمة المنظمة البحرية الدولية الرسمية.",
        "basis": "عدّ مباشر من القائمة الرسمية للمنظمة البحرية الدولية (appendices/imo-incidents.json)؛ لا تُرفع فيها الروايات ولا تُحتسب غير المؤكدة.",
        "sources": ["appendices/imo-incidents.json", IMO_URL],
        "confidence": "عالية",
    }
    data = _load_imo_source()
    if data is None:
        base["basis"] += " ملف القائمة الرسمية مفقود أو غير صالح؛ لذلك القيمتان null."
        base["confidence"] = "غير متاح"
        return base
    incidents = data.get("incidents") or []
    totals = data.get("totals") or {}
    cumulative = totals.get("confirmed_incidents")
    if cumulative is None:
        cumulative = len(incidents)
    previous = _imo_previous_total(data, "confirmed_incidents")
    stamp = _imo_as_at_date(data)
    # قاعدة صحيحة: الفرق يُحتسب في يوم تحديث المصدر نفسه فقط؛ أي يوم لاحق بلا تحديث = 0
    same_day = bool(stamp and today and stamp == today)
    day_hits = (cumulative - previous) if (previous is not None and same_day) else 0
    base.update({
        "today": day_hits,
        "cumulative": cumulative,
        "updated": stamp.isoformat() if stamp else None,
    })
    base["basis"] += (" قاعدة today: الفرق بين totals الحالية وprevious.totals، ويُحتسب صفرًا في أي يوم لا يوجد فيه تحديث للمصدر "
                      "(لا يُنقل فرق يوم سابق إلى يوم جديد)؛ قاعدة updated: source.as_at في الصفحة الرسمية.")
    base["definition"] = data.get("definition") or base["definition"]
    warn = data.get("comparison_warning")
    if warn:
        base["basis"] += " " + str(warn)
    return base


def make_imo_deaths(today: dt.date) -> dict[str, Any]:
    """مقياس وفيات البحارة من نفس سجل IMO الرسمي، بلا اشتقاق من دفتر الوقائع."""
    base = {
        "id": "imo-seafarer-deaths",
        "title": "أعداد الوفيات من IMO",
        "today": None,
        "cumulative": None,
        "updated": None,
        "definition": "عدد وفيات البحارة المؤكد في القائمة الرسمية للمنظمة البحرية الدولية.",
        "basis": "عدّ مباشر من القائمة الرسمية للمنظمة البحرية الدولية (appendices/imo-incidents.json)؛ لا يُستنتج من دفتر المشروع.",
        "sources": ["appendices/imo-incidents.json", IMO_URL],
        "confidence": "عالية",
    }
    data = _load_imo_source()
    if data is None:
        base["basis"] += " ملف القائمة الرسمية مفقود أو غير صالح؛ لذلك القيمتان null."
        base["confidence"] = "غير متاح"
        return base
    totals = data.get("totals") or {}
    cumulative = totals.get("confirmed_seafarer_deaths")
    previous = _imo_previous_total(data, "confirmed_seafarer_deaths")
    stamp = _imo_as_at_date(data)
    same_day = bool(stamp and today and stamp == today)
    base.update({
        "today": (cumulative - previous) if (isinstance(cumulative, int) and previous is not None and same_day) else 0,
        "cumulative": cumulative if isinstance(cumulative, int) else None,
        "updated": stamp.isoformat() if stamp else None,
    })
    base["basis"] += (" قاعدة today: الفرق بين totals الحالية وprevious.totals، ويُحتسب صفرًا في أي يوم لا يوجد فيه تحديث للمصدر؛ "
                      "قاعدة updated: source.as_at في الصفحة الرسمية.")
    return base


def make_deaths(rows: list[dict[str, Any]], today: dt.date) -> dict[str, Any]:
    raw_selected = [event for event in rows if numeric_deaths(event) is not None]
    excluded_non_seafarer = [
        event for event in raw_selected
        if str(event.get("casualty_scope") or "") in NON_SEAFARER_CASUALTY_SCOPES
    ]
    selected = [event for event in raw_selected if event not in excluded_non_seafarer]
    today_selected = [event for event in selected if event["_event_date"] == today.isoformat()]
    updated_values = [source_date(event) for event in selected]
    updated_values = [value for value in updated_values if value is not None]
    updated = max(updated_values).isoformat() if updated_values else None
    cumulative = sum(numeric_deaths(event) or 0 for event in selected) if selected else None
    if today_selected:
        today_value: int | None = sum(numeric_deaths(event) or 0 for event in today_selected)
        today_note = "اليوم حُسب من القيم الرقمية الصريحة deaths_confirmed في صفوف اليوم."
    else:
        today_value = None
        today_note = "لا يوجد صف في تاريخ اليوم يحمل deaths_confirmed رقميًا؛ today=null ولا يُستنتج الصفر من غياب الحقل."
    basis = (
        "المجموع هو جمع deaths_confirmed الموجب والمعلن فقط بعد استبعاد سجل counted=false/duplicate_of؛ "
        "لا تُقرأ الأرقام من العناوين أو الملخصات التراكمية، وتُستبعد وفيات غير البحارة بحسب casualty_scope. "
        + today_note
        + f" استُبعدت {len(excluded_non_seafarer)} صفوف غير بحارة من القياس."
        + " قاعدة updated: أعلى تاريخ من published_at أو retrieved_at أو date_start، مع استخدام تاريخ الواقعة عند غياب الحقلين الأولين."
    )
    return {
        "id": "deaths",
        "title": METRIC_TITLES["deaths"],
        "today": today_value,
        "cumulative": cumulative,
        "updated": updated,
        "definition": "مجموع الوفيات التي يثبتها الحقل الرقمي deaths_confirmed في واقعة فريدة.",
        "basis": basis,
        "sources": metric_sources(),
        "confidence": "متوسطة" if selected else "غير متاح",
    }


def build_payload(target: dt.date) -> tuple[dict[str, Any], dict[str, Any]]:
    daily_rows, days_total, daily_duplicate_codes, gap_days = load_daily(target)
    master_rows, excluded_master = load_master()
    # daily_rows is intentionally retained as a validated input and its
    # coverage is reported.  Metrics use the canonical master events list.
    del daily_rows
    target_iso = target.isoformat()
    range_rows = [
        event
        for event in master_rows
        if START_DATE.isoformat() <= event["_event_date"] <= target_iso
    ]
    metrics = [
        make_metric(
            "ukmto-reports",
            range_rows,
            target,
            direct_ukmto,
            "عدد السجلات الفريدة التي يذكر مصدرها UKMTO أو رابط ukmto.org.",
            "عدّ مباشر من source(s)؛ صف JMIC · UKMTO يُحسب صفًا واحدًا، والتاريخ يُسند إلى date_start.",
            "عالية",
        ),
        make_metric(
            "qualifying-incidents",
            range_rows,
            target,
            qualifying,
            "واقعة بحرية لها نوع مؤهل (هجوم/استهداف/إطلاق/انفجار/ألغام/اختطاف/حريق/غرق/إعاقة/تعطيل ملاحي/نشاط مشبوه) وهدف بحري أو ملاحي.",
            "تطبيق علامات النوع والهدف على description/classification/outcome بعد استبعاد صفوف لا واقعة؛ لا تُستخرج أرقام من عناوين الملخصات.",
            "متوسطة",
        ),
        make_metric(
            "unconfirmed-narratives",
            range_rows,
            target,
            unconfirmed_narrative,
            "رواية يصفها السجل صراحةً بأنها رواية أو يصنفها كذلك، مع evidence_status غير محسوم.",
            "الوصف يبدأ بـ«رواية» أو classification يحمل وسم الرواية؛ تُذكر الرواية ولا تُرفع إلى واقعة مؤكدة.",
            "متوسطة",
        ),
        make_metric(
            "confirmed-incidents",
            range_rows,
            target,
            confirmed,
            "واقعة evidence_status لها confirmed_effect_or_attack في قائمة events الحاكمة.",
            "حالة الدفتر الرئيسي وحدها هي أساس التأكيد؛ لا تُحوّل تقارير IMO التراكمية أو العناوين إلى وقائع إضافية.",
            "عالية",
        ),
        make_deaths(range_rows, target),
        make_imo_attacks(target),
        make_imo_deaths(target),
        make_metric(
            "fire-incidents",
            range_rows,
            target,
            fire,
            "واقعة سفينة يتضمن outcome حريقًا أو نصها وصفًا صريحًا لحريق/اشتعال/إخماد حريق.",
            "بحث محافظ في outcome والنص داخل حالات واقعة مسجلة؛ لا تُحتسب نشرات التحذير أو ملخصات القرصنة بلا واقعة سفينة.",
            "متوسطة",
        ),
        make_metric(
            "official-products",
            range_rows,
            target,
            official_product,
            "سجل مصدره UKMTO أو JMIC؛ كل code/identity يُحسب مرة واحدة حتى إن جمع الجهتين.",
            "مطابقة اسم المصدر أو رابط المصدر مباشرة؛ لا تُدّعى جدة المنتج، بل رصده في السجل.",
            "عالية",
        ),
    ]
    payload = {
        "date": target_iso,
        "range": {
            "from": START_DATE.isoformat(),
            "to": target_iso,
            "days_covered": days_total,
            "days_total": days_total,
            "migration_gap_days": gap_days,
        },
        "metrics": metrics,
    }
    audit = {
        "daily_rows": None,
        "daily_duplicate_codes": daily_duplicate_codes,
        "master_events": len(master_rows) + len(excluded_master),
        "canonical_events": len(master_rows),
        "excluded_master": excluded_master,
        "range_events": len(range_rows),
    }
    return payload, audit


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temp_name).replace(path)
    except Exception:
        try:
            Path(temp_name).unlink(missing_ok=True)
        finally:
            raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build cumulative maritime ledger KPI totals")
    parser.add_argument("--date", required=True, help="Target ledger date in YYYY-MM-DD")
    parser.add_argument("--write", action="store_true", help="Write web/kpis-totals/<date>.json atomically")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        target = parse_iso_date(args.date, "--date")
        payload, _audit = build_payload(target)
        content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.write:
            output_path = OUTPUT_DIR / f"{target.isoformat()}.json"
            atomic_write(output_path, content)
        sys.stdout.write(content)
        return 0
    except LedgerError as exc:
        sys.stderr.write(f"فشل مغلق: {exc}\n")
        return 2
    except Exception as exc:  # unexpected parser/data errors are also fail-closed
        sys.stderr.write(f"فشل مغلق غير متوقع: {type(exc).__name__}: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
