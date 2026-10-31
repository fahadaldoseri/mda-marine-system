#!/usr/bin/env python3
"""اختبارات ثابتة لسجل بطاقات العدادات الفعّال."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validators.check_card_counters import _counter, validate_card_documents, validate_hero_kpis, validate_official_cards  # noqa: E402
sys.path.insert(0, "/home/ubuntu/seawatch/generator")
from i18n_en import translate_page  # noqa: E402


ZONES_DATA = {
    "zones": [{"id": f"Z{i}"} for i in range(1, 5)],
    "counter": {
        "qualifying": 4,
        "confirmed": 1,
        "probable": 1,
        "excluded": 11,
        "nonspatial": 1,
        "total": 16,
    },
}

AR_REPORT = """
<html lang="ar"><body>
<section class="tz" aria-label="مستوى التهديد حسب القطاعات">
  <header class="tz-head"><h3>مستوى التهديد حسب القطاعات</h3></header>
  <ul class="tz-zones"><li>Z1</li><li>Z2</li><li>Z3</li><li>Z4</li></ul>
  <p class="tz-count">العدّاد: وقائع مؤهّلة <span class="bidi">4</span> · مؤكدة <span class="bidi">1</span> · مرجّحة <span class="bidi">1</span> · مستثناة <span class="bidi">11</span> · غير مكانية <span class="bidi">1</span> · إجمالي <span class="bidi">16</span></p>
</section>
<div class="sc-card" aria-label="أهم الأخبار المتعلقة بالأمن البحري">
  <div class="sc-row"><div class="sc-l">ما تغيّر</div><div class="sc-more">6 بنود <a href="/additions.html#sec-00" data-goto="ما تغيّر منذ التقرير السابق">التفاصيل</a></div></div>
  <div class="sc-row"><div class="sc-l">التحذيرات والنشرات الرسمية</div><div class="sc-more">تحذيران <a href="/reports/2026-10-31.html#sec-06" data-goto="التحذيرات والنشرات الرسمية">القسم الرسمي</a></div></div>
  <div class="sc-row"><div class="sc-l">ما يُراقب خلال 24–72 ساعة</div><div class="sc-more">5 بنود <a href="/additions.html#sec-04-sub-02" data-goto="علامات الإنذار المبكر 24–72 ساعة">المؤشرات الكاملة</a></div></div>
</div>
<section id="sec-06"><h2>التحذيرات والنشرات الرسمية</h2><table><thead><tr><th>الجهة</th><th>النص</th></tr></thead><tbody><tr><td>UKMTO</td><td>النص الرسمي الأول</td></tr><tr><td>JMIC</td><td>النص الرسمي الثاني</td></tr></tbody></table></section>
</body></html>
"""

AR_ADDITIONS = """
<html lang="ar"><body>
<section id="sec-00"><h2>ما تغيّر منذ التقرير السابق</h2><ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li><li>6</li></ul></section>
<section id="sec-04"><h2>قراءة الموقف وتحليل المؤشرات</h2><h3 id="sec-04-sub-02">علامات الإنذار المبكر 24–72 ساعة</h3><ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li></ul></section>
</body></html>
"""

EN_REPORT = """
<html lang="en"><body>
<section class="tz" aria-label="Threat level by sector">
  <header class="tz-head"><h3>Threat level by sector</h3></header>
  <ul class="tz-zones"><li>Z1</li><li>Z2</li><li>Z3</li><li>Z4</li></ul>
  <p class="tz-count">Counter: qualifying incidents <span class="bidi">4</span> · confirmed <span class="bidi">1</span> · probable <span class="bidi">1</span> · excluded <span class="bidi">11</span> · non-spatial <span class="bidi">1</span> · total <span class="bidi">16</span></p>
</section>
<div class="sc-card" aria-label="Top maritime security news">
  <div class="sc-row"><div class="sc-l">What changed</div><div class="sc-more">6 items <a href="/reports/en/additions.html#sec-00" data-goto="What changed since the previous report">Details</a></div></div>
  <div class="sc-row"><div class="sc-l">Official warnings and advisories</div><div class="sc-more">2 rows <a href="/reports/en/2026-10-31.html#sec-06" data-goto="Official warnings and advisories">Official section</a></div></div>
  <div class="sc-row"><div class="sc-l">What is monitored over the next 24–72 hours</div><div class="sc-more">5 items <a href="/reports/en/additions.html#sec-04-sub-02" data-goto="Early-warning indicators 24–72 hours">Indicators</a></div></div>
</div>
<section id="sec-06"><h2>Official warnings and advisories</h2><table><tbody><tr><td>UKMTO</td><td>Official text one</td></tr><tr><td>JMIC</td><td>Official text two</td></tr></tbody></table></section>
</body></html>
"""

EN_ADDITIONS = """
<html lang="en"><body>
<section id="sec-00"><h2>What changed since the previous report</h2><ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li><li>6</li></ul></section>
<section id="sec-04"><h2>Situation reading and indicator analysis</h2><h3 id="sec-04-sub-02">Early-warning indicators 24–72 hours</h3><ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li></ul></section>
</body></html>
"""


class CardCounterGateTests(unittest.TestCase):
    def docs(self):
        return {
            "ar_report": AR_REPORT,
            "ar_additions": AR_ADDITIONS,
            "en_report": EN_REPORT,
            "en_additions": EN_ADDITIONS,
            "zones_data": ZONES_DATA,
        }

    def test_positive_registry_matches_both_enabled_cards(self):
        self.assertEqual(validate_card_documents(**self.docs()), [])

    def test_registry_contains_two_enabled_cards(self):
        import json
        registry = json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8"))
        enabled = [c for c in registry["cards"] if c["status"]["state"] == "enabled"]
        self.assertGreaterEqual(len(enabled), 2)

    def test_unregistered_card_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace(
            'aria-label="مستوى التهديد حسب القطاعات"', 'aria-label="بطاقة غير مسجلة"', 1
        )
        errors = validate_card_documents(**docs)
        self.assertTrue(any("غير مسجلة" in e for e in errors), errors)

    def test_registered_card_missing_required_counter_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("· مؤكدة <span", "· <span", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("مفتاح" in e and "confirmed" in e for e in errors), errors)

    def test_zone_counter_drift_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("وقائع مؤهّلة <span class=\"bidi\">4", "وقائع مؤهّلة <span class=\"bidi\">3", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("qualifying" in e and "4" in e and "3" in e for e in errors), errors)

    def test_negative_counter_change_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("6 بنود", "5 بنود", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("ما تغيّر" in e and "6" in e and "5" in e for e in errors), errors)

    def test_negative_anchor_title_change_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("#sec-04-sub-02", "#sec-04", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("علامات الإنذار المبكر" in e and "مرسا" in e for e in errors), errors)

    def test_negative_arabic_counter_grammar_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("تحذيران", "2 صفوف", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("صياغة" in e and "التحذيرات" in e for e in errors), errors)

    def test_negative_arabic_card_latin_outside_allowlist_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("تحذيران <a", "تحذيران XYZ <a", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("لاتينية" in e and "التحذيرات" in e for e in errors), errors)

    def test_zone_heading_anchor_drift_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("<h3>مستوى التهديد حسب القطاعات", "<h3>عنوان منحرف", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("مرسا" in e and "القطاعات" in e for e in errors), errors)

    def test_arabic_counter_forms_remain_strict(self):
        expected = {"لا بنود": 0, "بند واحد": 1, "بندان": 2, "3 بنود": 3, "لا تحذيرات": 0, "تحذير واحد": 1, "تحذيران": 2, "3 تحذيرات": 3}
        for text, count in expected.items():
            self.assertEqual(_counter(text + " · التفاصيل", "ar"), count, text)
        self.assertIsNone(_counter("2 صفوف · التفاصيل", "ar"))

    def test_english_threat_counter_is_generated_from_all_registered_labels(self):
        html = '<html lang="ar"><body><p class="tz-count">العدّاد: وقائع مؤهّلة <span class="bidi">4</span> · مؤكدة <span class="bidi">1</span> · مرجّحة <span class="bidi">1</span> · مستثناة <span class="bidi">11</span> · غير مكانية <span class="bidi">1</span> · إجمالي <span class="bidi">16</span></p></body></html>'
        translated, _, _ = translate_page(html, "2026-10-31", {}, {})
        expected = ("Counter: qualifying incidents", "confirmed", "probable", "excluded", "non-spatial", "total")
        for label in expected:
            self.assertIn(label, translated)


class HeroKpiGateTests(unittest.TestCase):
    """حواجز المؤشرات الجديدة: العنوان ثابت، الموضع حاضر، والتفصيل مصدره العدّاد."""

    def setUp(self):
        import copy
        import json
        self.copy = copy
        self.meta = json.loads(Path("/home/ubuntu/seawatch/sources/meta/2026-10-31.json").read_text(encoding="utf-8"))
        self.zones = json.loads((ROOT / "web/zones/2026-10-31.json").read_text(encoding="utf-8"))
        self.registry = json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8"))

    def test_current_day_hero_kpis_match_source_contract(self):
        self.assertEqual(validate_hero_kpis(self.meta, self.zones, self.registry), [])

    def _rendered_hero_html(self, report_count=1, screen_count=1):
        tiles = "".join('<div class="kpi hero-kpi"></div>' for _ in range(7))
        report = "".join(f'<div class="kpis hero-kpis">{tiles}</div>' for _ in range(report_count))
        screen = "".join(f'<div class="sc-kpis hero-kpis">{tiles}</div>' for _ in range(screen_count))
        return f'<html lang="ar"><body>{report}<div class="sc-hero no-print">{screen}</div></body></html>'

    def test_rendered_hero_kpis_allow_one_container_per_surface(self):
        errors = validate_hero_kpis(self.meta, self.zones, self.registry,
                                     rendered_html=self._rendered_hero_html())
        self.assertEqual(errors, [])

    def test_negative_duplicate_hero_container_within_same_surface_fails_closed(self):
        errors = validate_hero_kpis(self.meta, self.zones, self.registry,
                                     rendered_html=self._rendered_hero_html(report_count=2))
        self.assertTrue(any("سطح التقرير/الطباعة" in e and "2" in e for e in errors), errors)

    def test_unconfirmed_card_keeps_total_and_qualifying_dimensions(self):
        counter = self.zones["counter"]
        self.assertEqual(counter["unconfirmed_total"], 3)
        self.assertEqual(counter["unconfirmed_qualifying"], 2)
        card = next(c for c in self.meta["hero_kpis"] if c["id"] == "unconfirmed-narratives")
        self.assertEqual(card["value"], "3")
        self.assertEqual(card["detail"], "3 روايات · منها 2 مؤهلة · تُذكر ولا تُحتسب")

    def test_negative_fixed_title_change_fails_closed(self):
        changed = self.copy.deepcopy(self.meta)
        changed["hero_kpis"][0]["title"] = "بلاغات UKMTO عن وقائع"
        errors = validate_hero_kpis(changed, self.zones, self.registry)
        self.assertTrue(any("ثبات العنوان" in e for e in errors), errors)

    def test_negative_missing_card_fails_closed(self):
        changed = self.copy.deepcopy(self.meta)
        changed["hero_kpis"].pop(3)
        errors = validate_hero_kpis(changed, self.zones, self.registry)
        self.assertTrue(any("وجود البطاقة" in e or "صف" in e for e in errors), errors)

    def test_negative_detail_composition_fails_closed(self):
        changed = self.copy.deepcopy(self.meta)
        changed["hero_kpis"][1]["detail"] = "3 مؤكدة + 1 مرجحة"
        errors = validate_hero_kpis(changed, self.zones, self.registry)
        self.assertTrue(any("تفصيل البطاقة" in e for e in errors), errors)


class OfficialCardGateTests(unittest.TestCase):
    """اختبارات RED/GREEN للبطاقات الرسمية ذات الطبقات الثلاث."""

    def setUp(self):
        import copy
        import json
        self.copy = copy
        self.meta = json.loads(Path("/home/ubuntu/seawatch/sources/meta/2026-10-31.json").read_text(encoding="utf-8"))
        self.registry = json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8"))

    def test_official_cards_have_three_layers_and_source_basis(self):
        errors = validate_official_cards(self.meta, self.registry)
        self.assertEqual(errors, [])

    def test_false_zero_death_card_fails_closed(self):
        changed = self.copy.deepcopy(self.meta)
        changed["official_cards"] = self.copy.deepcopy(changed.get("official_cards") or [])
        death = next(card for card in changed["official_cards"] if card["id"] == "imo-seafarer-deaths")
        death["layers"]["daily"]["value"] = "0"
        errors = validate_official_cards(changed, self.registry)
        self.assertTrue(any("الصفر الكاذب" in error or "لم يُعلن" in error for error in errors), errors)

    def test_transit_without_reading_uses_no_coverage_not_zero(self):
        changed = self.copy.deepcopy(self.meta)
        changed["official_cards"] = self.copy.deepcopy(changed.get("official_cards") or [])
        transit = next(card for card in changed["official_cards"] if card["id"] == "imo-transit-september-2026")
        transit["layers"]["daily"]["value"] = "0"
        errors = validate_official_cards(changed, self.registry)
        self.assertTrue(any("لا تغطية" in error or "الصفر" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
