#!/usr/bin/env python3
"""Regression tests for evidence fidelity in daily report surfaces."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import build_report  # noqa: E402


EVIDENCE_URL = "https://www.ukmto.org/recent-incidents#c151e68e-75d0-4014-b192-491812e31aac"


def _event() -> dict:
    return {
        "code": "MN-2026-11-11-01",
        "date": "2026-11-11",
        "class": "بلاغ رسمي",
        "title": "بلاغ UKMTO 201-26",
        "source": "UKMTO — الحوادث الأخيرة",
        "confidence": "منخفضة",
        "time_kind": "نشر",
        "evidence_ref": EVIDENCE_URL,
        "source_url": "https://www.ukmto.org/",
        "source_excerpt": "10/11/2026 Attack: UKMTO incident 201-26...",
    }


def _meta() -> dict:
    return {
        "source_reliability": {
            "rows": [
                {
                    "name": "UKMTO — الحوادث الأخيرة",
                    "source_reliability": "A",
                    "information_credibility": 2,
                }
            ]
        }
    }


def _render_event(tmp_path: Path) -> str:
    return build_report.render_ledger_events(
        [_event()], {}, tmp_path / "2026-11-11-sectioned.md", meta=_meta()
    )


def test_event_card_separates_source_reliability_from_analytic_confidence(tmp_path: Path) -> None:
    html = _render_event(tmp_path)
    assert "موثوقية المصدر: A/2" in html
    assert "درجة الثقة التحليلية: منخفضة" in html
    assert "درجة الموثوقية: منخفضة" not in html


def test_event_card_prefers_saved_evidence_anchor_to_generic_account_url(tmp_path: Path) -> None:
    html = _render_event(tmp_path)
    assert f'href="{EVIDENCE_URL}"' in html
    assert 'href="https://www.ukmto.org/"' not in html


def test_event_card_marks_publish_only_time_and_truncated_excerpt(tmp_path: Path) -> None:
    html = _render_event(tmp_path)
    assert "وقت الواقعة غير متاح" in html
    assert "مقتطف المصدر" in html
    assert '<span class="ev-k">مقتطف المصدر</span>' in html
    assert "النص الأصلي كما في المصدر" not in html


def test_map_qualifying_ratio_is_explicitly_ltr_isolated() -> None:
    html = build_report._map_decision_strip(
        {"threat_zones": {"counter": {"qualifying": 1, "total": 2}}}
    )
    assert '<bdi dir="ltr">1 / 2</bdi>' in html


def test_map_horizontal_scroll_hint_is_third_person() -> None:
    html = build_report.hero_map("<div class=\"map\"></div>")
    assert "يمكن استعراض كامل الخريطة بالتمرير الأفقي" in html
    assert "اسحب أفقيًا" not in html


def test_imo_map_reference_uses_interface_updated_value(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "imo-incidents.json"
    source_path.write_text(
        json.dumps(
            {
                "totals": {"confirmed_incidents": 128},
                "source": {"list_updated": "2026-10-30"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(build_report, "IMO_INCIDENTS_JSON", source_path)
    meta = {
        "official_cards": [
            {
                "id": "imo-confirmed-incidents",
                "layers": {"updated": {"value": "03/11/2026"}},
            }
        ]
    }
    html = build_report._imo_reference_line(meta)
    assert "3 نوفمبر 2026" in html
    assert "30 أكتوبر 2026" not in html


def test_imo_reference_uses_value_in_force_on_report_day(tmp_path, monkeypatch) -> None:
    """صفحة إصدار قديم لا تعرض عدد المالك الحي بجوار تاريخ إصدارها (2026-11-19)."""
    source_path = tmp_path / "imo-incidents.json"
    source_path.write_text(json.dumps({"totals": {"confirmed_incidents": 138},
                                       "source": {"as_at": "17 November 2026"}}), encoding="utf-8")
    monkeypatch.setattr(build_report, "IMO_INCIDENTS_JSON", source_path)
    old = {"official_cards": [{"id": "imo-confirmed-incidents", "layers": {
        "cumulative": {"value": "128"}, "updated": {"value": "03/11/2026"}}}]}
    html = build_report._imo_reference_line(old)
    assert ">128<" in html and ">138<" not in html and "3 نوفمبر 2026" in html
    bare = {"official_cards": [{"id": "imo-confirmed-incidents", "layers": {"updated": {"value": "17/11/2026"}}}]}
    assert ">138<" in build_report._imo_reference_line(bare)


def test_unverified_cumulative_is_not_rendered_as_a_current_number() -> None:
    kpi = {
        "cumulative": 168,
        "source": "web/zones/{date}.json · counter",
        "updated": "2026-11-11",
    }
    render = getattr(build_report, "_hero_cumulative_html", lambda _k: "")
    html = render(kpi)
    assert "غير قابلة للتحقق" in html
    assert "168" not in html
    assert "web/zones/{date}.json" not in html


def test_official_cumulative_shows_source_and_read_date_from_meta_fields() -> None:
    kpi = {
        "cumulative": 222,
        "source": "سجل الوقائع الرسمي UKMTO",
        "updated": "2026-11-11",
    }
    render = getattr(build_report, "_hero_cumulative_html", lambda _k: "")
    html = render(kpi)
    assert "222" in html
    assert "المصدر الرسمي" in html
    assert "سجل الوقائع الرسمي UKMTO" in html
    assert "تاريخ القراءة" in html
    assert "2026-11-11" in html


def test_additions_surface_has_backlink_to_corresponding_report_version() -> None:
    make_link = getattr(build_report, "_additions_return_link", lambda _date: "")
    html = make_link("2026-11-11")
    assert 'href="/reports/2026-11-11.html"' in html
    assert "العودة إلى إصدار التقرير" in html
