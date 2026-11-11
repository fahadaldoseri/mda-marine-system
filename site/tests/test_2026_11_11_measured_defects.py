#!/usr/bin/env python3
"""اختبارات الانحدار لعيوب الإصدار المقيسة في 2026-11-11."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import blocks  # noqa: E402
import i18n_en  # noqa: E402
import map_gulf  # noqa: E402
import site_chrome  # noqa: E402


FULL_EVENT_ID = "MN-2026-11-11-02"
SHORT_EVENT_ID = "MN-11-02"


def test_map_details_show_full_event_id_and_badge_marks_abbreviation() -> None:
    point = {
        "code": FULL_EVENT_ID,
        "label": "نشاط مشبوه",
        "area": "مضيق هرمز",
        "lat": 26.56,
        "lon": 56.4,
        "kind": "unconfirm",
        "ref": "UKMTO 202-26",
        "source": "UKMTO",
        "precision": "approximate",
    }
    with patch.object(map_gulf, "REPORT_DATE", "2026-11-11"):
        html = map_gulf.build_map([point], "المصدر: جدول توزيع الوقائع.", None)
    table = html.split('<table class="mp-ev-table">', 1)[1].split("</table>", 1)[0]

    assert f'<td><bdi class="bidi">{FULL_EVENT_ID}</bdi></td>' in table
    assert f"اختصار: {SHORT_EVENT_ID}" in html
    assert f"الرمز الكامل: {FULL_EVENT_ID}" in html


def test_english_translation_preserves_dynamic_sector_and_coverage_markup(tmp_path: Path) -> None:
    (tmp_path / "2026-11-11-sectioned.en.md").write_text(
        "## Threat Level\n"
        "Overall level: High — highest sector: Strait of Hormuz, Gulf of Oman and the Arabian Gulf.\n",
        encoding="utf-8",
    )
    html = (
        '<html lang="ar" dir="rtl"><head>'
        '<meta name="description" content="Arabic source description">'
        '</head><body>'
        '<p class="tz-sub">أعلى نطاق: مضيق هرمز وخليج عُمان والخليج العربي</p>'
        '<p class="coverage"><span class="coverage-label">فترة التغطية:</span>'
        '<span class="coverage-value">خلال 24 ساعة السابقة '
        '(<span class="ltr">UTC</span>)</span></p>'
        '</body></html>'
    )
    with (
        patch.object(i18n_en, "I18N", tmp_path),
        patch.object(i18n_en, "_sector_counter_labels", return_value={}),
    ):
        translated, missing, _ = i18n_en.translate_page(
            html, "2026-11-11", {"فترة التغطية:": "Coverage period:"}, {}
        )

    assert "Highest sector: Strait of Hormuz, Gulf of Oman and the Arabian Gulf" in translated
    assert "During the previous 24 hours (UTC)" in translated
    assert missing == [], missing
    assert 'content="Daily Maritime Security Report — English edition, translated and governed against the Arabic source.">' in translated
    assert ">>" not in translated


def test_additions_navigation_links_to_matching_arabic_and_english_reports() -> None:
    source = (
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        '<title>إضافات — 11/11/2026</title></head>'
        '<body><div class="wrap">صفحة الإضافات</div></body></html>'
    )
    with patch.object(site_chrome, "en_edition_href", return_value="/reports/en/2026-11-11.html"):
        rendered = site_chrome.inject(source, active="additions")

    assert 'href="/reports/2026-11-11.html"' in rendered
    assert 'href="/reports/en/2026-11-11.html"' in rendered
    assert "التقرير العربي الموافق" in rendered
    assert "Matching English report" in rendered


def test_external_indicators_without_daily_evidence_are_not_current_readings() -> None:
    html = blocks.intel_analysis(
        {
            "report_date": "2026-11-11",
            "indicators": [
                {
                    "name": "أحدث تاريخ ظاهر في سجل المنظمة البحرية الدولية",
                    "baseline": "المنظمة البحرية الدولية (IMO)",
                    "current": "29 سبتمبر",
                    "previous": "29 سبتمبر",
                    "trend": "بلا تغيير",
                    "meaning": "لا يعرض السجل في التغذية الحالية إضافة أحدث تطابق البلاغين.",
                },
                {
                    "name": "حوادث MSCIO الأخيرة",
                    "baseline": "MSCIO",
                    "current": "Recent Incidents (0)",
                    "previous": "Recent Incidents (0)",
                    "trend": "بلا تغيير",
                    "meaning": "لا يظهر في صفحة التنبيهات بند حادث.",
                },
            ],
        },
        lambda value: value,
    )

    assert html.count("غير قابل للتحقق") >= 2
    assert "29 سبتمبر" not in html
    assert "Recent Incidents (0)" not in html
    assert "القيمة الحالية" not in html


def test_external_indicator_daily_evidence_keeps_zero_and_links_record() -> None:
    html = blocks.intel_analysis(
        {
            "report_date": "2026-11-11",
            "indicators": [
                {
                    "name": "MSCIO",
                    "baseline": "MSCIO",
                    "current": "ignored without evidence",
                    "previous": "0",
                    "trend": "بلا تغيير",
                    "meaning": "دليل تجريبي",
                    "daily_evidence": {
                        "date": "2026-11-11",
                        "checked_at": "2026-11-11T04:00:00Z",
                        "url": "https://example.org/evidence/2026-11-11",
                        "result": 0,
                    },
                }
            ],
        },
        lambda value: value,
    )

    assert 'href="https://example.org/evidence/2026-11-11"' in html
    assert "2026-11-11T04:00:00Z" in html
    assert "2026-11-11" in html
    assert "<td>0<br>" in html
    assert "غير قابل للتحقق" not in html
