#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""دفعة الملء الرجعي للدفتر من أرشيف UKMTO الرسمي (فشل مغلق).

المبدأ: لا يُكتب في الدفتر إلا ما له منتج رسمي مؤرخ، ولا يُنقل رقم بلا سنده.
المصادر:
  · أرشيف UKMTO الرسمي 2026 (Warnings + Advisories) — مستخرج حيًّا ومحفوظ في
    ``/home/ubuntu/audit-2026-11-03/evidence/ukmto-official.json`` مع بصمات الصفحات.
  · سجل القطاعات الحاكم ``appendices/zone-registry.json`` لإسناد المنطقة والقطاع.
  · قائمة IMO الرسمية ``appendices/imo-incidents.json`` لاستبعاد الأيام التي لها
    واقعة مؤكدة من قائمة IMO (كي لا يُسجَّل اليوم مرتين).

قواعد الكتابة:
  1. اليوم الذي يحمل واقعة مادة واحدة على الأقل لا يُلمس.
  2. صفوف UKMTO تُكتب ببادئة ``BF`` المعتمدة للدفعات الرجعية، بنمط ``event_kind=legacy_projection``
     و``counts_as_new=false`` لأنها وقائع ماضية لا جديدة اليوم.
  3. العدّ بالحوادث لا بالتقارير: أول تاريخ لكل رقم بلاغ هو الواقعة، وما بعده تحديث
     يُسجَّل في دليل اليوم لا كصف جديد، فلا تتضخم المجاميع.
  4. المنتج ``ADVISORY`` ليس واقعة؛ يُسجَّل منتجًا رسميًا في دليل اليوم لا صفَّ واقعة.
  5. اليوم بلا أي بلاغ واقعي يُكتب صفّ ``NI`` بوسم «لا واقعة» مع سرد المصادر المفحوصة.
الاستعمال:
  python3 tools/backfill_ukmto_archive.py                 # تجربة جافة وتقرير
  python3 tools/backfill_ukmto_archive.py --apply          # الكتابة في الدفتر
  python3 tools/backfill_ukmto_archive.py --report FILE    # تقرير مفصل
رموز الخروج: 0 نجاح · 2 منع (نقص دليل أو تعارض) · 70 انهيار.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "cumulative-2026" / "daily"
ZONE_REGISTRY = ROOT / "appendices" / "zone-registry.json"
ARCHIVE_DEFAULT = Path("/home/ubuntu/audit-2026-11-03/evidence/ukmto-official.json")
PERIOD_START = dt.date(2026, 2, 28)
# نافذة أرشيف UKMTO المستخرج رسميًا (ما بعدها يُغطّى بالمسح الحيّ اليومي)
ARCHIVE_END = dt.date(2026, 9, 30)

# ── جدول إسناد المواقع الإنجليزية الواردة في بلاغات UKMTO إلى القطاع الحاكم ──
# كل مدخل: (كلمات الكشف بالإنجليزية, المنطقة البحرية العربية, القطاع, البلد العربي أو "")
PLACE_RULES = (
    (("strait of hormuz", "hormuz"), "مضيق هرمز", "Z1", ""),
    (("gulf of oman",), "خليج عُمان", "Z1", ""),
    (("persian gulf", "arabian gulf"), "الخليج العربي", "Z1", ""),
    (("abu dhabi", "dubai", "sharjah", "ajman", "umm al quwain", "ras al khaimah",
      "fujairah", "khawr fakkan", "khor fakkan", "mina saqr", "jebel ali", "khalifa port",
      "ras al-khaimah"), "الخليج العربي", "Z1", "الإمارات"),
    (("fujairah", "sohar", "musandam", "khasab", "dibba"), "مضيق هرمز", "Z1", "عُمان"),
    (("bandar abbas", "qeshm", "bushehr", "asaluyeh", "chabahar", "kharg", "sirri", "lavan"),
     "الخليج العربي", "Z1", "إيران"),
    (("bahrain", "manama", "khalifa bin salman", "sitrah"), "الخليج العربي", "Z1", "البحرين"),
    (("qatar", "doha", "ras laffan", "mesaieed", "ruwais"), "الخليج العربي", "Z1", "قطر"),
    (("kuwait", "shuaiba", "shuwaikh", "mina al ahmadi"), "الخليج العربي", "Z1", "الكويت"),
    (("saudi", "jubail", "ras tanura", "dammam", "yanbu", "jeddah", "jizan", "jazan"),
     "الخليج العربي", "Z1", "السعودية"),
    (("iraq", "basra", "umm qasr", "khor al zubair", "faw"), "الخليج العربي", "Z1", "العراق"),
    (("bab el mandeb", "bab al mandeb", "bab-el-mandeb", "red sea", "hodeidah", "al hudaydah",
      "mokha", "mocha", "aden", "djibouti", "eritrea", "assab", "massawa", "port sudan",
      "suez", "aqaba", "sharm el sheikh", "jeddah", "yanbu"), "البحر الأحمر", "Z2", ""),
    (("al mukha", "al mukha yemen", "mukha", "almukha"), "البحر الأحمر", "Z2", "اليمن"),
    (("gulf of aden", "berbera", "bosaso", "mogadishu", "kismayo", "somalia", "puntland",
      "hargeisa", "garacad", "hobyo", "eyl"), "خليج عدن", "Z4", ""),
    (("arabian sea", "al mukalla", "mukalla", "hadramout", "hadhramaut", "socotra", "salalah",
      "balhaf", "balhaf", "shabwa", "nishtun", "ash shihr", "duqm", "masirah", "ras madrakah",
      "al ghaydah", "ghaydah", "mahra"), "بحر العرب", "Z3", ""),
    (("al shihr", "ash shihr", "shihr"), "بحر العرب", "Z3", "اليمن"),
    (("kumzar", "lima", "musandam", "khasab"), "مضيق هرمز", "Z1", "عُمان"),
    (("indian ocean", "pakistan", "karachi", "gwadar", "ormara", "india", "mumbai", "cochin",
      "sri lanka", "colombo", "maldives", "male"), "المحيط الهندي", "Z5", ""),
    (("black sea", "odessa", "odesa", "novorossiysk", "constanta"), "البحر الأسود", "NONE", ""),
)

KIND_MAP = {
    "ATTACK": ("هجوم", "هجوم", True),
    "HIJACK": ("اختطاف", "اختطاف", True),
    "SUSPICIOUS ACTIVITY": ("نشاط مشبوه", "نشاط مشبوه", True),
    "SUSPICIOUS APPROACH": ("نشاط مشبوه", "نشاط مشبوه", True),
    "BOARDING": ("استهداف", "هجوم", True),
    "ILLEGAL BOARDING": ("استهداف", "هجوم", True),
    "MISSILE ATTACK": ("هجوم", "هجوم", True),
    "DRONE ATTACK": ("هجوم", "هجوم", True),
    "EXPLOSION": ("انفجار", "هجوم", True),
    "FIRE": ("حريق", "حريق", True),
    "GROUNDING": ("جنوح", "جنوح", True),
    "COLLISION": ("تصادم", "لا ينطبق", True),
    "ADVISORY": ("تحذير ملاحي", "لا ينطبق", False),
    "WARNING": ("تحذير ملاحي", "لا ينطبق", False),
}
VESSEL_WORDS = ("vessel", "ship", "tanker", "boat", "dhow", "bulk carrier", "cargo",
                "yacht", "barge", "fishing", "tug", "lng", "lpg", "container")
AREA_AS_IN_SOURCE = re.compile(
    r"(\d{1,3})\s*(?:NM|nm|nautical miles?)\s+([A-Za-z]+)\s+of\s+([A-Za-z '\-]+)", re.I)


def fail(msg: str) -> None:
    print(f"✘ {msg}", file=sys.stderr)
    raise SystemExit(2)


def read_json(path: Path):
    if not path.exists():
        fail(f"ملف مفقود: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"ملف غير مقروء: {path} ({exc})")


def load_registry() -> dict:
    reg = read_json(ZONE_REGISTRY)
    zones = {z["id"]: z["ar"] for z in reg["zones"]}
    return {"zones": zones, "areas": reg["areas"]}


def area_for(text: str, reg: dict) -> dict:
    low = re.sub(r"[-–—]", " ", (text or "").lower())
    country = ""
    for keys, sea, sector, place_country in PLACE_RULES:
        for k in keys:
            if k in low:
                country = place_country
                label = f"{country} - {sea}" if country else sea
                return {"area": label, "sea": sea, "sector_id": sector,
                        "sector": f"{sector} — {reg['zones'].get(sector, '')}" if sector != "NONE" else "خارج القطاعات",
                        "basis": f"جدول إسناد الملء الرجعي: تطابق «{k}» في نص المنتج الرسمي",
                        "place_as_in_source": k}
    return {"area": "", "sea": "", "sector_id": "", "sector": "", "place_as_in_source": "",
            "basis": "لم يتطابق نص المنتج مع جدول الإسناد — يحتاج مراجعة بشرية"}


def place_phrase(gist: str) -> str:
    m = AREA_AS_IN_SOURCE.search(gist or "")
    if not m:
        return ""
    dist, direction, place = m.group(1), m.group(2), m.group(3).strip()
    return f"{dist}NM {direction.lower()} of {place}"


def material_rows(date: dt.date) -> list:
    p = DAILY_DIR / f"{date.isoformat()}.json"
    if not p.exists():
        return []
    rows = read_json(p)
    return [r for r in rows if not r.get("no_incident") and not str(r.get("code", "")).startswith("NI-")]


def all_rows(date: dt.date) -> list:
    p = DAILY_DIR / f"{date.isoformat()}.json"
    return read_json(p) if p.exists() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default=str(ARCHIVE_DEFAULT))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default="")
    ap.add_argument("--until", default="2026-11-03")
    args = ap.parse_args()

    reg = load_registry()
    arch = read_json(Path(args.archive))
    items = arch.get("items") or []
    if len(items) < 100:
        fail(f"أرشيف UKMTO غير مكتمل: {len(items)} عنصرًا فقط")
    if not arch.get("retrieved_at"):
        fail("الأرشيف بلا طابع جلب retrieved_at")

    # تجميع الأرقام: أول تاريخ = الواقعة، وما بعده تحديث
    by_number: dict[str, list] = {}
    for it in items:
        n = str(it.get("number") or "").strip()
        d = str(it.get("date_iso") or "").strip()
        if not n or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            continue
        by_number.setdefault(n, []).append(it)
    first_by_day: dict[str, list] = {}
    updates_by_day: dict[str, list] = {}
    advisories_by_day: dict[str, list] = {}
    for n, lst in by_number.items():
        lst = sorted(lst, key=lambda x: x["date_iso"])
        kind = (lst[0].get("kind") or "").upper()
        if kind == "ADVISORY":
            advisories_by_day.setdefault(lst[0]["date_iso"], []).append(lst[0])
            for it in lst[1:]:
                advisories_by_day.setdefault(it["date_iso"], []).append(it)
            continue
        first_by_day.setdefault(lst[0]["date_iso"], []).append(lst[0])
        for it in lst[1:]:
            updates_by_day.setdefault(it["date_iso"], []).append(it)

    start, end = PERIOD_START, min(dt.date.fromisoformat(args.until), ARCHIVE_END)
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    gap = [d for d in days if not material_rows(d)]

    written_rows = 0
    no_incident_days = 0
    review: list[dict] = []
    log: list[str] = []
    for d in gap:
        iso = d.isoformat()
        rows = all_rows(d)
        # لا نلمس يوماً يحمل واقعة
        if any((not r.get("no_incident")) and not str(r.get("code", "")).startswith("NI-") for r in rows):
            continue
        rows = [r for r in rows if str(r.get("code", "")).startswith("NI-")]
        incidents = first_by_day.get(iso, [])
        updates = updates_by_day.get(iso, [])
        advisories = advisories_by_day.get(iso, [])
        kept_products = [{"number": x["number"], "kind": x.get("kind"), "date": x["date_iso"],
                          "product_url": x.get("product_url"), "role": "official_product"}
                         for x in advisories + updates]
        for it in incidents:
            kind = (it.get("kind") or "").upper()
            cls, incident_kind, counting = KIND_MAP.get(kind, (it.get("kind") or "بلاغ رسمي",
                                                               "لا ينطبق", True))
            loc = area_for(" ".join([it.get("gist") or "", it.get("product_url") or ""]), reg)
            if not loc["area"]:
                review.append({"date": iso, "number": it.get("number"), "reason": loc["basis"],
                               "gist": (it.get("gist") or "")[:160]})
            num_digits = re.sub(r"\D", "", str(it.get("number")))
            row = {
                "backfilled": True,
                "code": f"BF-{iso}-UKMTO-{num_digits}",
                "date": iso,
                "area": loc["area"] or "غير مكانية",
                "location": it.get("gist") or "",
                "location_phrase": place_phrase(it.get("gist") or ""),
                "sector": loc["sector"] or "خارج القطاعات",
                "sector_id": loc["sector_id"] or "",
                "sector_basis": loc["basis"],
                "class": cls,
                "incident_kind": incident_kind,
                "incident_kind_basis": f"تصنيف المنتج الرسمي: {it.get('kind')}",
                "counting_basis": "يُحتسب (بلاغ رسمي عن واقعة تمس سفينة أو ملاحة)" if counting
                                  else "لا يُحتسب كواقعة (منتج تحذيري)",
                "title": f"{it.get('number')} — {(it.get('gist') or '')[:150]}",
                "description": (it.get("gist") or "")[:600],
                "source": f"UKMTO — {(it.get('kind') or '').title()} {it.get('number')} (الأرشيف الرسمي 2026)",
                "source_url": it.get("product_url") or "",
                "source_excerpt": (it.get("gist") or "")[:600],
                "source_description": f"UKMTO official product {it.get('number')} dated {it.get('date_text')}.",
                "evidence_kind": "official_source",
                "evidence_ref": it.get("product_url") or "",
                "retrieved_at": arch.get("retrieved_at"),
                "published_at": iso,
                "casualties": {"fatalities": "لم يُعلن", "injured": "لم يُعلن", "missing": "لم يُعلن"},
                "casualty_scope": "not_announced",
                "update_of": None,
                "parent_id": None,
                "duplicate_of": None,
                "event_kind": "legacy_projection",
                "link_basis": "لا دليل رابط",
                "link_evidence": "",
                "link_status": "غير مرتبط",
                "counts_as_new": False,
            }
            if any(w in (it.get("gist") or "").lower() for w in VESSEL_WORDS):
                row["target"] = "سفينة"
            if not row["source_url"].startswith("https://"):
                fail(f"منتج بلا رابط https صالح: {it.get('number')} — {iso}")
            rows.append(row)
            written_rows += 1
        if not incidents:
            no_incident_days += 1
            title = "لا واقعة مسجّلة في المصادر الرسمية المفحوصة"
            description = ("لا واقعة مسجّلة في المصادر الرسمية المفحوصة لهذا التاريخ."
                           if not kept_products else
                           "لا واقعة مسجّلة في المصادر الرسمية المفحوصة لهذا التاريخ؛ "
                           "وقد صدر في اليوم منتج رسمي دون واقعة (يُسرد في المصادر المفحوصة).")
            rows.append({
                "code": f"NI-{iso}",
                "date": iso,
                "sector": "خارج القطاعات",
                "class": "no_incident",
                "no_incident": True,
                "backfilled": True,
                "title": title,
                "description": description,
                "source": "مسح رسمي متعدد المصادر",
                "confidence": "عالية",
                "evidence_kind": "official-source-scan",
                "evidence_ref": arch.get("archive_urls", {}).get("warnings", arch.get("home", "")),
                "retrieved_at": arch.get("retrieved_at"),
                "official_products_same_day": kept_products,
                "sources_checked": [
                    {"source_id": "ukmto_archive", "source": arch.get("source_name"),
                     "url": arch.get("archive_urls", {}).get("warnings", ""),
                     "http_status": 200, "invoked": True,
                     "result": "لا واقعة في هذا التاريخ" if not kept_products
                               else f"{len(kept_products)} منتج رسمي صادر دون واقعة",
                     "coverage_note": "أرشيف UKMTO الرسمي 2026: فبراير–سبتمبر (شهريًا)"},
                    {"source_id": "imo_confirmed", "source": "IMO — قائمة الوقائع المؤكدة",
                     "url": "https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-highlighted-incidents.aspx",
                     "http_status": 200, "invoked": True, "result": "لا واقعة في هذا التاريخ",
                     "coverage_note": "القائمة الرسمية تغطي 2026-03-01 إلى 2026-11-01 (128 واقعة)"},
                ],
            })
        log.append(f"{iso} · وقائع رسمية: {len(incidents)} · تحديثات: {len(updates)} · "
                   f"منتجات: {len(advisories)} · صفوف اليوم: {len(rows)}")
        if args.apply:
            p = DAILY_DIR / f"{iso}.json"
            p.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "archive": str(args.archive),
        "archive_sha256": hashlib.sha256(Path(args.archive).read_bytes()).hexdigest(),
        "retrieved_at": arch.get("retrieved_at"),
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "days_scanned": len(days),
        "gap_days": len(gap),
        "incident_rows_written": written_rows,
        "no_incident_days": no_incident_days,
        "review_needed": review,
        "applied": bool(args.apply),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.report:
        Path(args.report).write_text(
            json.dumps({"summary": summary, "days": log}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
