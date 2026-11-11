#!/usr/bin/env python3
"""اختبارات انحدار للتاريخ العربي وسياق بطاقة الأخبار في صفحة الإضافات."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import build_report  # noqa: E402
import build_site  # noqa: E402


def test_ar_date_uses_correct_names_for_all_twelve_months() -> None:
    expected_months = [
        "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
    ]
    expected = [f"11 {month} 2026" for month in expected_months]
    actual = [build_site.ar_date(f"2026-{month:02d}-11") for month in range(1, 13)]
    assert actual == expected
    assert build_site.ar_date("2026-11-11") == "11 نوفمبر 2026"


def test_additions_news_card_keeps_sector_counter_and_action(tmp_path: Path) -> None:
    report_date = "2026-11-06"
    md = ROOT / "sources" / "reports" / f"{report_date}-sectioned.md"
    meta = json.loads(
        (ROOT / "sources" / "meta" / f"{report_date}.json").read_text(encoding="utf-8")
    )
    # أسماء البنية وقيمها مأخوذة من brain/web/meta/2026-11-11.json:
    # threat_zones.top_zone, threat_zones.counter.qualifying/total, decision_card.action.
    meta["threat_zones"] = {
        "top_zone": "قطاع اختبار بطاقة الأخبار",
        "overall": "متوسط",
        "counter": {"qualifying": 1, "total": 2},
    }
    meta["decision_card"] = {
        "changed": ["تغيير اختبار بطاقة الأخبار."],
        "watch": ["مؤشر اختبار بطاقة الأخبار."],
        "action": ["إجراء اختبار بطاقة الأخبار."],
    }
    reports = [{"iso": report_date, "md": md, "meta": meta}]
    build_report.load_section_policy()

    warnings: list[str] = []
    count = build_site.build_additions(ROOT, tmp_path, reports, warnings)
    assert not warnings, warnings
    assert count > 0

    html = (tmp_path / "additions.html").read_text(encoding="utf-8")
    card_start = html.index('id="news-card"')
    card_end = html.index("</section>", card_start)
    card = html[card_start:card_end]
    assert "أعلى قطاع" in card
    assert "قطاع اختبار بطاقة الأخبار — متوسط" in card
    assert "الوقائع المؤهلة" in card
    assert "1 / 2" in card
    assert "إجراء اليوم" in card
    assert "إجراء اختبار بطاقة الأخبار." in card
