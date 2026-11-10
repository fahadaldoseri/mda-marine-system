#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for exact matching and ltr-tag translation boundaries."""
from __future__ import annotations

import sys
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
import i18n_en as I  # noqa: E402


def test_complete_phrase_key_does_not_translate_a_fragment_before_ltr_tag() -> None:
    html = (
        '<html><body><p>مادة '
        '<span class="ltr">JMIC</span> الأمنية</p></body></html>'
    )
    tm = {"مادة JMIC الأمنية": "JMIC security material"}

    collector = I._Collector()
    collector.feed(html)
    assert collector.units == ["مادة ", "JMIC", " الأمنية"], collector.units

    with patch.object(I, "_sector_counter_labels", return_value={}):
        translated, _, _ = I.translate_page(html, "2026-11-10", tm, {})

    untouched_fragments = '<p>مادة <span class="ltr">JMIC</span> الأمنية</p>'
    assert untouched_fragments in translated, translated
    assert "JMIC security material <span" not in translated, translated


def test_single_word_glossary_entry_does_not_consume_a_longer_text_node() -> None:
    translate = I.make_translator({}, {"مادة": "material"})
    original = "مادة خام"

    assert translate(original) == original


def test_exact_only_phrase_translates_only_the_exact_node(tmp_path: Path) -> None:
    key = "المصدر والموقع والوقت"
    glossary_path = tmp_path / "glossary.json"
    glossary_path.write_text(
        json.dumps(
            {
                "entries": {key: "Source, location, and time"},
                "exact_match_only_entries": [key],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with (
        patch.object(I, "I18N", tmp_path),
        patch.object(I, "chrome_glossary", return_value={}),
        patch.object(I, "confidence_grade_map", return_value={}),
        patch.object(I, "BRAIN", tmp_path / "brain"),
    ):
        glossary = I.load_glossary()

    translate = I.make_translator({}, glossary)
    assert translate(key) == "Source, location, and time"
    longer = key + " والظرف"
    assert translate(longer) == longer


def test_exact_only_glossary_reference_must_exist(tmp_path: Path) -> None:
    (tmp_path / "glossary.json").write_text(
        json.dumps(
            {
                "entries": {"عنوان": "Heading"},
                "exact_match_only_entries": ["مفتاح غير موجود"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with (
        patch.object(I, "I18N", tmp_path),
        patch.object(I, "chrome_glossary", return_value={}),
        patch.object(I, "confidence_grade_map", return_value={}),
        patch.object(I, "BRAIN", tmp_path / "brain"),
    ):
        with pytest.raises(ValueError, match="exact_match_only_entries"):
            I.load_glossary()


def test_split_sentence_around_ltr_entity_uses_master_translation_once() -> None:
    html = (
        '<html><body><p>أبلغت <span class="ltr">UKMTO</span> '
        'عن واقعة هجوم على سفينة في مضيق هرمز</p></body></html>'
    )
    source = "أبلغت UKMTO عن واقعة هجوم على سفينة في مضيق هرمز"
    expected = "UKMTO reported an attack incident on a vessel in the Strait of Hormuz"

    with patch.object(I, "_sector_counter_labels", return_value={}):
        translated, missing, _ = I.translate_page(html, "2026-11-10", {source: expected}, {})

    assert missing == [], missing
    assert f'<p><span class="ltr">UKMTO</span> reported an attack incident on a vessel in the Strait of Hormuz</p>' in translated
    assert translated.count("UKMTO") == 1, translated


def test_split_sentence_around_non_ltr_inline_entities_uses_master_and_restores_placeholders() -> None:
    html = (
        '<html><body><p>قُدم '
        '<span class="classification">Attack</span> بتاريخ '
        '<span class="warning-id">WARNING 199-26</span> ضد '
        '<span class="vessel-name">Silent Sentinel II</span> وسُجلت '
        '<span class="incident-count">1</span> واقعة.</p></body></html>'
    )
    source = (
        "قُدم Attack بتاريخ WARNING 199-26 ضد Silent Sentinel II وسُجلت 1 واقعة."
    )
    target = (
        "1 incident concerning Silent Sentinel II was classified as Attack in WARNING 199-26."
    )
    expected = (
        '<p><span class="incident-count">1</span> incident concerning '
        '<span class="vessel-name">Silent Sentinel II</span> was classified as '
        '<span class="classification">Attack</span> in '
        '<span class="warning-id">WARNING 199-26</span>.</p>'
    )

    with patch.object(I, "_sector_counter_labels", return_value={}):
        translated, missing, _ = I.translate_page(html, "2026-11-10", {source: target}, {})

    assert missing == [], missing
    assert expected in translated, translated
    sentence = translated[translated.index("<p>"):translated.index("</p>") + len("</p>")]
    assert sentence.count('<span class="incident-count">1</span>') == 1, sentence
    for entity in ("Attack", "WARNING 199-26", "Silent Sentinel II"):
        assert sentence.count(entity) == 1, sentence


def test_inline_entity_repeated_by_master_is_emitted_once() -> None:
    html = (
        '<html><body><p>وردت السفينة '
        '<span class="vessel-name">Silent Sentinel II</span> في البلاغ.</p></body></html>'
    )
    source = "وردت السفينة Silent Sentinel II في البلاغ."
    target = (
        "Silent Sentinel II was named, and Silent Sentinel II was mentioned in the report."
    )

    with patch.object(I, "_sector_counter_labels", return_value={}):
        translated, missing, _ = I.translate_page(html, "2026-11-10", {source: target}, {})

    assert missing == [], missing
    assert translated.count("Silent Sentinel II") == 1, translated
    assert translated.count('<span class="vessel-name">Silent Sentinel II</span>') == 1, translated


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
