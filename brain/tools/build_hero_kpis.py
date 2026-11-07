#!/usr/bin/env python3
"""يبني بطاقات صفّي المؤشرات (hero_kpis) من عقدها الحاكم والعدّادات — مصدر واحد بلا كتابة يدوية.

العلّة الجذرية التي يعالجها: كانت بطاقات صف المؤشرات تُكتب نصًّا في ملف الواجهة، فتتباعد قيمها
وتفاصيلها ووسومها عن السجل الحاكم (appendices/card_registry.json) وعن عدّادات القطاعات
(web/zones/{date}.json) ومجاميع الدفتر (web/kpis-totals/{date}.json)، فيمنعها حارس العدّادات.

القاعدة: العقد هو مصدر العناوين والوسوم والترتيب ومصادر العرض؛ والقيم والتفاصيل تُحسب من العدّادات
والمجاميع. يُعاد التوليد في كل جولة، فلا يمكن أن تنحرف البطاقة عن مصدرها.

الاستخدام:
    python3 tools/build_hero_kpis.py --date 2026-11-05 --check     # قياس بلا كتابة
    python3 tools/build_hero_kpis.py --date 2026-11-05 --apply     # كتابة في ملف الواجهة
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ALLOWED_ACCENTS = frozenset(("ok", "info", "warn", "danger"))
sys.path.insert(0, str(ROOT))
from tools.arabic_counter import format_arabic_count  # noqa: E402


def load(path: pathlib.Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def metric(kpis: dict, metric_id: str, field: str = "today"):
    for item in (kpis.get("metrics") or []):
        if isinstance(item, dict) and str(item.get("id")) == metric_id:
            return item.get(field)
    return None


def hero_value(meta: dict, zones: dict, card: dict, kpis: dict):
    source = card.get("source") or {}
    kind = source.get("kind")
    if kind == "zones_counter":
        return (zones.get("counter") or {}).get(source.get("key"))
    if kind == "zones_sum":
        ids = set(source.get("zone_ids") or [])
        return sum(int(z.get(source.get("field"), 0) or 0)
                   for z in (zones.get("zones") or []) if z.get("id") in ids)
    if kind == "meta_path":
        value = meta
        for part in source.get("path") or []:
            value = value[part]
        return value
    if kind == "kpis_totals":
        return metric(kpis, str(source.get("id") or ""), source.get("field", "today"))
    return None


def hero_detail(meta: dict, zones: dict, card: dict) -> str:
    detail = card.get("detail") or {}
    counter = zones.get("counter") or {}
    if detail.get("kind") == "qualifying_composition":
        return (f"{counter.get('confirmed') or 0} مؤكدة + {counter.get('probable') or 0} مرجّحة + "
                f"{counter.get('unconfirmed_qualifying') or 0} غير مؤكدة مؤهلة")
    if detail.get("kind") == "unconfirmed_split":
        total = counter.get("unconfirmed_total") or 0
        count = int(total)
        return (f"{format_arabic_count(count, card.get('number_format'))} · منها "
                f"{counter.get('unconfirmed_qualifying') or 0} مؤهلة · تُذكر ولا تُحتسب")
    if detail.get("kind") == "fire_split":
        fire = (meta.get("hero_sources") or {}).get("fire") or {}
        return (f"المؤكد: {fire.get('confirmed') or 0} · المرجّح: {fire.get('probable') or 0} · "
                f"غير المؤكد: {fire.get('unconfirmed') or 0}")
    return str(detail.get("ar") or "")


def _display_date(value) -> str:
    """يحوّل تاريخ المصدر ISO إلى صيغة العرض دون اختراع تاريخ بديل."""
    raw = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw)
    return f"{match.group(3)}/{match.group(2)}/{match.group(1)}" if match else raw


def _source_updated(meta: dict, zones: dict, card: dict, kpis: dict) -> str:
    source = card.get("source") or {}
    kind = source.get("kind")
    if kind in {"zones_counter", "zones_sum"}:
        return _display_date(zones.get("date"))
    if kind == "kpis_totals":
        return _display_date(metric(kpis, str(source.get("id") or ""), "updated"))
    if kind == "meta_path":
        return _display_date(metric(kpis, str(card.get("id") or ""), "updated"))
    return ""


def hero_note(meta: dict, zones: dict, card: dict, kpis: dict, value) -> str:
    """ينشئ ملاحظة قابلة للتدقيق من التفصيل المشتق وتاريخ المصدر."""
    presentation = card.get("presentation") or {}
    kind = presentation.get("note")
    detail = hero_detail(meta, zones, card)
    if kind == "scoped_value_with_source_date":
        tag = str(card.get("tag") or "").strip() or "النطاق المسجل"
        detail = f"{value} وقائع مثبتة في {tag} خلال فترة التقرير"
    if not detail:
        return ""
    updated = _source_updated(meta, zones, card, kpis)
    if kind in {"derived_detail_with_source_date", "scoped_value_with_source_date"} and updated:
        return f"{detail}؛ آخر تحديث المصدر: {updated}."
    return detail


def hero_accent(zones: dict, card: dict, allowed: set[str]) -> str:
    """يشتق accent من حالة العداد وفق قاعدة العقد، ضمن القيم المسموحة فقط."""
    rule = (card.get("presentation") or {}).get("accent_rule") or {}
    kind = rule.get("kind")
    counter = zones.get("counter") or {}
    if kind == "explicit":
        value = str(rule.get("value") or "")
    elif kind == "unconfirmed_or_probable_warn":
        value = "warn" if any(int(counter.get(key) or 0) > 0 for key in ("unconfirmed_qualifying", "probable")) else "ok"
    elif kind == "positive_warn":
        value = "warn" if int(counter.get("unconfirmed_total") or 0) > 0 else "info"
    elif kind == "positive_danger":
        value = "danger" if int(card.get("_derived_value") or 0) > 0 else "ok"
    else:
        value = "info"
    if value not in allowed:
        raise ValueError(f"accent غير مسموح في عقد hero_kpis: {value}")
    return value


def _imo_totals() -> tuple[dict, dict]:
    """يقرأ مجاميع IMO وتاريخ القراءة من المصدر المحفوظ، لا من نص يوم سابق."""
    appendix = load(ROOT / "appendices" / "imo-incidents.json")
    return appendix.get("totals") or {}, appendix.get("source") or {}


def _imo_date(source: dict) -> str:
    """يحوّل ``3 November 2026`` إلى صيغة العرض المعتمدة في البطاقات."""
    raw = str(source.get("as_at") or "").strip()
    months = {
        "January": "01", "February": "02", "March": "03", "April": "04",
        "May": "05", "June": "06", "July": "07", "August": "08",
        "September": "09", "October": "10", "November": "11", "December": "12",
    }
    match = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw)
    if not match or match.group(2) not in months:
        return raw
    return f"{int(match.group(1)):02d}/{months[match.group(2)]}/{match.group(3)}"


def _previous_total(previous: dict, card_id: str) -> int:
    """يستخرج مجموع يوم أمس لتكوين طبقة daily بلا تخمين أو كتابة يدوية."""
    card = previous.get(card_id) or {}
    value = ((card.get("layers") or {}).get("cumulative") or {}).get("value")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_official_cards(meta: dict, registry: dict) -> list[dict]:
    """ينشئ قائمة البطاقات الرسمية من العقد ومصدر IMO في كل تشغيل.

    العقد يحدد الشكل والعناوين، وملف IMO يحدد المجاميع وتاريخ القراءة. إذا كانت
    بطاقة اليوم موجودة، يُستخدم مجموعها السابق لحساب فرق اليوم فقط؛ ولا يُنسخ
    ملف يوم سابق كاملًا ولا تُضاف بطاقة يدويًا إلى ملف تاريخ بعينه.
    """
    contract = registry.get("official_cards") or {}
    previous = {str(c.get("id")): c for c in (meta.get("official_cards") or [])
                if isinstance(c, dict) and c.get("id")}
    totals, source = _imo_totals()
    incidents = int(totals.get("confirmed_incidents") or 0)
    deaths = int(totals.get("confirmed_seafarer_deaths") or 0)
    as_at = _imo_date(source)
    cards: list[dict] = []
    for item in contract.get("cards") or []:
        card = copy.deepcopy(item)
        cid = str(card.get("id"))
        layers = card.setdefault("layers", {})
        if cid == "imo-confirmed-incidents":
            before = _previous_total(previous, cid)
            daily = incidents - before if before else 0
            daily_layer = layers.setdefault("daily", {})
            daily_layer.update({
                "state": "shown",
                "value": str(daily),
                "value_en": str(daily),
                "source": f"قائمة IMO الرسمية؛ الفرق بين القراءة الحالية والسابقة = {daily}",
                "source_en": f"Official IMO list; difference from the previous reading = {daily}",
            })
            cumulative = layers.setdefault("cumulative", {})
            cumulative.update({
                "value": str(incidents),
                "value_en": str(incidents),
                "source": f"IMO — {incidents} حادثة مؤكدة حتى {as_at}",
                "source_en": f"IMO — {incidents} confirmed incidents as at {as_at}",
            })
            updated = layers.setdefault("updated", {})
            updated.update({
                "value": as_at,
                "value_en": as_at,
                "source": f"القائمة الرسمية بتاريخ بيانات {as_at}",
                "source_en": f"Official list as at {as_at}",
            })
        elif cid == "imo-seafarer-deaths":
            before = _previous_total(previous, cid)
            daily = deaths - before if before else 0
            daily_layer = layers.setdefault("daily", {})
            daily_layer.update({
                "state": "shown",
                "value": str(daily),
                "value_en": str(daily),
                "source": f"قائمة IMO الرسمية؛ الفرق بين القراءة الحالية والسابقة = {daily}",
                "source_en": f"Official IMO list; difference from the previous reading = {daily}",
            })
            cumulative = layers.setdefault("cumulative", {})
            cumulative.update({
                "value": str(deaths),
                "value_en": str(deaths),
                "source": f"IMO — {deaths} وفاة بحّار مؤكدة حتى {as_at}",
                "source_en": f"IMO — {deaths} confirmed seafarer deaths as at {as_at}",
            })
            updated = layers.setdefault("updated", {})
            updated.update({
                "value": as_at,
                "value_en": as_at,
                "source": f"القائمة الرسمية بتاريخ بيانات {as_at}",
                "source_en": f"Official list as at {as_at}",
            })
        cards.append(card)
    return cards


def build(meta: dict, zones: dict, registry: dict, kpis: dict) -> list[dict]:
    contract = registry.get("hero_kpis") or {}
    allowed = set(contract.get("allowed_accents") or DEFAULT_ALLOWED_ACCENTS)
    if not allowed or not allowed.issubset(DEFAULT_ALLOWED_ACCENTS):
        raise ValueError(f"مجموعة accent في العقد غير صالحة: {sorted(allowed)}")
    previous = {str(c.get("id")): c for c in (meta.get("hero_kpis") or []) if isinstance(c, dict)}
    cards: list[dict] = []
    for item in (contract.get("cards") or []):
        cid = str(item.get("id"))
        card = dict(previous.get(cid) or {})
        card["id"] = cid
        card["row"] = item.get("row")
        card["title"] = item.get("title")
        card["title_en"] = item.get("title_en")
        card["tag"] = item.get("tag")
        card["tag_en"] = item.get("tag_en")
        card["source"] = item.get("source_label")
        value = hero_value(meta, zones, item, kpis)
        card["value"] = "" if value is None else str(value)
        card["detail"] = hero_detail(meta, zones, item)
        if not str(card.get("label") or "").strip():
            card["label"] = item.get("title") or ""
        if not str(card.get("note") or "").strip():
            card["note"] = hero_note(meta, zones, item, kpis, value)
        existing_accent = str(card.get("accent") or "").strip()
        if existing_accent not in allowed:
            contract_card = dict(item)
            contract_card["_derived_value"] = value
            card["accent"] = hero_accent(zones, contract_card, allowed)
        source = item.get("source") or {}
        if source.get("kind") == "kpis_totals":
            metric_id = str(source.get("id") or "")
            card["cumulative"] = str(metric(kpis, metric_id, "cumulative"))
            card["updated"] = str(metric(kpis, metric_id, "updated"))
        cards.append(card)
    return cards


def main() -> int:
    parser = argparse.ArgumentParser(description="بناء بطاقات صف المؤشرات من العقد والعدّادات")
    parser.add_argument("--date", required=True)
    parser.add_argument("--apply", action="store_true", help="اكتب في ملف الواجهة")
    parser.add_argument("--check", action="store_true", help="قياس بلا كتابة")
    args = parser.parse_args()

    meta_path = ROOT / "web" / "meta" / f"{args.date}.json"
    zones_path = ROOT / "web" / "zones" / f"{args.date}.json"
    kpis_path = ROOT / "web" / "kpis-totals" / f"{args.date}.json"
    registry_path = ROOT / "appendices" / "card_registry.json"
    for path in (meta_path, zones_path, registry_path):
        if not path.exists():
            print(f"   ✘ ملف مفقود: {path}")
            return 2

    meta = load(meta_path)
    zones = load(zones_path)
    registry = load(registry_path)
    kpis = load(kpis_path)
    cards = build(meta, zones, registry, kpis)
    contract = registry.get("hero_kpis") or {}
    changed = [c["id"] for c in cards if c != next(
        (x for x in (meta.get("hero_kpis") or []) if str(x.get("id")) == c["id"]), {})]

    if args.apply:
        meta["hero_kpis"] = cards
        meta["hero_risk_patterns"] = list(contract.get("risk_patterns") or [])
        official_cards = build_official_cards(meta, registry)
        meta["official_cards"] = official_cards
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"   ✔ بُني {len(cards)} بطاقة من العقد · تغيّرت: {len(changed)}"
              + (f" ({', '.join(changed)})" if changed else "")
              + f" · official_cards: {len(official_cards)} من العقد والمصدر الرسمي")
    else:
        print(f"   ✔ قياس: {len(cards)} بطاقة · مطابقة: {len(cards) - len(changed)} · مخالفة: {len(changed)}")
        for cid in changed:
            card = next(c for c in cards if c["id"] == cid)
            print(f"      · {cid}: value={card['value']} · detail={card['detail'][:60]} · source={str(card['source'])[:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
