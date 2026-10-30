#!/usr/bin/env python3
"""مزامنة أعداد المصادر في قسم البنية من السجل الحاكم.

الافتراضي قراءة وقياس فقط؛ لا تُكتب الملفات إلا مع ``--write``.
يستمد العدد المعتمد من ``appendices/sources-manifest.json``، ويستمد توزيع
المسارات من ``tools/source_channels.py``، ثم يستبدل المحتوى بين علامتي الإدراج
في ``sections/30-structure.md`` دون إعادة تنسيق بقية الملف.

الاستخدام:
  python3 tools/sources_count_sync.py          # قياس/تحقق بلا كتابة
  python3 tools/sources_count_sync.py --write  # تحديث الكتل المعلّمة فقط
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "appendices" / "sources-manifest.json"
TARGET = ROOT / "sections" / "30-structure.md"
START = "<!-- AUTO-SOURCES-COUNT:START -->"
END = "<!-- AUTO-SOURCES-COUNT:END -->"
MARKED = re.compile(re.escape(START) + r".*?" + re.escape(END))


def load_approved_count() -> int:
    """اقرأ العدد من المانيفست وتحقق من قائمة السجلات المرتبطة به."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    approved = int(manifest["approved_source_count"])
    if approved <= 0:
        raise ValueError("approved_source_count يجب أن يكون موجبًا")
    source_list_json = manifest.get("source_list_json")
    if not source_list_json:
        raise ValueError("source_list_json مفقود من المانيفست")
    records = json.loads((ROOT / source_list_json).read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != approved:
        raise ValueError(
            f"عدد سجلات {source_list_json} لا يطابق المعتمد {approved}"
        )
    return approved


def channel_counts() -> tuple[int, int, int, int]:
    """أعد (المعتمد، الآلي، اليدوي، البديل) بعد مطابقة القنوات للمانيفست."""
    sys.path.insert(0, str(ROOT / "tools"))
    import source_channels  # noqa: WPS433

    approved = load_approved_count()
    channels = source_channels.channels()
    auto = len(channels["rss"])
    manual = len(channels["browser"])
    proxy = len(channels["proxy"])
    all_numbers = channels["rss"] | channels["browser"] | channels["proxy"]
    if len(all_numbers) != approved:
        raise ValueError(
            f"توزيع القنوات {len(all_numbers)} لا يساوي المعتمد {approved}"
        )
    if auto + manual + proxy != approved:
        raise ValueError(
            f"مجموع القنوات {auto + manual + proxy} لا يساوي المعتمد {approved}"
        )
    return approved, auto, manual, proxy


def expected_text() -> str:
    """كوّن نص الخلية من القيم المقروءة، لا من رقم ثابت."""
    approved, auto, manual, proxy = channel_counts()
    parts = [f"{auto} بالمسار الآلي", f"{manual} بالمرجعية اليدوية"]
    if proxy:
        parts.append(f"{proxy} بمسار رسمي بديل")
    return f"{approved} مصدرًا بحالة كل مصدر ({' · '.join(parts)})"


def replace_marked(text: str, generated: str) -> tuple[str, int]:
    """استبدل محتوى الكتل المعلّمة فقط، مع رفض العلامات الناقصة أو المكررة."""
    matches = list(MARKED.finditer(text))
    if not matches:
        raise ValueError("لا توجد كتلة AUTO-SOURCES-COUNT معلّمة")
    replacement = f"{START}{generated}{END}"
    updated = MARKED.sub(replacement, text)
    return updated, len(matches)


def current_marked(text: str) -> list[str]:
    return [m.group(0) for m in MARKED.finditer(text)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="قياس/مزامنة عدد المصادر من sources-manifest.json؛ --write هو خيار الكتابة الوحيد."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="اكتب النص المولّد بين علامات الإدراج في sections/30-structure.md",
    )
    args = parser.parse_args()

    generated = expected_text()
    original = TARGET.read_text(encoding="utf-8")
    updated, blocks = replace_marked(original, generated)
    current = current_marked(original)
    expected_block = f"{START}{generated}{END}"
    in_sync = all(block == expected_block for block in current)

    print(f"السجل الحاكم: {MANIFEST}")
    print(f"النص المتوقع: {generated}")
    print(f"الكتل المعلّمة: {blocks}")
    print(f"الحالة قبل الكتابة: {'مطابق' if in_sync else 'منحرف'}")

    if args.write:
        if original != updated:
            TARGET.write_text(updated, encoding="utf-8")
            print(f"كُتبت الكتل المعلّمة فقط: {TARGET}")
        else:
            print("لا تغيير: الكتل المعلّمة مطابقة")
        return 0

    if not in_sync:
        print("النتيجة: انحراف — أعد التشغيل مع --write للتحديث الصريح")
        return 2
    print("النتيجة: مطابق — وضع القراءة فقط لم يكتب أي ملف")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "validators"))
    from _guard import run

    run(main)
