#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار محاذاة مقطع HTML المقطوع عند مرساة لاتينية."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import derive_en_units as D  # noqa: E402


def test_arabic_and_persian_digits_normalize_to_latin() -> None:
    assert hasattr(D, "_build_arabic_digits")
    assert D._canonical_identifier_text("0123456789 ۰۱۲۳۴۵۶۷۸۹") == (
        "0123456789 0123456789"
    )


def test_short_incident_ids_normalize_before_body_alignment() -> None:
    pairs = [
        (
            "- أفادت straits.live بتقارير إيرانية عن إصابة خمس ناقلات بألغام بحرية قرب مضيق هرمز خلال 24 ساعة. لم يؤكد UKMTO أو IMO الأسماء أو الأضرار أو الخسائر، لذلك تُسجّل كرواية واحدة غير مؤكدة (MN-2026-11-06-02).",
            "- straits.live reported Iranian accounts that five tankers were hit by sea mines near the Strait of Hormuz during 24 hours. UKMTO and IMO did not confirm the names, damage or casualties, so this is recorded as one unconfirmed account (MN-2026-11-06-02).",
        ),
        (
            "- **MN-2026-11-06-01** — **ما حدث:** أدرجت UKMTO بلاغ رقم 196-26 عن واقعة شمال مدينة الشمال. **الموقع:** الخليج العربي، شمال مدينة الشمال. **الحالة:** بلاغ رسمي.",
            "- **MN-2026-11-06-01** — **What happened:** UKMTO listed report 196-26 about an incident north of Madinat ash Shamal. **Location:** Arabian Gulf, north of Madinat ash Shamal. **Status:** official report.",
        ),
    ]

    parenthetical = "الأسماء أو الأضرار أو الخسائر، لذلك تُسجّل كرواية واحدة غير مؤكدة (06-02)."
    bare = "الواقعة 06-01 — المنطقة شمال مدينة الشمال - الخليج العربي، الصفة بلاغ رسمي."

    parenthetical_result = D.derive(parenthetical, pairs, source_date="2026-11-06")
    bare_result = D.derive(bare, pairs, source_date="2026-11-06")

    assert parenthetical_result == (
        "names, damage or casualties, so this is recorded as one unconfirmed account "
        "(MN-2026-11-06-02)."
    )
    assert bare_result == (
        "MN-2026-11-06-01 — What happened: UKMTO listed report 196-26 about an incident "
        "north of Madinat ash Shamal."
    )


def test_fragment_after_inline_latin_anchor_uses_governing_sentence() -> None:
    arabic = (
        "- أدرجت قائمة تحذيرات UKMTO بلاغ 196-26 عن واقعة على بعد 50 ميلًا بحريًا "
        "شمال مدينة الشمال، مع وصفها هجومًا؛ التفاصيل الكاملة للبلاغ غير متاحة في مواد اليوم "
        "(MN-2026-11-06-01)."
    )
    english = (
        "- The UKMTO warnings list included report 196-26 about an incident 50 nautical miles "
        "north of Madinat ash Shamal and described it as an attack; the full details of the report "
        "are not available in today's material (MN-2026-11-06-01)."
    )
    fragment = "بلاغ 196-26 عن واقعة على بعد 50 ميلًا بحريًا شمال مدينة الشمال"
    expected = (
        "report 196-26 about an incident 50 nautical miles north of Madinat ash Shamal "
        "and described it as an attack; the full details of the report are not available "
        "in today's material"
    )
    assert D.derive(fragment, [(arabic, english)]) == expected


if __name__ == "__main__":
    test_fragment_after_inline_latin_anchor_uses_governing_sentence()
    print("derive fragment anchor regression: PASS")
