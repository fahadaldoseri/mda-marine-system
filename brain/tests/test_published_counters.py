#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار انحدار لحارس الأرقام المنشورة (ك-554).

الاختبار يبني نسخة مؤقتة من الملفات المالكة من المشروع نفسه، ثم:
- يثبت الحالة الموجبة: لا مانع عندما كل رقم يطابق مالكه.
- يثبت الحالة السالبة لكل ربط: يُفسد الرقم في المالك أو في السطح فيجب أن يمنع الحارس.

القاعدة المقيسة: حارس لا يفشل عند إفساد مدخله ليس حارسًا.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()
BRAIN = HERE.parents[1]
sys.path.insert(0, str(BRAIN / 'validators'))

import check_published_counters as gate  # noqa: E402

DATE = '2026-11-07'
NEEDED = [
    'appendices/imo-incidents.json',
    'appendices/zone-registry.json',
    'appendices/source-reliability-40.json',
    f'web/meta/{DATE}.json',
    f'web/kpis-totals/{DATE}.json',
    f'feeds/feeds-{DATE}.status.json',
    f'reports/{DATE}-sectioned.md',
    'INDEX.md',
    'runbook/runbook.json',
    'runbook/delivery-policy.json',
    'watchlist/ofac-targets.txt',
]


@pytest.fixture()
def sandbox(tmp_path):
    for rel in NEEDED:
        src = BRAIN / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    # مالك IMO كما كان يوم التقرير (128 · السابق 122)، لا الملف الحي الذي يحدّثه S060 يوميًا.
    shutil.copy2(BRAIN / 'tests/fixtures/imo-incidents-2026-11-04.json',
                 tmp_path / 'appendices/imo-incidents.json')
    return tmp_path


def mutate_json(path: pathlib.Path, fn):
    d = json.loads(path.read_text(encoding='utf-8'))
    fn(d)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


def test_positive_no_blockers(sandbox):
    out, blockers = gate.collect(sandbox, DATE)
    assert not blockers, blockers
    assert len(out) >= 8


def test_imo_historical_number_in_body_is_blocked(sandbox):
    p = sandbox / f'reports/{DATE}-sectioned.md'
    d = json.loads((sandbox / 'appendices/imo-incidents.json').read_text(encoding='utf-8'))
    prev = d['previous']['totals']['confirmed_incidents']
    p.write_text(p.read_text(encoding='utf-8') + f'\n- سجل IMO: {prev} حادثًا.\n', encoding='utf-8')
    _, blockers = gate.collect(sandbox, DATE)
    assert any('الرقم التاريخي' in b for b in blockers), blockers


def test_current_imo_number_missing_is_blocked(sandbox):
    p = sandbox / f'reports/{DATE}-sectioned.md'
    t = p.read_text(encoding='utf-8')
    d = json.loads((sandbox / 'appendices/imo-incidents.json').read_text(encoding='utf-8'))
    cur = str(d['totals']['confirmed_incidents'])
    lines = [l for l in t.splitlines() if 'IMO' in l and cur in l]
    assert lines
    for l in lines:
        t = t.replace(l, l.replace(cur, '999'))
    p.write_text(t, encoding='utf-8')
    _, blockers = gate.collect(sandbox, DATE)
    assert any('لا ينشر الرقم الحالي' in b for b in blockers), blockers


def test_stale_mismatch_is_blocked(sandbox):
    mutate_json(sandbox / f'web/meta/{DATE}.json',
                lambda d: d['source_reliability'].__setitem__('stale', 99))
    _, blockers = gate.collect(sandbox, DATE)
    assert any('التقادم' in b for b in blockers), blockers


def test_card_vs_metric_mismatch_is_blocked(sandbox):
    def bump(d):
        for c in d['hero_kpis']:
            if c.get('id') == 'ukmto-reports':
                c['value'] = '7'
    mutate_json(sandbox / f'web/meta/{DATE}.json', bump)
    _, blockers = gate.collect(sandbox, DATE)
    assert any('البطاقة' in b for b in blockers), blockers


def test_delivery_policy_missing_step_is_blocked(sandbox):
    def drop(d):
        d['manifest_delivery_steps'] = [s for s in d['manifest_delivery_steps'] if s != 'D010']
    mutate_json(sandbox / 'runbook/delivery-policy.json', drop)
    _, blockers = gate.collect(sandbox, DATE)
    assert any('خطوات تسليم' in b for b in blockers), blockers


def test_ofac_junk_entry_is_blocked(sandbox):
    p = sandbox / 'watchlist/ofac-targets.txt'
    p.write_text(p.read_text(encoding='utf-8') + 'UPDATE-001\n', encoding='utf-8')
    _, blockers = gate.collect(sandbox, DATE)
    assert any('OFAC' in b for b in blockers), blockers


def test_probability_shares_must_sum_to_100(sandbox):
    def break_sum(d):
        d['hypotheses'][0]['likelihood'] = '10%'
    mutate_json(sandbox / f'web/meta/{DATE}.json', break_sum)
    _, blockers = gate.collect(sandbox, DATE)
    assert any('النسب المشتقة' in b for b in blockers), blockers


def test_sources_approved_mismatch_is_blocked(sandbox):
    mutate_json(sandbox / f'web/meta/{DATE}.json',
                lambda d: d.__setitem__('sources_approved', 40))
    _, blockers = gate.collect(sandbox, DATE)
    assert any('عدد المصادر' in b for b in blockers), blockers


def test_zones_count_mismatch_is_blocked(sandbox):
    def drop_zone(d):
        d['threat_zone_levels'].pop('Z5', None)
    mutate_json(sandbox / f'web/meta/{DATE}.json', drop_zone)
    _, blockers = gate.collect(sandbox, DATE)
    assert any('عدد القطاعات' in b for b in blockers), blockers

def _declare_no_estimate(d):
    import hypothesis_distribution as hd
    d['distribution_rule'] = hd.NO_ESTIMATE_RULE
    for h in d['hypotheses']:
        h['likelihood'] = 'لا يمكن قياس الاحتمال من المادة الرسمية.'
        h['likelihood_kind'] = hd.NO_ESTIMATE_KIND
        h.pop('likelihood_range', None)


def test_declared_no_estimate_is_accepted(sandbox):
    """إعلان عدم التقدير المعتمد (2026-11-12 و2026-11-18) لا يُقرأ نسبة مفقودة."""
    sys.path.insert(0, str(BRAIN / 'tools'))
    mutate_json(sandbox / f'web/meta/{DATE}.json', _declare_no_estimate)
    out, blockers = gate.collect(sandbox, DATE)
    assert not any('فرضية' in b or 'الفرضيات' in b or 'النسب' in b for b in blockers), blockers
    assert any(row[0] == 'الفرضيات' and row[-1] == 'معلن' for row in out)


def test_mixed_no_estimate_declaration_is_blocked(sandbox):
    sys.path.insert(0, str(BRAIN / 'tools'))

    def mixed(d):
        _declare_no_estimate(d)
        d['hypotheses'][0]['likelihood_kind'] = 'point_from_range'
    mutate_json(sandbox / f'web/meta/{DATE}.json', mixed)
    _, blockers = gate.collect(sandbox, DATE)
    assert any('إعلان الفرضيات غير صالح' in b for b in blockers), blockers


def _owner_updated_after_report(d):
    """القائمة الرسمية تحدّثت بعد يوم التقرير: 138 حاليًا (17 نوفمبر) · 128 سابقًا (4 نوفمبر)."""
    d['previous'] = {'totals': dict(d['totals']), 'retrieved': '2026-11-04', 'incidents_count': 128}
    d['totals'] = {'confirmed_incidents': 138, 'confirmed_seafarer_deaths': 25}
    d.setdefault('source', {})['as_at'] = '17 November 2026'


def test_past_report_is_measured_against_value_in_force_that_day(sandbox):
    """تقرير 7 نوفمبر نشر 128 وهو النافذ يومه؛ تحديث 17 نوفمبر إلى 138 لا يجعله مخالفًا."""
    mutate_json(sandbox / 'appendices/imo-incidents.json', _owner_updated_after_report)
    out, blockers = gate.collect(sandbox, DATE)
    assert not any('IMO' in b for b in blockers), blockers
    assert any('النافذة يوم التقرير' in str(row[3]) for row in out)


def test_past_report_missing_value_in_force_is_blocked(sandbox):
    mutate_json(sandbox / 'appendices/imo-incidents.json', _owner_updated_after_report)
    report = sandbox / f'reports/{DATE}-sectioned.md'
    report.write_text(report.read_text(encoding='utf-8').replace('128', '١٢٨'), encoding='utf-8')
    _, blockers = gate.collect(sandbox, DATE)
    assert any('النافذة يومه' in b for b in blockers), blockers
