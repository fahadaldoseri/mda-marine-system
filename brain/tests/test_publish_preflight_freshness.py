"""اختبار انحدار: قرار النشر على قياس جهوزية جديد لا على لقطة مخزّنة (عطل ك-555).

الواقع الذي أوجب الاختبار: لقطة جهوزية قديمة كانت تقول «لا قناة جاهزة» فرفضت
أداة النشر النشر برمز 2، بينما القياس الحي في اللحظة نفسها يقول إن Cloudflare
Pages جاهزة. القاعدة: لا قرار نشر على حالة مخزّنة.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN / 'tools'))

_spec = importlib.util.spec_from_file_location('publish_channels_mod', BRAIN / 'tools' / 'publish_channels.py')
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

READY = {'cloudflare-pages': {'state': 'ready', 'presentation_eligible': True,
                              'url': 'https://mda-bh.pages.dev', 'reason': 'جاهزة'}}
NOT_READY = {'cloudflare-pages': {'state': 'down', 'presentation_eligible': True, 'reason': 'متوقفة'},
             'raw-githack': {'state': 'down', 'presentation_eligible': True, 'reason': 'متوقفة'}}


def test_fresh_statuses_runs_preflight_even_with_stale_cache(tmp_path: Path, monkeypatch) -> None:
    """وجود لقطة مخزّنة سالبة لا يمنع القياس الجديد."""
    logs = tmp_path / 'logs'
    logs.mkdir()
    (logs / 'publish-channel-2026-11-07.json').write_text(
        json.dumps({'date': '2026-11-07', 'channels': NOT_READY, 'at': '2026-11-07T00:01:00Z'},
                   ensure_ascii=False), encoding='utf-8')

    calls = []

    def fake_preflight(root, date, repo):
        calls.append(date)
        return 0, {'channels': READY}

    monkeypatch.setattr(pc, 'preflight', fake_preflight)
    rc, statuses = pc._fresh_statuses(tmp_path, '2026-11-07', 'fahadaldoseri/seawatch-live')

    assert calls == ['2026-11-07'], 'لم يُشغَّل القياس الجديد'
    assert rc == 0
    assert pc.choose_channel(statuses) == 'cloudflare-pages'


def test_publish_fails_closed_when_fresh_preflight_finds_nothing(tmp_path: Path, monkeypatch) -> None:
    """فشل مغلق عند عدم جهوزية أي قناة في القياس الجديد، مع تسجيل السبب الصريح."""
    (tmp_path / 'logs').mkdir()

    def fake_preflight(root, date, repo):
        return 2, {'channels': NOT_READY}

    monkeypatch.setattr(pc, 'preflight', fake_preflight)
    rc = pc.publish(tmp_path, '2026-11-07', 'fahadaldoseri/seawatch-live')

    assert rc == 2
    doc = json.loads((tmp_path / 'logs' / 'publish-2026-11-07.json').read_text(encoding='utf-8'))
    assert doc['status'] == 'failed'
    assert 'fresh preflight' in doc['why']
    assert doc['preflight_rc'] == 2