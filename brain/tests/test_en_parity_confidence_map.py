#!/usr/bin/env python3
"""اختبار انحدار لتماثل درجات الإسناد عبر الخريطة الحاكمة."""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_en_parity", BRAIN / "validators" / "check_en_parity.py"
)
assert SPEC and SPEC.loader
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def test_grade_description_matches_code_and_grade_digits_are_not_standalone() -> None:
    ar = BRAIN / "tests" / "_tmp_parity_ar.md"
    en = BRAIN / "tests" / "_tmp_parity_en.md"
    try:
        ar.write_text("درجة الإسناد: C/3\nالعدد المثبت: 128\n", encoding="utf-8")
        en.write_text(
            "Attribution grade: medium reliability, medium corroboration\n"
            "Confirmed count: 128\n",
            encoding="utf-8",
        )
        ar_counts = parity.counts(ar)
        en_counts = parity.counts(en)
        expected_grade = Counter({"reliability=medium|corroboration=medium": 1})
        assert ar_counts["tokens"]["درجات الثقة"] == expected_grade
        assert en_counts["tokens"]["درجات الثقة"] == expected_grade
        assert ar_counts["tokens"]["كل الأرقام"] == Counter({"128": 1})
        assert en_counts["tokens"]["كل الأرقام"] == Counter({"128": 1})
    finally:
        ar.unlink(missing_ok=True)
        en.unlink(missing_ok=True)


if __name__ == "__main__":
    test_grade_description_matches_code_and_grade_digits_are_not_standalone()
    print("confidence-grade parity regression: 1/1")
