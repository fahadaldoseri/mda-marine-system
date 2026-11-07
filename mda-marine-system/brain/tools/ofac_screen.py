#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص أسماء السفن والوسطاء مقابل قائمة OFAC SDN.

قاعدة المطابقة: رقم IMO أولًا، ثم الاسم الكامل أو نسبة كلمات عالية. لا تُعد كلمة
واحدة مشتركة تطابقًا، وتُحفظ طريقة المطابقة ودرجتها مع كل نتيجة.
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

import csv
import datetime as dt
import io
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

URLS = ['https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV',
        'https://www.treasury.gov/ofac/downloads/sdn.csv']
UA = {'User-Agent': 'Mozilla/5.0'}
IMO_RE = re.compile(r'\bIMO\s*(?:NO\.?|NUMBER|#)?\s*([0-9]{7})\b', re.IGNORECASE)

# قائمة معلنة لكلمات وظيفية شائعة في أسماء الشركات؛ لا تُحذف أي كلمة أخرى بسبب طولها.
NAME_STOP_WORDS = frozenset({
    'AND', 'CO', 'COMPANY', 'CORP', 'GROUP', 'INC', 'INTERNATIONAL', 'LTD', 'LLC',
    'LINE', 'LINES', 'MARINE', 'MARITIME', 'MV', 'MT', 'OF', 'SA', 'SHIP', 'SHIPPING',
    'THE', 'TRADING',
})
NAME_PARTIAL_MIN_SCORE = 75


def extract_imos(value: str) -> set[str]:
    """يستخرج أرقام IMO ذات السبعة أرقام من أي حقل نصي."""
    return {m.group(1) for m in IMO_RE.finditer(str(value or ''))}


def _name_tokens(value: str) -> set[str]:
    """يعيد كلمات الاسم بعد حذف كلمات الوظيفة المعلنة فقط."""
    without_imo = IMO_RE.sub(' ', str(value or '').upper())
    tokens = re.findall(r'[A-Z0-9]+', without_imo)
    return {token for token in tokens if token not in NAME_STOP_WORDS and token != 'IMO'}


def _normalise_entry(entry: Any) -> dict[str, Any]:
    """يوحّد إدخالات القائمة، مع قبول اسم نصي للتوافق مع المستعملين السابقين."""
    if isinstance(entry, str):
        return {'name': entry, 'imos': extract_imos(entry)}
    if not isinstance(entry, dict):
        return {'name': str(entry), 'imos': set()}
    name = str(entry.get('name') or entry.get('sdn_name') or '').strip()
    imos: set[str] = set()
    for key in ('imos', 'imo', 'imo_number'):
        value = entry.get(key)
        if isinstance(value, (list, tuple, set)):
            for item in value:
                text = str(item)
                imos |= extract_imos(text)
                if re.fullmatch(r'\d{7}', text.strip()):
                    imos.add(text.strip())
        elif value:
            text = str(value)
            imos |= extract_imos(text)
            if re.fullmatch(r'\d{7}', text.strip()):
                imos.add(text.strip())
    imos |= extract_imos(name)
    return {'name': name, 'imos': imos}


def _name_score(target: str, candidate: str) -> tuple[str | None, int]:
    target_tokens = _name_tokens(target)
    candidate_tokens = _name_tokens(candidate)
    if not target_tokens or not candidate_tokens:
        return None, 0
    shared = target_tokens & candidate_tokens
    if target_tokens == candidate_tokens:
        return 'name_full', 100
    # مقياس F1 يمنع اسمًا من كلمة واحدة من مطابقة اسم من كلمتين بكلمة مشتركة.
    if len(shared) < 2:
        return None, round(100 * (2 * len(shared) / (len(target_tokens) + len(candidate_tokens))))
    score = round(100 * (2 * len(shared) / (len(target_tokens) + len(candidate_tokens))))
    return ('name_partial', score) if score >= NAME_PARTIAL_MIN_SCORE else (None, score)


def _detail(entry: dict[str, Any], match_type: str, score: int) -> dict[str, Any]:
    return {
        'name': entry['name'],
        'type': match_type,
        'score': score,
        'percentage': f'{score}%',
    }


def _result(target: str, result: str, details: list[dict[str, Any]]) -> dict[str, Any]:
    first = details[0] if details else None
    return {
        'target': target,
        'match': [d['name'] for d in details[:5]],
        'match_details': details[:5],
        'match_type': first['type'] if first else None,
        'match_score': first['score'] if first else None,
        'match_percentage': first['percentage'] if first else None,
        'result': result,
    }


def match_target(target: str, entries: list[Any]) -> dict[str, Any]:
    """يفحص مستهدفًا: IMO أولًا، ثم الاسم الكامل، ثم الاسم الجزئي عالي النسبة."""
    normalised = [_normalise_entry(entry) for entry in entries]
    target_imos = extract_imos(target)
    imo_hits = [entry for entry in normalised if target_imos & entry['imos']]
    if imo_hits:
        return _result(target, 'match', [_detail(entry, 'imo', 100) for entry in imo_hits])

    full_hits, partial_hits = [], []
    for entry in normalised:
        match_type, score = _name_score(target, entry['name'])
        if match_type == 'name_full':
            full_hits.append(_detail(entry, match_type, score))
        elif match_type == 'name_partial':
            partial_hits.append(_detail(entry, match_type, score))
    if full_hits:
        return _result(target, 'match', full_hits)
    if partial_hits:
        partial_hits.sort(key=lambda detail: (-detail['score'], detail['name']))
        return _result(target, 'review', partial_hits)
    return _result(target, 'no_match', [])


def load() -> tuple[str | None, list[dict[str, Any]]]:
    """يحمّل أسماء القائمة وأرقام IMO الموجودة في صفوفها."""
    for url in URLS:
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            text = raw.decode('utf-8', 'ignore')
            entries = []
            for row in csv.reader(io.StringIO(text)):
                fields = [field.strip() for field in row if field.strip()]
                if not fields:
                    continue
                name = next((field for field in fields[1:] if not field.isdigit()), fields[0])
                entries.append({'name': name.upper(), 'imos': sorted(extract_imos(' '.join(fields)))})
            if entries:
                return url, entries
        except Exception as e:
            print(f"  تعذر {url[:60]} → {str(e)[:60]}")
    return None, []


def partial_strength(vessel: str, names: list[str]) -> tuple[str, str]:
    """يحافظ على واجهة التصنيف القديمة مع تطبيق قاعدة الاسم الموزون."""
    details = []
    for name in names:
        match_type, score = _name_score(vessel, name)
        if match_type == 'name_partial':
            details.append(f'{name} ({score}%)')
    return ('warning', ' · '.join(details)) if details else ('info', ' · '.join(names))


def main() -> int:
    seen, targets = set(), []
    for line in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines():
        target = line.strip()
        if target and target.upper() not in seen:
            seen.add(target.upper())
            targets.append(target)
    if not targets:
        print("  · لا مستهدف في القائمة — لا فحص مطلوب")
        return 0
    source, entries = load()
    if not entries:
        print("  ✘ تعذر تحميل قائمة SDN — تُسجَّل النتيجة (تعذر) ولا يُدَّعى فحص")
        (Path(f'{BRAIN}/archive') / 'ofac-screen-latest.json').write_text(
            json.dumps({'utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'list': None, 'names': 0, 'status': 'list_unavailable',
                        'rule_note': 'تعذر تحميل قائمة SDN — لا يُدَّعى فحص',
                        'results': [_result(t, 'no_result', []) for t in targets]},
                       ensure_ascii=False, indent=1), encoding='utf-8')
        return 2
    print(f"  قائمة SDN: {len(entries)} اسمًا · المصدر: {source[:70]}")
    hits = []
    for target in targets:
        hit = match_target(target, entries)
        hits.append(hit)
        if hit['match_type']:
            detail = hit['match_details'][:2]
            print(f"   ⚠ {hit['result']} · {target} → {detail}")
        else:
            print(f"   ✔ لا تطابق · {target}")
    out = Path(f'{BRAIN}/archive')
    out.mkdir(exist_ok=True)
    (out / 'ofac-screen-latest.json').write_text(json.dumps(
        {'utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
         'list': source, 'names': len(entries),
         'rule_note': 'قاعدة 50%: تُعد الكيانات المملوكة 50% أو أكثر من كيان مُدرج مُدرجة حكمًا؛ مطابقة الاسم تتطلب تطابقًا كاملًا أو نسبة كلمات عالية.',
         'name_stop_words': sorted(NAME_STOP_WORDS),
         'results': hits}, ensure_ascii=False, indent=1), encoding='utf-8')
    matches = [hit for hit in hits if hit['result'] == 'match']
    reviews = [hit for hit in hits if hit['result'] == 'review']
    print(f"  ✔ حُفظ: archive/ofac-screen-latest.json · تطابق: {len(matches)} · جزئي: {len(reviews)} · لا تطابق: {len(hits)-len(matches)-len(reviews)}")
    if matches:
        print("  ✘ مانع — تطابق إدراج صريح يحتاج قرارًا قبل النشر: " + " · ".join(hit['target'] for hit in matches))
        return 2
    if reviews:
        print("  ◐ تحذير — تطابق جزئي يحتاج تحققًا يدويًا")
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
