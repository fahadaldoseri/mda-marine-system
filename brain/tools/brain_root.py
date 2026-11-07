#!/usr/bin/env python3
"""اشتقاق جذر brain القانوني بالقياس لا بالاسم — وفشل مغلق.

العطل الذي أوجب هذه الوحدة: أدوات حيّة كانت تشتق جذرها بالبحث عن مجلد باسم
`brain-marine-news` في سلسلة الآباء، فإذا وُجدت شجرة قديمة بهذا الاسم كتبت
الأداة فيها بدل الجذر القانوني، فيتخلّف القياس عن الواقع بلا رسالة خطأ.

القاعدة: الجذر القانوني هو أول مجلد صعودًا يحوي `runbook/runbook.json`،
أو قيمة `BRAIN_DIR` إن كانت تحوي المانيفست. غير ذلك = فشل مغلق.
"""
from __future__ import annotations

import os
from pathlib import Path

MANIFEST_REL = Path('runbook') / 'runbook.json'


def is_brain(path: Path) -> bool:
    """هل هذا المجلد جذر brain قانوني (يحوي المانيفست)؟"""
    return (Path(path) / MANIFEST_REL).is_file()


def canonical_brain_root(start: Path | str | None = None) -> Path:
    """يعيد جذر brain القانوني، أو يفشل مغلقًا برسالة تسمّي ما فُحص."""
    env = os.environ.get('BRAIN_DIR')
    if env:
        p = Path(env).resolve()
        if is_brain(p):
            return p
        raise SystemExit(f'BRAIN_DIR لا يحوي {MANIFEST_REL}: {p}')

    base = Path(start).resolve() if start else Path(__file__).resolve().parent
    checked = []
    for cand in [base, *base.parents]:
        checked.append(str(cand))
        if is_brain(cand):
            return cand
    raise SystemExit('تعذّر العثور على جذر brain قانوني (runbook/runbook.json). '
                     'المسارات المفحوصة: ' + ' · '.join(checked[:6]))


def canonical_site_root(start: Path | str | None = None) -> Path:
    """يعيد جذر الموقع (مجلد يحوي dist/) صعودًا من نقطة البداية."""
    base = Path(start).resolve() if start else Path(__file__).resolve().parent
    checked = []
    for cand in [base, *base.parents]:
        checked.append(str(cand))
        if (cand / 'dist').is_dir():
            return cand
    raise SystemExit('تعذّر العثور على جذر موقع يحوي dist/. '
                     'المسارات المفحوصة: ' + ' · '.join(checked[:6]))