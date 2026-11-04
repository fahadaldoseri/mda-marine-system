#!/usr/bin/env python3
"""ترقيع واجهة اليوم وفق قرارات المالك — قابل لإعادة التشغيل بلا أثر مزدوج.

يشمل: حذف بطاقة «هجمات مؤكدة على سفن» من صف المؤشرات (دُمجت)، تسمية البطاقة الدائمة
«أعداد الوفيات من IMO»، إضافة بطاقة «سجل الحوادث المؤكدة من IMO» بثلاث طبقات، إخراج
صف تحديث بيانات IMO من سجل الأحداث، ومواءمة المواقع والقطاعات.
"""
from __future__ import annotations
import json
import pathlib
import sys

BRAIN = pathlib.Path("/home/ubuntu/brain-marine-news")
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-11-03"
Z1 = "Z1 — مضيق هرمز وخليج عُمان والخليج العربي"

META = BRAIN / "web" / "meta" / f"{DATE}.json"
ZONES = BRAIN / "web" / "zones" / f"{DATE}.json"


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
        d0["layers"]["cumulative"]["value"] = "24"
        d0["layers"]["cumulative"]["source"] = "IMO — 24 وفاة بحّار مؤكدة"
        d0["layers"]["updated"]["value"] = "02/11/2026"
        d0["layers"]["updated"]["value_en"] = "02/11/2026"
        d0["layers"]["updated"]["source"] = "قائمة IMO الرسمية كما حُفظت في 02/11/2026"
        d0["layers"]["updated"]["source_en"] = "Official IMO list as saved on 02/11/2026"

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
                          "source": "قائمة IMO الرسمية؛ لا إضافة جديدة في آخر تحديث 02/11/2026",
                          "source_en": "Official IMO list; no new addition in the 2 November 2026 update"},
                "cumulative": {"label": "المجموع منذ 28 فبراير 2026", "label_en": "Total since 28 February 2026",
                               "value": "125", "value_en": "125",
                               "source": "IMO — 125 حادثة مؤكدة على سفن تجارية",
                               "source_en": "IMO — 125 confirmed incidents on commercial ships"},
                "updated": {"label": "آخر تحديث للمصدر", "label_en": "Source last updated",
                            "value": "02/11/2026", "value_en": "02/11/2026",
                            "source": "القائمة الرسمية كما حُفظت في 02/11/2026",
                            "source_en": "Official list as saved on 2 November 2026"},
            },
        })
        log.append("official_cards: أُضيفت بطاقة سجل الحوادث المؤكدة من IMO")
    log.append(f"official_cards: {len(oc)} بطاقات")

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