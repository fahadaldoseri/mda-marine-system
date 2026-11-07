#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""إصلاح جذري للتعارضات العشرة المقيسة في سجل التعارضات (ت-01 … ت-10).

القاعدة: كل تعارض يُصلح في مالكه أو في سطحه، مع إعلان المالك الواحد، ولا يُخفى فرق.
كل استبدال يتحقق من عدد المطابقات؛ فإن اختلف العدد يُعلن فشلًا ولا يكتب.

الاستخدام: python3 tools/_oneoff/fix_conflicts_20261107.py [--apply]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

B = pathlib.Path(__file__).resolve().parents[2]
REPO = B.parent
DATE = '2026-11-07'
APPLY = '--apply' in sys.argv
log: list[str] = []
fail: list[str] = []


def rep(rel: str, old: str, new: str, expect: int = 1) -> None:
    p = B / rel
    t = p.read_text(encoding='utf-8')
    n = t.count(old)
    if n != expect:
        fail.append(f'{rel}: توقّع {expect} مطابقة للنص «{old[:40]}» فوجد {n}')
        return
    if APPLY:
        p.write_text(t.replace(old, new), encoding='utf-8')
    log.append(f'{rel}: استُبدل «{old[:36]}» → «{new[:36]}»')


def rep_regex(rel: str, pattern: str, new: str, expect: int | None = None) -> int:
    p = B / rel
    t = p.read_text(encoding='utf-8')
    matches = re.findall(pattern, t)
    if expect is not None and len(matches) != expect:
        fail.append(f'{rel}: توقّع {expect} مطابقة للنمط فوجد {len(matches)}')
        return 0
    if APPLY:
        p.write_text(re.sub(pattern, new, t), encoding='utf-8')
    log.append(f'{rel}: {len(matches)} مطابقة للنمط → استُبدلت')
    return len(matches)


def jset(rel: str, fn) -> None:
    p = B / rel
    d = json.loads(p.read_text(encoding='utf-8'))
    fn(d)
    if APPLY:
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log.append(f'{rel}: عُدّل حقل')


# ── ت-02 · رقم سجل IMO في المتن (122 = لقطة سابقة) ──
report = f'reports/{DATE}-sectioned.md'
imo = json.loads((B / 'appendices/imo-incidents.json').read_text(encoding='utf-8'))
current = imo['totals']['confirmed_incidents']
previous = imo['previous']['totals']['confirmed_incidents']
lines = (B / report).read_text(encoding='utf-8').splitlines()
imo_lines = [(i, l) for i, l in enumerate(lines) if 'IMO' in l and str(previous) in l]
print(f'   أسطر IMO في المتن تحمل الرقم السابق {previous}: {[i + 1 for i, _ in imo_lines]}')
for i, l in imo_lines:
    rep(report, l, l.replace(str(previous), str(current)))

# ── ت-05 · النسب المشتقة على سطح المتن ──
meta = json.loads((B / f'web/meta/{DATE}.json').read_text(encoding='utf-8'))
hyps = meta.get('hypotheses') or []
for h in hyps:
    share = str(h.get('likelihood'))
    rng = str(h.get('likelihood_range') or '')
    if not rng:
        continue
    old = rng
    new = f'{share} · النطاق {rng}'
    t = (B / report).read_text(encoding='utf-8')
    if old in t and share not in t:
        rep(report, old, new)

# ── ت-06 · بطاقة «روايات لم تتأكد» تُشتق من عدّاد الدفتر ──
kpis = json.loads((B / f'web/kpis-totals/{DATE}.json').read_text(encoding='utf-8'))
metric = next((m for m in kpis['metrics'] if m['id'] == 'unconfirmed-narratives'), {})
owner_today = str(metric.get('today'))
owner_updated = str(metric.get('updated'))


def fix_card(d):
    for c in d.get('hero_kpis', []):
        if c.get('id') == 'unconfirmed-narratives':
            c['value'] = owner_today
            c['detail'] = (f'{owner_today} رواية جديدة في الدفتر · منها 0 مؤهلة · تُذكر ولا تُحتسب · '
                           f'آخر تحديث للدفتر {owner_updated}')
            c['note'] = c['detail']
            c['source'] = f'web/kpis-totals/{DATE}.json · unconfirmed-narratives (المالك الواحد)'
        if c.get('id') == 'unconfirmed-narratives' and False:
            pass
    sr = d.get('source_reliability') or {}
    status = json.loads((B / f'feeds/feeds-{DATE}.status.json').read_text(encoding='utf-8'))
    sr['stale'] = len(status.get('stale') or [])
    sr['stale_days_limit'] = status.get('stale_days_limit')
    d['source_reliability'] = sr


jset(f'web/meta/{DATE}.json', fix_card)

# ── ت-03 · التقادم يُشتق في المولّد لا يُكتب يدويًا ──
sc = 'tools/source_counts.py'
t = (B / sc).read_text(encoding='utf-8')
anchor = 'd["source_reliability"]["ok"] = c["ok"]'
if anchor in t and 'stale_days_limit' not in t.split(anchor)[1][:400]:
    if APPLY:
        (B / sc).write_text(
            t.replace(anchor, anchor + '\n    if isinstance(d.get("source_reliability"), dict):\n'
                                    '        _st = json.loads((B / "feeds" / f"feeds-{date}.status.json")'
                                    '.read_text(encoding="utf-8")) if (B / "feeds" / f"feeds-{date}.status.json").exists() else {}\n'
                                    '        d["source_reliability"]["stale"] = len(_st.get("stale") or [])\n'
                                    '        d["source_reliability"]["stale_days_limit"] = _st.get("stale_days_limit")'),
            encoding='utf-8')
    log.append(f'{sc}: التقادم صار يُشتق من ملف حالة التغذيات')
else:
    log.append(f'{sc}: لا حاجة لتعديل التقادم (مشتق أو مختلف)')

# ── ت-01 · عدد المصادر المعتمد في INDEX ──
rep('INDEX.md', '- القائمة المعتمدة: **40 مصدرًا** (37 + Jerusalem Post + IHO + MarineTraffic) → `sections/10-sources.md`',
    '- القائمة المعتمدة: **62 مصدرًا** بحسب السجل الحاكم `appendices/source-reliability-40.json` (الاسم تاريخي).\n'
    '- العدد التاريخي **40 مصدرًا** (37 + Jerusalem Post + IHO + MarineTraffic) محفوظ كمرجع في `sections/10-sources.md` ولا يُنشر كعدد معتمد.')

# ── ت-04 · القطاعات في المهارة ──
for rel in ('skills/threat-zone-card-ops/SKILL.md', 'brain/skills/threat-zone-card-ops/SKILL.md'):
    p = REPO / rel
    if not p.exists():
        continue
    t = p.read_text(encoding='utf-8')
    t2 = (t.replace('القطاعات الأربعة', 'القطاعات الخمسة')
           .replace('ثبّت أربعة قطاعات فقط', 'ثبّت خمسة قطاعات فقط')
           .replace('/home/ubuntu/brain-marine-news/', '/home/ubuntu/mda-marine-system/brain/'))
    if t2 != t:
        if APPLY:
            p.write_text(t2, encoding='utf-8')
        log.append(f'{rel}: القطاعات صارت خمسة والمسارات قانونية')
    else:
        log.append(f'{rel}: لا نص مطابق')

# ── ت-07 · خطوات التسليم المعلنة ──
rb = json.loads((B / 'runbook/runbook.json').read_text(encoding='utf-8'))
deliver = [s['id'] for s in rb['steps'] if str(s.get('phase', '')).lower().startswith('deliver')]


def fix_policy(d):
    d['manifest_delivery_steps'] = deliver


jset('runbook/delivery-policy.json', fix_policy)

# ── ت-08 · توقيت الجدولة والمسار في SETUP ──
rep('SETUP.md', 'مهمة مجدولة عند **06:40 بتوقيت البحرين**',
    'مهمة مجدولة عند **07:00 بتوقيت البحرين**')
rep('SETUP.md', '40 3 * * *  cd /path/to/brain-marine-news && bash tools/final_gate.sh',
    '0 4 * * *  cd /path/to/mda-marine-system/brain && bash tools/final_gate.sh')
rep('SETUP.md', '(03:40 UTC = 06:40 بتوقيت البحرين)', '(04:00 UTC = 07:00 بتوقيت البحرين)')

# ── ت-10 · قائمة OFAC ──
ofac = B / 'watchlist/ofac-targets.txt'
if ofac.exists():
    keep = [l for l in ofac.read_text(encoding='utf-8').splitlines()
            if not re.search(r'UPDATE-\d+|ISNA|HTTP\s*\d{3}', l, re.I)]
    if APPLY:
        ofac.write_text('\n'.join(keep) + '\n', encoding='utf-8')
    log.append('watchlist/ofac-targets.txt: أُزيلت العناصر غير السفن')

# ── ت-09 · النسخة التاريخية المكرّرة ──
dup = 'historical/event-ledger-2026-02-28-to-2026-10-11.json'
canonical = 'cumulative-2026/event-ledger-sectioned-2026-02-28-to-2026-10-11.json'


def mark_dup(d):
    if isinstance(d, dict):
        d['duplicate_of'] = canonical
        d['duplicate_note'] = 'نسخة تاريخية مطابقة للسجل المعتمد؛ لا تُقرأ كمصدر حاكم.'


jset(dup, mark_dup)

# ── التقرير ──
print('   ═══ ما نُفّذ ═══')
for l in log:
    print('   · ' + l)
if fail:
    print('   ═══ فشل ═══')
    for f in fail:
        print('   ✘ ' + f)
print('   الوضع: %s' % ('تجربة جافة (بلا كتابة)' if not APPLY else 'طُبّق فعليًا'))
sys.exit(1 if fail else 0)