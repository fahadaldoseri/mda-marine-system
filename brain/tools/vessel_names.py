#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""وحدة موحّدة لاستخراج أسماء السفن من نص التقرير وملف الواجهة.

الغرض: مصدر واحد لتحديد «السفن المذكورة في إصدار اليوم» تستخدمه
أدوات توليد قائمة فحص العقوبات وبوابة تغطية الفحص، فلا تبقى سفينة بلا فحص.
"""
from __future__ import annotations
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

import json
import re
from pathlib import Path

B = Path(f'{BRAIN}')

# كلمات وظيفية لا تُكوِّن اسم سفينة
STOP = {
    'THE', 'AND', 'OF', 'FOR', 'WITH', 'FROM', 'TO', 'IN', 'ON', 'AT', 'BY',
    'LTD', 'LLC', 'INC', 'CO', 'SA', 'SHIP', 'SHIPS', 'SHIPPING', 'LINE', 'LINES',
    'MARINE', 'MARITIME', 'GROUP', 'GLOBAL', 'INTERNATIONAL', 'TRADING', 'COMPANY',
    'STAR', 'SEA', 'SEAS', 'OCEAN', 'PORT', 'PORTS', 'NEW', 'NORTH', 'SOUTH',
    'EAST', 'WEST', 'GULF', 'STRAIT', 'CAPE', 'BAY', 'ISLAND', 'ISLANDS',
}

# مختصرات لاتينية ليست أسماء سفن (جهات ومصطلحات ونطاقات)
# أسماء الأشهر واختصاراتها: تُظهرها صيغة DTG فلا تُقرأ أسماء سفن
MONTHS = {
    'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'SEPT', 'OCT',
    'NOV', 'DEC',
}
DENY = {
    'UKMTO', 'NAVAREA', 'JMIC', 'MSCIO', 'IMO', 'AIS', 'OFAC', 'SDN', 'UN', 'UNSC',
    'IRGC', 'CENTCOM', 'CMPC', 'CSIS', 'SOH', 'EEZ', 'GPS', 'VHF', 'SOLAS', 'ISM',
    'ISPS', 'MARSEC', 'NAVWARN', 'MRCC', 'SAR', 'OIL', 'LNG', 'LPG', 'VLCC', 'SBM',
    'ADNOC', 'AD', 'DPA', 'JWC', 'LMA', 'IUMI', 'BIMCO', 'DWT', 'TEU', 'AIS', 'MMSI',
    'CH-', 'REV', 'NO', 'WARNING', 'SUMMARY', 'ANNEX', 'NATO', 'EUCENTCOM', 'CPI',
    # رموز ومصطلحات تحليلية تُكتب لاتينية في القاموس فلا تُقرأ أسماء سفن
    'ICD', 'DTG', 'EST', 'ACH', 'UTC', 'TZ', 'MDA', 'RTL',
    # آثار جلب ونشرات لا أسماء سفن: «HTTP 403» من سطر تغطية المصادر أوقف G054 يوم 21 نوفمبر
    'HTTP', 'HTTPS', 'ADVISORY', 'UPDATE', 'ISNA',
}

_TOKEN = r'[A-Z][A-Z0-9]*(?:[- ][A-Z0-9]+){0,3}'
_CAND = re.compile(rf'(?<![A-Za-z0-9]){_TOKEN}(?![A-Za-z0-9])')

VESSEL_CONTEXT = ('سفينة', 'ناقلة', 'قُطر', 'قطر', 'حطام', 'باخرة', 'سفن', 'مركب')


def _plausible(cand: str) -> bool:
    toks = [t for t in re.split(r'[-\s]+', cand) if t]
    if len(toks) < 2:
        return False
    if len(cand) < 6 or len(cand) > 40:
        return False
    if any(re.fullmatch(r'(19|20)\d\d', t) for t in toks):
        return False
    if any(t in DENY for t in toks):
        return False
    if any(t in MONTHS for t in toks):
        return False
    letters = [t for t in toks if t.isalpha() and len(t) >= 3 and t not in STOP]
    if not letters:
        return False
    if all(t in STOP for t in toks):
        return False
    return True


def extract(text: str) -> list[str]:
    """يُرجع أسماء السفن المرشّحة بترتيب تكرارها."""
    strong: set[str] = set()
    # إشارات قوية: داخل **غامق** أو «» أو قرب كلمة سياقية
    for m in re.finditer(r'\*\*([^*]{3,60})\*\*|«([^»]{3,60})»', text):
        frag = m.group(1) or m.group(2)
        for c in _CAND.findall(frag):
            if _plausible(c):
                strong.add(c.strip())
    counts: dict[str, int] = {}
    for m in _CAND.finditer(text):
        c = m.group(0).strip()
        if not _plausible(c):
            continue
        tail = text[max(0, m.start() - 60): m.start()]
        head = text[m.end(): m.end() + 40]
        near = any(w in tail[-40:] or w in head for w in VESSEL_CONTEXT)
        counts[c] = counts.get(c, 0) + (2 if near else 1)
    out = {c: n for c, n in counts.items() if n >= 2 or c in strong}
    return [c for c, _ in sorted(out.items(), key=lambda kv: (-kv[1], kv[0]))]


def from_ledger(day: str) -> list[str]:
    """أسماء السفن من حقل vessel_name في دفتر اليوم: مرجع منظَّم قاطع يُفحص مهما قصر الاسم.

    الاستخراج من النص يشترط مقطعين فأكثر، فيسقط اسم ذو مقطع واحد مثل «ST3» من فحص العقوبات
    (seawatch-brain #6). الدفتر لا يحتاج استدلالًا بالنمط، فكل اسم فيه يُضاف كما هو.
    """
    path = B / 'cumulative-2026' / 'daily' / f'{day}.json'
    if not path.exists():
        return []
    try:
        recs = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(recs, list):
        return []
    out = []
    for r in recs:
        if isinstance(r, dict):
            n = str(r.get('vessel_name') or '').strip()
            if n and n not in ('—', '-', 'غير معلن', 'غير محدد'):
                out.append(n)
    return out


def from_report(day: str) -> list[str]:
    """يجمع السفن من نص التقرير وملف الواجهة معًا."""
    names: list[str] = []
    md = B / 'reports' / f'{day}-sectioned.md'
    if md.exists():
        names += extract(md.read_text(encoding='utf-8'))
    meta = B / 'web' / 'meta' / f'{day}.json'
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
            # القاموس يشرح رموزًا لاتينية (ICD · DTG · EST) وليست أسماء سفن، فيُستثنى من الاستخراج
            data.pop('glossary', None)
            names += extract(json.dumps(data, ensure_ascii=False))
        except json.JSONDecodeError:
            pass
    names += from_ledger(day)
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if any(a in ('--help', '-h') for a in args):
        print(__doc__)
        raise SystemExit(0)
    unknown = [a for a in args if a.startswith('-')]
    if unknown or len(args) > 1:
        print(f'وسيط غير معروف: {unknown[0]}' if unknown else 'الاستخدام: vessel_names.py [التاريخ]', file=sys.stderr)
        raise SystemExit(2)
    d = args[0] if args else ''
    for n in from_report(d):
        print(n)
