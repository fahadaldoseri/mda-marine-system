#!/usr/bin/env python3
"""ترقيع واجهة اليوم وفق قرارات المالك — قابل لإعادة التشغيل بلا أثر مزدوج.

يشمل: حذف بطاقة «هجمات مؤكدة على سفن» من صف المؤشرات (دُمجت)، تسمية البطاقة الدائمة
«أعداد الوفيات من IMO»، إضافة بطاقة «سجل الحوادث المؤكدة من IMO» بثلاث طبقات، إخراج
صف تحديث بيانات IMO من سجل الأحداث، ومواءمة المواقع والقطاعات.
"""
from __future__ import annotations
import json
import os
import pathlib
import sys

BRAIN = pathlib.Path(os.environ.get("BRAIN_DIR") or pathlib.Path(__file__).resolve().parents[1])
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-11-03"
Z1 = "Z1 — مضيق هرمز وخليج عُمان والخليج العربي"

META = BRAIN / "web" / "meta" / f"{DATE}.json"
REGISTRY = json.loads((BRAIN / "appendices" / "card_registry.json").read_text(encoding="utf-8"))
IMO_URL = "https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx"
IMO_SOURCE_STRING = f"appendices/imo-incidents.json + {IMO_URL}"
ZONES = BRAIN / "web" / "zones" / f"{DATE}.json"

# عطل ك-487: كانت أرقام IMO مثبّتة نصًّا (125/24 وتاريخ 02/11/2026) فعادت قيمة متقادمة
# إلى ملف الواجهة. القاعدة: الرقم يُقرأ من القائمة الرسمية المحفوظة لحظة التشغيل، لا من نص ثابت.
_IMO = json.loads((BRAIN / "appendices" / "imo-incidents.json").read_text(encoding="utf-8"))
_IMO_TOTALS = _IMO.get("totals") or {}
IMO_INCIDENTS = str(_IMO_TOTALS.get("confirmed_incidents") or "")
IMO_DEATHS = str(_IMO_TOTALS.get("confirmed_seafarer_deaths") or "")
_MONTHS = {"January": "01", "February": "02", "March": "03", "April": "04", "May": "05", "June": "06",
           "July": "07", "August": "08", "September": "09", "October": "10", "November": "11", "December": "12"}


def imo_as_at() -> str:
    """تاريخ بيانات القائمة الرسمية (المصدر يكتبه بالإنجليزية) بصيغة يوم/شهر/سنة."""
    raw = str((_IMO.get("source") or {}).get("as_at") or "").strip()
    parts = raw.replace(",", "").split()
    if len(parts) == 3 and parts[1] in _MONTHS:
        return f"{int(parts[0]):02d}/{_MONTHS[parts[1]]}/{parts[2]}"
    return raw


def imo_as_at_iso() -> str:
    """تاريخ بيانات القائمة الرسمية بصيغة ISO للمقارنة مع مقاييس الدفتر."""
    d = imo_as_at()
    parts = d.split("/")
    return f"{parts[2]}-{parts[1]}-{parts[0]}" if len(parts) == 3 else d


def sync_official_cards(oc: list[dict]) -> int:
    """يوحّد البطاقات الدائمة مع عقدها الحاكم: العقد مصدر واحد لا تُكتب قيمه يدويًا."""
    contracts = {str(c.get("id")): c for c in (REGISTRY.get("official_cards") or {}).get("cards", [])}
    touched = 0
    for card in oc:
        contract = contracts.get(str(card.get("id")))
        if not contract:
            continue
        for key, value in contract.items():
            if key == "layers":
                for lk, lv in (value or {}).items():
                    target = card.setdefault("layers", {}).setdefault(lk, {})
                    for kk in ("label", "label_en", "state"):
                        if kk in (lv or {}):
                            target[kk] = lv[kk]
            elif key != "id":
                card[key] = value
        touched += 1
    return touched


def patch_meta() -> list[str]:
    m = json.loads(META.read_text(encoding="utf-8"))
    z = json.loads(ZONES.read_text(encoding="utf-8"))
    log = []

    before = len(m["hero_kpis"])
    m["hero_kpis"] = [c for c in m["hero_kpis"] if c.get("id") != "imo-confirmed-attacks"]
    log.append(f"hero_kpis: {before} → {len(m['hero_kpis'])}")

    oc = m["official_cards"]
    d0 = next((c for c in oc if c["id"] == "imo-seafarer-deaths"), None)
    if d0:
        d0["title"] = "أعداد الوفيات من IMO"
        d0["title_en"] = "IMO seafarer fatalities"
        d0["layers"]["cumulative"]["value"] = IMO_DEATHS
        d0["layers"]["cumulative"]["value_en"] = IMO_DEATHS
        d0["layers"]["cumulative"]["source"] = f"IMO — {IMO_DEATHS} وفاة بحّار مؤكدة بتاريخ {imo_as_at()}"
        d0["layers"]["cumulative"]["source_en"] = f"IMO — {IMO_DEATHS} confirmed seafarer fatalities as at {imo_as_at()}"
        d0["layers"]["updated"]["value"] = imo_as_at()
        d0["layers"]["updated"]["value_en"] = imo_as_at()
        d0["layers"]["updated"]["source"] = f"القائمة الرسمية بتاريخ بيانات {imo_as_at()}"
        d0["layers"]["updated"]["source_en"] = f"Official list as at {imo_as_at()}"

    if not any(c["id"] == "imo-confirmed-incidents" for c in oc):
        oc.append({
            "id": "imo-confirmed-incidents",
            "title": "سجل الحوادث المؤكدة من IMO",
            "title_en": "IMO confirmed incidents log",
            "basis": "رسمي — قائمة IMO للحوادث المؤكدة على سفن تجارية",
            "basis_en": "Official — IMO confirmed incidents on commercial ships",
            "source_label": "IMO — سجل الحوادث المؤكدة",
            "source_label_en": "IMO — confirmed incidents log",
            "badges": ["بطاقة دائمة"],
            "badges_en": ["Permanent card"],
            "layers": {
                "daily": {"label": "عدد اليوم", "label_en": "Today", "value": "0", "value_en": "0",
                          "source": f"قائمة IMO الرسمية؛ لا إضافة مسندة بعد قراءة {imo_as_at()}",
                          "source_en": f"Official IMO list; no attributed addition after the {imo_as_at()} reading"},
                "cumulative": {"label": "المجموع منذ 28 فبراير 2026", "label_en": "Total since 28 February 2026",
                               "value": IMO_INCIDENTS, "value_en": IMO_INCIDENTS,
                               "source": f"IMO — {IMO_INCIDENTS} حادثة مؤكدة على سفن تجارية بتاريخ {imo_as_at()}",
                               "source_en": f"IMO — {IMO_INCIDENTS} confirmed incidents on commercial ships as at {imo_as_at()}"},
                "updated": {"label": "آخر تحديث للمصدر", "label_en": "Source last updated",
                            "value": imo_as_at(), "value_en": imo_as_at(),
                            "source": f"القائمة الرسمية بتاريخ بيانات {imo_as_at()}",
                            "source_en": f"Official list as at {imo_as_at()}"},
            },
        })
        log.append("official_cards: أُضيفت بطاقة سجل الحوادث المؤكدة من IMO")
    touched = sync_official_cards(oc)
    log.append(f"official_cards: {len(oc)} بطاقات · مُزامَنة مع العقد: {touched}")

    # بطاقات IMO في صف المؤشرات: المصدر والرابط والقيم من المصدر الرسمي وحده
    for card in m["hero_kpis"]:
        if str(card.get("id")) not in ("imo-confirmed-incidents", "imo-seafarer-deaths"):
            continue
        cumulative = IMO_INCIDENTS if card["id"] == "imo-confirmed-incidents" else IMO_DEATHS
        card["source"] = IMO_SOURCE_STRING
        card["source_url"] = IMO_URL
        card["value"] = str(card.get("value") or "0")
        card["cumulative"] = cumulative
        card["updated"] = imo_as_at_iso()
    log.append("hero_kpis: مواءمة بطاقتَي IMO مع المصدر الرسمي")

    ek = m["event_keys"]
    m["event_keys"] = [e for e in ek if e.get("code") != "MN-2026-11-03-04"]
    fix = {"MN-2026-11-03-01": ("لما، عُمان - مضيق هرمز", "Z1", Z1),
           "MN-2026-11-03-03": ("الخليج العربي", "Z1", Z1),
           "MN-2026-11-03-12": ("المحيط الهندي", "Z5", "Z5 — المحيط الهندي")}
    for e in m["event_keys"]:
        f = fix.get(e.get("code"))
        if f:
            e["area"], e["sector_id"], e["sector"] = f
    log.append(f"event_keys: {len(ek)} → {len(m['event_keys'])}")

    levels = {q["id"]: q.get("level") for q in z.get("zones", [])}
    m["threat_zone_levels"] = dict(levels)
    m.setdefault("glossary", {})["Z5"] = "المحيط الهندي"
    tz = m.get("threat_zones") or {}
    tz["zones"] = [{"id": q["id"], "name": q["name"], "level": q.get("level")} for q in z.get("zones", [])]
    ov = z.get("overall")
    if isinstance(ov, dict):
        tz["overall"] = ov.get("level")
        tz["top_zone"] = ov.get("top_zone")
    m["threat_zones"] = tz
    log.append(f"threat_zone_levels: {list(levels.keys())}")

    META.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return log


if __name__ == "__main__":
    for line in patch_meta():
        print("   ✔", line)
