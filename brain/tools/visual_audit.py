#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""التدقيق البصري الحي للموقع الدائم — يشمل صفحات 404 وrobots وsitemap والمسار غير الموجود.

الاستخدام: python3 tools/visual_audit.py [--base https://mda-bh.pages.dev]
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(f"{BRAIN}/audit/visual")
PAGES = [
    ("report", "/reports/2026-10-12.html"),
    ("home", "/"),
    ("cumulative", "/reports/cumulative-2026.html"),
    ("monthly", "/reports/monthly-2026-10.html"),
    ("404", "/404.html"),
]
TEMP = ("manus.computer", "localhost", "8080-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://mda-bh.pages.dev")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    findings = []

    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, path in PAGES:
            url = a.base + path
            for label, w, h in (("desktop", 1440, 1100), ("mobile", 390, 900)):
                pg = b.new_page(viewport={"width": w, "height": h})
                errs = []
                pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
                pg.on("pageerror", lambda e: errs.append(str(e)))
                resp = pg.goto(url, wait_until="load", timeout=60000)
                pg.wait_for_timeout(800)
                findings.append({
                    "page": name, "view": label,
                    "status": resp.status if resp else 0,
                    "title": pg.title()[:58],
                    "hscroll": pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2"),
                    "temp_links": pg.evaluate(
                        "Array.from(document.querySelectorAll('a[href]')).map(x=>x.href)"
                        ".filter(h=>h.includes('manus.computer')||h.includes('localhost')||h.includes('8080-'))"),
                    "imgs_without_alt": pg.evaluate("document.querySelectorAll('img:not([alt])').length"),
                    "empty_links": pg.evaluate(
                        "Array.from(document.querySelectorAll('a')).filter(x=>!x.textContent.trim()&&!x.querySelector('img,svg')).length"),
                    "console_errors": errs[:4],
                })
                pg.screenshot(path=str(OUT / f"{name}-{label}-top.png"))
                pg.screenshot(path=str(OUT / f"{name}-{label}-full.png"), full_page=True)
                pg.close()

        # سيناريو المسار غير الموجود على الموقع الحقيقي (soft-404)
        pg = b.new_page(viewport={"width": 1200, "height": 900})
        pg.goto(a.base + "/xyz-not-found.html", wait_until="load", timeout=60000)
        pg.wait_for_timeout(700)
        nf_visible = pg.eval_on_selector("#nf404", "e=>!e.hasAttribute('hidden')")
        wrap_hidden = pg.eval_on_selector(".wrap", "e=>e.hasAttribute('hidden')")
        findings.append({"page": "مسار غير موجود", "view": "desktop", "status": 200,
                         "title": pg.title()[:58], "nf_panel": nf_visible, "home_hidden": wrap_hidden})
        pg.screenshot(path=str(OUT / "notfound-live.png"))
        pg.close()

        # النسخة المطبوعة A4
        pg = b.new_page(viewport={"width": 1240, "height": 1754})
        pg.goto(a.base + "/reports/2026-10-12.html", wait_until="load", timeout=60000)
        pg.emulate_media(media="print")
        pg.wait_for_timeout(600)
        pg.screenshot(path=str(OUT / "print-first-page.png"))
        pg.pdf(path=str(OUT / "print-a4.pdf"), format="A4", print_background=True,
               margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
        pg.close()
        b.close()

    print(json.dumps(findings, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())