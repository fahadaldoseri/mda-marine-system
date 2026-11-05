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
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


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
        return (f"{counter.get('unconfirmed_total') or 0} روايات · منها "
                f"{counter.get('unconfirmed_qualifying') or 0} مؤهلة · تُذكر ولا تُحتسب")
    if detail.get("kind") == "fire_split":
        fire = (meta.get("hero_sources") or {}).get("fire") or {}
        return (f"المؤكد: {fire.get('confirmed') or 0} · المرجّح: {fire.get('probable') or 0} · "
                f"غير المؤكد: {fire.get('unconfirmed') or 0}")
    return str(detail.get("ar") or "")


def build(meta: dict, zones: dict, registry: dict, kpis: dict) -> list[dict]:
    contract = registry.get("hero_kpis") or {}
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
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"   ✔ بُني {len(cards)} بطاقة من العقد · تغيّرت: {len(changed)}"
              + (f" ({', '.join(changed)})" if changed else ""))
    else:
        print(f"   ✔ قياس: {len(cards)} بطاقة · مطابقة: {len(cards) - len(changed)} · مخالفة: {len(changed)}")
        for cid in changed:
            card = next(c for c in cards if c["id"] == cid)
            print(f"      · {cid}: value={card['value']} · detail={card['detail'][:60]} · source={str(card['source'])[:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())