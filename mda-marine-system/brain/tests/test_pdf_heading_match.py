#!/usr/bin/env python3
"""اختبار مطابقة عناوين الأقسام في نص PDF المستخرج: يجب أن تصمد أمام قلب «لا» إلى «ال» الذي ينتجه pdftotext
مع الحروف المتصلة (يختلف بحسب إصدار poppler والخط)، فلا تفشل البوابة في بيئة وتنجح في أخرى.
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("cpf", Path(__file__).resolve().parent.parent / "validators" / "check_pdf_format.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

cases = [
    ("الحركة الملاحية والتكدس", "قبلالحركةالمالحيةوالتكدسبعد", True),   # «لا» قُلبت إلى «ال» في الاستخراج
    ("الخلاصة", "قبلالخالصةبعد", True),
    ("الخلاصة", "قبلالخلاصةبعد", True),                                # استخراج سليم
    ("التوجيهات التشغيلية", "قبلالتوجيهاتالتشغيليةبعد", True),
    ("الوقائع الجديدة", "نصآخرتماما", False),                           # غائب فعلًا يجب أن يبقى غائبًا
    ("مستوى التهديد", "مستوىالحمايةفقط", False),
]
fail = 0
fn = getattr(m, "heading_present", None)
if fn is None:
    print("✘ الدالة heading_present غير موجودة")
    sys.exit(1)
for head, flat, want in cases:
    got = fn(head, flat)
    print(("  ✔" if got == want else "  ✘"), head, "←", flat, f"(المتوقع {want})")
    fail += got != want
print(f"\nالحصيلة: {len(cases) - fail} من {len(cases)}")
sys.exit(1 if fail else 0)
