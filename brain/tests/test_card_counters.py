#!/usr/bin/env python3
"""اختبارات ثابتة لبوابة عدادات بطاقة أهم الأخبار."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validators.check_card_counters import validate_card_documents  # noqa: E402


AR_REPORT = """
<html lang="ar"><body>
<div class="sc-card">
  <div class="sc-row"><div class="sc-l">ما تغيّر</div><div class="sc-more">6 بنود <a href="/additions.html#sec-00" data-goto="ما تغيّر منذ التقرير السابق">التفاصيل</a></div></div>
  <div class="sc-row"><div class="sc-l">التحذيرات والنشرات الرسمية</div><div class="sc-more">2 صفوف <a href="/reports/2026-10-31.html#sec-06" data-goto="التحذيرات والنشرات الرسمية">القسم الرسمي</a></div></div>
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
<div class="sc-card">
  <div class="sc-row"><div class="sc-l">What changed</div><div class="sc-more">6 items <a href="/additions.html#sec-00" data-goto="What changed since the previous report">Details</a></div></div>
  <div class="sc-row"><div class="sc-l">Official warnings and advisories</div><div class="sc-more">2 rows <a href="/reports/2026-10-31.html#sec-06" data-goto="Official warnings and advisories">Official section</a></div></div>
  <div class="sc-row"><div class="sc-l">What is monitored over the next 24–72 hours</div><div class="sc-more">5 items <a href="/additions.html#sec-04-sub-02" data-goto="Early-warning indicators 24–72 hours">Indicators</a></div></div>
</div>
<section id="sec-06"><h2>Official Warnings and Advisories</h2><table><tbody><tr><td>UKMTO</td><td>Official text one</td></tr><tr><td>JMIC</td><td>Official text two</td></tr></tbody></table></section>
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
        }

    def test_positive_matches_counts_titles_and_anchors(self):
        self.assertEqual(validate_card_documents(**self.docs()), [])

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


if __name__ == "__main__":
    unittest.main()
