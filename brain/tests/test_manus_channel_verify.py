"""اختبار انحدار: شرط تحقق قناة Manus المرآة يفشل مغلقًا ولا يُصدّق ادعاءً بلا قياس.

الحالات المثبتة:
  · لا سجل نشر ولا قياس جهوزية اليوم            → غير مستوفى (1)
  · قياس جهوزية موثّق اليوم (الإضافة غير جاهزة) → مستوفى (0)
  · سجل نشر مع تحقق حي مطابق للبصمة             → مستوفى (0)
  · سجل نشر مع تحقق حي فاشل                     → فشل مغلق (2)
  · سجل نشر مع بصمة مخدومة مختلفة               → فشل مغلق (2)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN / 'tools'))

_spec = importlib.util.spec_from_file_location('manus_channel_mod', BRAIN / 'tools' / 'manus_channel_attempt.py')
mc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mc)

DATE = '2026-11-07'


def _root(tmp: Path) -> Path:
    (tmp / 'state').mkdir(parents=True, exist_ok=True)
    (tmp / 'logs' / 'manus-channel').mkdir(parents=True, exist_ok=True)
    return tmp


def _write_marker(tmp: Path, sha: str) -> None:
    (tmp / 'state' / f'manus-channel-{DATE}.json').write_text(
        json.dumps({'date': DATE, 'status': 200, 'bytes': 150000, 'sha256': sha}, ensure_ascii=False),
        encoding='utf-8')


def _write_log(tmp: Path, state: str) -> None:
    (tmp / 'logs' / 'manus-channel' / f'{DATE}.jsonl').write_text(
        json.dumps({'ts': '2026-11-07T18:00:00Z', 'date': DATE, 'state': state,
                    'why': 'إضافة المنصة لم تكتمل استعادتها'}, ensure_ascii=False) + '\n',
        encoding='utf-8')


def test_no_marker_no_measurement_is_not_satisfied(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mc, 'B', _root(tmp_path))
    monkeypatch.setattr(mc, 'LOG_DIR', tmp_path / 'logs' / 'manus-channel')
    rc, why = mc.verify_only(DATE)
    assert rc == 1
    assert 'لا سجل نشر' in why


def test_recorded_measurement_satisfies_condition(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mc, 'B', _root(tmp_path))
    monkeypatch.setattr(mc, 'LOG_DIR', tmp_path / 'logs' / 'manus-channel')
    _write_log(tmp_path, 'not-ready')
    rc, why = mc.verify_only(DATE)
    assert rc == 0
    assert 'قياس موثّق' in why


def test_marker_with_matching_live_fingerprint_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mc, 'B', _root(tmp_path))
    monkeypatch.setattr(mc, 'LOG_DIR', tmp_path / 'logs' / 'manus-channel')
    _write_marker(tmp_path, 'abc123')
    monkeypatch.setattr(mc, 'verify_live', lambda date, timeout=45: {
        'url': 'u', 'status': 200, 'content_type': 'text/html', 'bytes': 150000,
        'sha256': 'abc123', 'ok': True, 'reason': ''})
    rc, why = mc.verify_only(DATE)
    assert rc == 0
    assert 'محقَّقة حيًّا' in why


def test_marker_with_failed_live_check_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mc, 'B', _root(tmp_path))
    monkeypatch.setattr(mc, 'LOG_DIR', tmp_path / 'logs' / 'manus-channel')
    _write_marker(tmp_path, 'abc123')
    monkeypatch.setattr(mc, 'verify_live', lambda date, timeout=45: {
        'url': 'u', 'status': 404, 'content_type': '', 'bytes': 0,
        'sha256': '', 'ok': False, 'reason': 'شرط التحقق غير مستوفى'})
    rc, why = mc.verify_only(DATE)
    assert rc == 2
    assert 'التحقق الحي فشل' in why


def test_marker_with_changed_fingerprint_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mc, 'B', _root(tmp_path))
    monkeypatch.setattr(mc, 'LOG_DIR', tmp_path / 'logs' / 'manus-channel')
    _write_marker(tmp_path, 'abc123')
    monkeypatch.setattr(mc, 'verify_live', lambda date, timeout=45: {
        'url': 'u', 'status': 200, 'content_type': 'text/html', 'bytes': 150000,
        'sha256': 'zzz999', 'ok': True, 'reason': ''})
    rc, why = mc.verify_only(DATE)
    assert rc == 2
    assert 'البصمة' in why


def test_probe_classification() -> None:
    assert mc.classify_probe(0, 'workspace recovery has not completed')[0] == 'not-ready'
    assert mc.classify_probe(1, 'boom')[0] == 'error'
    assert mc.classify_probe(0, 'tools listed')[0] == 'ready'


def test_publish_args_fail_closed_on_unknown_required_field() -> None:
    schema = json.dumps({'properties': {'project_id': {'type': 'string'}, 'secret_token': {'type': 'string'}},
                         'required': ['project_id', 'secret_token']})
    args, why = mc.build_publish_args(schema)
    assert args is None
    assert 'secret_token' in why


def test_publish_args_maps_known_fields() -> None:
    schema = json.dumps({'properties': {'project_id': {'type': 'string'}, 'directory': {'type': 'string'}},
                         'required': ['project_id']})
    args, why = mc.build_publish_args(schema)
    assert args == {'project_id': mc.PROJECT_ID, 'directory': mc.PROJECT_DIR}
    assert why == ''