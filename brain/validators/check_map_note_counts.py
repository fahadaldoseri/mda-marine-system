#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس جملة «حالات الخريطة»: العدّادات المعلنة = العدّادات المحسوبة من نقاط الخريطة.

يفشل مغلقًا (rc=2) إذا:
  1) جملة المصدر (points_note في ملف الواجهة) خالفت التوزيع المحسوب،
  2) points_stats خالفت التوزيع المحسوب أو عدد النقاط المرسومة،
  3) صفحة التقرير العربية المنشورة خالفت التوزيع المحسوب،
  4) صفحة التقرير الإنجليزية المنشورة خالفت التوزيع المحسوب.

الصياغة مرنة (ترتيب/تسمية)، والحكم على الأعداد واكتمال الفئات غير الصفرية.

الاستخدام:
  python3 validators/check_map_note_counts.py --date 2026-11-01 [--site "$SITE"] [--json out.json]
"""
from __future__ import annotations

import os
import pathlib
import argparse, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEYS = ("confirmed", "probable", "unconfirmed", "not_qualifying", "status_unknown")

# صيغة المصدر المعتمدة في ملف الواجهة
AR_SRC = re.compile(
    r"وتوزيع الحالة: مؤكد (\d+) · مرجّح (\d+) · غير مؤكد مؤهل (\d+) · غير مؤهل (\d+) · حالة غير محددة (\d+)")

# كلمات التصنيف في النص المعروض (عربي وإنجليزي)
AR_HINTS = (("unconfirmed", ("غير مؤكد مؤهل",)),
            ("not_qualifying", ("غير مؤهل",)),
            ("confirmed", ("مؤكد",)),
            ("probable", ("مرجّح", "مرجح")),
            ("status_unknown", ("حالة غير محددة", "غير محدد", "لم تُذكر", "لم تذكر")))
EN_HINTS = (("unconfirmed", ("unconfirmed qualifying", "unconfirmed")),
            ("not_qualifying", ("not qualifying", "non-qualifying")),
            ("confirmed", ("confirmed",)),
            ("probable", ("probable",)),
            ("status_unknown", ("status not stated", "status unknown", "not stated")))


def compute(points: list[dict]) -> dict:
    st = {k: 0 for k in KEYS}
    for p in points:
        q = p.get("qualifying")
        c = str(p.get("confirmation") or "").strip().lower()
        if q is True and c == "confirmed":
            st["confirmed"] += 1
        elif q is True and c == "probable":
            st["probable"] += 1
        elif q is True:
            st["unconfirmed"] += 1
        elif q is False:
            st["not_qualifying"] += 1
        else:
            st["status_unknown"] += 1
    return st


def parse_segments(text: str, hints, label: str, calc: dict, problems: list[str]) -> bool:
    """يستخرج عدّادات من مقاطع مفصولة بـ· ويقارنها بالمحسوب. يعيد True إن قرأ عدّادًا واحدًا."""
    # نقتصر على الجزء الذي يلي وسم الحالات، ثم نقرأ الرقم الملاصق لكل تصنيف
    # (لا أول رقم في المقطع، حتى لا يُقرأ عدّاد آخر من جملة مجاورة).
    for marker in ("الحالات:", "statuses:", "status mix:", "حالات:"):
        i = text.lower().find(marker)
        if i != -1:
            text = text[i + len(marker):]
            break
    segs = [s.strip() for s in re.split(r"[·•|]", text) if s.strip()]
    seen = {}
    for s in segs:
        low = s.lower()
        matched = False
        for key, words in hints:
            for w in words:
                m2 = re.search(re.escape(w.lower()) + r"[^\d]{0,30}(\d+)", low)
                if not m2:
                    m2 = re.search(r"(\d+)[^\d]{0,12}" + re.escape(w.lower()), low)
                if m2:
                    seen.setdefault(key, int(m2.group(1)))
                    matched = True
                    break
            if matched:
                break
    if not seen:
        problems.append(f"{label}: لم أقرأ أي عدّاد حالات معروف")
        return False
    for k, v in seen.items():
        if v != calc[k]:
            problems.append(f"{label}: {k} معلن {v} والمحسوب {calc[k]}")
    for k in KEYS:
        if calc[k] > 0 and k not in seen:
            problems.append(f"{label}: الفئة {k} = {calc[k]} غير مذكورة في الجملة")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--site", default=os.environ.get("SITE") or os.environ.get("SITE_DIR") or str(pathlib.Path(__file__).resolve().parents[1].parent / "seawatch"))
    ap.add_argument("--json")
    args = ap.parse_args()

    problems: list[str] = []
    meta_p = ROOT / "web" / "meta" / f"{args.date}.json"
    if not meta_p.exists():
        print(f"  ✘ فشل مغلق: ملف الواجهة غير موجود: {meta_p}")
        return 2
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    mp = meta.get("map") or {}
    points = mp.get("points") or []
    note = mp.get("points_note") or ""
    stats = mp.get("points_stats") or {}
    # يوم بلا وقائع مخطّطة: لا جملة حالة تُبنى، وهي محذوفة من الأسطح بقرار المالك.
    # لا يُخفَّف الفحص: تُشترط إحصاءات صفرية كاملة، ويُمنع ظهور جملة الحالات على السطحين.
    zero_day = not points
    if zero_day:
        nonzero = {
            k: int(stats.get(k, 0) or 0)
            for k in list(KEYS) + ["drawn", "events", "with_area", "exact", "approximate", "off_map", "excluded"]
            if int(stats.get(k, 0) or 0) != 0
        }
        if nonzero:
            problems.append(f"يوم بلا نقاط لكن إحصاءاته غير صفرية: {nonzero}")
        else:
            print("  ✔ يوم بلا وقائع مخطّطة (0 نقطة) وإحصاءاته صفرية — الجملة محذوفة بقرار المالك")
    calc = compute(points)

    m = None
    # 1) جملة المصدر — حُذفت من الأسطح بقرار المالك (ملاحظة 6 و8)؛ تُتحقق فقط إن وُجدت.
    if not str(note).strip():
        print("  ✔ ملاحظة الخريطة محذوفة بقرار المالك — لا جملة مصدر للتحقق")
    else:
        m = AR_SRC.search(note)
        if not m:
            problems.append("جملة المصدر (points_note) موجودة لكن ليست بصيغتها المعتمدة")
        else:
            got = dict(zip(KEYS, (int(x) for x in m.groups())))
            for k, v in got.items():
                if v != calc[k]:
                    problems.append(f"جملة المصدر: {k} معلن {v} والمحسوب {calc[k]}")

    # 2) إحصاءات النقاط
    for k in KEYS:
        if int(stats.get(k, -1)) != calc[k]:
            problems.append(f"points_stats: {k} = {stats.get(k)} والمحسوب {calc[k]}")
    if int(stats.get("drawn", -1)) != len(points):
        problems.append(f"points_stats.drawn = {stats.get('drawn')} وعدد النقاط {len(points)}")
    if int(stats.get("exact", 0)) + int(stats.get("approximate", 0)) != len(points):
        problems.append("مجموع الدقيق + التقريبي لا يساوي عدد النقاط")

    # 3) الصفحة العربية المنشورة
    ar_ok = False
    ar_p = pathlib.Path(args.site) / "dist" / "reports" / f"{args.date}.html"
    if ar_p.exists():
        html = ar_p.read_text(encoding="utf-8", errors="ignore")
        mm = re.search(r"aria-label=\"([^\"]*الحالات:[^\"]*)\"", html) or re.search(r"الحالات:([^\"<]{10,220})", html)
        if not mm:
            if zero_day:
                ar_ok = True
                print("  ✔ الصفحة العربية: لا جملة حالات — مطابق ليوم بلا وقائع مخطّطة")
            else:
                problems.append("الصفحة العربية: جملة الحالات غير موجودة")
        elif zero_day:
            problems.append("الصفحة العربية: ظهرت جملة حالات في يوم بلا وقائع مخطّطة بعد حذفها بقرار المالك")
        else:
            ar_ok = parse_segments(mm.group(1), AR_HINTS, "الصفحة العربية", calc, problems)
    else:
        problems.append(f"الصفحة العربية غير موجودة: {ar_p}")

    # 4) الصفحة الإنجليزية
    en_ok = False
    en_p = pathlib.Path(args.site) / "dist" / "reports" / "en" / f"{args.date}.html"
    if en_p.exists():
        html = en_p.read_text(encoding="utf-8", errors="ignore")
        me = re.search(r"aria-label=\"([^\"]*[Ss]tatus[^\"]*)\"", html) or \
             re.search(r"[Ss]tatuses?:([^\"<]{10,220})", html)
        if not me:
            if zero_day:
                en_ok = True
                print("  ✔ الصفحة الإنجليزية: لا جملة حالات — مطابق ليوم بلا وقائع مخطّطة")
            else:
                problems.append("الصفحة الإنجليزية: جملة الحالات غير موجودة")
        elif zero_day:
            problems.append("الصفحة الإنجليزية: ظهرت جملة حالات في يوم بلا وقائع مخطّطة بعد حذفها بقرار المالك")
        else:
            en_ok = parse_segments(me.group(1), EN_HINTS, "الصفحة الإنجليزية", calc, problems)
    else:
        problems.append(f"الصفحة الإنجليزية غير موجودة: {en_p}")

    out = {"date": args.date, "points": len(points), "computed": calc, "stats": stats,
           "source_note_ok": (not str(note).strip()) or bool(m), "arabic_page_ok": ar_ok, "english_page_ok": en_ok,
           "problems": problems}
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    if problems:
        print("  ✘ فشل مغلق — عطل في جملة حالات الخريطة:")
        for p in problems:
            print("     -", p)
        return 2
    print(f"  ✔ جملة الحالات مطابقة: مؤكد {calc['confirmed']} · مرجّح {calc['probable']} · "
          f"غير مؤكد مؤهل {calc['unconfirmed']} · غير مؤهل {calc['not_qualifying']} · "
          f"غير محددة {calc['status_unknown']} · نقاط {len(points)} · العربية ✓ · الإنجليزية ✓")
    return 0


if __name__ == "__main__":
    import sys as _sys, pathlib as _pl
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
