#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regressions: keep master-backed dynamic English content in translated HTML."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
import i18n_en as I  # noqa: E402


DATE = "2026-10-31"
EVENT_CODE = re.compile(r"MN-\d{4}-\d{2}-\d{2}-\d{2}")
ARABIC = re.compile(r"[\u0600-\u06FF]")


def test_latest_official_card_uses_its_bilingual_data_contract() -> None:
    html = (
        '<html><body><div class="kpi" data-kpi-id="latest-official">'
        '<div class="k-l">أحدث بلاغ رسمي</div>'
        '<div class="k-v">30 أكتوبر 2026</div>'
        '<div class="k-d">الساعة غير متاحة</div>'
        '<div class="k-s">UKMTO</div>'
        '</div></body></html>'
    )

    with patch.object(I, "_sector_counter_labels", return_value={}):
        translated, _, _ = I.translate_page(html, DATE, {}, {})

    assert 'data-kpi-id="latest-official"' in translated, translated
    assert '<div class="k-l">Latest official report</div>' in translated, translated
    assert "omitted KPI" not in translated, translated


def test_dynamic_headline_is_composed_from_english_master_components() -> None:
    html = (
        '<html><body><h1>بلاغات <span class="ltr">UKMTO</span> عن ثلاث وقائع '
        'في مضيق هرمز وخليج عُمان والخليج العربي مع استمرار تضارب روايات '
        'الألغام والناقلات</h1></body></html>'
    )
    expected = (
        '<h1><span class="ltr">UKMTO</span> reports of 3 incidents in the Strait of '
        'Hormuz, Gulf of Oman and the Arabian Gulf align with continuing reports '
        'of vessel damage and conflicting accounts concerning mines and projectiles</h1>'
    )

    with patch.object(I, "_sector_counter_labels", return_value={}):
        translated, missing, _ = I.translate_page(html, DATE, {}, {})

    assert missing == [], missing
    assert expected in translated, translated
    assert "omitted source headline" not in translated, translated


def test_dynamic_incident_card_title_uses_indicator_and_sector_components() -> None:
    html = (
        '<html><body><article class="dg"><div class="dg-top">'
        '<span class="dg-idx">1</span><b class="dg-t">بلاغات '
        '<span class="ltr">UKMTO</span> عن وقائع في مضيق هرمز وخليج عُمان '
        'والخليج العربي داخل الفترة</b></div></article></body></html>'
    )
    expected = (
        '<b class="dg-t"><span class="ltr">UKMTO</span> reports of incidents in the '
        'Strait of Hormuz, Gulf of Oman and the Arabian Gulf during the period</b>'
    )

    with patch.object(I, "_sector_counter_labels", return_value={}):
        translated, missing, _ = I.translate_page(html, DATE, {}, {})

    assert missing == [], missing
    assert expected in translated, translated
    assert "omitted dynamic title" not in translated, translated


def _event_rows(markdown: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in markdown.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and EVENT_CODE.fullmatch(cells[0]):
            rows[cells[0]] = cells
    return rows


def test_all_report_event_rows_have_english_body_counterparts_and_preserve_numbers() -> None:
    """Every generated event-card field must be backed by its dated English master row."""
    master_paths = sorted(I.I18N.glob("*-sectioned.en.md"))
    assert master_paths, f"no English masters found in {I.I18N}"

    checked_dates: list[str] = []
    problems: list[str] = []
    for master_path in master_paths:
        date = master_path.name.removesuffix("-sectioned.en.md")
        arabic_path = I.AR_MD / f"{date}-sectioned.md"
        if not arabic_path.is_file():
            continue

        arabic_rows = _event_rows(arabic_path.read_text(encoding="utf-8"))
        english_rows = _event_rows(master_path.read_text(encoding="utf-8"))
        checked_dates.append(date)
        if set(arabic_rows) != set(english_rows):
            missing_en = sorted(set(arabic_rows) - set(english_rows))
            extra_en = sorted(set(english_rows) - set(arabic_rows))
            problems.append(
                f"{date}: event IDs differ; missing English={missing_en}; extra English={extra_en}"
            )

        for code in sorted(set(arabic_rows) & set(english_rows)):
            ar_cells, en_cells = arabic_rows[code], english_rows[code]
            for column, label in ((1, "event"), (2, "source/location/time")):
                if column >= len(ar_cells) or column >= len(en_cells):
                    problems.append(f"{date} {code}: missing {label} cell")
                    continue
                source, target = ar_cells[column], en_cells[column]
                if not target:
                    problems.append(f"{date} {code}: empty English {label} counterpart")
                if ARABIC.search(target):
                    problems.append(f"{date} {code}: Arabic remains in English {label}: {target}")
                if I._numeric_tokens(source) != I._numeric_tokens(target):
                    problems.append(
                        f"{date} {code}: numeric values differ in {label}: "
                        f"{I._numeric_tokens(source)} != {I._numeric_tokens(target)}"
                    )

    assert checked_dates, f"no report/master pairs found (brain={I.AR_MD}, site={I.I18N})"
    assert not problems, "\n".join(problems)


def test_dynamic_glossary_translations_preserve_numeric_tokens() -> None:
    meta = json.loads(
        (I.ROOT / "sources" / "meta" / "2026-10-30.json").read_text(encoding="utf-8")
    )
    gl = I.load_glossary()
    translate = I.make_translator({}, gl)
    sources = (
        meta["headline"],
        meta["lede"],
        "صدرت خمسة منتجات رسمية من",
        "رواية اشتعال أربع ناقلات بعد اصطدامها بألغام",
    )

    for source in sources:
        translated = translate(source)
        assert not ARABIC.search(translated), (source, translated)
        assert I._numeric_tokens(source) == I._numeric_tokens(translated), (
            source,
            translated,
            I._numeric_tokens(source),
            I._numeric_tokens(translated),
        )


def main() -> None:
    test_latest_official_card_uses_its_bilingual_data_contract()
    test_dynamic_headline_is_composed_from_english_master_components()
    test_dynamic_incident_card_title_uses_indicator_and_sector_components()
    test_all_report_event_rows_have_english_body_counterparts_and_preserve_numbers()
    test_dynamic_glossary_translations_preserve_numeric_tokens()
    print("master-backed dynamic-content regressions: PASS")


if __name__ == "__main__":
    main()
