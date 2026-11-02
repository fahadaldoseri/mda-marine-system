#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس «هل العيب في الصفحة أم في أداة القياس؟».

يأخذ صفحة HTML (محلية أو منشورة) ورموزًا مشتبهة، ويطبع:
  · عدّ كل رمز في العرض الفعلي (document.body.innerText عبر Chromium)؛
  · عدّه في نص مستخرج بتحويل الوسوم بتعبير نمطي (strip_html) — لبيان فرق القياس.

الاستخدام:
  python3 verify_extraction.py --page dist/reports/2026-11-01.html \
      --token ") ." --token "االتقرير" --token "IMO ؛"
  python3 verify_extraction.py --url https://example.test/page.html --token " ،"

الرمز: 0 إذا طابق العدّان · 2 إذا اختلفا (عيب قياس محتمل).
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import re
import sys

INLINE = {"span", "bdi", "b", "i", "em", "strong", "a", "code", "small", "sup", "sub",
          "mark", "u", "s", "abbr", "cite", "q", "time", "kbd", "samp", "var", "font",
          "label", "big", "tt", "data", "dfn", "ins", "del", "nobr", "wbr"}
_MARK, _INLINE_MARK = "\u0001", "\u0002"
_PUNCT = "،.:؛!؟"


def strip_html(raw: str) -> str:
    """تحويل وسوم HTML إلى نص وفق قواعد العرض (نسخة مرجعية للقياس المقارن)."""
    raw = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", "", raw)
    raw = re.sub(r"(?is)<!--.*?-->", "", raw)

    def tag(m: re.Match) -> str:
        g = re.match(r"</?\s*([A-Za-z0-9]+)", m.group(0))
        name = g.group(1).lower() if g else ""
        return _INLINE_MARK if name in INLINE else _MARK

    raw = re.sub(r"(?s)<[^>]+>", tag, raw)
    raw = re.sub(r"(?<=[\w\u0621-\u064A\u0671-\u06D3])" + _INLINE_MARK + r"+(?=[\w\u0621-\u064A\u0671-\u06D3])", " ", raw)
    raw = re.sub(r"[ \t\u00a0]*(?:" + _MARK + "|" + _INLINE_MARK + r")+[ \t\u00a0]*(?=[" + re.escape(_PUNCT) + r"])", "", raw)
    raw = raw.replace(_INLINE_MARK, "")
    raw = raw.replace("\r", "")
    raw = re.sub(r"[ \t\u00a0]+\n", "\n", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.replace(_MARK, "\n")


async def rendered_text(target: str) -> str:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1440, "height": 1200})
        if target.startswith("http"):
            await pg.goto(target, wait_until="networkidle")
        else:
            await pg.goto(pathlib.Path(target).resolve().as_uri())
        txt = await pg.evaluate("document.body.innerText")
        await b.close()
    return txt or ""


def main() -> int:
    ap = argparse.ArgumentParser(description="قياس الرموز في العرض مقابل النص المستخرج")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--page", help="مسار صفحة HTML محلية")
    src.add_argument("--url", help="عنوان صفحة منشورة")
    ap.add_argument("--token", action="append", required=True, help="رمز مشتبه (يُكرّر)")
    a = ap.parse_args()

    target = a.url or a.page
    view = asyncio.run(rendered_text(target))
    if target.startswith("http"):
        import urllib.request
        raw = urllib.request.urlopen(target, timeout=60).read().decode("utf-8", "replace")
    else:
        raw = pathlib.Path(target).read_text(encoding="utf-8", errors="replace")
    extracted = strip_html(raw)

    diff = 0
    print(f"   السطح: {target}")
    for t in a.token:
        v, e = view.count(t), extracted.count(t)
        flag = "✓" if v == e else "✘ عيب قياس محتمل"
        print(f"   {flag}  «{t}»: العرض={v} · الاستخراج={e}")
        diff += 0 if v == e else 1
    print("   ── النتيجة:", "مطابق" if diff == 0 else f"اختلاف في {diff} رمزًا — راجع قواعد الاستخراج")
    return 0 if diff == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
