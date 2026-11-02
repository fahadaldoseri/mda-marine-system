#!/usr/bin/env python3
"""اختبارات ثابتة لسجل بطاقات العدادات الفعّال."""
from pathlib import Path
import pathlib
import re
import os
import tempfile
SITE_ROOT = pathlib.Path(__file__).resolve().parents[1].parent / "seawatch"
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validators.check_card_counters import (_counter, validate_card_documents,
                                             validate_hero_kpis, validate_official_cards,
                                             _measure_rendered_target)  # noqa: E402
sys.path.insert(0, str(SITE_ROOT / "generator"))
from i18n_en import translate_page  # noqa: E402
import build_report as site_build_report  # noqa: E402



def _latest_day() -> str:
    """اليوم المرجعي للاختبار: من البيئة إن حُدد، وإلا أحدث ملف واجهة مبني.

    عطل (2026-11-01): كان الاختبار يثبّت 2026-10-31 فيسقط في اليوم التالي عند تغيّر
    تفصيل بطاقة رسمية. القاعدة الآن: يُقرأ أحدث يوم مُبنى، فلا يعتمد على الذاكرة.
    """
    for key in ("D", "DATE"):
        env = (os.environ.get(key) or "").strip()
        if env and (SITE_ROOT / "sources" / "meta" / f"{env}.json").exists():
            return env
    metas = sorted(x.stem for x in (SITE_ROOT / "sources" / "meta").glob("*.json")
                   if re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.stem))
    return metas[-1] if metas else "2026-10-31"


DAY = _latest_day()


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
<section class="tz" aria-label="مستوى التهديد">
  <header class="tz-head"><h3>مستوى التهديد</h3></header>
  <ul class="tz-zones"><li>Z1</li><li>Z2</li><li>Z3</li><li>Z4</li></ul>
  <p class="tz-count">العدّاد: وقائع مؤهّلة <span class="bidi">4</span> · مؤكدة <span class="bidi">1</span> · مرجّحة <span class="bidi">1</span> · مستثناة <span class="bidi">11</span> · غير مكانية <span class="bidi">1</span> · إجمالي <span class="bidi">16</span></p>
</section>
<div class="sc-card" aria-label="أهم الأخبار المتعلقة بالأمن البحري">
  <div class="sc-row"><div class="sc-l">خلال 24 ساعة السابقة</div><div class="sc-more">6 بنود <a href="/additions.html#sec-00" data-goto="ما تغيّر منذ التقرير السابق">التفاصيل</a></div></div>
  <div class="sc-row"><div class="sc-l">التحذيرات والتنبيهات النشطة</div><div class="sc-more">تحذيران <a href="/additions.html#sec-warnings" data-goto="التحذيرات والتنبيهات النشطة">القسم الرسمي</a></div></div>
  <div class="sc-row"><div class="sc-l">ما يُراقب خلال 24 ساعة</div><div class="sc-more">بند واحد <a href="/additions.html#sec-monitoring" data-goto="المراقبة المستمرة">قسم المراقبة</a></div></div>
</div>
</body></html>
"""

AR_ADDITIONS = """
<html lang="ar"><body>
<section id="sec-00"><h2>ما تغيّر منذ التقرير السابق</h2><ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li><li>6</li></ul></section>
<section id="sec-warnings"><h2>التحذيرات والتنبيهات النشطة</h2><table><thead><tr><th>الجهة</th><th>النص</th></tr></thead><tbody><tr><td>UKMTO</td><td>النص الرسمي الأول</td></tr><tr><td>JMIC</td><td>النص الرسمي الثاني</td></tr></tbody></table></section>
<section id="sec-monitoring"><h2>المراقبة المستمرة</h2><p>متابعة الجهات الرسمية والبلاغات ذات الصلة.</p></section>
</body></html>
"""

EN_REPORT = """
<html lang="en"><body>
<section class="tz" aria-label="Threat level">
  <header class="tz-head"><h3>Threat level</h3></header>
  <ul class="tz-zones"><li>Z1</li><li>Z2</li><li>Z3</li><li>Z4</li></ul>
  <p class="tz-count">Counter: qualifying incidents <span class="bidi">4</span> · confirmed <span class="bidi">1</span> · probable <span class="bidi">1</span> · excluded <span class="bidi">11</span> · non-spatial <span class="bidi">1</span> · total <span class="bidi">16</span></p>
</section>
<div class="sc-card" aria-label="Top maritime security news">
  <div class="sc-row"><div class="sc-l">During the previous 24 hours</div><div class="sc-more">6 items <a href="/reports/en/additions.html#sec-00" data-goto="What changed since the previous report">Details</a></div></div>
  <div class="sc-row"><div class="sc-l">Active warnings and advisories</div><div class="sc-more">2 rows <a href="/reports/en/additions.html#sec-warnings" data-goto="Active Warnings and Advisories">Official section</a></div></div>
  <div class="sc-row"><div class="sc-l">What is monitored over the next 24 hours</div><div class="sc-more">1 item <a href="/reports/en/additions.html#sec-monitoring" data-goto="Continuous Monitoring">Monitoring section</a></div></div>
</div>
</body></html>
"""

EN_ADDITIONS = """
<html lang="en"><body>
<section id="sec-00"><h2>What changed since the previous report</h2><ul><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li><li>6</li></ul></section>
<section id="sec-warnings"><h2>Active Warnings and Advisories</h2><table><tbody><tr><td>UKMTO</td><td>Official text one</td></tr><tr><td>JMIC</td><td>Official text two</td></tr></tbody></table></section>
<section id="sec-monitoring"><h2>Continuous Monitoring</h2><p>Monitor official updates and relevant reports.</p></section>
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

    def test_policy_surface_is_used_for_counter_targets(self):
        policy = {
            "required_in_report": ["مستوى التهديد"],
            "required_in_additions": [
                "ما تغيّر منذ التقرير السابق",
                "التحذيرات والتنبيهات النشطة",
                "المراقبة المستمرة",
            ],
        }
        errors = validate_card_documents(**self.docs(), sections_policy=policy)
        self.assertEqual(errors, [])

    def test_policy_surface_maps_translated_english_targets_after_section_move(self):
        import json
        policy = {
            "required_in_report": ["مستوى التهديد"],
            "required_in_additions": [
                "ما تغيّر",
                "التحذيرات والتنبيهات النشطة",
                "المراقبة المستمرة",
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            glossary = Path(tmp) / "glossary.json"
            glossary.write_text(json.dumps({"entries": {
                "ما تغيّر": "What changed",
                "التحذيرات والتنبيهات النشطة": "Active Warnings and Advisories",
                "قراءة الموقف وتحليل المؤشرات": "Situation reading and indicator analysis",
            }}, ensure_ascii=False), encoding="utf-8")
            errors = validate_card_documents(
                **self.docs(), glossary_path=glossary, sections_policy=policy
            )
        self.assertEqual(errors, [])

    def test_rendered_additions_targets_measure_section_content_and_use_actual_ids(self):
        """قياس البطاقة يجب أن يساوي ما في المصدر نفسه، والمرساة تُشير إلى معرّف قسم حقيقي.
        لا تواريخ ولا أرقام من الذاكرة: يُقاس الإصدار المرجعي الحالي (DAY)."""
        import json
        day = DAY
        source = SITE_ROOT / f"sources/reports/{day}-sectioned.md"
        self.assertTrue(source.exists(), source)
        text = source.read_text(encoding="utf-8")
        sections = site_build_report.parse_sections(text)
        defs = site_build_report.parse_ref_defs(text)
        meta = json.loads((SITE_ROOT / f"sources/meta/{day}.json").read_text(encoding="utf-8"))
        warn_titles = ("التحذيرات والتنبيهات النشطة", "التحذيرات والنشرات الرسمية")
        warn = next((sec for sec in sections if sec["title"] in warn_titles), None)
        watch = next((sec for sec in sections if sec["title"] == "المراقبة المستمرة"), None)
        self.assertIsNotNone(warn)
        self.assertIsNotNone(watch)
        rows = 0
        lines = warn["lines"]
        for i, ln in enumerate(lines):
            if ln.strip().startswith("|") and i + 1 < len(lines) and site_build_report.is_sep(lines[i + 1]):
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    rows += 1
                    j += 1
        items = len([ln for ln in watch["lines"] if ln.strip().startswith("- ")])
        targets = site_build_report._card_targets(sections, sections, meta, defs, day)
        self.assertEqual(targets["warning_count"], rows)
        self.assertEqual(targets["watch_count"], items)
        for key in ("changed_href", "warning_href", "watch_href"):
            self.assertIn("#sec-", targets[key], targets[key])
        self.assertEqual(targets["watch_title"], "المراقبة المستمرة")

    def test_shared_measurement_function_counts_rendered_target_structures(self):
        self.assertEqual(_measure_rendered_target(AR_ADDITIONS, "table_body_rows", "sec-warnings"), 2)
        self.assertEqual(_measure_rendered_target(AR_ADDITIONS, "visible_items", "sec-monitoring"), 1)

    def test_negative_anchor_rule_rejects_section_id_that_lands_on_other_heading(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace(
            "#sec-monitoring\" data-goto=\"المراقبة المستمرة",
            "#sec-warnings\" data-goto=\"المراقبة المستمرة",
        )
        docs["en_report"] = docs["en_report"].replace(
            "#sec-monitoring\" data-goto=\"Continuous Monitoring",
            "#sec-warnings\" data-goto=\"Continuous Monitoring",
        )
        errors = validate_card_documents(**docs)
        self.assertTrue(any("مرسا" in error or "عداد" in error for error in errors), errors)

    def test_monitoring_counter_accepts_full_section_anchor_and_visible_paragraph(self):
        import copy
        import json
        with tempfile.TemporaryDirectory() as tmp:
            registry = copy.deepcopy(json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8")))
            news = next(card for card in registry["cards"] if card["id"] == "maritime-security-news")
            watch = next(counter for counter in news["counters"] if counter["key"] == "watch")
            watch.update({
                "target_title": {"ar": "المراقبة المستمرة", "en": "Continuous Monitoring"},
                "surface": "additions",
                "measurement": "visible_items",
                "anchor_rule": {"mode": "section", "type": "section|heading"},
            })
            registry_path = Path(tmp) / "card_registry.json"
            registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
            docs = self.docs()
            docs["ar_report"] = docs["ar_report"].replace("5 بنود", "بند واحد", 1)
            docs["en_report"] = docs["en_report"].replace("5 items", "1 item", 1)
            docs["ar_report"] = docs["ar_report"].replace(
                "#sec-04-sub-02\" data-goto=\"علامات الإنذار المبكر 24–72 ساعة",
                "#sec-monitoring\" data-goto=\"المراقبة المستمرة",
            )
            docs["en_report"] = docs["en_report"].replace(
                "#sec-04-sub-02\" data-goto=\"Early-warning indicators 24–72 hours",
                "#sec-monitoring\" data-goto=\"Continuous Monitoring",
            )
            docs["ar_additions"] = docs["ar_additions"].replace(
                "</body>", '<section id="sec-monitoring"><h2>المراقبة المستمرة</h2><p>متابعة الجهات الرسمية والبلاغات ذات الصلة.</p></section></body>'
            )
            docs["en_additions"] = docs["en_additions"].replace(
                "</body>", '<section id="sec-monitoring"><h2>Continuous Monitoring</h2><p>Monitor official updates and relevant reports.</p></section></body>'
            )
            policy = {
                "required_in_report": ["مستوى التهديد"],
                "required_in_additions": ["ما تغيّر", "التحذيرات والتنبيهات النشطة", "المراقبة المستمرة"],
            }
            errors = validate_card_documents(**docs, registry_path=registry_path, sections_policy=policy)
        self.assertEqual(errors, [])

    def test_monitoring_anchor_to_unrelated_section_fails_closed(self):
        import copy
        import json
        with tempfile.TemporaryDirectory() as tmp:
            registry = copy.deepcopy(json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8")))
            news = next(card for card in registry["cards"] if card["id"] == "maritime-security-news")
            watch = next(counter for counter in news["counters"] if counter["key"] == "watch")
            watch.update({
                "target_title": {"ar": "المراقبة المستمرة", "en": "Continuous Monitoring"},
                "surface": "additions",
                "measurement": "visible_items",
                "anchor_rule": {"mode": "section", "type": "section|heading"},
            })
            registry_path = Path(tmp) / "card_registry.json"
            registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
            docs = self.docs()
            docs["ar_report"] = docs["ar_report"].replace(
                "#sec-monitoring\" data-goto=\"المراقبة المستمرة",
                "#sec-00\" data-goto=\"المراقبة المستمرة",
            )
            docs["en_report"] = docs["en_report"].replace(
                "#sec-monitoring\" data-goto=\"Continuous Monitoring",
                "#sec-00\" data-goto=\"Continuous Monitoring",
            )
            docs["ar_additions"] = docs["ar_additions"].replace(
                "</body>", '<section id="sec-monitoring"><h2>المراقبة المستمرة</h2><p>متابعة الجهات الرسمية والبلاغات ذات الصلة.</p></section></body>'
            )
            docs["en_additions"] = docs["en_additions"].replace(
                "</body>", '<section id="sec-monitoring"><h2>Continuous Monitoring</h2><p>Monitor official updates and relevant reports.</p></section></body>'
            )
            policy = {
                "required_in_report": ["مستوى التهديد"],
                "required_in_additions": ["ما تغيّر", "التحذيرات والتنبيهات النشطة", "المراقبة المستمرة"],
            }
            errors = validate_card_documents(**docs, registry_path=registry_path, sections_policy=policy)
        self.assertTrue(any("مرسا" in error or "عداد" in error for error in errors), errors)

    def test_stale_fragment_uses_policy_surface_and_data_goto_title(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("#sec-04-sub-02", "#legacy-watch-anchor", 1)
        docs["en_report"] = docs["en_report"].replace("#sec-04-sub-02", "#legacy-watch-anchor", 1)
        errors = validate_card_documents(**docs)
        self.assertEqual(errors, [])

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
            'aria-label="مستوى التهديد"', 'aria-label="بطاقة غير مسجلة"', 1
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
        self.assertTrue(any("خلال 24 ساعة السابقة" in e and "6" in e and "5" in e for e in errors), errors)

    def test_negative_anchor_title_change_fails_closed(self):
        docs = self.docs()
        docs["ar_report"] = docs["ar_report"].replace("#sec-monitoring", "#sec-warnings", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("مرسا" in e or "عداد" in e for e in errors), errors)

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
        docs["ar_report"] = docs["ar_report"].replace("<h3>مستوى التهديد", "<h3>عنوان منحرف", 1)
        errors = validate_card_documents(**docs)
        self.assertTrue(any("مرسا" in e and "القطاعات" in e for e in errors), errors)

    def test_arabic_counter_forms_remain_strict(self):
        expected = {"لا بنود": 0, "بند واحد": 1, "بندان": 2, "3 بنود": 3, "لا تحذيرات": 0, "تحذير واحد": 1, "تحذيران": 2, "3 تحذيرات": 3}
        for text, count in expected.items():
            self.assertEqual(_counter(text + " · التفاصيل", "ar"), count, text)
        self.assertIsNone(_counter("2 صفوف · التفاصيل", "ar"))

    def test_english_threat_counter_is_generated_from_all_registered_labels(self):
        html = '<html lang="ar"><body><p class="tz-count">العدّاد: وقائع مؤهّلة <span class="bidi">4</span> · مؤكدة <span class="bidi">1</span> · مرجّحة <span class="bidi">1</span> · مستثناة <span class="bidi">11</span> · غير مكانية <span class="bidi">1</span> · إجمالي <span class="bidi">16</span></p></body></html>'
        translated, _, _ = translate_page(html, DAY, {}, {})
        expected = ("Counter: qualifying incidents", "confirmed", "probable", "excluded", "non-spatial", "total")
        for label in expected:
            self.assertIn(label, translated)


class HeroKpiGateTests(unittest.TestCase):
    """حواجز المؤشرات الجديدة: العنوان ثابت، الموضع حاضر، والتفصيل مصدره العدّاد."""

    def setUp(self):
        import copy
        import json
        self.copy = copy
        self.meta = json.loads(Path(str(SITE_ROOT / f"sources/meta/{DAY}.json")).read_text(encoding="utf-8"))
        self.zones = json.loads((ROOT / f"web/zones/{DAY}.json").read_text(encoding="utf-8"))
        self.registry = json.loads((ROOT / "appendices/card_registry.json").read_text(encoding="utf-8"))

    def test_current_day_hero_kpis_match_source_contract(self):
        self.assertEqual(validate_hero_kpis(self.meta, self.zones, self.registry), [])

    def test_imo_confirmed_attacks_card_matches_governing_kpi(self):
        import json
        totals = json.loads((ROOT / f"web/kpis-totals/{DAY}.json").read_text(encoding="utf-8"))
        metric = next((item for item in totals["metrics"] if item["id"] == "imo-confirmed-attacks"), None)
        self.assertIsNotNone(metric, "مقياس IMO الثامن مفقود من ملف المقاييس")
        if metric is None:
            return
        card = next((item for item in self.meta["hero_kpis"] if item["id"] == "imo-confirmed-attacks"), None)
        self.assertIsNotNone(card, "البطاقة الثامنة مفقودة من meta")
        if card is None:
            return
        self.assertEqual(card["row"], 2)
        self.assertEqual(card["value"], str(metric["today"]))
        self.assertEqual(card["cumulative"], metric["cumulative"])
        self.assertEqual(card["updated"], metric["updated"])
        contract_card = next(item for item in self.registry["hero_kpis"]["cards"] if item["id"] == card["id"])
        self.assertEqual(contract_card["source"]["kind"], "kpis_totals")
        self.assertEqual(contract_card["source"]["id"], metric["id"])
        self.assertEqual({layer["id"] for layer in contract_card["layers"].values()}, {metric["id"]})

    def test_imo_confirmed_attacks_value_drift_fails_closed(self):
        changed = self.copy.deepcopy(self.meta)
        card = next((item for item in changed["hero_kpis"] if item["id"] == "imo-confirmed-attacks"), None)
        self.assertIsNotNone(card, "البطاقة الثامنة مفقودة من meta")
        if card is None:
            return
        card["cumulative"] = 123
        errors = validate_hero_kpis(changed, self.zones, self.registry)
        self.assertTrue(any("imo-confirmed-attacks" in error and "122" in error and "123" in error for error in errors), errors)

    def _rendered_hero_html(self, report_count=1, screen_count=1):
        tiles = "".join('<div class="kpi hero-kpi"></div>' for _ in range(8))
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
        total = int(counter["unconfirmed_total"])
        qualifying = int(counter["unconfirmed_qualifying"])
        self.assertGreaterEqual(total, qualifying)
        card = next(c for c in self.meta["hero_kpis"] if c["id"] == "unconfirmed-narratives")
        self.assertEqual(card["value"], str(total))
        self.assertIn(str(total), card["detail"])
        self.assertIn(str(qualifying), card["detail"])
        self.assertIn("تُذكر ولا تُحتسب", card["detail"])

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
        self.meta = json.loads(Path(str(SITE_ROOT / "sources/meta/2026-10-31.json")).read_text(encoding="utf-8"))
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
