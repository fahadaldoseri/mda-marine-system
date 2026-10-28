#!/usr/bin/env python3
"""اختبار سلبي/إيجابي لدالة violating_pages — يفصل الفهرس والملحق عن متن التقرير."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_additions_surface import violating_pages  # noqa: E402

B = "\u202b"   # محرف اتجاه يظهر في pdftotext
M = "\u064e"   # تشكيل

INDEX = f"الفهرس {B}التوجيهات التشغيلية{B} {B}الوقائع الجديدة{B} {B}الخلفية{B} {B}التحذيرات والنشرات الرسمية{B}"
BODY = f"{B}بطاقة القرار{B} متن التقرير بلا أقسام منقولة"
ANNEX = f"{B}إضافات{B} {B}الوقائع الجديدة{B} تفصيل الوقائع {B}الخلفية{B} سياق الخلفية"

cases = [
    ("فهرس + متن نظيف + ملحق يحوي العناوين → يجتاز", [INDEX, BODY, ANNEX], {}),
    ("عنوان منقول كسطر مستقل في متن التقرير → يُمنع",
     [INDEX, f"{B}بطاقة القرار{B}\n{B}الوقائع الجديدة{B}\nنصّ", ANNEX], {"الوقائع الجديدة": [2]}),
    ("عنوان منقول في الفهرس وحده → يجتاز", [INDEX, BODY], {}),
    ("عنوان بتشكيل مختلف في المتن → يُمنع",
     [INDEX, f"{B}بطاقة القرار{B}\n{B}الوقا{M}ئع الجديدة{B}", ANNEX], {"الوقائع الجديدة": [2]}),
    ("ذِكر العنوان داخل جملة لا يُعدّ عنوانًا → يجتاز",
     [INDEX, f"{B}بطاقة القرار{B}\nما تغير منذ التقرير السابق في الفقرة", ANNEX], {}),
]

ok = True
for name, pages, expected in cases:
    got = violating_pages("\f".join(pages), ["التوجيهات التشغيلية", "الوقائع الجديدة", "الخلفية", "التحذيرات والنشرات الرسمية"])
    good = got == expected
    ok &= good
    print(f"  {'✔' if good else '✘'} {name} → {got}")

print("  الحصيلة:", "كل الاختبارات نجحت ✔" if ok else "فشل ✘")
sys.exit(0 if ok else 2)
