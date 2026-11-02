#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة ربط الأرقام: كل رقم منشور يُعاد حسابه من ملفه المالك ويُقارن.

السبب (ك-453 وك-455): كُتب في الكتيب «فحص التغذيات (40 مصدرًا)» والمعتمد 62، وعدّاد
هجمات IMO يُنشر بلا أي بوابة تحرسه. القاعدة التي تمنع تكرار ذلك:
**رقم بلا مالك معلن وبوابة تقارنه = رقم غير محروس**، ولو كان صحيحًا اليوم.

لكل ربط ثلاثة عناصر: (١) ملف مالك واحد، (٢) طريقة استخراج من الملف، (٣) سطح منشور.
الفشل مغلق (2) عند اختلاف أي ربط، وعند فساد الملف المالك.

الاستخدام: python3 validators/check_number_bindings.py [--date YYYY-MM-DD] [--brain DIR] [--site DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[1]


def _tree(env: str, base: pathlib.Path, *names: str) -> pathlib.Path:
    v = os.environ.get(env)
    if v:
        return pathlib.Path(v)
    for n in names:
        c = base.parent / n
        if c.is_dir():
            return c
    return base.parent / names[0]


def load_json(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8"))


def metric_value(brain: pathlib.Path, date: str, metric_id: str):
    f = brain / "web" / "kpis-totals" / f"{date}.json"
    if not f.is_file():
        return None, f"ملف المقاييس غير موجود: {f}"
    for m in load_json(f).get("metrics", []):
        if isinstance(m, dict) and m.get("id") == metric_id:
            return m, None
    return None, f"لا مقياس بالمعرّف {metric_id} في {f.name}"


def check_imo(brain: pathlib.Path, date: str, out: list, blockers: list) -> None:
    owner = brain / "appendices" / "imo-incidents.json"
    if not owner.is_file():
        blockers.append(f"ملف مالك مفقود: {owner}")
        return
    d = load_json(owner)
    rows = d.get("incidents") or []
    totals = d.get("totals") or {}
    declared = totals.get("confirmed_incidents")
    deaths = totals.get("confirmed_seafarer_deaths")

    # (1) تماسك المالك: المجموع المعلن = عدد الصفوف
    if declared != len(rows):
        blockers.append(f"تماسك المالك مكسور: totals.confirmed_incidents={declared} "
                        f"بينما الصفوف={len(rows)} في imo-incidents.json")
    out.append(("هجمات IMO المؤكدة (تراكمي)", declared, "appendices/imo-incidents.json", "تماسك المالك", "مطابق" if declared == len(rows) else "مخالف"))

    # (2) السطح المنشور: بطاقة العدّاد التراكمي
    m, err = metric_value(brain, date, "imo-confirmed-attacks")
    if m is None:
        blockers.append(f"ربط هجمات IMO بلا سطح منشور: {err}")
    else:
        pub = m.get("cumulative")
        ok = pub == declared
        out.append(("هجمات IMO المؤكدة (تراكمي)", pub, f"web/kpis-totals/{date}.json", "بطاقة العدّاد", "مطابق" if ok else "مخالف"))
        if not ok:
            blockers.append(f"اختلاف ربط هجمات IMO: المنشور {pub} · المالك {declared}")

    # (3) وفيات البحّارة المؤكدة: تُقارن بأي سطح يعلنها نصًّا
    meta = brain / "web" / "meta" / f"{date}.json"
    if meta.is_file() and deaths is not None:
        text = meta.read_text(encoding="utf-8")
        found = {int(x) for x in re.findall(r"(\d{1,3})\s*وفاة", text)}
        if found:
            ok = found == {deaths}
            out.append(("وفيات البحّارة المؤكدة (IMO)", deaths, "appendices/imo-incidents.json",
                        f"واجهة اليوم: {sorted(found)}", "مطابق" if ok else "مخالف"))
            if not ok:
                blockers.append(f"اختلاف ربط الوفيات: الواجهة {sorted(found)} · المالك {deaths}")
        else:
            out.append(("وفيات البحّارة المؤكدة (IMO)", deaths, "appendices/imo-incidents.json",
                        "لا سطح يعلنها", "بلا سطح"))


def check_sources(brain: pathlib.Path, site: pathlib.Path, date: str, out: list, blockers: list) -> None:
    man = brain / "appendices" / "sources-manifest.json"
    lst = brain / "sections" / "10-sources.md"
    if not (man.is_file() and lst.is_file()):
        blockers.append("ملف المصادر الواحد أو قائمة المصادر مفقود")
        return
    approved = int(load_json(man)["approved_source_count"])
    nums = [int(n) for n in re.findall(r"^\|\s*(\d+)\s*\|", lst.read_text(encoding="utf-8"), re.M)]
    rows = sorted(set(n for n in nums if 1 <= n <= approved))
    ok = len(rows) == approved and rows[-1] == approved
    out.append(("عدد المصادر المعتمد", approved, "appendices/sources-manifest.json",
                f"أرقام قائمة المصادر: {len(rows)} صفًا حتى {rows[-1] if rows else 0}", "مطابق" if ok else "مخالف"))
    if not ok:
        blockers.append(f"اختلاف ربط عدد المصادر: المعتمد {approved} · القائمة {len(rows)}")

    # أي سطح منشور يعلن عددًا للمصادر يجب أن يساوي المعتمد
    # ك-455: صفحات الإصدارات الأرشيفية تسجّل عدد مصادر زمانها، فهي وثيقة تاريخية لا ادعاء حالي.
    # النطاق المحروس: الأسطح الحالية وحدها (الرئيسية · إصدار اليوم وترجمته · المصادر · الإضافات · السجل التراكمي).
    dist = site / "dist"
    current = [dist / "index.html", dist / "sources.html", dist / "additions.html",
               dist / "reports" / "cumulative-2026.html",
               dist / "reports" / f"{date}.html", dist / "reports" / "en" / f"{date}.html"]
    for p in current:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in re.finditer(r"(\d{2,3})\s*مصدر", text):
            n = int(m.group(1))
            after = text[m.end():m.end() + 16]
            before = text[max(0, m.start() - 40):m.start()]
            # كميات أخرى مشروعة: مفحوص في تشغيل · مستشهد به · مؤرخ بـ«آنذاك/في ذلك الشهر».
            OTHER = ("مفحوص", "مستشهد", "متقادم", "آنذاك", "ذلك الشهر", "في حينه", "تاريخي")
            if any(k in after for k in OTHER) or any(k in before for k in ("آنذاك", "في حينه", "تاريخي")):
                out.append((f"كمية أخرى للمصادر ({n})", n, "—", f"{p.name}: كمية لا ادعاء معتمد", "مقبول"))
                continue
            # ادعاء صريح عن القائمة المعتمدة: يجب أن يساوي المعتمد
            if "معتمد" in before or "معتمد" in after:
                if n != approved:
                    blockers.append(f"ادعاء معتمد مخالف في {p.name}: «{n} مصدرًا» والمعتمد {approved}")
                else:
                    out.append((f"عدد المصادر المعتمد ({n})", n, "sources-manifest.json", p.name, "مطابق"))
                continue
            blockers.append(f"رقم مصادر بلا مؤهّل في {p.name}: «{n} مصدرًا» (المعتمد {approved})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--brain", default=str(ROOT))
    ap.add_argument("--site", default=None)
    a = ap.parse_args()

    brain = pathlib.Path(a.brain)
    site = pathlib.Path(a.site) if a.site else _tree("SITE_DIR", brain, "seawatch", "site")
    date = a.date
    if not date:
        cands = sorted((brain / "web" / "kpis-totals").glob("*.json"))
        date = cands[-1].stem if cands else ""

    print(f"=== بوابة ربط الأرقام — التاريخ {date} ===")
    rows: list[tuple] = []
    blockers: list[str] = []
    check_imo(brain, date, rows, blockers)
    check_sources(brain, site, date, rows, blockers)

    print(f"   {'الرقم':<32} {'القيمة':>7}  {'الملف المالك':<34} {'السطح':<34} الحالة")
    for name, val, owner, surface, state in rows:
        print(f"   {name:<32} {str(val):>7}  {owner:<34} {surface:<34} {state}")

    for b in blockers:
        print(f"   ✘ {b}")
    if blockers:
        print(f"  النتيجة: مانع — {len(blockers)} ربطًا مكسورًا")
        return 2
    print(f"  النتيجة: مطابق — {len(rows)} رقمًا مربوطًا بمالكه وبوابته")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
