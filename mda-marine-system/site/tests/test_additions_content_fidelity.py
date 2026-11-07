#!/usr/bin/env python3
"""اختبار انحدار: كتلة hypotheses لا تُسقط عند بناء صفحة الإضافات."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))

import build_report  # noqa: E402
import build_site  # noqa: E402
import i18n_en  # noqa: E402


GENERATED_ADDITIONS_UNITS = {
    "Update 111؛ التفاصيل التشغيلية غير متاحة": "Update 111; operational details are not available",
    "استمرار خطر الهجمات على السفن في خليج عُمان · مضيق هرمز خلال 24 إلى 72 ساعة":
        "Continued risk of attacks on ships in the Gulf of Oman and the Strait of Hormuz over the next 24 to 72 hours",
    "الخبر نقل إعلامي بلا أصل رسمي ظاهر في المواد.":
        "The report is media reporting with no official source visible in the material.",
    "الفجوة": "Gap",
    "الفجوة · الجهة القادرة على حسمها · أثر استمرارها.":
        "Gap · Authority able to resolve it · Impact of persistence.",
    "الفرضية": "Hypothesis",
    "المؤيد": "Supporting evidence",
    "المصدر: دفتر الأحداث التراكمي. الأعداد تعني سجلات مرصودة لا هجمات مؤكدة.":
        "Source: cumulative event ledger. The counts represent observed records, not confirmed attacks.",
    "المعارض": "Contrary evidence",
    "تبقى هوية السفن وحجم الضرر غير متاحة.":
        "The ships' identities and the extent of damage remain unavailable.",
    "ترجيح الاحتمالات": "Probability assessment",
    "تكليفات المتابعة": "Follow-up assignments",
    "درجة الاحتمال": "Probability level",
    "سجل التتبع أو النشرة الرسمية": "Tracking record or official notice",
    "غياب تأكيد": "Absence of confirmation",
    "لا إشعار إغلاق رسمي في مواد اليوم.": "No official closure notice appears in today's material.",
    "لا تُثبت المواد أضرارًا متعددة أو تعطيلًا كاملًا للممر.":
        "The material does not establish multiple instances of damage or a complete disruption of the passage.",
    "لا يثبتان إغلاقًا.": "They do not establish a closure.",
    "لا يظهر رقم أحدث أو إضافة مؤكدة في مواد اليوم.":
        "No later figure or confirmed addition appears in today's material.",
    "لا يمكن استخراج أثر تشغيلي تفصيلي للنشرة.":
        "A detailed operational impact cannot be extracted from the notice.",
    "لا يمكن تحويل الرواية المجمعة إلى خمس وقائع مؤكدة.":
        "The consolidated account cannot be converted into five confirmed incidents.",
    "لا يمكن تقدير حجم الضرر أو الخسائر البشرية من المقتطف المتاح.":
        "The extent of damage or human losses cannot be estimated from the available excerpt.",
    "وIMO وعدم وجود أسماء سفن أو أرقام": "and IMO, with no ship names or IMO numbers",
    "وIMO؛ المصدر: straits.live؛ gCaptain؛ MarineLink؛ Splash 247؛ TradeWinds؛ الحالة: غير مؤكدة.":
        "and IMO; source: straits.live; gCaptain; MarineLink; Splash 247; TradeWinds; status: unconfirmed.",
    "ورواية الناقلات وخبر الأصول البحرية الكورية":
        "and the tanker account and report of South Korean naval assets",
    "ونشرة": "and the notice",
    "ما لم تحدده المواد بعد، وما يلزم متابعته في التقرير التالي.":
        "What the material has not established yet and what needs follow-up in the next report.",
}


def test_additions_keeps_hypotheses_data_grid(tmp_path: Path) -> None:
    date = "2026-11-06"
    md = ROOT / "sources" / "reports" / f"{date}-sectioned.md"
    meta = json.loads((ROOT / "sources" / "meta" / f"{date}.json").read_text(encoding="utf-8"))
    reports = [{"iso": date, "md": md, "meta": meta}]
    build_report.load_section_policy()

    warnings: list[str] = []
    count = build_site.build_additions(ROOT, tmp_path, reports, warnings)
    assert not warnings, warnings
    assert count > 0

    html = (tmp_path / "additions.html").read_text(encoding="utf-8")
    start = html.index("الاحتمالات ونسبة الحوادث إلى جهات")
    end = html.index("</section>", start)
    section = html[start:end]
    assert '<div class="tbl-wrap"><table>' in section
    assert section.count("<tr>") >= 4
    assert "صدور إشعار ملاحي دولي بإغلاق مضيق هرمز خلال الفترة" in section


def test_generated_additions_units_have_governed_english_source() -> None:
    glossary = i18n_en.load_glossary()
    for arabic, english in GENERATED_ADDITIONS_UNITS.items():
        assert glossary.get(i18n_en.norm(arabic)) == english
        assert not i18n_en.ARABIC.search(glossary[arabic])


def test_generated_additions_use_governed_public_gap_language(tmp_path: Path) -> None:
    """لا تعيد صفحة الإضافات لفظًا ممنوعًا عند بناء النص من المصدر."""
    date = "2026-11-06"
    md = ROOT / "sources" / "reports" / f"{date}-sectioned.md"
    meta = json.loads((ROOT / "sources" / "meta" / f"{date}.json").read_text(encoding="utf-8"))
    reports = [{"iso": date, "md": md, "meta": meta}]
    build_report.load_section_policy()

    warnings: list[str] = []
    count = build_site.build_additions(ROOT, tmp_path, reports, warnings)
    assert not warnings, warnings
    assert count > 0

    html = (tmp_path / "additions.html").read_text(encoding="utf-8")
    assert "ما لم تحدده المواد بعد، وما يلزم متابعته في التقرير التالي." in html
    assert "ما لا يزال مجهولًا، وما يلزم متابعته في التقرير التالي." not in html
    assert "الجهة القادرة على الحسم" not in html
    assert "الجهة التي تستطيع التأكيد" in html
