#!/usr/bin/env python3
"""تدقيق المحاذاة في وسائط الطباعة يتجاهل العناصر المحجوبة في الطباعة (no-print: display:none) ولا يتجاهل المرئي المخالف.
(طبقة الشاشة بصنف no-print كانت تُحسب كتلًا غير مصفّرة وهي لا تُطبع أصلًا.)
الاستعمال: python3 tests/test_print_alignment_hidden.py   (يحتاج Chromium الخاص بـ Playwright)"""
import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cpq", HERE / "validators" / "check_print_quality.py")
cpq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpq)

TXT = "نص طويل بما يكفي ليتجاوز الحد الأدنى من الأحرف المباشرة داخل العنصر نفسه "
html = f"""<!doctype html><meta charset=utf-8><style>
@media print{{.no-print{{display:none !important}} p{{text-align:justify}} p.bad{{text-align:right}}}}
</style><body dir=rtl>
<div class="no-print"><p class="hidden-bad" style="text-align:right">{TXT}</p></div>
<p>{TXT}</p>
<p class="bad">{TXT}</p></body>"""
p = Path(tempfile.mkdtemp()) / "t.html"
p.write_text(html, encoding="utf-8")
bad = cpq.alignment_report(p)
cls = sorted(b["cls"] for b in bad)
f = 0
for ok, n in ((cls == ["bad"], f"يُرصد المرئي المخالف فقط (الفعلي: {cls})"),):
    print(("  ✔ " if ok else "  ✘ ") + n)
    f += not ok
sys.exit(1 if f else 0)
