#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تصنيف وقائع اليوم على القطاعات الأربعة وحساب مستوى تهديد لكل قطاع.

المصادر الحاكمة:
  appendices/zone-registry.json    حدود القطاعات وقواعد الإسناد والعدّ والتأكيد
  appendices/threat-scale.json     السلّم الخمسي ورتبه وحدوده الدنيا
  appendices/zone-overrides.json   الأحكام المحوكمة لكل واقعة (قطاع · أهلية · تأكيد · دمج)

المخرج:
  web/zones/<date>.json            بطاقة القطاعات: مستوى كل قطاع + المستوى العام + العدّاد

قواعد صارمة:
  - لا يُكتب أي مستوى خارج قائمة السلّم المعتمد (فشل مغلق).
  - كل واقعة تُنسب إلى قطاع واحد فقط أو تُوسم «غير مكانية».
  - العدّ بالحوادث: تقارير الحادثة الواحدة تُدمج عبر incident_group.
  - الادعاء غير المؤكد يُذكر ولا يرفع المستوى.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "appendices/zone-registry.json"
SCALE = ROOT / "appendices/threat-scale.json"
OVERRIDES = ROOT / "appendices/zone-overrides.json"
LEDGER_DIR = ROOT / "cumulative-2026/daily"
OUT_DIR = ROOT / "web/zones"

WINDOW_LABEL = "خلال 24 ساعة السابقة"

DAMAGE_MARKERS = ("أضرار", "حريق", "غرق", "إصابات", "توقف", "إخماد", "اشتعال", "انفجار")
# معيار العدّ (قرار المالك): ما يصيب السفن أو يمسّ ملاحتها فقط.
MARITIME_TARGETS = (
    "سفينة", "سفن", "ناقلة", "ناقلات", "قارب", "زورق", "مركب", "يخت", "باخرة", "عائمة",
    "وحدة بحرية", "سفينة شحن", "حاملة", "رصيف", "ميناء",
)
NAV_MARKERS = (
    "ملاحة", "الملاحة", "ممر", "مضيق", "إشارات", "كابلات", "خطوط ملاحية", "تعطيل",
    "ميلًا بحريًا", "ميل بحري", "بحريًا",
)
LAND_ONLY_TARGETS = ("مطار", "منشأة", "مصفاة", "قاعدة عسكرية", "مدينة", "قرية", "مخيم", "مبنى")

# تصنيف ثابت لكل واقعة ⇒ نص البطاقة يُبنى من معجم مغلق قابل للترجمة آليًا
CATEGORY_OF_TYPE = {
    "هجوم": "هجوم على سفينة",
    "استهداف": "استهداف سفينة",
    "نشاط مشبوه": "نشاط مشبوه",
    "حريق": "حريق على متن سفينة",
    "انفجار": "انفجار قرب سفينة",
    "اختطاف": "اختطاف",
    "استيلاء": "استيلاء على سفينة",
    "ألغام": "تهديد ألغام",
    "تفتيش": "تفتيش غير قانوني",
    "إشارات": "تعطيل ملاحي",
    "كابلات": "تعطيل ملاحي",
    "تعطيل": "تعطيل ملاحي",
}
FULL_DISRUPTION_MARKERS = ("إغلاق الممر", "تعليق الملاحة", "توقف كامل", "إغلاق المضيق")
CASUALTY_MARKERS = ("قتلى", "خسائر بشرية", "إصابات بشرية", "مفقودين")


class FailClosed(Exception):
    """خروج فاشل مغلق برمز 2 مع رسالة مانعة."""


def _load(path: pathlib.Path):
    if not path.exists():
        raise FailClosed(f"ملف حاكم مفقود: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        raise FailClosed(f"تعذّر قراءة {path}: {exc}")


def load_governed():
    reg = _load(REGISTRY)
    scale = _load(SCALE)
    ovr = _load(OVERRIDES)
    levels = {lv["ar"]: lv for lv in scale["levels"]}
    if len(levels) != 5:
        raise FailClosed("السلّم المعتمد لا يحتوي خمسة مستويات")
    # منع تداخل الكلمات بين القطاعات
    seen: dict[str, str] = {}
    for z in reg["zones"]:
        for kw in z["keywords"]:
            if kw in seen:
                raise FailClosed(f"كلمة مكررة بين قطاعين: «{kw}» في {seen[kw]} و{z['id']}")
            seen[kw] = z["id"]
    return reg, scale, levels, ovr


def zone_of(event: dict, reg: dict, day_overrides: dict) -> tuple[str | None, str]:
    """يُعيد (معرّف القطاع أو None، سبب الإسناد)."""
    code = event.get("code", "")
    ov = day_overrides.get(code) or {}
    if "zone" in ov:
        return ov["zone"], "حكم محوكم في zone-overrides"
    hay = " ".join(str(event.get(k, "")) for k in ("area", "title", "source_excerpt"))
    hits: list[tuple[int, str, str]] = []
    for z in reg["zones"]:
        for kw in z["keywords"]:
            if kw in hay:
                hits.append((len(kw), z["id"], kw))
    if hits:
        hits.sort(reverse=True)  # الكلمة الأطول تُرجَّح عند التزاحم
        return hits[0][1], f"كلمة الموقع «{hits[0][2]}»"
    return None, "بلا موقع بحري"


def is_qualifying(event: dict, reg: dict, day_overrides: dict) -> tuple[bool, str, str]:
    """يُعيد (مؤهّلة؟، درجة التأكيد، السبب)."""
    code = event.get("code", "")
    ov = day_overrides.get(code) or {}
    conf_map = reg["counting"]["confirmation"]
    cls = event.get("class", "")
    conf = "unconfirmed"
    for level, classes in conf_map.items():
        if cls in classes:
            conf = level
            break
    if "confirmation" in ov:
        conf = ov["confirmation"]
    hay = f"{event.get('title','')} {event.get('source_excerpt','')}"
    qual_hit = next((t for t in reg["counting"]["qualifying_types"] if t in hay), None)
    non_hit = next((t for t in reg["counting"]["non_qualifying_types"] if t in hay), None)
    if "qualifying" in ov:
        reason = ov.get("reason", "حكم محوكم")
        return bool(ov["qualifying"]), conf, reason
    if non_hit and not qual_hit:
        return False, conf, f"نوع غير مؤهّل: «{non_hit}»"
    if qual_hit:
        maritime = next((t for t in MARITIME_TARGETS if t in hay), None)
        nav = next((t for t in NAV_MARKERS if t in hay), None)
        if maritime or nav:
            tag = maritime or nav
            return True, conf, f"نوع مؤهّل: «{qual_hit}» وهدف بحري/ملاحي: «{tag}»"
        land = next((t for t in LAND_ONLY_TARGETS if t in hay), None)
        if land:
            return False, conf, f"نوع مؤهّل «{qual_hit}» لكن الهدف بري «{land}» لا يمسّ الملاحة"
        return False, conf, f"نوع مؤهّل «{qual_hit}» بلا هدف بحري مثبت ⇒ يلزم بحث في المصادر"
    return False, conf, "لا نوع مؤهّل في العنوان"


def rank_of_zone(rows: list[dict], levels: dict, registry_order: list[str]) -> dict:
    """يحسب رتبة القطاع من صفوفه المصنّفة."""
    groups: dict[str, dict] = {}
    for r in rows:
        if not r["qualifying"]:
            continue
        g = r.get("incident_group") or r["code"]
        cur = groups.setdefault(g, {"conf": r["confirmation"], "titles": [], "codes": [], "texts": []})
        cur["titles"].append(r["title"])
        cur["codes"].append(r["code"])
        cur["texts"].append(r["title"] + " " + str(r.get("source_excerpt", "")))
        order = {"confirmed": 3, "probable": 2, "unconfirmed": 1}
        if order[r["confirmation"]] > order[cur["conf"]]:
            cur["conf"] = r["confirmation"]
    confirmed = [g for g, v in groups.items() if v["conf"] == "confirmed"]
    probable = [g for g, v in groups.items() if v["conf"] == "probable"]
    unconfirmed = [g for g, v in groups.items() if v["conf"] == "unconfirmed"]
    attack_damage = bool(
        any(
            v["conf"] == "confirmed"
            and any(t in " ".join(v["texts"]) for t in ("هجوم", "استهداف", "انفجار"))
            and any(d in " ".join(v["texts"]) for d in DAMAGE_MARKERS)
            for v in groups.values()
        )
    )
    hay = " ".join(r["title"] + " " + str(r.get("source_excerpt", "")) for r in rows if r["qualifying"])
    full_disruption = any(m in hay for m in FULL_DISRUPTION_MARKERS)
    casualties = any(m in hay for m in CASUALTY_MARKERS)
    sinking = "غرق" in hay
    if full_disruption or casualties or sinking:
        ar = "حرج"
    elif len(confirmed) >= 2 or attack_damage:
        ar = "مرتفع جدًا"
    elif len(confirmed) == 1:
        ar = "مرتفع"
    elif probable or unconfirmed:
        ar = "متوسط"
    else:
        ar = "منخفض"
    if ar not in levels:
        raise FailClosed(f"مستوى غير معتمد: «{ar}» — لا يُكتب أي مستوى خارج السلّم")
    return {
        "level": ar,
        "rank": levels[ar]["rank"],
        "confirmed": len(confirmed),
        "probable": len(probable),
        "unconfirmed_qualifying": len(unconfirmed),
        "incidents": {g: groups[g]["conf"] for g in groups},
        "attack_with_damage": attack_damage,
        "full_disruption": full_disruption,
        "casualties": casualties,
        "sinking": sinking,
    }


def load_day(date: str) -> list[dict] | None:
    p = LEDGER_DIR / f"{date}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in ("events", "items", "rows"):
            if isinstance(data.get(key), list):
                return data[key]
        raise FailClosed(f"بنية دفتر غير معروفة: {p}")
    if not isinstance(data, list):
        raise FailClosed(f"بنية دفتر غير معروفة: {p}")
    return data


def is_unconfirmed_narrative(row: dict) -> bool:
    """يميز الرواية غير المؤكدة عن كل نقل غير مؤكد أو سجل عدم وقوع."""
    return row.get("confirmation") == "unconfirmed" and str(row.get("title", "")).startswith("رواية ")


def classify_day(date: str, reg, scale, levels, ovr, *, carry: bool = True) -> dict:
    """يصنّف يومًا واحدًا. carry=False يمنع التعاود عند البحث عن رتبة سابقة."""
    events = load_day(date)
    if events is None:
        raise FailClosed(f"لا يوجد دفتر وقائع لليوم {date}")
    day_ov = (ovr.get("dates") or {}).get(date) or {}
    rows = []
    for ev in events:
        z, zreason = zone_of(ev, reg, day_ov)
        q, conf, qreason = is_qualifying(ev, reg, day_ov)
        ov = day_ov.get(ev.get("code", "")) or {}
        nonspatial = bool(ov.get("nonspatial")) or z is None
        rows.append({
            "code": ev.get("code", ""),
            "title": ev.get("title", ""),
            "area": ev.get("area", ""),
            "class": ev.get("class", ""),
            "zone": None if nonspatial else z,
            "nonspatial": nonspatial,
            "zone_reason": zreason,
            "qualifying": q and not nonspatial,
            "confirmation": conf,
            "qualify_reason": qreason,
            "incident_group": ov.get("incident_group") or ev.get("code", ""),
            "source_excerpt": ev.get("source_excerpt", ""),
        })
    for r in rows:
        r["category"] = ""
        for t, cat in CATEGORY_OF_TYPE.items():
            if t in (r["title"] + " " + r["source_excerpt"]):
                r["category"] = cat
                break
    zones_out = []
    for z in reg["zones"]:
        zrows = [r for r in rows if r["zone"] == z["id"]]
        res = rank_of_zone(zrows, levels, [x["id"] for x in reg["zones"]])
        qcodes = [r["code"] for r in zrows if r["qualifying"]]
        basis_bits = [r["title"] for r in zrows if r["qualifying"]]
        basis = ("وقائع مؤهّلة: " + " · ".join(dict.fromkeys(basis_bits)))[:320] if basis_bits else "لا واقعة مؤهّلة داخل الفترة."
        zones_out.append({
            "id": z["id"],
            "name": z["ar"],
            "level": res["level"],
            "rank": res["rank"],
            "confirmed": res["confirmed"],
            "probable": res["probable"],
            "excluded": len([r for r in zrows if not r["qualifying"]]),
            "events": len(zrows),
            "qualifying_codes": qcodes,
            "categories": list(dict.fromkeys([r["category"] for r in zrows if r["qualifying"] and r["category"]])),
            "basis": basis,
            "flags": {k: res[k] for k in ("attack_with_damage", "full_disruption", "casualties", "sinking")},
            "carry_over": False,
            "last_change": date,
        })
    # الحمل: قطاع بلا واقعة اليوم يرث رتبة آخر واقعة داخل مدة الحمل
    carry_days = int(scale.get("carry_over_days", 7))
    for z in (zones_out if carry else []):
        if z["confirmed"] or z["probable"] or z["rank"] > 1:
            continue
        found = None
        for back in range(1, carry_days + 1):
            d = _shift(date, -back)
            try:
                prev = classify_day(d, reg, scale, levels, ovr, carry=False)
            except FailClosed:
                continue
            pz = next((x for x in prev["zones"] if x["id"] == z["id"]), None)
            if pz and pz["rank"] > 1:
                found = (d, pz)
                break
        if found:
            d, pz = found
            z["level"] = pz["level"]
            z["rank"] = pz["rank"]
            z["carry_over"] = True
            z["carry_from"] = d
            z["last_change"] = d
            z["basis"] = f"استمراري — آخر واقعة مؤهّلة في هذا القطاع بتاريخ {d}."
    overall = max(zones_out, key=lambda z: (z["rank"], -[x["id"] for x in reg["zones"]].index(z["id"])))
    counter = {
        "total": len(rows),
        "qualifying": len({r["incident_group"] for r in rows if r["qualifying"]}),
        "confirmed": len({r["incident_group"] for r in rows if r["qualifying"] and r["confirmation"] == "confirmed"}),
        "probable": len({r["incident_group"] for r in rows if r["qualifying"] and r["confirmation"] == "probable"}),
        "unconfirmed_qualifying": len({r["incident_group"] for r in rows if r["qualifying"] and r["confirmation"] == "unconfirmed"}),
        "unconfirmed_total": len({r["incident_group"] for r in rows if is_unconfirmed_narrative(r)}),
        "excluded": len([r for r in rows if not r["qualifying"] and not r["nonspatial"]]),
        "nonspatial": len([r for r in rows if r["nonspatial"]]),
    }
    top_basis = f"أعلى قطاع: {overall['name']} — {overall['basis']}"
    return {
        "date": date,
        "window": WINDOW_LABEL,
        "scale_version": scale["version"],
        "registry_version": reg["version"],
        "scale_levels": [{"ar": lv["ar"], "rank": lv["rank"], "token": lv["token"], "color": lv["color"], "marker": lv["marker"]} for lv in scale["levels"]],
        "overall": {
            "level": overall["level"],
            "rank": overall["rank"],
            "top_zone": overall["name"],
            "top_zone_id": overall["id"],
            "basis": top_basis,
        },
        "zones": zones_out,
        "counter": counter,
        "generated_from": f"cumulative-2026/daily/{date}.json",
        "events": rows,
    }


def _shift(date: str, days: int) -> str:
    import datetime
    y, m, d = (int(x) for x in date.split("-"))
    return (datetime.date(y, m, d) + datetime.timedelta(days=days)).isoformat()


def selftest() -> int:
    reg, scale, levels, ovr = load_governed()
    bad = 0
    # (1) مستوى خارج السلّم يجب أن يُمنع
    try:
        rank_of_zone([{"qualifying": True, "confirmation": "confirmed", "title": "حرج جدًا على الملاحة", "code": "X"}], {"حرج جدًا": {"rank": 9}}, [])
        print("   ✘ فشل: قُبل مستوى خارج السلّم")
        bad += 1
    except FailClosed:
        print("   ✔ مستوى خارج السلّم يُمنع")
    # (2) كلمة مكررة بين قطاعين تُمنع
    import copy
    reg2 = copy.deepcopy(reg)
    reg2["zones"][1]["keywords"].append(reg2["zones"][0]["keywords"][0])
    try:
        seen = {}
        for z in reg2["zones"]:
            for kw in z["keywords"]:
                if kw in seen:
                    raise FailClosed("dup")
                seen[kw] = z["id"]
        print("   ✘ فشل: قبل تداخل الكلمات")
        bad += 1
    except FailClosed:
        print("   ✔ تداخل الكلمات بين القطاعات يُمنع")
    # (3) الكلمة الأطول تُرجَّح
    ev = {"code": "T", "area": "خليج عدن", "title": "حادثة", "source_excerpt": ""}
    z, _ = zone_of(ev, reg, {})
    if z == "Z4":
        print("   ✔ «خليج عدن» تُرجَّح إلى القرن الأفريقي")
    else:
        print(f"   ✘ فشل: أُسندت «خليج عدن» إلى {z}")
        bad += 1
    # (4) واقعة بلا موقع بحري تُوسم غير مكانية
    z2, _ = zone_of({"code": "T2", "area": "قطر", "title": "زيارة وفد", "source_excerpt": ""}, reg, {})
    if z2 is None:
        print("   ✔ الواقعة بلا موقع بحري تُوسم غير مكانية")
    else:
        print(f"   ✘ فشل: أُسندت واقعة قطر إلى {z2}")
        bad += 1
    print(f"   ── الاختبار الذاتي: {'نجح' if bad == 0 else str(bad) + ' فشل'} ──")
    return 0 if bad == 0 else 2


def main() -> int:
    ap = argparse.ArgumentParser(description="تصنيف القطاعات وحساب مستوى التهديد")
    ap.add_argument("--date", help="التاريخ YYYY-MM-DD")
    ap.add_argument("--write", action="store_true", help="كتابة المخرج في web/zones/<date>.json")
    ap.add_argument("--json", help="مسار مخرج بديل")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true", help="طباعة الملخص")
    args = ap.parse_args()
    try:
        if args.selftest:
            return selftest()
        if not args.date:
            raise FailClosed("يلزم --date")
        reg, scale, levels, ovr = load_governed()
        out = classify_day(args.date, reg, scale, levels, ovr)
        if args.write or args.json:
            dest = pathlib.Path(args.json) if args.json else (OUT_DIR / f"{args.date}.json")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"   كُتب: {dest}")
            # مصدر حكم واحد: المستوى المشتق من القطاعات يُكتب في ملف الواجهة أيضًا
            meta_p = ROOT / "web/meta" / f"{args.date}.json"
            if meta_p.exists():
                meta = json.loads(meta_p.read_text(encoding="utf-8"))
                lv = out["overall"]["level"]
                tok = next((x["token"] for x in out["scale_levels"] if x["ar"] == lv), None)
                if not tok:
                    raise FailClosed(f"مستوى غير معتمد: «{lv}»")
                meta["threat_level"] = lv
                meta["threat_zone_levels"] = {z["id"]: z["level"] for z in out["zones"]}
                meta["threat_zones"] = {
                    "overall": lv,
                    "rank": out["overall"]["rank"],
                    "top_zone": out["overall"]["top_zone"],
                    "window": out["window"],
                    "counter": out["counter"],
                    "zones": [
                        {"id": z["id"], "name": z["name"], "level": z["level"], "rank": z["rank"],
                         "confirmed": z["confirmed"], "probable": z["probable"],
                         "qualifying": len(z["qualifying_codes"]), "carry_over": z["carry_over"]}
                        for z in out["zones"]
                    ],
                }
                dc = meta.setdefault("decision_card", {})
                dc["risk"] = lv
                dc["risk_kind"] = tok
                dc["risk_ref"] = "بطاقة الترويسة: مستوى التهديد حسب القطاعات"
                meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                print(f"   زُوّد ملف الواجهة بالمستوى المشتق: {lv} ({tok})")
        if args.show or not (args.write or args.json):
            print(f"   ══ {out['date']} · {out['window']} ══")
            print(f"   المستوى العام: {out['overall']['level']} — أعلى قطاع: {out['overall']['top_zone']}")
            for z in out["zones"]:
                tag = " (استمراري)" if z["carry_over"] else ""
                print(f"   {z['id']} {z['name']}: {z['level']}{tag} — مؤكد {z['confirmed']} · مرجّح {z['probable']} · مستثنى {z['excluded']}")
            c = out["counter"]
            print(f"   العدّاد: مؤهّلة {c['qualifying']} (مؤكد {c['confirmed']} · مرجّح {c['probable']}) · مستثنى {c['excluded']} · غير مكانية {c['nonspatial']} · إجمالي {c['total']}")
        return 0
    except FailClosed as exc:
        print(f"   ✘ منع (فشل مغلق): {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
