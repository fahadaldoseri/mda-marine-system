#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار: رسالة الترجمة الناقصة لا تقص القائمة إلى أول 15 بندًا."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
from build_report_en import missing_translation_error  # noqa: E402


def test_missing_translation_error_lists_every_unique_unit() -> None:
    missing = [
        "لا واقعة مؤهلة.",
        "لا واقعة مؤكدة، والبلاغ المهني وحده لا يكفي.",
        *[f"نص عربي ناقص رقم {i:02d}." for i in range(3, 18)],
        "لا واقعة مؤهلة.",
    ]
    message = missing_translation_error("2026-11-06.html", missing)
    lines = message.splitlines()
    bullets = [line for line in lines if line.startswith("  - ")]
    assert len(bullets) == 17, bullets
    assert len(set(bullets)) == 17, bullets
    assert "  - لا واقعة مؤهلة." in bullets
    assert "  - لا واقعة مؤكدة، والبلاغ المهني وحده لا يكفي." in bullets
    assert "  - نص عربي ناقص رقم 17." in bullets


if __name__ == "__main__":
    test_missing_translation_error_lists_every_unique_unit()
    print("missing translation batch regression: PASS")
