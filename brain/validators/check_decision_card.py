#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة أهم الأخبار المتعلقة بالأمن البحري — تمنع إفراغ صفوف البطاقة على أي سطح قارئ (عطل ك-239).

تُشغَّل على الصفحة المبنية فعليًا بمتصفح حقيقي، لأن الإفراغ كان يحدث في المتصفح
(سكربت الروابط كان يحذف الرابط عند غياب القسم من الصفحة، فيبقى الصف فارغًا)
ولا يظهر في نص HTML المصدر.

المعايير:
1. كل صف في أهم الأخبار المتعلقة بالأمن البحري يحمل نصًّا فعليًّا (≥ 40 حرفًا) في خليّة القيمة.
2. لكل صف إمّا رابط داخلي/خارجي صالح، وإمّا نص بديل ظاهر (sc-plain) — لا خلوّ.
3. لا خلوّ في أي <p class="sc-more"> من نص.
4. كل وجهة خارجية (/additions.html#sec-NN) تشير إلى ملف موجود وقسم موجود داخله.

الخروج: 0 مطابق · 2 مانع.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

# ── جذر محمول (بوابة قابلية النقل) ──
import os as _os
from pathlib import Path as _Path
_P = _Path(__file__).resolve()
_C = [_P.parents[i] for i in range(1, min(6, len(_P.parents)))]
def _brain_root():
    e = _os.environ.get("BRAIN_DIR")
    if e and _Path(e).is_dir():
        return _Path(e)
    for r in _C:
        c = r / "brain-marine-news"
        if (c / "reports").is_dir():
            return c
    for r in _C:
        if (r / "reports").is_dir():
            return r
    return _C[0] / "brain-marine-news"
BRAIN = _brain_root()
def _site_root():
    e = _os.environ.get("SITE_DIR")
    if e and _Path(e).is_dir():
        return _Path(e)
    for r in _C:
        c = r / "seawatch"
        if (c / "generator").is_dir():
            return c
    return _C[0] / "seawatch"
SITE = _site_root()



MIN_CHARS = 40


def _check_page(page_path: pathlib.Path, dist_root: pathlib.Path, required: bool = True) -> list[str]:
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.goto(page_path.as_uri(), wait_until="load")
        page.wait_for_timeout(1200)
        rows = page.eval_on_selector_all(
            ".sc-card .sc-row",
            """els => els.map(e => {
                 const l = e.querySelector('.sc-l'), v = e.querySelector('.sc-v');
                 const a = v ? v.querySelector('a') : null;
                 const pl = v ? v.querySelector('.sc-plain') : null;
                 const more = v ? v.querySelector('.sc-more') : null;
                 return {label: l ? l.innerText.trim() : '(بلا عنوان)',
                         text: v ? v.innerText.trim() : '',
                         anchors: v ? v.querySelectorAll('a').length : 0,
                         href: a ? a.getAttribute('href') : null,
                         plain: pl ? pl.innerText.trim() : null,
                         more: more ? more.innerText.trim() : null};
               })""",
        )
        browser.close()

    if not rows:
        if required:
            return [f"{page_path.name}: لا صفوف في أهم الأخبار المتعلقة بالأمن البحري (بطاقة غائبة أو فارغة)"]
        print(f"ملاحظة: لا بطاقة قرار على {page_path.name} — يُتخطّى")
        return []

    for row in rows:
        label = row["label"]
        if len(row["text"]) < MIN_CHARS:
            problems.append(
                f"{page_path.name}: صف «{label}» نصّه {len(row['text'])} حرفًا فقط (الحد {MIN_CHARS})"
            )
        if row["anchors"] == 0 and not row["plain"]:
            problems.append(f"{page_path.name}: صف «{label}» بلا رابط وبلا نص بديل")
        if not row["more"]:
            problems.append(f"{page_path.name}: سطر العدّاد/الرابط في صف «{label}» فارغ")
        href = row["href"] or ""
        if href.startswith("/"):
            target, _, frag = href.partition("#")
            file_path = dist_root / target.lstrip("/")
            if not file_path.is_file():
                problems.append(f"{page_path.name}: وجهة الرابط {href} غير موجودة ({file_path})")
            elif frag:
                body = file_path.read_text(encoding="utf-8", errors="replace")
                if f'id="{frag}"' not in body:
                    problems.append(f"{page_path.name}: قسم {frag} غير موجود في {target}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="فحص أهم الأخبار المتعلقة بالأمن البحري على السطح المبني")
    ap.add_argument("--page", help="مسار صفحة التقرير المبنية (يُستنتج من --date)")
    ap.add_argument("--additions", help="مسار صفحة إضافات المبنية (يُستنتج من --date)")
    ap.add_argument("--dist-root", default=str(SITE / "dist"), help="جذر dist لحلّ الروابط المطلقة")
    ap.add_argument("--date", default=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%d"),
                    help="تاريخ التشغيل (افتراضيًا اليوم بتوقيت UTC)")
    args = ap.parse_args()

    if not args.page:
        args.page = str(pathlib.Path(args.dist_root) / "reports" / f"{args.date}.html")
    if not args.additions:
        args.additions = str(pathlib.Path(args.dist_root) / "additions.html")

    page_path = pathlib.Path(args.page).expanduser().resolve()
    if not page_path.is_file():
        print(f"مانع: الصفحة غير موجودة: {page_path}")
        return 2
    dist_root = pathlib.Path(args.dist_root).expanduser().resolve() if args.dist_root else page_path.parent.parent

    problems = _check_page(page_path, dist_root)
    if args.additions:
        add_path = pathlib.Path(args.additions).expanduser().resolve()
        if add_path.is_file():
            problems += _check_page(add_path, dist_root, required=False)

    if problems:
        print("مانع: أهم الأخبار المتعلقة بالأمن البحري غير مكتملة:")
        for item in problems:
            print(f"  ✗ {item}")
        return 2
    print("أهم الأخبار المتعلقة بالأمن البحري: مطابقة ✓ — كل صف يحمل نصًّا ورابطًا صالحًا على السطحين")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ولا يُبتلع.
    sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from _guard import run
    run(main)
