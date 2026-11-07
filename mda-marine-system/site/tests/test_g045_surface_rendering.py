#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات انحدار لإصلاح مخرجات G045 في طبقة التوليد."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import build_report  # noqa: E402


def test_additions_grade_codes_are_rendered_as_reader_labels():
    source = "<p>UKMTO A/1 · straits.live C/3 · نقل D/4</p>"
    rendered = build_report.redact_internal_grade_codes(source)
    assert "A/1" not in rendered
    assert "C/3" not in rendered
    assert "D/4" not in rendered
    assert "موثوقية" in rendered


def test_report_surfaces_do_not_expose_c3():
    dist = ROOT / "dist" / "reports"
    pages = sorted(dist.rglob("*.html"))
    assert pages, "expected generated report pages"
    leaking = [str(path.relative_to(ROOT)) for path in pages if "C/3" in path.read_text(encoding="utf-8")]
    assert not leaking, f"internal grade code exposed in report surfaces: {leaking}"


def test_threat_section_display_is_compacted_below_gate_limit():
    source = (
        "<p>المستوى العام: مرتفع — أعلى قطاع: مضيق هرمز.</p>"
        "<table><thead><tr><th>القطاع والمستوى</th>"
        "<th>ما يبرره في كلمات قليلة</th></tr></thead><tbody>"
        "<tr><td>المستوى في مضيق هرمز: مرتفع</td><td>بلاغ رسمي مستقل</td></tr>"
        "<tr><td>المستوى في باب المندب: منخفض</td><td>لا واقعة مؤهلة داخل الفترة</td></tr>"
        "</tbody></table>"
        "<p>لماذا لم يرتفع أكثر: لا تأكيد رسمي لتضرر سفن؛ الانتقال إلى حالة حرجة يتطلب تعطيلًا كاملاً للممر.</p>"
        "<p>ما يرفعه أو يخفضه: يرفعه تأكيد رسمي؛ يخفضه نفي رسمي موثق.</p>"
    )
    compacted = build_report.compact_threat_section_html(source)
    assert "المستوى في " not in compacted
    assert "ما يبرره في كلمات قليلة" not in compacted
    assert "لماذا لم يرتفع أكثر:" not in compacted
    assert "ما يرفعه أو يخفضه:" not in compacted
    assert "لا واقعة مؤهلة داخل الفترة" not in compacted


if __name__ == "__main__":
    test_additions_grade_codes_are_rendered_as_reader_labels()
    test_threat_section_display_is_compacted_below_gate_limit()
    print("اختبارا توليد سطح G045: نجاح")
