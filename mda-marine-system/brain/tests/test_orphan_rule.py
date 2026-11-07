#!/usr/bin/env python3
"""ك-148: اختبار وحدة لقاعدة العنوان اليتيم على صفحة نصية، بعد أن عجز بناء تجريبي عن إنتاج عنوان يتيم حقيقي."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cpf", ROOT / 'validators/check_pdf_format.py')
cpf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpf)

HEAD = "مستوى التهديد"
pages = [
    # صفحة سليمة: العنوان يتبعه مضمون
    f"{HEAD}\nالتفاصيل هنا\nمتن طويل",
    # صفحة معيبة: آخر سطر عنوان وحده
    "متن سابق\nخط تحتها\n" + HEAD,
    # صفحة معيبة ثانية: عنوان ثم تذييل يجب تجاهله
    "متن\n" + HEAD + "\nصفحة 3\nمركز الوعي بالمجال البحري",
    # صفحة سليمة: آخر سطر متن عادي
    "متن أكثر",
]
bad = cpf.orphan_titles(pages, {HEAD})
assert bad == [(2, HEAD), (3, HEAD)], f"القاعدة لم تكتشف العنوان اليتيم كما يجب: {bad}"
print(f"  · اكتُشف {len(bad)} عنوانًا يتيمًا في الصفحتين 2 و3 · وتُجوهلت صفحتان سليمتان")