#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار موجب وسالب لبوابة سجل الأحداث الحي وسطح الأقسام المنقولة."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validators.check_daily_event_surface import validate_documents  # noqa: E402


POLICY = {
    "required_in_additions": [
        "سجل IMO والحوادث المؤكدة",
        "حالة المصادر والإفصاح",
        "الاحتمالات ونسبة الحوادث إلى جهات",
        "التحذيرات والنشرات الرسمية",
        "المراقبة المستمرة",
    ],
    "required_in_report": ["سجل الأحداث", "مؤشرات الموقف", "مستوى التهديد"],
}


def report_html(count: int = 2, *, second_branch: str = "") -> str:
    cards = []
    for i in range(1, count + 1):
        code = f"MN-TEST-{i:02d}"
        branch = second_branch if i == 2 else ""
        cards.append(
            f'<article class="ev reveal b-official" data-event-code="{code}" '
            f'data-event-date="2026-10-31"><p>وصف {i}</p>{branch}</article>'
        )
    return (
        '<html><body><main>'
        '<section><h2>سجل الأحداث</h2>'
        f'<div class="ev-grid" data-count="{count}" data-source-count="{count}" '
        f'data-relation-count="{1 if second_branch else 0}" data-branch-count="{1 if second_branch else 0}" '
        f'data-unresolved-branch-count="0">{"".join(cards)}</div></section>'
        '<section><h2>مؤشرات الموقف</h2><p>محتوى</p></section>'
        '<section><h2>مستوى التهديد</h2><p>محتوى</p></section>'
        '</main></body></html>'
    )


def additions_html() -> str:
    return (
        '<html><body><main>'
        '<section><h2>سجل IMO والحوادث المؤكدة</h2><p>محتوى IMO كامل.</p></section>'
        '<section><h2>حالة المصادر والإفصاح</h2><p>محتوى المصادر كامل.</p></section>'
        '<section><h2>الاحتمالات ونسبة الحوادث إلى جهات</h2><p>محتوى الاحتمالات كامل.</p></section>'
        '<section><h2>التحذيرات والنشرات الرسمية</h2><p>محتوى التحذيرات كامل.</p></section>'
        '<section><h2>المراقبة المستمرة</h2><p>محتوى المراقبة كامل.</p></section>'
        '</main></body></html>'
    )


class DailyEventSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.daily = [
            {"code": "MN-TEST-01", "date": "2026-10-31", "title": "وصف 1"},
            {"code": "MN-TEST-02", "date": "2026-10-31", "title": "وصف 2"},
        ]
        self.site = Path(tempfile.mkdtemp())

    def test_positive_all_daily_events_and_moved_sections(self):
        errors = validate_documents(
            daily=self.daily, report=report_html(), additions=additions_html(),
            site=self.site, policy=POLICY,
        )
        self.assertEqual(errors, [])

    def test_positive_split_imo_heading_is_read_from_additions(self):
        additions = additions_html().replace(
            "<h2>سجل IMO والحوادث المؤكدة</h2>",
            '<h2>سجل <span class="ltr">IMO</span> والحوادث المؤكدة</h2>',
            1,
        )
        errors = validate_documents(
            daily=self.daily, report=report_html(), additions=additions,
            site=self.site, policy=POLICY,
        )
        self.assertEqual(errors, [])

    def test_negative_event_count_drift_fails_closed(self):
        errors = validate_documents(
            daily=self.daily, report=report_html(count=1), additions=additions_html(),
            site=self.site, policy=POLICY,
        )
        self.assertTrue(any("عدد بطاقات" in error or "عداد مصدر" in error for error in errors), errors)

    def test_negative_marked_update_without_branch_fails_closed(self):
        daily = list(self.daily)
        daily[1] = {**daily[1], "event_kind": "update"}
        errors = validate_documents(
            daily=daily, report=report_html(), additions=additions_html(),
            site=self.site, policy=POLICY,
        )
        self.assertTrue(any("فرعه السابق" in error or "مرجع حاكم" in error for error in errors), errors)

    def test_negative_imo_after_event_in_additions_fails_closed(self):
        bad = additions_html().replace(
            '<section><h2>سجل IMO والحوادث المؤكدة</h2>',
            '<section><h2>سجل الأحداث</h2><p>حدث.</p></section><section><h2>سجل IMO والحوادث المؤكدة</h2>',
            1,
        )
        errors = validate_documents(
            daily=self.daily, report=report_html(), additions=bad,
            site=self.site, policy=POLICY,
        )
        self.assertTrue(any("ترتيب الإضافات" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
