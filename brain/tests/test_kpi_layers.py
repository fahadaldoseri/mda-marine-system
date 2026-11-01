#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات بوابة طبقات البطاقات: موجب على المخرج الحقيقي، وسالب بتغيير رقم في نسخة معزولة."""
import pathlib
import shutil
import os
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'validators'))
import check_kpi_layers as G  # noqa: E402

DATE = '2026-10-31'
BRAIN = ROOT
DIST = SITE_ROOT = pathlib.Path(__file__).resolve().parents[1].parent / 'seawatch'
DIST = SITE_ROOT / 'dist'


def test_positive_on_real_output():
    problems = G.check(DATE, DIST, BRAIN)
    assert problems == [], problems


def test_negative_tampered_cumulative(tmp_path):
    dst = tmp_path / 'dist'
    for sub in ('reports', 'reports/en'):
        (dst / sub).mkdir(parents=True)
        src = DIST / sub / f'{DATE}.html'
        if not src.exists():
            return
        html = src.read_text(encoding='utf-8')
        html = html.replace('<b class="bidi">158</b>', '<b class="bidi">159</b>', 1)
        (dst / sub / f'{DATE}.html').write_text(html, encoding='utf-8')
    problems = G.check(DATE, dst, BRAIN)
    assert any('طبقة cumulative' in p for p in problems), problems
    shutil.rmtree(dst, ignore_errors=True)


def test_negative_missing_metrics(tmp_path):
    problems = G.check('2026-11-01', DIST, BRAIN)
    assert problems and 'مفقود' in problems[0], problems


if __name__ == '__main__':
    test_positive_on_real_output()
    print('   ✔ موجب')
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        test_negative_tampered_cumulative(pathlib.Path(t))
    print('   ✔ سالب (رقم مُحرَّف)')
    test_negative_missing_metrics(pathlib.Path('/tmp'))
    print('   ✔ سالب (ملف مقاييس مفقود)')