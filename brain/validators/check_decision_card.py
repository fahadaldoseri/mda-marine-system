#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة بطاقة القرار — تمنع إفراغ صفوف البطاقة على أي سطح قارئ (عطل ك-239).

تُشغَّل على الصفحة المبنية فعليًا بمتصفح حقيقي، لأن الإفراغ كان يحدث في المتصفح
(سكربت الروابط كان يحذف الرابط عند غياب القسم من الصفحة، فيبقى الصف فارغًا)
ولا يظهر في نص HTML المصدر.

المعايير:
1. كل صف في بطاقة القرار يحمل نصًّا فعليًّا (≥ 40 حرفًا) في خليّة القيمة.
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
            return [f"{page_path.name}: لا صفوف في بطاقة القرار (بطاقة غائبة أو فارغة)"]
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
    ap = argparse.ArgumentParser(description="فحص بطاقة القرار على السطح المبني")
    ap.add_argument("--page", help="مسار صفحة التقرير المبنية (يُستنتج من --date)")
    ap.add_argument("--additions", help="مسار صفحة إضافات المبنية (يُستنتج من --date)")
    ap.add_argument("--dist-root", default="/home/ubuntu/seawatch/dist", help="جذر dist لحلّ الروابط المطلقة")
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
        print("مانع: بطاقة القرار غير مكتملة:")
        for item in problems:
            print(f"  ✗ {item}")
        return 2
    print("بطاقة القرار: مطابقة ✓ — كل صف يحمل نصًّا ورابطًا صالحًا على السطحين")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ImportError as exc:  # pragma: no cover
        print(f"مانع: تعذّر تشغيل المتصفح: {exc}")
        raise SystemExit(2)
