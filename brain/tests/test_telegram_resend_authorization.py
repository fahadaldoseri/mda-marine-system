"""اختبار انحدار: إعادة إرسال تلغرام لا تعمل إلا بتفويض مكتوب ومؤرّخ.

يمنع حالتين: إعادة إرسال بلا تفويض، وتفويض ناقص أو لتاريخ آخر.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN / 'tools'))

_spec = importlib.util.spec_from_file_location('telegram_resend_mod', BRAIN / 'tools' / 'telegram_resend.py')
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)

DATE = '2026-11-07'
FULL = {'date': DATE, 'authorized_by': 'فهد الدوسري', 'authorized_at': '2026-11-07T18:05:00Z',
        'channel': 'personal', 'reason': 'أمر صريح من المالك: إعادة إرسال ملخص التقرير بعد اكتمال النشر'}


def _write(tmp: Path, doc: dict) -> None:
    (tmp / 'state').mkdir(exist_ok=True)
    (tmp / 'state' / f'telegram-resend-{DATE}.json').write_text(
        json.dumps(doc, ensure_ascii=False), encoding='utf-8')


def test_missing_authorization_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(tr, 'B', tmp_path)
    auth, why = tr.read_authorization(DATE)
    assert auth is None
    assert 'لا تفويض' in why


def test_incomplete_authorization_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(tr, 'B', tmp_path)
    _write(tmp_path, {**FULL, 'reason': 'قصير'})
    auth, why = tr.read_authorization(DATE)
    assert auth is None
    assert 'الحد الأدنى' in why or 'ناقص' in why


def test_authorization_for_other_date_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(tr, 'B', tmp_path)
    _write(tmp_path, {**FULL, 'date': '2026-11-06'})
    auth, why = tr.read_authorization(DATE)
    assert auth is None
    assert 'لا يطابق' in why


def test_full_authorization_is_accepted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(tr, 'B', tmp_path)
    _write(tmp_path, FULL)
    auth, why = tr.read_authorization(DATE)
    assert auth is not None and why == ''
    assert auth['authorized_by'] == 'فهد الدوسري'


def test_resend_requires_digest_file(tmp_path: Path, monkeypatch, capsys) -> None:
    """تفويض صحيح بلا ملف ملخص = رفض بلا إرسال."""
    monkeypatch.setattr(tr, 'B', tmp_path)
    _write(tmp_path, FULL)
    rc = tr.main(['--date', DATE, '--digest', 'logs/لا-يوجد.html'])
    assert rc == 2
    assert 'ملف الملخص غير موجود' in capsys.readouterr().out


def test_automatic_duplicate_guard_still_blocks_without_authorization() -> None:
    """منع التكرار التلقائي في أداة الإرسال يبقى فعّالًا: بلا --owner-approved يُرفض."""
    spec = importlib.util.spec_from_file_location('telegram_send_mod', BRAIN / 'tools' / 'telegram_send.py')
    ts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ts)

    class Args:
        owner_approved = False
        daily_report = True
        date = DATE
        document = None
        photo = None
        validate_only = False

    text = 'التقرير اليومي لأمن الملاحة — الإصدار و ب · الفترة · توقيت البحرين'
    allowed, verdict = ts.guard(Args(), text, [{'label': 'المحادثة الشخصية'}])
    if ts._sent_today('المحادثة الشخصية', DATE):
        assert allowed is False
        assert 'لا تكرار' in verdict
    else:
        assert allowed is True