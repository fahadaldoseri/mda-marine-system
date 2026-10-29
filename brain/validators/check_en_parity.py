#!/usr/bin/env python3
"""بوابة تماثل النسخة الإنجليزية مع المتن العربي (تفشل مغلقًا).

تحرس أمرين:
(أ) المتن: لا إسقاط ولا إضافة في البنية أو الأرقام.
    1) عدد عناوين H2 متساوٍ.  2) أسطر الجداول.  3) بنود القوائم.
    4) تطابق تام لكل: أكواد الوقائع والتقديرات · تحذيرات NAVAREA/UKMTO · الحسابات ·
       النسب المئوية · المديات · درجات الثقة · التواريخ والأوقات · كل الأرقام.
(ب) الصفحتان المبنيتان (ك-311): النسخة الإنجليزية تُشتق من صفحة الإصدار العربية نفسها،
    فيجب تطابق البنية المرئية حرفيًا: h1/h2/h3/جداول/صفوف/SVG/أزرار/بنود/روابط/أقسام
    مطويّة، مع lang=en وdir=ltr، و0 مقطع عربي متبقٍّ خارج الوسم غير المرئي.
    أي اختلاف في البنية = فشل مغلق (الحالة التي كشفت إسقاط الخريطة والبطاقات).

الاستعمال: python3 validators/check_en_parity.py --date 2026-10-29
الخروج: 0 مطابق · 1 مخالف · 2 إدخال ناقص.
"""
from __future__ import annotations
import argparse, collections, pathlib, re, sys

import os


def _root(env: str, base: pathlib.Path, *names: str) -> pathlib.Path:
    """جذر الشجرة: من متغيّر البيئة أو من مجلد شقيق معتمد (قابلية النقل)."""
    v = os.environ.get(env)
    if v:
        return pathlib.Path(v)
    for n in names:
        if (base / n).is_dir():
            return base / n
    return base / names[0]


_HOME = pathlib.Path(__file__).resolve().parents[1].parent
BRAIN = _root("BRAIN_DIR", _HOME, "brain-marine-news", "brain")
SITE = _root("SITE_DIR", _HOME, "seawatch", "site")
AR = BRAIN / "reports"
EN = SITE / "sources" / "i18n" / "en"
AR_PAGE = SITE / "dist" / "reports"
EN_PAGE = SITE / "dist" / "reports" / "en"
ARABIC = re.compile(r"[\u0600-\u06FF][\u0600-\u06FF\s]{2,}")

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

PAGE_KEYS = ("h1", "h2", "h3", "tables", "rows", "svg", "buttons", "list_items", "links", "collapsed")


def counts(p: pathlib.Path):
    t = p.read_text(encoding="utf-8")
    return {
        "h2": len(re.findall(r"^## ", t, re.M)),
        "table_rows": len([l for l in t.splitlines() if l.strip().startswith("|")]),
        "list_items": len([l for l in t.splitlines() if re.match(r"^\s*[-*]\s+", l)]),
        "tokens": {name: collections.Counter(re.findall(pat, t)) for name, pat in TOKENS},
    }


def page_stats(p: pathlib.Path) -> dict:
    h = p.read_text(encoding="utf-8")
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", h.split("</head>", 1)[-1], flags=re.S)
    text = re.sub(r"<[^>]+>", " ", body)
    m_lang = re.search(r'<html[^>]*lang="([^"]+)"', h)
    m_dir = re.search(r'<html[^>]*dir="([^"]+)"', h)
    return {
        "h1": len(re.findall(r"<h1", body)),
        "h2": len(re.findall(r"<h2", body)),
        "h3": len(re.findall(r"<h3", body)),
        "tables": len(re.findall(r"<table", body)),
        "rows": len(re.findall(r"<tr", body)),
        "svg": len(re.findall(r"<svg", body)),
        "buttons": len(re.findall(r"<button", body)),
        "list_items": len(re.findall(r"<li", body)),
        "links": len(re.findall(r"<a ", body)),
        "collapsed": len(re.findall(r"sc-collapsed", body)),
        "lang": m_lang.group(1) if m_lang else "",
        "dir": m_dir.group(1) if m_dir else "",
        "arabic_runs": sorted({re.sub(r"\s+", " ", x.group(0)).strip() for x in ARABIC.finditer(text)}),
    }


def check_attributes() -> tuple[bool, str]:
    """ك-315: لا يجوز أن تبقى سمات عربية (title/aria-label/alt) في صفحة إنجليزية."""
    bad = []
    for page in sorted(EN_PAGE.glob("*.html")):
        h = page.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'\b(title|aria-label|alt|placeholder)="([^"]*)"', h):
            if re.search(r"[\u0600-\u06FF]", m.group(2)):
                bad.append(f"{page.name}: {m.group(1)}=\"{m.group(2)[:40]}\"")
    if bad:
        return False, "سمات عربية في النسخة الإنجليزية: " + " · ".join(bad[:4])
    return True, "لا سمات عربية في النسخة الإنجليزية"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--skip-pages", action="store_true", help="تخطّي فحص الصفحتين المبنيتين (لا يُستعمل في البوابات)")
    a = ap.parse_args()
    bad: list[str] = []
    # ك-315 (تكملة): فحص السمات يفشل مغلقًا — واجهة إنجليزية بسمات عربية عيب مؤكد.
    ok_attrs, msg_attrs = check_attributes()
    if not ok_attrs:
        bad.append(msg_attrs)

    ar_p, en_p = AR / f"{a.date}-sectioned.md", EN / f"{a.date}-sectioned.en.md"
    for p in (ar_p, en_p):
        if not p.exists():
            print(f"   ✘ إدخال ناقص: {p}")
            return 2
    ar, en = counts(ar_p), counts(en_p)
    print("   ── المتن ──")
    for k, label in (("h2", "عناوين H2"), ("table_rows", "أسطر الجداول"), ("list_items", "بنود القوائم")):
        mark = "✔" if ar[k] == en[k] else "✘"
        print(f"   {mark} {label}: عربي {ar[k]} · إنجليزي {en[k]}")
        if ar[k] != en[k]:
            bad.append(label)
    for name, _ in TOKENS:
        d_ar, d_en = ar["tokens"][name], en["tokens"][name]
        missing, extra = dict(d_ar - d_en), dict(d_en - d_ar)
        mark = "✔" if not missing and not extra else "✘"
        print(f"   {mark} {name}: إجمالي عربي {sum(d_ar.values())} · إنجليزي {sum(d_en.values())}")
        if missing:
            print(f"      ناقص في الإنجليزية: {dict(list(missing.items())[:6])}")
        if extra:
            print(f"      زائد في الإنجليزية: {dict(list(extra.items())[:6])}")
        if missing or extra:
            bad.append(name)

    if not a.skip_pages:
        ar_page, en_page = AR_PAGE / f"{a.date}.html", EN_PAGE / f"{a.date}.html"
        for p in (ar_page, en_page):
            if not p.exists():
                print(f"   ✘ صفحة ناقصة: {p}")
                return 2
        A, E = page_stats(ar_page), page_stats(en_page)
        print("   ── الصفحتان المبنيتان ──")
        for k in PAGE_KEYS:
            mark = "✔" if A[k] == E[k] else "✘"
            print(f"   {mark} {k}: عربي {A[k]} · إنجليزي {E[k]}")
            if A[k] != E[k]:
                bad.append(f"بنية:{k}")
        lang_ok = E["lang"] == "en" and E["dir"] == "ltr"
        print(f"   {'✔' if lang_ok else '✘'} لغة الصفحة الإنجليزية: lang={E['lang']} dir={E['dir']}")
        if not lang_ok:
            bad.append("لغة الصفحة الإنجليزية")
        n_ar = len(E["arabic_runs"])
        print(f"   {'✔' if n_ar == 0 else '✘'} نصوص عربية متبقية في الصفحة الإنجليزية: {n_ar}")
        for r in E["arabic_runs"][:8]:
            print(f"      · {r[:80]}")
        if n_ar:
            bad.append(f"نص عربي متبقٍّ ({n_ar})")

    if bad:
        print("   ✘ النتيجة: مخالف — " + " · ".join(bad))
        return 1
    print("   ✔ النتيجة: النسخة الإنجليزية مطابقة للمتن ولصفحة الإصدار في البنية والأرقام والأكواد واللغة")
    return 0


if __name__ == "__main__":
    sys.exit(main())
