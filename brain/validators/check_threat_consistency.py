#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة اتساق مستوى التهديد ومصدر الحكم الواحد (تصميم معتمد 2026-10-30).

تمنع (فشل مغلق) عند أي من:
  1. لفظ مستوى خارج القائمة المسموحة في المتن أو ملف الواجهة أو بطاقة القطاعات.
  2. اختلاف المستوى العام عن أعلى مستوى قطاع.
  3. اختلاف decision_card.risk عن المستوى العام.
  4. اختلاف مستوى أي قطاع بين المتن وبطاقة القطاعات.
  5. واقعة منسوبة إلى قطاعين، أو أساس قطاع يشير إلى موقع قطاع آخر.
  6. صف قطاع بلا أساس، أو أساس يشير إلى واقعة غير موجودة في دفتر اليوم.
  7. واقعة مرمّزة داخل الفترة مع وصف «استمراري» (تناقض منطقي).
  8. غياب القطاعات الأربعة أو تغيّر أسمائها عن السجل المعتمد.

الاستعمال: python3 validators/check_threat_consistency.py --date YYYY-MM-DD [--brain .]
رمز الخروج: 0 اجتاز · 2 منع · 70 انهيار داخلي.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import traceback

ALLOWED_FALLBACK = ["حرج", "مرتفع جدًا", "مرتفع", "متوسط", "منخفض"]
DECL = re.compile(r"المستوى العام:\s*([^\n·—]+)")


class Blocked(RuntimeError):
    pass


def load(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def check_all(brain: pathlib.Path, date: str) -> int:
    problems: list[str] = []
    notes: list[str] = []

    scale = load(brain / "appendices/threat-scale.json") or {}
    allowed = [lv["ar"] for lv in (scale.get("levels") or [])] or ALLOWED_FALLBACK
    reg = load(brain / "appendices/zone-registry.json") or {}
    zones_json = load(brain / "web/zones" / f"{date}.json")
    meta = load(brain / "web/meta" / f"{date}.json")
    ledger = load(brain / "cumulative-2026/daily" / f"{date}.json")
    md_p = brain / "reports" / f"{date}-sectioned.md"

    if not zones_json:
        problems.append(f"لا يوجد ملف قطاعات محسوب: web/zones/{date}.json")
    if not meta:
        problems.append(f"لا يوجد ملف واجهة: web/meta/{date}.json")
    if not md_p.exists():
        problems.append(f"لا يوجد متن للتقرير: {md_p.name}")
    if problems:
        raise Blocked(" · ".join(problems))

    md = md_p.read_text(encoding="utf-8")

    # (8) القطاعات الأربعة بأسمائها المعتمدة
    reg_zones = {z["id"]: z["ar"] for z in (reg.get("zones") or [])}
    got = {z["id"]: z["name"] for z in (zones_json.get("zones") or [])}
    if reg_zones and got != reg_zones:
        problems.append(f"(8) القطاعات في البطاقة لا تطابق السجل المعتمد: {got} ≠ {reg_zones}")

    overall = zones_json.get("overall") or {}
    lvl = overall.get("level")

    # (1) القائمة المسموحة
    if lvl not in allowed:
        problems.append(f"(1) المستوى العام «{lvl}» خارج القائمة المسموحة {allowed}")
    if meta.get("threat_level") not in allowed:
        problems.append(f"(1) threat_level في الواجهة «{meta.get('threat_level')}» خارج القائمة المسموحة")

    # (2) المستوى العام = أعلى مستوى قطاع
    ranks = {z["id"]: z.get("rank", 0) for z in (zones_json.get("zones") or [])}
    if ranks:
        top_id = max(ranks, key=lambda k: ranks[k])
        top_zone = next(z for z in zones_json["zones"] if z["id"] == top_id)
        if top_zone.get("level") != lvl:
            problems.append(f"(2) المستوى العام «{lvl}» لا يساوي أعلى قطاع «{top_zone.get('level')}» ({top_id})")
        if overall.get("top_zone_id") and overall["top_zone_id"] != top_id:
            problems.append(f"(2) أعلى قطاع معلن {overall['top_zone_id']} والمحسوب {top_id}")

    # (3) decision_card.risk = المستوى العام
    dc = meta.get("decision_card") or {}
    if dc.get("risk") and dc["risk"] != lvl:
        problems.append(f"(3) decision_card.risk «{dc['risk']}» ≠ المستوى العام «{lvl}»")

    # (4) المتن: إعلان المستوى العام
    m = DECL.search(md)
    if not m:
        problems.append("(4) المتن لا يحمل سطر «المستوى العام: …» — مصدر الحكم غير معلن")
    else:
        declared = m.group(1).strip()
        if declared != lvl:
            problems.append(f"(4) المتن يعلن «{declared}» والمحسوب «{lvl}»")

    # (4-ب) لكل قطاع سطر إعلان «المستوى في <القطاع>: <المستوى>» يطابق بطاقته
    zone_levels = {z["name"]: z["level"] for z in (zones_json.get("zones") or [])}
    for zname, zlv in zone_levels.items():
        mz = re.search(rf"المستوى في {re.escape(zname)}:\s*(حرج|مرتفع جدًا|مرتفع|متوسط|منخفض)", md)
        if not mz:
            problems.append(f"(4) المتن لا يعلن مستوى القطاع «{zname}»")
            continue
        got_z = mz.group(1).strip()
        if got_z != zlv:
            problems.append(f"(4) المتن يعلن للقطاع «{zname}» المستوى «{got_z}» وبطاقته «{zlv}»")

    # (4-ج) سطر الحالة يعلن المستوى العام نفسه
    mst = re.search(r"مستوى التهديد\s+(حرج|مرتفع جدًا|مرتفع|متوسط|منخفض)", md)
    if mst and mst.group(1) != lvl:
        problems.append(f"(4) سطر الحالة يعلن «{mst.group(1)}» والمستوى العام «{lvl}»")

    # (5) واقعة في قطاعين + أساس يشير إلى موقع قطاع آخر
    seen: dict[str, str] = {}
    for ev in zones_json.get("events") or []:
        zid = ev.get("zone")
        if not zid:
            continue
        code = ev.get("code")
        if code in seen and seen[code] != zid:
            problems.append(f"(5) الواقعة {code} منسوبة إلى قطاعين: {seen[code]} و{zid}")
        seen[code] = zid
    for z in zones_json.get("zones") or []:
        for other_id, other_name in reg_zones.items():
            if other_id == z["id"]:
                continue
            # اسم قطاع آخر داخل أساس هذا القطاع ⇒ تداخل
            for token in re.split(r"[·—\s]+", other_name):
                if len(token) > 3 and token in (z.get("basis") or ""):
                    problems.append(f"(5) أساس القطاع {z['id']} يشير إلى موقع من قطاع آخر: «{token}»")
                    break

    # (6) أساس موجود + كل واقعة مؤهّلة موجودة في دفتر اليوم
    ledger_codes = set()
    if ledger:
        seq = ledger if isinstance(ledger, list) else []
        if isinstance(ledger, dict):
            for key in ("events", "incidents", "rows"):
                if isinstance(ledger.get(key), list):
                    seq = seq + ledger[key]
        for e in seq:
            if isinstance(e, dict) and e.get("code"):
                ledger_codes.add(e["code"])
    for z in zones_json.get("zones") or []:
        if not (z.get("basis") or "").strip():
            problems.append(f"(6) القطاع {z['id']} بلا أساس تقدير")
        for c in z.get("qualifying_codes") or []:
            if ledger_codes and c not in ledger_codes:
                problems.append(f"(6) القطاع {z['id']} يستند إلى واقعة غير موجودة في دفتر اليوم: {c}")

    # (7) «استمراري» مع واقعة داخل الفترة
    for z in zones_json.get("zones") or []:
        if z.get("carry_over") and (z.get("qualifying_codes") or []):
            problems.append(f"(7) القطاع {z['id']} موصوف استمراريًا وله واقعة داخل الفترة: {z['qualifying_codes']}")

    # (9) ترويسة الإصدار (lede/headline) — عطل 2026-10-30: بقيت الجملة الأولى تذكر الفترة الرقمية
    #     وموقعًا ليس من القطاعات («شرق المتوسط») ومستوى يخالف البطاقة.
    lede = (meta.get("lede") or "") + " " + (meta.get("headline") or "")
    if re.search(r"\d{6}Z", lede):
        problems.append("(9) الترويسة تحمل الفترة الرقمية (نمط 290400Z) — المعتمد «خلال 24 ساعة السابقة»")
    forbidden = ["شرق المتوسط", "شرق البحر المتوسط", "البحر الأحمر وباب المندب"]
    for w in forbidden:
        if w in lede:
            problems.append(f"(9) الترويسة تذكر موقعًا/صيغة خارج القطاعات المعتمدة: «{w}»")
    top_zone = (overall.get("top_zone") or "").strip()
    if top_zone and lvl and lvl != allowed[-1] and top_zone not in lede:
        problems.append(f"(9) الترويسة لا تسمّي أعلى قطاع ({top_zone}) مع مستوى {lvl}")

    if not notes:
        notes.append(f"المستوى العام {lvl} · أعلى قطاع {overall.get('top_zone')} · عدّاد {zones_json.get('counter')}")

    if problems:
        print("   ✘ منع: بوابة اتساق مستوى التهديد — مصدر الحكم غير متسق")
        for p in problems:
            print(f"     - {p}")
        return 2
    for n in notes:
        print(f"   ✔ {n}")
    print("   ✔ اجتاز: المستوى العام وملف الواجهة وبطاقة القرار والمتن متسقة على مصدر واحد")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--brain", default=".")
    a = ap.parse_args()
    try:
        return check_all(pathlib.Path(a.brain).resolve(), a.date)
    except Blocked as e:
        print(f"   ✘ منع: {e}")
        return 2
    except Exception:
        print("   ✘ انهيار داخلي في بوابة اتساق التهديد (70):")
        traceback.print_exc()
        return 70


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _guard import run

    run(main)
