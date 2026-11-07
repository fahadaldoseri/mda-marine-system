#!/usr/bin/env python3
"""حاجز G001: لا يعيد مولّد الكتل ألفاظًا ممنوعة إلى سطح القارئ."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import blocks  # noqa: E402

OLD = "الجهة القادرة على الحسم"
NEW = "الجهة التي تستطيع التأكيد"


def main() -> int:
    rendered = blocks.gaps_table(
        [{"gap": "فجوة اختبار", "owner": OLD, "impact": "أثر اختبار"}],
        lambda value: str(value),
    )
    failures: list[str] = []
    if OLD in rendered:
        failures.append(f"اللفظ القديم تسرب إلى المخرج: {OLD}")
    if NEW not in rendered:
        failures.append(f"البديل الحاكم غائب من المخرج: {NEW}")
    if failures:
        for failure in failures:
            print(f"  ✘ {failure}")
        print("الحصيلة: RED — حاجز ألفاظ المولد فشل")
        return 1
    print("  ✔ حقن اللفظ القديم يُستبدل بالبديل الحاكم")
    print("  ✔ رأس كتلة الإضافات يستخدم البديل الحاكم")
    print("الحصيلة: GREEN — لا لفظ ممنوع في مخرج كتلة الإضافات")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
