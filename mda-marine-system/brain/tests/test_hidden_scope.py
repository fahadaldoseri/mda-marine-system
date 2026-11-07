#!/usr/bin/env python3
"""اختبار دائم لنطاق فحص الحجب في بوابة المخرج 6 (qa_gates.gate_hidden).

السبب (عطل 2026-10-28): القياس القديم كان يعدّ سطر الفهرس (‏«.10 الوقائع الجديدة ص 6»)
وإحالة داخل جملة في المتن إظهارًا للقسم، فأوقف تسليمًا سليمًا. القاعدة المعتمدة الآن:

  1) يُقاس المتن وحده — الملحق (المجموعة المنقولة) هو الموضع المعتمد للأقسام المنقولة.
  2) سطر الفهرس (يحمل «ص» ورقم صفحة) أو سطر بنقاط قيادة ليس إظهارًا لقسم.
  3) يُعدّ القسم ظاهرًا فقط إذا جاء عنوانًا قائمًا بذاته في المتن.

الاختبار سلبي/إيجابي: يثبت أن التضييق لا يُضعف الحارس — عنوان قائم في المتن ما زال يمنع.

الاستعمال: python3 tests/test_hidden_scope.py
"""
import importlib.util
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("qa_gates", B / "tools" / "qa_gates.py")
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)

fails = 0


def ok(cond, name):
    global fails
    print(("  ✔ " if cond else "  ✘ ") + name)
    fails += not cond


T = "الوقائع الجديدة"

# 1) سطر فهرس — ليس إظهارًا
ok(not qa._heading_shown(".10 الوقائع الجديدة ص 6", T), "سطر الفهرس لا يُعدّ إظهارًا للقسم")
ok(not qa._heading_shown("الوقائع الجديدة ......... 6", T), "سطر بنقاط قيادة لا يُعدّ إظهارًا")

# 2) إحالة داخل جملة — ليست إظهارًا
ok(not qa._heading_shown("مع نقص في الوقائع الجديدة المسجلة خلال الفترة", T),
   "الإحالة داخل جملة لا تُعدّ إظهارًا")

# 3) عنوان قائم بذاته في المتن — إظهار مانع
ok(qa._heading_shown("الوقائع الجديدة\nبند أول", T), "العنوان القائم بذاته في المتن يمنع")
ok(qa._heading_shown("  الوقائع الجديدة  ", T), "العنوان المفرد في سطر يمنع")

# 4) الملحق خارج نطاق القياس
txt = "متن التقرير\n" + qa.APPENDIX_MARKERS[0] + "\nالوقائع الجديدة\n"
ok(not qa._heading_shown(qa._body_before_appendix(txt), T),
   "ما بعد الملحق لا يُحسب إظهارًا للقسم في المتن")

# 5) الملف الحقيقي: القياس الحيّ على PDF اليوم
if (B / ".." / "seawatch" / "dist" / "reports" / "pdf").is_dir():
    from datetime import datetime, timezone
    d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pdf = B / ".." / "seawatch" / "dist" / "reports" / "pdf" / f"{d}.pdf"
    if pdf.is_file():
        res = qa.gate_hidden(d)
        ok(bool(res[0]), f"القياس الحيّ على PDF {d}: {res[1]}")
    else:
        print(f"  · لا PDF لليوم ({pdf.name}) — تُخطّى القياس الحيّة")

print("─" * 40)
print(f"النتيجة: {'نجاح' if not fails else 'فشل'} · فشل: {fails}")
sys.exit(1 if fails else 0)