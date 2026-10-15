#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مدقّق بساطة اللغة للتقرير الصباحي — يمنع تسليم نص ثقيل.

الاستخدام: python3 validators/check_language.py reports/2026-10-12-sectioned.md

بوابة القبول (من sections/20-language):
  - متوسط كلمات الجملة أقل من 18
  - الجمل التي تتجاوز 35 كلمة أقل من 5%
  - لا عبارات ثقيلة من القائمة المحظورة
  - لا كلمات غير معتمدة من قائمة الرصد
يعيد رمز خروج 0 عند النجاح، و2 عند المخالفة، مع طباعة الموضع.
"""

import re
import sys
from pathlib import Path

MAX_AVG = 18.0
MAX_LONG_RATIO = 0.05
LONG_WORDS = 35

HEAVY = ["بيد أن", "في هذا الصدد", "تجدر الإشارة", "من شأنه أن", "حيال", "إزاء",
         "على ضوء", "في سياق", "استناداً إلى", "استنادا إلى", "مؤداه", "مفادها",
         "تكمن أهمية", "يساور", "يعتري", "في ظل", "لا سيما"]

WATCH = {"قياس": "تقرير أمس", "قياسًا آنيًا": "قراءة لحظية", "إدخالات": "بنود",
         "المحفوظ": "تقرير أمس", "التغير الأهم": "أهم ما تغيّر", "المقياس": "الرقم",
         # مستخلصة من تدقيق 15 أكتوبر 2026 (terminology.md — الاستبدالات الإلزامية)
         "إنذار": "تحذير بحري", "ممسكة بموضعها": "واقفة في مواضعها",
         "خطط الساحل": "خط الساحل", "الاستهداف الجوي": "الاستهداف بالصواريخ والمسيّرات",
         "إغراق": "غرق (إلا إذا ثبت التعمد)", "بسلامة": "تُحذف",
         "يُتساوَى": "لا تُساوى البلاغات بعدد الهجمات",
         "تكدس ملاحي متراكم": "تكدس ملاحي متزايد",
         "تأمين يرتفع": "أقساط التأمين ترتفع", "بسعة": "بحمولة"}


def analyze(text):
    clean = re.sub(r"\|.*\|", " ", text)
    clean = re.sub(r"[#*_>`\-]{1,}", " ", clean)
    clean = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    words = re.findall(r"[\u0600-\u06FF]{2,}", clean)
    sents = [s.strip() for s in re.split(r"[.!؟\n]+", clean) if len(s.strip()) > 15]
    lens = [len(re.findall(r"[\u0600-\u06FF]{2,}", s)) for s in sents]
    avg = sum(lens) / len(lens) if lens else 0.0
    long_ratio = (sum(1 for x in lens if x > LONG_WORDS) / len(lens)) if lens else 0.0
    return {"words": len(words), "sents": len(sents), "avg": avg,
            "long_ratio": long_ratio, "heavy": {h: clean.count(h) for h in HEAVY if clean.count(h)},
            "watch": {w: clean.count(w) for w in WATCH if clean.count(w)}}


def main():
    if len(sys.argv) < 2:
        print("الاستخدام: check_language.py <ملف التقرير>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"الملف غير موجود: {p}")
        return 2
    m = analyze(p.read_text(encoding="utf-8"))
    print(f"كلمات: {m['words']} | جمل: {m['sents']} | متوسط الجملة: {m['avg']:.1f} كلمة "
          f"| نسبة الجمل الطويلة: {m['long_ratio']*100:.1f}%")

    fails = []
    if m["avg"] >= MAX_AVG:
        fails.append(f"متوسط الجملة {m['avg']:.1f} تجاوز {MAX_AVG}")
    if m["long_ratio"] > MAX_LONG_RATIO:
        fails.append(f"نسبة الجمل الطويلة {m['long_ratio']*100:.1f}% تجاوزت {MAX_LONG_RATIO*100:.0f}%")
    if m["heavy"]:
        fails.append("عبارات ثقيلة: " + ", ".join(f"{k}×{v}" for k, v in m["heavy"].items()))
    if m["watch"]:
        print("تنبيه (مرشحة للتبسيط): " + ", ".join(f"{k} → {WATCH[k]}" for k in m["watch"]))

    if fails:
        print("رفض التسليم:")
        for f in fails:
            print("  -", f)
        return 2
    print("مقبول: اللغة بسيطة والمصطلحات سليمة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
