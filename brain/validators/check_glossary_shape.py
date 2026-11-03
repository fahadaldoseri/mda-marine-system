#!/usr/bin/env python3
"""حارس شكل معجم النسخة الإنجليزية (عطل ك-491).

يمنع كتابة مفاتيح في جذر الملف بدل قاموس `entries`، لأن ذلك يُسقط الترجمة
ويُفشل البناء برسالة «نصوص عربية بلا ترجمة» بلا سبب ظاهر.
يفشل مغلقًا (رمز 2) عند أي مفتاح جذري غير معروف.
"""
from __future__ import annotations

import json
import pathlib
import sys

GLOSSARY = pathlib.Path(
    sys.argv[sys.argv.index("--file") + 1]
    if "--file" in sys.argv
    else "/home/ubuntu/seawatch/sources/i18n/en/glossary.json"
)
ALLOWED_TOP_LEVEL = {
    "_note",
    "_derived",
    "entries",
    "updated",
    "date_updated",
    "date_created",
    "legacy_surface_units_note",
}


def main() -> int:
    if not GLOSSARY.exists():
        print(f"✘ ملف المعجم غير موجود: {GLOSSARY}")
        return 2
    try:
        data = json.loads(GLOSSARY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"✘ المعجم ليس JSON صالحًا: {exc}")
        return 2
    if not isinstance(data, dict):
        print("✘ جذر المعجم ليس كائنًا (object)")
        return 2
    stray = sorted(k for k in data if k not in ALLOWED_TOP_LEVEL)
    entries = data.get("entries")
    if not isinstance(entries, dict):
        print("✘ «entries» مفقود أو ليس كائنًا — لا مكان للمدخلات")
        return 2
    # كل قيمة جذرية غير معروفة تعني مدخلًا كُتب في المكان الخطأ
    if stray:
        print(f"✘ مفاتيح في الجذر بدل entries: {len(stray)}")
        for k in stray[:5]:
            print(f"   · {k[:70]}")
        print("  الإصلاح: انقل المدخل إلى entries وأعد البناء.")
        return 2
    print(f"✔ شكل المعجم سليم · مدخلات={len(entries)} · مفاتيح الجذر={len(data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
