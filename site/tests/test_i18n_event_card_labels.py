#!/usr/bin/env python3
"""Regression test for governed English event-card row labels."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
import i18n_en as I  # noqa: E402


CARD = """<html lang="ar" dir="rtl"><body>
<article class="ev" data-event-code="MN-2026-11-06-01" data-event-rows="9">
  <div class="ev-meta">
    <div class="ev-field" data-row="6" data-row-state="shown">
      <span class="ev-k">المصدر</span>
      <span class="ev-mv"><a class="ev-link" href="https://example.com">UKMTO</a></span>
    </div>
  </div>
</article>
</body></html>"""


def _row_label(page: str, row: int) -> str:
    match = re.search(
        rf'<div\b[^>]*\bclass="ev-field"[^>]*\bdata-row="{row}"[^>]*>.*?'
        r'<span class="ev-k">([^<]*)</span>',
        page,
        flags=re.S,
    )
    assert match, f"row {row} label missing from translated card"
    return match.group(1).strip()


def test_event_card_source_row_uses_governed_structural_label() -> None:
    # The aligned report memory contains a longer table heading beginning with
    # «المصدر». Prefix lookup must not leak that prose heading into a card label.
    translated, missing, _ = I.translate_page(
        CARD,
        "2026-11-06",
        {"المصدر والحدود": "Source and limits"},
        {"المصدر: جدول التوزيع الجغرافي للوقائع في هذا التقرير. النسب لا تمثل أعداد هجمات مستقلة.":
         "Source: Geographic distribution of incidents table in this report. Percentages do not represent independent attack counts."},
    )
    assert missing == [], missing
    assert _row_label(translated, 6) == "Source"
    assert "Source and limits" not in _row_label(translated, 6)
