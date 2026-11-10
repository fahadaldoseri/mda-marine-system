#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات موجب/سالب لحراس المرحلة (د): الروابط والفهرس · أسلوب الغائب · عقد النشر.

كل حارس يُقاس على شجرة مؤقتة صغيرة: حالة مخالفة تُنتج 2، وحالة نظيفة تُنتج 0،
ومدخل بيئة ناقص يُنتج 3. لا يعتمد الاختبار على مخرج المشروع الحقيقي.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parent
VALIDATORS = BRAIN / "validators"
BRAIN = Path(__file__).resolve().parents[1]
SITE = Path(os.environ.get("SITE_DIR") or os.environ.get("SITE")
            or BRAIN.parent / "seawatch")


def run(script: Path, *args) -> int:
    r = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True)
    return r.returncode


PAGE_OK = """<!DOCTYPE html><html dir="rtl"><body>
<nav class="toc"><a href="#sec-01">سجل الأحداث</a><a href="#sec-02">مستوى التهديد</a></nav>
<section id="sec-01"><h2 id="h-01">سجل الأحداث</h2><p>نص</p></section>
<section id="sec-02"><h2 id="h-02">مستوى التهديد</h2><p>نص</p></section>
<a href="/other.html#sec-09">رابط سليم</a>
</body></html>"""

PAGE_OTHER = """<!DOCTYPE html><html dir="rtl"><body>
<section id="sec-09"><h2 id="h-09">قسم آخر</h2><p>نص</p></section>
</body></html>"""


class TestSiteLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guards_"))
        (self.tmp / "dist").mkdir()
        (self.tmp / "dist" / "other.html").write_text(PAGE_OTHER, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, html):
        (self.tmp / "dist" / "index.html").write_text(html, encoding="utf-8")

    def test_clean_passes(self):
        self.write(PAGE_OK)
        self.assertEqual(run(VALIDATORS / "check_site_links.py", "--site", str(self.tmp)), 0)

    def test_broken_anchor_fails(self):
        self.write(PAGE_OK.replace('href="#sec-02"', 'href="#sec-missing"'))
        self.assertEqual(run(VALIDATORS / "check_site_links.py", "--site", str(self.tmp)), 2)

    def test_empty_href_fails(self):
        self.write(PAGE_OK.replace('<a href="/other.html#sec-09">رابط سليم</a>', '<a href="#">رابط فارغ</a>'))
        self.assertEqual(run(VALIDATORS / "check_site_links.py", "--site", str(self.tmp)), 2)

    def test_unencrypted_link_fails(self):
        self.write(PAGE_OK.replace("/other.html#sec-09", "http://example.com/x"))
        self.assertEqual(run(VALIDATORS / "check_site_links.py", "--site", str(self.tmp)), 2)

    def test_cross_page_anchor_fails_when_id_absent(self):
        self.write(PAGE_OK.replace("/other.html#sec-09", "/other.html#sec-404"))
        self.assertEqual(run(VALIDATORS / "check_site_links.py", "--site", str(self.tmp)), 2)

    def test_section_outside_toc_fails(self):
        self.write(PAGE_OK.replace('<a href="#sec-02">مستوى التهديد</a>', ""))
        self.assertEqual(run(VALIDATORS / "check_site_links.py", "--site", str(self.tmp)), 2)

    def test_missing_dist_is_env_error(self):
        self.assertEqual(run(VALIDATORS / "check_site_links.py", "--site", str(self.tmp / "nope")), 3)


class TestImperativeStyle(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guards_imp_"))
        (self.tmp / "dist").mkdir()
        (self.tmp / "generator").mkdir()
        src = SITE / "generator" / "third_person.py"
        if src.is_file():
            shutil.copy2(src, self.tmp / "generator" / "third_person.py")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_imperative_fails_and_third_person_passes(self):
        if not (self.tmp / "generator" / "third_person.py").is_file():
            self.skipTest("وحدة أسلوب الغائب غير متاحة")
        (self.tmp / "dist" / "index.html").write_text(
            "<html><body><p>ارفعوا التأهب قبل دخول المضيق.</p></body></html>", encoding="utf-8")
        self.assertEqual(run(VALIDATORS / "check_imperative_style.py", "--site", str(self.tmp)), 2)
        (self.tmp / "dist" / "index.html").write_text(
            "<html><body><p>يُرفع التأهب قبل دخول المضيق.</p></body></html>", encoding="utf-8")
        self.assertEqual(run(VALIDATORS / "check_imperative_style.py", "--site", str(self.tmp)), 0)

    def test_script_content_is_ignored(self):
        if not (self.tmp / "generator" / "third_person.py").is_file():
            self.skipTest("وحدة أسلوب الغائب غير متاحة")
        (self.tmp / "dist" / "index.html").write_text(
            "<html><body><script>var s='ارفعوا التأهب';</script><p>يُرفع التأهب.</p></body></html>",
            encoding="utf-8")
        self.assertEqual(run(VALIDATORS / "check_imperative_style.py", "--site", str(self.tmp)), 0)

    def test_missing_unit_is_env_error(self):
        (self.tmp / "generator" / "third_person.py").unlink(missing_ok=True)
        (self.tmp / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
        self.assertEqual(run(VALIDATORS / "check_imperative_style.py", "--site", str(self.tmp)), 3)


class TestPublishContract(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guards_pub_"))
        (self.tmp / "brain" / "runbook").mkdir(parents=True)
        (self.tmp / "brain" / "tools").mkdir(parents=True)
        (self.tmp / "site" / "tools").mkdir(parents=True)
        (self.tmp / "brain" / "runbook" / "runbook.json").write_text(
            json.dumps({"steps": [{"id": "D010", "command": "python3 brain/tools/publish_channels.py --go"}]},
                       ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def args(self):
        return ["--brain", str(self.tmp / "brain"), "--site", str(self.tmp / "site")]

    def test_rogue_publisher_fails(self):
        (self.tmp / "site" / "tools" / "quick_publish.sh").write_text(
            "#!/bin/sh\ngit push origin main\n", encoding="utf-8")
        self.assertEqual(run(VALIDATORS / "check_publish_contract.py", *self.args()), 2)

    def test_declared_tool_passes(self):
        (self.tmp / "brain" / "tools" / "publish_channels.py").write_text(
            "import subprocess\nsubprocess.run(['git','push','origin','main'])\n", encoding="utf-8")
        self.assertEqual(run(VALIDATORS / "check_publish_contract.py", *self.args()), 0)

    def test_comment_only_is_ignored(self):
        (self.tmp / "site" / "tools" / "notes.py").write_text(
            "# النشر يتم عبر git push في خطوة المانيفست\nx = 1\n", encoding="utf-8")
        self.assertEqual(run(VALIDATORS / "check_publish_contract.py", *self.args()), 0)

    def test_missing_manifest_is_env_error(self):
        (self.tmp / "brain" / "runbook" / "runbook.json").unlink()
        self.assertEqual(run(VALIDATORS / "check_publish_contract.py", *self.args()), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)