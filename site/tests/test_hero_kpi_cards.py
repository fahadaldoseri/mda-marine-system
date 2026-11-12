#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس دائم لبطاقات الأرقام أعلى التقرير — يفشل مغلقًا (rc=1) عند رجوع أي عيب.

يغطي سبعة أعطال مقيسة في 2026-11-12:
  1) شريط لوني بلا مفتاح يشرح دلالته.
  2) سقوط صامت للفئة إلى الأخضر عند غياب accent (نقص بيانات يتحول إلى إيحاء سلامة).
  3) الصف الثاني بأربعة أعمدة لبطاقتين (فراغ أفقي).
  4) نصوص ثانوية أصغر من 14px على الشاشة، أو أصغر من 10.5pt في الطباعة.
  5) قيمة وصفية طويلة في خانة الرقم الكبير بلا صنف مخصص.
  6) تفصيل مكرر حرفيًا بين بطاقتين، أو رقم بلا سند (128 · 24 · 03/11/2026).
  7) شارة نطاق تفقد قطاعًا (Z2–Z4 تسقط Z3).

الاستخدام:
    SITE_DIR=<site-root> BRAIN_DIR=<brain-root> \
        python3 tests/test_hero_kpi_cards.py [--date 2026-11-11]
"""
import argparse
import json
import os
import pathlib
import re
import sys

FAILS = []


def check(cond, label):
    if cond:
        print(f"   ✓ {label}")
    else:
        print(f"   ✘ {label}")
        FAILS.append(label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=os.environ.get("CHECK_DATE", "2026-11-11"))
    args = ap.parse_args()

    local = pathlib.Path(__file__).resolve().parents[1]
    site = pathlib.Path(os.environ.get("SITE_DIR") or local)
    brain = pathlib.Path(os.environ.get("BRAIN_DIR") or site.parent / "brain")
    os.environ.setdefault("BRAIN_DIR", str(brain))

    print("═══ حارس بطاقات الأرقام ═══")
    print(f"   الشجرة: {site}")
    print(f"   التاريخ: {args.date}")

    sl_p = site / "generator/screen_layer.py"
    if not sl_p.exists():
        print(f"   ✘ ملف طبقة العرض غير موجود: {sl_p}")
        return 1
    sl = sl_p.read_text(encoding="utf-8")

    # ── 1) المفتاح والسقوط الصامت والأعمدة والخطوط ──
    check("sc-kpi-key" in sl, "مفتاح ألوان البطاقات موجود في طبقة العرض")
    check(
        re.search(r'get\(\s*["\']accent["\']\s*,\s*["\']ok["\']\s*\)', sl) is None,
        "لا سقوط صامت للفئة إلى الأخضر",
    )
    check(
        re.search(r"\.sc-kpi-row-2\s*\{[^}]*repeat\(\s*2\s*,", sl) is not None,
        "الصف الثاني عمودان على الشاشة",
    )
    check(
        re.search(r"\.sc-kn\s*\{[^}]*font-size:\s*14px", sl) is not None,
        "السطر التوضيحي 14px على الشاشة",
    )
    check(
        re.search(r"\.sc-k-tag\s*\{[^}]*font-size:\s*13px", sl) is not None,
        "وسم البطاقة 13px على الشاشة",
    )
    check("10.5pt" in sl, "النصوص الثانوية في الطباعة 10.5pt")
    check("8.6pt" not in sl, "لا تصغير للنصوص الثانوية إلى 8.6pt في الطباعة")
    check("sc-kv-long" in sl, "صنف القيمة الوصفية الطويلة موجود")

    # ── 2) بيانات البطاقات ──
    meta_p = site / f"sources/meta/{args.date}.json"
    if not meta_p.exists():
        print(f"   ✘ ملف الواجهة غير موجود: {meta_p}")
        return 1
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    cards = meta.get("hero_kpis") or meta.get("kpis") or []
    check(len(cards) == 6, f"عدد البطاقات 6 (فعليًا {len(cards)})")

    def by_label(frag):
        for c in cards:
            if frag in str(c.get("label") or c.get("title") or ""):
                return c
        return {}

    ukmto = by_label("المواد الرسمية")
    crit = by_label("مستوفية لمعيار")
    unc = by_label("روايات")
    conf = by_label("وقائع مثبتة")
    inc = by_label("الحوادث المؤكدة")
    dth = by_label("وفيات")

    check(str(ukmto.get("value")) == "2", "قيمة بطاقة المواد الرسمية رقم 2")
    check("201-26" in str(ukmto.get("detail")) and "202-26" in str(ukmto.get("detail")),
          "تفصيل المواد الرسمية يحفظ المعرّفين 201-26 و202-26")
    check(unc.get("accent") == "warn", "الروايات غير المؤكدة فئتها warn لا ok")
    check(conf.get("accent") == "info", "وقائع مثبتة خارج Z1 فئتها info محايدة")
    check(not any(c.get("accent") == "ok" for c in cards),
          "لا بطاقة مصنّفة ok في هذا الإصدار (لا إيحاء سلامة)")
    check("Z3" in str(conf.get("tag")), "شارة النطاق تحفظ القطاع الأوسط Z3")
    check("128" in str(inc.get("detail")) and "03/11/2026" in str(inc.get("detail")),
          "تفصيل الحوادث يحمل الإجمالي 128 وتاريخ 03/11/2026")
    check("24" in str(dth.get("detail")), "تفصيل الوفيات يحمل الإجمالي 24")
    details = [str(c.get("detail") or "").strip() for c in cards]
    check(len(set(details)) == len(details), "لا تفصيل مكرر حرفيًا بين بطاقتين")
    check("مستوفية" in str(crit.get("detail")) or "مؤهلة" in str(crit.get("detail")),
          "تفصيل الوقائع المستوفية يحفظ التوزيع")

    # ── 3) العرض الفعلي: المفتاح يظهر مع البطاقات المصنّفة ──
    sys.path.insert(0, str(site / "generator"))
    try:
        import screen_layer  # noqa: E402
        fn = getattr(screen_layer, "screen_hero", None) or getattr(screen_layer, "render_hero", None)
        if fn is None:
            check(False, "دالة عرض بطاقات الشاشة متاحة")
        else:
            # مسار موثوق: بناء الصفحة الفعلي ثم قياس مخرجها
            _md = pathlib.Path("sources/reports/%s-sectioned.md" % args.date)
            html = None
            if _md.exists():
                try:
                    sys.path.insert(0, "generator")
                    import build_report as _BR
                    _out = pathlib.Path("dist/reports/%s.html" % args.date)
                    _out.parent.mkdir(parents=True, exist_ok=True)
                    _BR.build(_md, _out, json.loads(pathlib.Path("sources/meta/%s.json" % args.date).read_text(encoding="utf-8")))
                    html = _out.read_text(encoding="utf-8")
                except Exception as _e:
                    print("BUILD-ERR:", type(_e).__name__, _e, file=sys.stderr)
                    html = None
            else:
                print("   · تخطّي فحص المخرج: لا شجرة بناء هنا (متن المصدر غير موجود)")
            if html is None and _md.exists():
                raise RuntimeError("تعذّر بناء الصفحة لقياس المخرج")
            html = html if isinstance(html, str) else json.dumps(html, ensure_ascii=False)
            check("sc-kpi-key" in html, "المفتاح يظهر في المخرج مع بطاقات مصنّفة")
            check(html.count("sc-kpi-row-2") >= 1, "صفّ ثانٍ مُخرَج في المخرج")
    except Exception as exc:  # pragma: no cover
        check(False, f"تعذّر استدعاء طبقة العرض: {type(exc).__name__}: {exc}")

    print("═══ النتيجة ═══")
    if FAILS:
        print(f"   مانع: {len(FAILS)} بندًا فاشلًا")
        for f in FAILS:
            print(f"     · {f}")
        return 1
    print("   نجاح: كل بنود الحارس خضراء")
    return 0


if __name__ == "__main__":
    sys.exit(main())
