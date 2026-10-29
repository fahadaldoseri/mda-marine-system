#!/usr/bin/env python3
"""يعيد إنتاج خلل أمانة المحتوى في نسخة اختبارية: يستبدل بطاقات بيانات القسم ببطاقات مصدر."""
import pathlib, sys
p = pathlib.Path(sys.argv[1]); sec = sys.argv[2]
h = p.read_text(encoding="utf-8")
i = h.find(sec); j = h.find("</section>", i)
if i < 0 or j < 0:
    print("   تعذّر تحديد القسم:", sec); sys.exit(2)
win = h[i:j]
win2 = win.replace('class="dg"', 'class="src s-none"')
if win2 == win:
    win2 = win + '<div class="src s-none"><b>حقن اختباري</b></div>'
p.write_text(h[:i] + win2 + h[j:], encoding="utf-8")
print("   ✓ حُقن الخلل في نسخة مؤقتة")
