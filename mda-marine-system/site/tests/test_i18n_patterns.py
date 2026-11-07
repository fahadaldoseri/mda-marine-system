#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات ترجمة عائلات الجمل المتكررة وحارس الفشل المغلق."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
import i18n_en as I  # noqa: E402

ARABIC = re.compile(r"[\u0600-\u06FF]")


def test_repeated_sentence_families_translate_without_glossary_entries() -> None:
    translate = I.make_translator({}, {})
    cases = {
        "، من دون تفاصيل عن السفينة أو عن الضرر":
            ", without details about the vessel or the damage",
        "، والتحذير 193-26 بتاريخ 2 نوفمبر 2026":
            ", and warning No. 193-26 dated 2 November 2026",
        "صدر أربعة تحذيرات خلال الفترة: التحذير 193-26 (التحديث الأول) بتاريخ 2 نوفمبر":
            "Four warnings were issued during the period: warning No. 193-26 (the first update), dated 2 November",
        "ثلاثة تحذيرات خلال الفترة: تحديث التحذير 193-26، ثم التحذير 194-26 في 2 نوفمبر":
            "Three warnings during the period: an update to warning No. 193-26, followed by warning No. 194-26 on 2 November",
    }
    for arabic, expected in cases.items():
        translated = translate(arabic)
        assert translated == expected, (arabic, translated, expected)
        assert not ARABIC.search(translated), (arabic, translated)


def test_uncovered_arabic_text_fails_closed() -> None:
    html = "<html><head></head><body><p>نص عربي غير مغطّى</p></body></html>"
    _, missing, _ = I.translate_page(html, "2026-11-02", {}, {})
    assert missing == ["نص عربي غير مغطّى"], missing


def test_overall_level_family_covers_wording_variants_without_guessing() -> None:
    translate = I.make_translator({}, {})
    shared = (
        "المستوى العام: مرتفع جدًا — القطاع الأعلى: مضيق هرمز، خليج عُمان، الخليج العربي. "
        "{basis} إلى صدور ثلاثة تحذيرات رسمية خلال الفترة، منها بلاغ هجوم داخل مضيق هرمز "
        "وتحديث لتحذير سابق؛ {high} أعلى تكرار رسمي خلال الفترة القريبة. "
        "{negative} قبل تأكيد رسمي أو تأكيد من مصدرين مستقلين (02-01 إلى 02-05؛ B/2)."
    )
    cases = [
        (
            shared.format(
                basis="يستند هذا التقدير",
                high="وهو",
                negative="لا تُرفع درجة التهديد استنادًا إلى روايات غير مؤكدة",
            ),
            "Overall level: Very High — highest sector: the Strait of Hormuz, the Gulf of Oman and the Arabian Gulf. "
            "This assessment is based on the issuance of three official warnings during the period, including a report "
            "of an attack inside the Strait of Hormuz and an update to an earlier warning; this is the highest official "
            "frequency in the recent period. The threat level is not raised on the basis of unconfirmed accounts before "
            "official confirmation or confirmation from two independent sources (02-01 to 02-05; B/2).",
        ),
        (
            shared.format(
                basis="يُسند هذا التقدير",
                high="هذا",
                negative="لا تُرفع درجة التهديد استنادا إلى روايات غير مؤكدة",
            ),
            "Overall level: Very High — highest sector: the Strait of Hormuz, the Gulf of Oman and the Arabian Gulf. "
            "This assessment is based on the issuance of three official warnings during the period, including a report "
            "of an attack inside the Strait of Hormuz and an update to an earlier warning; this is the highest official "
            "frequency in the recent period. The threat level is not raised on the basis of unconfirmed accounts before "
            "official confirmation or confirmation from two independent sources (02-01 to 02-05; B/2).",
        ),
    ]
    for arabic, expected in cases:
        translated = translate(arabic)
        assert translated == expected, (arabic, translated, expected)
        assert not ARABIC.search(translated), translated

    near_miss = cases[0][0].replace("استنادًا إلى", "اعتمادًا على")
    assert translate(near_miss) == near_miss
    _, missing, _ = I.translate_page(f"<html><body><p>{near_miss}</p></body></html>", "2026-11-02", {}, {})
    assert missing == [near_miss], missing

    comma_variant = cases[0][0].replace("وتحديث لتحذير سابق؛", "وتحديث لتحذير سابق،")
    translated = translate(comma_variant)
    assert translated == cases[0][1], (comma_variant, translated, cases[0][1])
    assert not ARABIC.search(translated), translated


if __name__ == "__main__":
    test_repeated_sentence_families_translate_without_glossary_entries()
    print("positive pattern families: PASS")
    test_uncovered_arabic_text_fails_closed()
    print("negative uncovered Arabic guard: PASS")
    test_overall_level_family_covers_wording_variants_without_guessing()
    print("overall level wording variants: PASS")
    print("i18n pattern regression: PASS")
