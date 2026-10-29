#!/usr/bin/env python3
"""تحقق حي قابل لإعادة التشغيل من زرّي اللغة (ع/EN) على الموقع المنشور.

الاستعمال: python3 tools/check_lang_switch_live.py --url https://... --date 2026-10-29
الخروج: 0 نجاح · 1 مخالفة · 2 إدخال ناقص.

الحالات المقيسة (كلها على الموقع الحقيقي بمتصفح حقيقي):
1) الصفحة العربية: lang=ar · تسميات عربية · زرّان «ع» و«EN».
2) وجود تفضيل إنجليزي محفوظ مسبقًا لا يغيّر لغة الصفحة العربية (lang=ar وتسميات عربية).
3) الضغط على «EN» ينقل فعليًا إلى صفحة النسخة الإنجليزية: lang=en وdir=ltr وتسميات إنجليزية.
4) الضغط على «ع» يعيد إلى الصفحة العربية بلغتها وتسمياتها.
5) لا أخطاء JavaScript في أي مرحلة.
"""
from __future__ import annotations
import argparse, sys

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:  # pragma: no cover
    print(f"   ✘ إدخال ناقص: مكتبة Playwright غير متاحة ({exc})")
    sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--date", default="2026-10-29")
    a = ap.parse_args()
    U = a.url.rstrip("/")
    ar_url = f"{U}/reports/{a.date}.html"
    en_url = f"{U}/reports/en/{a.date}.html"
    fails: list[str] = []

    def mark(ok: bool, label: str, detail: str = "") -> None:
        print(f"   {'✔' if ok else '✘'} {label}{(' — ' + detail) if detail else ''}")
        if not ok:
            fails.append(label)

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1360, "height": 900})
        pg = ctx.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        pg.goto(en_url, wait_until="load")
        mark(pg.url.endswith(f"/en/{a.date}.html"), "صفحة النسخة الإنجليزية تُخدم وجودها", pg.url.replace(U, ""))
        b.close()

        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1360, "height": 900})
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(ar_url, wait_until="load")
        pg.wait_for_timeout(600)
        lang = pg.evaluate("()=>document.documentElement.lang")
        home = pg.eval_on_selector("[data-i18n=home]", "e=>e.textContent")
        btns = pg.evaluate("()=>[...document.querySelectorAll('[data-lang]')].map(b=>b.textContent)")
        mark(lang == "ar" and home == "الرئيسية" and btns == ["ع", "EN"],
             "الصفحة العربية: lang=ar وتسميات عربية وزرّان (ع/EN)", f"lang={lang} · الرئيسية={home} · {btns}")

        pg.evaluate("()=>localStorage.setItem('mn-lang','en')")
        pg.reload(wait_until="load")
        pg.wait_for_timeout(600)
        lang2 = pg.evaluate("()=>document.documentElement.lang")
        home2 = pg.eval_on_selector("[data-i18n=home]", "e=>e.textContent")
        mark(lang2 == "ar" and home2 == "الرئيسية",
             "تفضيل إنجليزي محفوظ لا يغيّر لغة الصفحة العربية", f"lang={lang2} · الرئيسية={home2}")

        pg.click('[data-lang="en"]')
        pg.wait_for_url(f"**/reports/en/{a.date}.html", timeout=20000)
        pg.wait_for_timeout(600)
        lang3 = pg.evaluate("()=>document.documentElement.lang")
        dir3 = pg.evaluate("()=>document.documentElement.dir")
        home3 = pg.eval_on_selector("[data-i18n=home]", "e=>e.textContent")
        mark(lang3 == "en" and dir3 == "ltr" and home3 == "Home",
             "زر EN ينقل إلى النسخة الإنجليزية بلغتها واتجاهها", f"lang={lang3} dir={dir3} Home={home3}")

        pg.click('[data-lang="ar"]')
        pg.wait_for_url(f"**/reports/{a.date}.html", timeout=20000)
        pg.wait_for_timeout(600)
        lang4 = pg.evaluate("()=>document.documentElement.lang")
        home4 = pg.eval_on_selector("[data-i18n=home]", "e=>e.textContent")
        mark(lang4 == "ar" and home4 == "الرئيسية",
             "زر ع يعيد إلى الصفحة العربية بلغتها", f"lang={lang4} · الرئيسية={home4}")

        mark(not errs, "لا أخطاء JavaScript في أي مرحلة", str(errs[:2]) if errs else "")
        b.close()

    if fails:
        print("   ✘ النتيجة: مخالف — " + " · ".join(fails))
        return 1
    print("   ✔ النتيجة: زرّا اللغة يعملان على الموقع المنشور في الحالات الخمس")
    return 0


if __name__ == "__main__":
    sys.exit(main())
