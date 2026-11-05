#!/usr/bin/env python3
"""اختبار انحدار (موجب/سالب) لنطاق كاشف التكرار النصّي في tools/live_dom_audit.py.

الحالة الموجبة: نصّ إنشائي (p) مكرّر مرتين ⇒ يجب أن يُكتشف.
الحالة السالبة: بطاقتا واقعتين تحملان حقل درجة الموثوقية نفسه (span بسمة data-reliability)
⇒ بيانات لا محتوى، فلا تُحتسب تكرارًا.

الرمز: 0 = اجتياز · 2 = فشل (يُسقط خطوة التحقق الحي).
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:  # فشل مغلق: غياب المتصفح يمنع الاختبار
    print(f"✘ تعذّر استيراد Playwright: {exc}", file=sys.stderr)
    sys.exit(2)


def load_js() -> str:
    spec = importlib.util.spec_from_file_location("live_dom_audit", ROOT / "tools/live_dom_audit.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.JS


PROSE = "هذا نصّ إنشائي طويل بما يكفي لتجاوز عتبة الستين محرفًا في كاشف التكرار النصّي."

RELIABILITY = ("درجة الموثوقية: منخفضة — تقرير مهني متخصص، ودرجة الإثبات على مستوى المصدر "
               "لا على مستوى وثيقة رسمية")

POSITIVE_HTML = f"""<!doctype html><html lang="ar" dir="rtl"><body>
<div class="ev-card"><p class="ev-what">{PROSE}</p></div>
<div class="ev-card"><p class="ev-what">{PROSE}</p></div>
</body></html>"""

NEGATIVE_HTML = f"""<!doctype html><html lang="ar" dir="rtl"><body>
<div class="ev-card" data-event-code="MN-2026-11-05-03"><div class="ev-top">
<span class="ev-idx bidi">03</span>
<span class="ev-code ltr">MN-2026-11-05-03</span>
<span class="ev-badge" data-row="2" data-classification="تقرير مهني">تقرير مهني</span>
<span class="ev-reliability" data-row="3" data-reliability="منخفضة">{RELIABILITY}</span></div></div>
<div class="ev-card" data-event-code="MN-2026-11-05-05"><div class="ev-top">
<span class="ev-idx bidi">05</span>
<span class="ev-code ltr">MN-2026-11-05-05</span>
<span class="ev-badge" data-row="2" data-classification="تقرير مهني">تقرير مهني</span>
<span class="ev-reliability" data-row="3" data-reliability="منخفضة">{RELIABILITY}</span></div></div>
</body></html>"""


def run_case(page, html: str) -> int:
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "case.html"
        f.write_text(html, encoding="utf-8")
        page.goto(f.as_uri(), wait_until="load", timeout=60000)
        page.wait_for_timeout(200)
        data = page.evaluate(load_js(), {"minTouch": 44})
        return int(data["counts"]["dup"])


def main() -> int:
    js_needed = load_js()
    del js_needed
    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        pos = run_case(page, POSITIVE_HTML)
        neg = run_case(page, NEGATIVE_HTML)
        ctx.close()
        browser.close()

    print(f"   موجب: نصّ إنشائي مكرّر ⇒ تكرار مقيس = {pos} (المطلوب ≥ 1)")
    print(f"   سالب: حقل بطاقة مكرّر بين واقعتين ⇒ تكرار مقيس = {neg} (المطلوب = 0)")
    if pos < 1:
        failures.append("الحالة الموجبة لم تُكتشف: كاشف التكرار فقد حساسيته للنصّ الإنشائي")
    if neg != 0:
        failures.append("الحالة السالبة فُقدت: حقول البطاقات القيمية تُحتسب تكرارًا نصيًّا")

    if failures:
        for f in failures:
            print(f"   ✘ {f}")
        print("   النتيجة: فشل")
        return 2
    print("   ✔ النتيجة: اجتاز (النطاق مضبوط: بيانات البطاقات ليست محتوى مكرّرًا)")
    return 0


if __name__ == "__main__":
    sys.exit(main())