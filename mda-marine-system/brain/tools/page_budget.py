#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ميزانية الصفحات بهامش أمان — تقيس المساحة المتبقية قبل أي تعديل نصي.

الأساس (ك-42 · ك-43 · ك-44): إضافة بند واحد في القاموس دفعت الترقيم من 16 إلى 17
صفحة فسقطت الصفحة الأخيرة إلى 22% ووقف التسليم. المقياس وحده لا يكفي؛ هذه الأداة
تُعلن الميزانية المتبقية بالأحرف مع هامش أمان قبل التعديل، وتمنع ما يتجاوزها.

الاستخدام:
  python3 tools/page_budget.py --date 2026-10-20                # تقرير الحالة
  python3 tools/page_budget.py --date 2026-10-20 --adding 400   # هل يتّسع 400 حرف؟
الرمز: 0 متّسع · 1 ضيق (تحذير) · 2 لا يتّسع (مانع)
"""
from __future__ import annotations
import argparse, sys, re, subprocess
import os
from pathlib import Path

B = Path(__file__).resolve().parent.parent
S = Path(os.environ.get("SITE_DIR") or B.parent / "seawatch")
sys.path.insert(0, str(B / "validators"))
from check_pdf_format import page_metrics  # noqa: E402

SAFETY = 0.80       # هامش الأمان: لا يُستهلك أكثر من 80% من المساحة الحرّة
# عطل ك-51: أعلنت الأداة «لا يتّسع» لإضافة 588 حرفًا، ثم بنى المخرج واستوعبها في
# 16 صفحة ورفع تعبئة الأخيرة من 80.4% إلى 97.0%. السبب: القاموس يُعرض بخط مدمج
# فكلفته المساحية ليست ككلفة المتن. المعامل المقيس: 0.36 من كثافة المتن.
GLOSSARY_DENSITY = 0.36
TIGHT = 0.25        # أقل من ربع الميزانية المتاحة = ضيق


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--adding", type=int, default=0,
                    help="عدد الأحرف المزمع إضافتها")
    a = ap.parse_args()

    pdf = S / "dist" / "reports" / "pdf" / f"{a.date}.pdf"
    md = B / "reports" / f"{a.date}-sectioned.md"
    if not pdf.exists():
        print(f"✘ لا ملف PDF: {pdf}"); return 2
    if not md.exists():
        print(f"✘ لا ملف مصدر: {md}"); return 2

    fills, _ = page_metrics(pdf)
    pages = len(fills)
    last = fills[-1]
    avg = sum(fills) / pages
    # عطل ك-50: كان العدد يُحسب من ملف المصدر كاملًا وفيه «المصادر وموثوقية المصادر»
    # وهي محجوبة في PDF، فكانت السعة لكل صفحة مبالغًا فيها فتصير الميزانية أسخى من
    # الحقيقة. والقياس من نص PDF نفسه بالغ أيضًا لأن كل صفحة تحمل ترويسة وتذييلًا.
    # الصحيح: متن المصدر قبل قسم المصادر + ما يُبنى من الواجهة (القاموس وأهم الأخبار المتعلقة بالأمن البحري).
    def visible_md(text: str) -> str:
        cut = text.find("## المصادر والمراجع")
        return text if cut < 0 else text[:cut]
    body = len(re.sub(r"\s+", " ", visible_md(md.read_text(encoding="utf-8"))))
    meta_f = B / "web" / "meta" / f"{a.date}.json"
    if meta_f.exists():
        import json as _j
        mm = _j.loads(meta_f.read_text(encoding="utf-8"))
        body += sum(len(str(k)) + len(str(v)) for k, v in mm.get("glossary", {}).items())
    content_pages = sum(fills) / 100.0
    chars_per_page = body / content_pages if content_pages else 0
    free_page = max(0.0, 1.0 - last / 100.0)
    budget = SAFETY * free_page * chars_per_page

    print(f"=== ميزانية الصفحات — {a.date} ===")
    print(f"  الصفحات: {pages} · متوسط التعبئة: {avg:.1f}% · تعبئة الأخيرة: {last:.1f}%")
    print(f"  أحرف PDF المرئية: {body:,} · أحرف لكل صفحة: {chars_per_page:,.0f}")
    print(f"  المساحة الحرّة في الأخيرة: {free_page*100:.1f}% من صفحة")
    print(f"  الميزانية الآمنة لمتن عادي (هامش {SAFETY:.0%}): {budget:,.0f} حرفًا")
    print(f"  ما يعادلها في القاموس المدمج: {budget / GLOSSARY_DENSITY:,.0f} حرفًا")

    rc = 0
    if a.adding:
        left = budget - a.adding
        print(f"  المزمع إضافته: {a.adding:,} حرفًا → المتبقي: {left:,.0f}")
        if a.adding > budget:
            print("  النتيجة التقديرية: يبدو متجاوزًا — والحكم النهائي بعد البناء لا قبله")
            print("     القاعدة: الحكم النهائي = عدد الصفحات ثابتًا + تعبئة الأخيرة فوق الحدّ")
            rc = 1
        elif left < budget * TIGHT:
            print("  النتيجة: يتّسع بهامش ضيق — قسّم الإضافة  · تحذير")
            rc = 1
        else:
            print("  النتيجة: يتّسع بهامش آمن  ✔")
    else:
        print("  الاستعمال: أضف --adding <عدد الأحرف> قبل أي تعديل نصي")
    return rc


if __name__ == "__main__":
    sys.exit(main())
