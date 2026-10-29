#!/usr/bin/env python3
"""بوابة تماثل النسخة الإنجليزية مع المتن العربي (تفشل مغلقًا).

تتحقق أن الترجمة لم تُسقط أو تُضف بنية أو رقمًا:
1) عدد عناوين H2 متساوٍ.  2) عدد أسطر الجداول متساوٍ.  3) عدد بنود القوائم متساوٍ.
4) تطابق تام (متعدد المجموعات) لكل: أكواد الوقائع والتقديرات · تحذيرات NAVAREA/UKMTO ·
   الحسابات · النسب المئوية · درجات الثقة (A/1، C/3) · التواريخ والأوقات.
الاستعمال: python3 validators/check_en_parity.py --date 2026-10-29
الخروج: 0 مطابق · 1 مخالف · 2 إدخال ناقص.
"""
from __future__ import annotations
import argparse, collections, pathlib, re, sys

AR = pathlib.Path("/home/ubuntu/brain-marine-news/reports")
EN = pathlib.Path("/home/ubuntu/seawatch/sources/i18n/en")

TOKENS = [
    ("أكواد الوقائع/التقديرات", r"(?<![\d-])(?:MN|EST|NAV|IMO|UKMTO)-\d{4}-\d{2}-\d{2}(?:-\d+)?"),
    ("تحذيرات NAVAREA/UKMTO", r"NAVAREA\s+[IVX]+\s+\d+/\d+|UKMTO\s+\d+[-/]\d+"),
    ("الحسابات", r"@[A-Za-z0-9_]+"),
    ("النسب المئوية", r"(?<![\d.])\d+(?:[.,]\d+)?\s*%"),
    ("المديات الرقمية", r"(?<![\d.])\d+\s*[–-]\s*\d+\s*%"),
    ("درجات الثقة", r"(?<![A-Za-z0-9])[A-C]/\d(?![0-9])"),
    ("التواريخ والأوقات", r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}:\d{2}(?::\d{2})?\b"),
    ("كل الأرقام", r"(?<![\d.])\d+(?:[.,]\d+)?(?![\d])"),
]


def counts(p: pathlib.Path):
    t = p.read_text(encoding="utf-8")
    return {
        "h2": len(re.findall(r"^## ", t, re.M)),
        "table_rows": len([l for l in t.splitlines() if l.strip().startswith("|")]),
        "list_items": len([l for l in t.splitlines() if re.match(r"^\s*[-*]\s+", l)]),
        "tokens": {name: collections.Counter(re.findall(pat, t)) for name, pat in TOKENS},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    ar_p = AR / f"{a.date}-sectioned.md"
    en_p = EN / f"{a.date}-sectioned.en.md"
    for p in (ar_p, en_p):
        if not p.exists():
            print(f"   ✘ إدخال ناقص: {p}")
            return 2
    ar, en = counts(ar_p), counts(en_p)
    bad = []
    for k, label in (("h2", "عناوين H2"), ("table_rows", "أسطر الجداول"), ("list_items", "بنود القوائم")):
        mark = "✔" if ar[k] == en[k] else "✘"
        print(f"   {mark} {label}: عربي {ar[k]} · إنجليزي {en[k]}")
        if ar[k] != en[k]:
            bad.append(label)
    for name, _ in TOKENS:
        d_ar, d_en = ar["tokens"][name], en["tokens"][name]
        missing = {k: v for k, v in (d_ar - d_en).items()}
        extra = {k: v for k, v in (d_en - d_ar).items()}
        mark = "✔" if not missing and not extra else "✘"
        print(f"   {mark} {name}: إجمالي عربي {sum(d_ar.values())} · إنجليزي {sum(d_en.values())}")
        if missing:
            print(f"      ناقص في الإنجليزية: {dict(list(missing.items())[:6])}")
        if extra:
            print(f"      زائد في الإنجليزية: {dict(list(extra.items())[:6])}")
        if missing or extra:
            bad.append(name)
    if bad:
        print("   ✘ النتيجة: مخالف — " + " · ".join(bad))
        return 1
    print("   ✔ النتيجة: الترجمة مطابقة للمتن في البنية والأرقام والأكواد")
    return 0


if __name__ == "__main__":
    sys.exit(main())
