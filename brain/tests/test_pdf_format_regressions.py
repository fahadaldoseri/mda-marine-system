#!/usr/bin/env python3
"""اختبارات اقتران بوابة شكل PDF: موجب نظيف وسالب لكل شرط مانع."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cpf", ROOT / "validators" / "check_pdf_format.py")
cpf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpf)


CLEAN_LEGEND = """
<ul class="map-key mp-key">
  <li><span class="lg-sw sw-zone"></span>واقعة مؤكدة</li>
  <li><span class="lg-sw sw-tss"></span>موقع تقريبي</li>
  <li><span class="lg-sw sw-route"></span>بلاغ غير مؤهل</li>
</ul>
"""


def test_map_legend_counts_semantic_items_and_rejects_missing_or_short_key():
    clean_items = cpf.extract_map_legend_items(CLEAN_LEGEND)
    assert clean_items == [
        "واقعة مؤكدة",
        "موقع تقريبي",
        "بلاغ غير مؤهل",
    ]
    assert cpf.legend_failure(clean_items) is None
    short_items = cpf.extract_map_legend_items(CLEAN_LEGEND.replace("موقع تقريبي", ""))
    assert short_items == [
        "واقعة مؤكدة",
        "بلاغ غير مؤهل",
    ]
    assert cpf.legend_failure(short_items)
    missing_items = cpf.extract_map_legend_items("<main>لا توجد خريطة</main>")
    assert missing_items == []
    assert cpf.legend_failure(missing_items)


def test_page_range_is_closed_at_7_to_12():
    assert cpf.page_count_failure(12, (7, 12)) is None
    assert cpf.page_count_failure(6, (7, 12))
    assert cpf.page_count_failure(13, (7, 12))


def test_layout_gate_rejects_low_page_fill_and_internal_gap():
    fills = [96.0, 94.0, 54.0, 93.0, 96.0]
    voids = [(1, 10.0), (2, 45.0), (3, 10.0), (4, 8.0), (5, 10.0)]
    failures = cpf.layout_failures(fills, voids, {"min_page_fill": 55, "max_internal_void_mm": 45})
    assert any("صفحات قليلة التعبئة" in failure for failure in failures)
    assert any("فجوات داخلية كبيرة" in failure for failure in failures)
    assert cpf.layout_failures(
        [96.0, 94.0, 56.0, 93.0, 96.0],
        [(1, 10.0), (2, 44.9), (3, 10.0), (4, 8.0), (5, 10.0)],
        {"min_page_fill": 55, "max_internal_void_mm": 45},
    ) == []


def test_print_css_fingerprint_rejects_mismatch_and_accepts_match():
    frozen = "@media print { .approved { color: black } }"
    assert cpf.css_fingerprint_failure(frozen, frozen) is None
    assert cpf.css_fingerprint_failure(frozen, frozen + " .drift { color: red }")


def test_pdf_css_preserves_closed_details_content_and_allows_table_flow():
    exporter = ROOT / "tools" / "export_report_assets.py"
    css = exporter.read_text(encoding="utf-8")
    assert ".print-map .mp-events-detail > :not(summary)" in css
    assert ".print-map .mp-ev-table" in css
    assert "break-inside:auto" in css
