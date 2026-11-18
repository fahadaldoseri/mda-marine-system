#!/usr/bin/env python3
"""حارس دائم: فصل موثوقية المصدر عن درجة الثقة التحليلية، ومرساة الدليل العميقة.

الموجب: صفحة الإصدار المبنية يجب أن تحمل وسمين منفصلين بخصيصتي بيانات مستقلتين،
        وأن يحمل كل رابط دليل مقطع مرساة (‎#‎) لا مجرد جذر مصدر عام.
السالب: صيغة مدموجة («درجة الموثوقية») أو رابط بلا مرساة يجب أن يُرفضا.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

REL_SRC = 'data-source-reliability='
REL_CONF = 'data-analytic-confidence='
CONFLATED = 'درجة الموثوقية'
EV_LINK = re.compile(r'<a class="ev-link" href="([^"]+)"')


def check(html: str) -> list[str]:
    errs: list[str] = []
    if REL_SRC not in html:
        errs.append("لا وسم لموثوقية المصدر (data-source-reliability)")
    if REL_CONF not in html:
        errs.append("لا وسم لدرجة الثقة التحليلية (data-analytic-confidence)")
    if CONFLATED in html:
        errs.append("صيغة مدموجة «درجة الموثوقية» تخلط موثوقية المصدر بالثقة التحليلية")
    links = EV_LINK.findall(html)
    if not links:
        errs.append("لا روابط دليل (ev-link) في الصفحة")
    for m in EV_LINK.finditer(html):
        h = m.group(1)
        # بطاقة «لا واقعة» (رمز NI-) دليلها حالة القائمة الرسمية نفسها، ولا عنصر فيها
        # يُرسى عليه؛ فلا تُطالب بمرساة. كل بطاقة واقعة غيرها تبقى مطالبة بها.
        art = html.rfind("<article", 0, m.start())
        code = re.search(r'data-event-code="([^"]*)"', html[art:m.start()]) if art >= 0 else None
        if code and code.group(1).startswith("NI-"):
            continue
        if "#" not in h or h.rstrip().endswith("#"):
            errs.append(f"رابط دليل بلا مرساة عميقة: {h[:80]}")
    return errs


def main() -> int:
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        page = pathlib.Path(sys.argv[1])
    else:
        local = pathlib.Path(__file__).resolve().parents[1]
        if local.name == 'brain':
            local = local.parent / 'site'
        site = pathlib.Path(os.environ.get('SITE_DIR') or os.environ.get('SITE') or local)
        cands = sorted(p for p in (site / 'dist' / 'reports').glob('20*.html')
                       if p.is_file())
        if not cands:
            print(f"لا صفحة إصدار مبنية في {site}/dist/reports")
            return 2
        page = cands[-1]
    if not page.exists():
        print(f"مفقود: {page}")
        return 2
    html = page.read_text(encoding='utf-8', errors='ignore')
    errs = check(html)
    print(f"   الصفحة: {page}")
    print(f"   موثوقية المصدر: {html.count(REL_SRC)} · الثقة التحليلية: {html.count(REL_CONF)} · روابط الدليل: {len(EV_LINK.findall(html))}")
    if errs:
        for e in errs:
            print("   ✘", e)
        return 1
    print("   ✔ فصل الوسمين قائم وكل روابط الدليل تحمل مرساة عميقة")
    neg = '<span class="ev-reliability">درجة الموثوقية: منخفضة</span><a class="ev-link" href="https://example.org/page">س</a>'
    neg_errs = check(neg)
    if len(neg_errs) < 3:
        print("   ✘ الحالة السالبة لم تُرفض كما يجب:", neg_errs)
        return 1
    print(f"   ✔ الحالة السالبة رُفضت بثلاثة أسباب ({len(neg_errs)})")
    # سالب ثانٍ: بطاقة واقعة عادية بلا مرساة تُرفض، وبطاقة NI- بلا مرساة تُقبل.
    inc = ('<span data-source-reliability="a"></span><span data-analytic-confidence="b"></span>'
           '<article class="ev" data-event-code="MN-2099-01-01-01"><a class="ev-link" href="https://example.org/page">س</a></article>')
    ni = inc.replace("MN-2099-01-01-01", "NI-2099-01-01")
    if not any("مرساة" in e for e in check(inc)) or check(ni):
        print("   ✘ إعفاء بطاقة «لا واقعة» غير محكوم:", check(inc), check(ni))
        return 1
    print("   ✔ بطاقة واقعة بلا مرساة تُرفض، وبطاقة «لا واقعة» تُقبل")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
