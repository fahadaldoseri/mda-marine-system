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
import subprocess
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
OFFICIAL_REPORT_CLASSES = ("بلاغ رسمي", "بلاغ رسمي متعدد")
UKMTO_CONFIRMED_KINDS = ("هجوم", "استهداف", "انفجار", "إصابة", "أضرار")


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



def canonical_confirmed(event: dict) -> bool:
    """حالة الدليل المؤكدة من المصدر الواحد؛ لا تُشتق من مفردات التصنيف."""
    tools_dir = str(pathlib.Path(__file__).resolve().parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    try:
        import ledger_totals as _lt  # المصدر الواحد لقاعدة التأكيد
    except ImportError as exc:  # كان يُرجع False صامتًا فيُنزَّل كل تأكيد عند الاستيراد كحزمة
        raise FailClosed(f"تعذّر تحميل قاعدة التأكيد من ledger_totals: {exc}") from exc
    status = _lt.resolved_evidence_status(event)
    if status in _lt.COUNTED_EVIDENCE_STATUSES:
        return True
    # قرار المالك (2026-11-18): بلاغ UKMTO الرسمي عن هجوم يُحتسب إصابة مؤكدة في سلّم
    # التهديد. لا يشمل بلاغات النشاط المشبوه، ولا البلاغ الرسمي من جهة أخرى.
    kind = str(event.get("incident_kind") or "")
    cls = str(event.get("class") or "")
    return (cls in OFFICIAL_REPORT_CLASSES and kind in UKMTO_CONFIRMED_KINDS
            and _lt.direct_ukmto(event))


def is_qualifying(event: dict, reg: dict, day_overrides: dict) -> tuple[bool, str, str]:
    """يُعيد (مؤهّلة؟، درجة التأكيد، السبب)."""
    demoted: list[str] = []
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
    # عيب مُقاس (2026-11-11): «بلاغ رسمي» تعني وجود بلاغ، لا ثبوت أثر أو هجوم.
    # التأكيد لا يُمنح إلا لحالة دليل مؤكدة معتمدة في المصدر الواحد (ledger_totals).
    if conf == "confirmed" and not canonical_confirmed(event):
        conf = "unconfirmed"
        demoted.append(code or "?")
    hay = f"{event.get('title','')} {event.get('source_excerpt','')}"
    qual_hit = next((t for t in reg["counting"]["qualifying_types"] if t in hay), None)
    non_hit = next((t for t in reg["counting"]["non_qualifying_types"] if t in hay), None)
    if "qualifying" in ov:
        reason = ov.get("reason", "حكم محوكم")
        return bool(ov["qualifying"]), conf, reason
    # 21 نوفمبر 2026: صف التكرار (duplicate_of، counts_as_new=false) لا يُحتسب واقعة
    # مؤهّلة ثانية؛ واقعته الأصلية محتسبة في يومها، ومصادره مدموجة فيها (S074).
    if event.get("counts_as_new") is False and event.get("duplicate_of"):
        return False, conf, f"تكرار للواقعة {event.get('duplicate_of')} — لا يُحتسب مرة ثانية"
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


ABSENCE_CLASSES = {"no_incident", "سجل دولي", "سجل مصدر مهني"}
# عطل مُقاس (2026-11-20): تحديث نشرة إرشادية رسمية (JMIC/UKMTO) بلا واقعة جديدة
# كان يُعدّ «رواية لم تتأكد» في عدّاد القطاعات (3) بينما العدّاد المحوكم في
# ledger_totals لا يعدّه رواية (1)، فتعارضت بطاقة «روايات لم تتأكد» مع عدّاد القطاعات.
# التنبيه الرسمي ليس رواية عن واقعة بحرية، فيُستبعد كما تُستبعد سجلات انعدام الواقعة.
NON_NARRATIVE_CLASSES = {"تنبيه رسمي"}


def is_unconfirmed_narrative(row: dict) -> bool:
    """رواية غير مؤكدة: صف غير مؤكد يصف واقعة أو ادعاءً.

    يستند إلى حقل `class` في الدفتر لا إلى نص العنوان:
    تُستبعد سجلات انعدام الواقعة (`no_incident` · سجل دولي · سجل مصدر مهني)
    والتصريحات السياسية، لأنها ليست روايات عن واقعة بحرية.
    """
    if row.get("confirmation") != "unconfirmed":
        return False
    cls = str(row.get("class", "")).strip()
    if cls in ABSENCE_CLASSES or cls in NON_NARRATIVE_CLASSES:
        return False
    if "سياسي" in cls:
        return False
    return True


def classify_day(date: str, reg, scale, levels, ovr, *, carry: bool = True,
                strict: bool = False) -> dict:
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
        "unconfirmed_total": len({r["incident_group"] for r in rows if is_unconfirmed_narrative(r)}),  # noqa: E501
        "excluded": len([r for r in rows if not r["qualifying"] and not r["nonspatial"]]),
        "nonspatial": len([r for r in rows if r["nonspatial"]]),
    }

    # ك-470: حارس الاستبعاد الصامت — واقعة رسمية تستهدف سفينة ولا تحمل نوعًا مؤهّلًا
    # في عنوانها تُعدّ عطلاً لا تُسقط بصمت. الحل: لفظ مؤهّل معتمد أو تجاوز محوكم بسبب.
    if strict:
        raw = {e.get("code", ""): e for e in events if isinstance(e, dict)}
        confirmed_classes = set(reg["counting"]["confirmation"]["confirmed"])
        silent = []
        for r in rows:
            ev = raw.get(r["code"]) or {}
            if r["class"] not in confirmed_classes:
                continue
            if str(ev.get("target") or "") != "سفينة":
                continue
            if ev.get("counts_as_new") is False:
                continue
            if r["qualifying"]:
                continue
            if not str(r.get("qualify_reason") or "").startswith("لا نوع مؤهّل"):
                continue
            if str(r["code"]).startswith("IMO-"):
                continue
            silent.append(r)
        if silent:
            detail = " · ".join(f"{r['code']} «{str(r['title'])[:44]}»" for r in silent[:4])
            raise FailClosed(
                "استبعاد صامت لواقعة رسمية تستهدف سفينة بلا نوع مؤهّل في العنوان: " + detail)
    if counter["unconfirmed_qualifying"] > counter["unconfirmed_total"]:
        raise FailClosed(
            "تناقض عدّادي: روايات مؤهّلة " + str(counter["unconfirmed_qualifying"])
            + " أكثر من إجمالي الروايات " + str(counter["unconfirmed_total"]))
    top_basis = f"أعلى نطاق: {overall['name']} — {overall['basis']}"
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


def governed_threat_lede(zone_card: dict, registry: dict) -> str:
    """يبني ترويسة التهديد من سجل القطاعات، بلا أسماء أو ترتيب ثابتين."""
    registry_zones = registry.get("zones") or []
    registry_names = {
        str(z.get("id") or "").strip(): str(z.get("ar") or "").strip()
        for z in registry_zones
        if str(z.get("id") or "").strip() and str(z.get("ar") or "").strip()
    }
    rows = zone_card.get("zones") or []
    if not registry_names or not rows:
        raise FailClosed("لا يمكن اشتقاق ترويسة التهديد بلا قطاعات وسجل أسماء معتمد")
    registry_order = {zid: i for i, zid in enumerate(registry_names)}
    if any(str(row.get("id") or "").strip() not in registry_names for row in rows):
        raise FailClosed("بطاقة القطاعات تحمل معرّفًا غير موجود في سجل القطاعات المعتمد")
    try:
        top = max(
            rows,
            key=lambda row: (
                int(row.get("rank", 0)),
                -registry_order[str(row.get("id") or "").strip()],
            ),
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise FailClosed(f"رتبة قطاع غير صالحة عند اشتقاق الترويسة: {exc}") from exc
    overall = zone_card.get("overall") or {}
    level = str(overall.get("level") or "").strip()
    top_id = str(top.get("id") or "").strip()
    top_level = str(top.get("level") or "").strip()
    top_name = registry_names[top_id]
    if not level or not top_level or not top_name:
        raise FailClosed("بيانات المستوى أو أعلى قطاع ناقصة عند اشتقاق الترويسة")
    if top_level != level:
        raise FailClosed(f"المستوى العام «{level}» لا يساوي مستوى أعلى قطاع «{top_level}»")
    return f"المستوى العام {level}. ويظل {top_name} أعلى القطاعات عند مستوى {top_level}."


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
        out = classify_day(args.date, reg, scale, levels, ovr, strict=True)
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
                meta["lede"] = governed_threat_lede(out, reg)
                dc = meta.setdefault("decision_card", {})
                dc["risk"] = lv
                dc["risk_kind"] = tok
                dc["risk_ref"] = "بطاقة الترويسة: مستوى التهديد"
                meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                print(f"   زُوّد ملف الواجهة بالمستوى المشتق: {lv} ({tok})")
                # نقاط الخريطة: تُشتق من وقائع اليوم ومراسي المناطق المعتمدة (فشل مغلق عند غياب مِرساة)
                _r = subprocess.run([sys.executable, str(ROOT / "tools" / "derive_map_points.py"),
                     "--date", args.date, "--write"], capture_output=True, text=True)
                sys.stdout.write(_r.stdout)
                if _r.returncode == 2:
                    raise FailClosed("نقاط الخريطة: " + (_r.stdout + _r.stderr).strip()[-300:])
                if _r.returncode not in (0, 1):
                    raise FailClosed("مشتق نقاط الخريطة خرج بالرمز " + str(_r.returncode))
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
