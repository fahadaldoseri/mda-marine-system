#!/usr/bin/env python3
"""إعادة إرسال ملخص التقرير على تلغرام — مسار محكوم بأمر صاحب القرار.

القاعدة: منع التكرار التلقائي يبقى كما هو. لا يُعاد الإرسال إلا بتفويض مكتوب
ومؤرّخ في ملف تفويض لليوم نفسه، يحمل: التاريخ · الجهة · السبب · المفوِّض · وقت التفويض.
غياب التفويض أو نقصه = فشل مغلق برمز 2 (لا إرسال).

الاستخدام:
  python3 tools/telegram_resend.py --date 2026-11-07 --digest logs/tg-digest-2026-11-07.html \
      [--targets primary] [--dry-run]
ملف التفويض: state/telegram-resend-<date>.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
MIN_REASON = 10


def authorization_path(date: str) -> Path:
    return B / 'state' / f'telegram-resend-{date}.json'


def read_authorization(date: str) -> tuple[dict | None, str]:
    """يعيد (التفويض، سبب الرفض) — رفض مغلق عند أي نقص."""
    path = authorization_path(date)
    if not path.is_file():
        return None, f'لا تفويض إعادة إرسال لهذا التاريخ: {path}'
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f'ملف تفويض غير صالح: {exc}'
    if str(doc.get('date')) != date:
        return None, f'تاريخ التفويض {doc.get("date")} لا يطابق تاريخ الإرسال {date}'
    for field in ('authorized_by', 'authorized_at', 'channel', 'reason'):
        if not str(doc.get(field) or '').strip():
            return None, f'التفويض ناقص الحقل: {field}'
    if len(str(doc['reason']).strip()) < MIN_REASON:
        return None, 'سبب التفويض أقصر من الحد الأدنى المقروء'
    return doc, ''


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--digest', required=True, help='ملف نص الملخص المرسل')
    ap.add_argument('--targets', default='primary')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)

    auth, why = read_authorization(a.date)
    if auth is None:
        print(f'[تلغرام] رفض الإعادة — {why}')
        return 2

    digest = Path(a.digest)
    if not digest.is_absolute():
        digest = B / digest
    if not digest.is_file():
        print(f'[تلغرام] رفض الإعادة — ملف الملخص غير موجود: {digest}')
        return 2

    cmd = [sys.executable, str(B / 'tools' / 'telegram_send.py'),
           '--file', str(digest), '--targets', a.targets,
           '--date', a.date, '--owner-approved', '--reason', str(auth['reason']).strip()]
    if a.dry_run:
        cmd.append('--dry-run')
    print(f"[تلغرام] إعادة إرسال محكومة — المفوِّض: {auth['authorized_by']} · "
          f"الجهة: {auth['channel']} · السبب: {str(auth['reason']).strip()[:80]}")
    proc = subprocess.run(cmd, cwd=B, text=True)
    return proc.returncode


if __name__ == '__main__':
    raise SystemExit(main())