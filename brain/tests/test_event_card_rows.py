#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات عقد صفوف بطاقة سجل الأحداث (اشتقاق المصدر وفشل مغلق)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validators.check_event_card_contract import (
    AR_LABELLED_ROWS,
    load_arabic_row_labels,
    load_english_row_labels,
    page_violations,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "appendices" / "event-card-contract.md"
GLOSSARY = Path("/home/ubuntu/seawatch/sources/i18n/en/glossary.json")


def _fixture_glossary(ar_labels: dict[int, str], *, omit: str | None = None) -> Path:
    entries = {
        ar_labels[number]: english
        for number, english in {
            4: "Date and time",
            5: "Location",
            6: "Source",
            7: "Official link",
            8: "Original text",
        }.items()
    }
    if ar_labels[5] == "الموضع":
        entries[ar_labels[5]] = "Position"
    entries["العلاقة"] = "Relation"
    if omit is not None:
        entries.pop(omit, None)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
    with handle:
        json.dump({"entries": entries}, handle, ensure_ascii=False)
    return Path(handle.name)


def _card_html(ar_labels: dict[int, str], *, branch_title: str | None = None) -> str:
    branch = (
        f'<div class="ev-branch" data-branch-status="shown">'
        f'<span class="ev-branch-title">{branch_title}</span>'
        '<span class="ev-mv">MN-2026-11-04-00</span></div>'
        if branch_title is not None
        else '<div data-row="9" data-branch-status="not-marked" hidden aria-hidden="true"></div>'
    )
    rows = """
    <p class="ev-what" data-row="1">واقعة اختبار</p>
    <span class="ev-badge" data-row="2" data-classification="بلاغ رسمي">بلاغ رسمي</span>
    <span class="ev-reliability" data-row="3" data-reliability="منخفضة">منخفضة</span>
    """
    rows += f'<div class="ev-field" data-row="4"><span class="ev-k">{ar_labels[4]}</span><span class="ev-mv">2026-11-04</span></div>'
    rows += f'<div class="ev-field" data-row="5"><span class="ev-k">{ar_labels[5]}</span><span class="ev-mv">Z1 · مضيق هرمز</span></div>'
    rows += f'<div class="ev-field" data-row="6"><span class="ev-k">{ar_labels[6]}</span><span class="ev-mv"><a class="ev-link" href="https://example.com/source">جهة رسمية</a></span></div>'
    rows += f'<div class="ev-field" data-row="7"><span class="ev-k">{ar_labels[7]}</span><span class="ev-mv"><a href="https://example.com/official">وثيقة</a></span></div>'
    rows += f'<div class="ev-field" data-row="8"><span class="ev-k">{ar_labels[8]}</span><span class="ev-mv">مطويّ — افتح للعرض</span><details class="ev-fold" data-fold="original-text"><summary>النص الأصلي كما في المصدر</summary><span>Raw text</span></details></div>'
    return f'''
    <article class="ev" data-event-code="MN-2026-11-04-01" data-event-rows="9"
             data-classification="بلاغ رسمي" data-reliability="منخفضة">
      {rows}{branch}
    </article>
    '''


def _english_card_html(ar_labels: dict[int, str], en_labels: dict[int, str]) -> str:
    html = _card_html(ar_labels)
    for number in AR_LABELLED_ROWS:
        html = html.replace(f">{ar_labels[number]}</span>", f">{en_labels[number]}</span>", 1)
    return html


class EventCardRowsTest(unittest.TestCase):
    def test_sound_arabic_and_english_cards_use_source_labels(self) -> None:
        ar_labels = load_arabic_row_labels(CONTRACT)
        glossary = _fixture_glossary(ar_labels)
        try:
            en_labels = load_english_row_labels(glossary, ar_labels, required_rows=AR_LABELLED_ROWS)
            ar_errors, _ = page_violations(_card_html(ar_labels), "العربية", ar_labels)
            en_errors, _ = page_violations(
                _english_card_html(ar_labels, en_labels), "الإنجليزية", en_labels
            )
            self.assertEqual([], ar_errors)
            self.assertEqual([], en_errors)
        finally:
            glossary.unlink()

    def test_wrong_or_missing_label_is_blocked(self) -> None:
        ar_labels = load_arabic_row_labels(CONTRACT)
        glossary = _fixture_glossary(ar_labels)
        try:
            en_labels = load_english_row_labels(glossary, ar_labels, required_rows=AR_LABELLED_ROWS)
            wrong = _english_card_html(ar_labels, en_labels).replace(
                ">Date and time</span>", ">Wrong label</span>", 1
            )
            errors, _ = page_violations(wrong, "الإنجليزية", en_labels)
            self.assertTrue(any("لا يطابق العقد" in error for error in errors), errors)

            missing = _english_card_html(ar_labels, en_labels).replace(
                '<span class="ev-k">Date and time</span>', "", 1
            )
            errors, _ = page_violations(missing, "الإنجليزية", en_labels)
            self.assertTrue(any("وسم الصف 4 مفقود" in error for error in errors), errors)
        finally:
            glossary.unlink()

    def test_missing_english_counterpart_fails_closed(self) -> None:
        ar_labels = load_arabic_row_labels(CONTRACT)
        glossary = _fixture_glossary(ar_labels, omit=ar_labels[5])
        try:
            with self.assertRaisesRegex(
                RuntimeError, "لا مقابل إنجليزي في المعجم للتسمية: الموقع"
            ):
                load_english_row_labels(glossary, ar_labels, required_rows=(5,))
        finally:
            glossary.unlink()

    def test_meaning_translation_is_blocked(self) -> None:
        ar_labels = load_arabic_row_labels(CONTRACT)
        glossary = _fixture_glossary(ar_labels)
        try:
            en_labels = load_english_row_labels(glossary, ar_labels, required_rows=AR_LABELLED_ROWS)
            translated = _english_card_html(ar_labels, en_labels).replace(
                ">Original text</span>", ">Meaning translation</span>", 1
            )
            errors, _ = page_violations(translated, "الإنجليزية", en_labels)
            self.assertTrue(any("ترجمة المعنى" in error for error in errors), errors)
        finally:
            glossary.unlink()

    def test_contract_label_change_changes_expected_label_automatically(self) -> None:
        original = CONTRACT.read_text(encoding="utf-8")
        changed = original.replace("| 5 | الموقع |", "| 5 | الموضع |", 1)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
            handle.write(changed)
            changed_contract = Path(handle.name)
        try:
            changed_labels = load_arabic_row_labels(changed_contract)
            self.assertEqual("الموضع", changed_labels[5])
            glossary = _fixture_glossary(changed_labels)
            try:
                en_labels = load_english_row_labels(
                    glossary, changed_labels, required_rows=AR_LABELLED_ROWS
                )
                errors, _ = page_violations(_card_html(changed_labels), "العربية", changed_labels)
                self.assertFalse(
                    any("لا يطابق العقد" in error for error in errors), errors
                )
                old_card_errors, _ = page_violations(
                    _card_html(changed_labels).replace("الموضع", "الموقع", 1),
                    "العربية",
                    changed_labels,
                )
                self.assertTrue(
                    any("الموضع" in error for error in old_card_errors), old_card_errors
                )
                self.assertEqual("Position", en_labels[5])
            finally:
                glossary.unlink()
        finally:
            changed_contract.unlink()

    def test_structural_rows_require_content_and_approved_state(self) -> None:
        ar_labels = load_arabic_row_labels(CONTRACT)
        empty = _card_html(ar_labels).replace(
            '<p class="ev-what" data-row="1">واقعة اختبار</p>',
            '<p class="ev-what" data-row="1"></p>',
            1,
        )
        errors, _ = page_violations(empty, "العربية", ar_labels)
        self.assertTrue(any("صف 1 بلا مضمون" in error for error in errors), errors)

        invalid_state = _card_html(ar_labels).replace(
            '<span class="ev-badge" data-row="2"',
            '<span class="ev-badge" data-row="2" data-row-state="invalid"',
            1,
        )
        errors, _ = page_violations(invalid_state, "العربية", ar_labels)
        self.assertTrue(any("صف 2 بحالة غير معروفة" in error for error in errors), errors)

    def test_synthetic_translation_fallback_is_blocked(self) -> None:
        ar_labels = load_arabic_row_labels(CONTRACT)
        page = _card_html(ar_labels) + "<p>الترجمة غير مدرجة في الدفتر</p>"
        errors, _ = page_violations(page, "الصفحة المبنية", ar_labels)
        self.assertTrue(any("نص ترجمة بديل" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
