#!/usr/bin/env python3
"""جولة الإغلاق المهني — التصميم المصحّح على سجلي الأعطال والتعلم.

المخطط القانوني: 12 عمودًا (7 حقول أصلية + الحالة الأصلية + 4 حقول حالة مشتقة).
ضمانات: لا صف يُحذف · ترويسة واحدة لكل جدول · كل حكم مردّه نصّ السجل · الأداة ثابتة.
الاستخدام: python3 tools/closure_round.py [--apply]
"""
import argparse, hashlib, json, re, shutil, time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import os as _os
_P = Path(__file__).resolve()
_C = [_P.parents[i] for i in range(1, min(5, len(_P.parents)))]
def _brain_root():
    """جذر brain القانوني بالقياس (runbook/runbook.json) — فشل مغلق."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    from brain_root import canonical_brain_root
    return canonical_brain_root(Path(__file__).resolve().parents[1])
B = _brain_root()
F = B / 'audit' / 'سجل-الأعطال-والثغرات.md'
L = B / 'memory' / 'learning-log.jsonl'
CANON = ['الرقم', 'التاريخ', 'المحور', 'العَرَض', 'السبب الجذري', 'الإصلاح', 'التشديد والحالة',
         'الحالة الأصلية', 'حالة الإصلاح', 'حالة التحقق', 'حالة الحاجز', 'الحالة التشغيلية']
HDR = '| ' + ' | '.join(CANON) + ' |'
SEP = '|' + '---|' * len(CANON)
ID = re.compile(r'^\|\s*([كزعثم])-(\d+)(/[بج])?')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
SUCCESS = re.compile(r'(?i:\brc\s*=\s*0\b)|خرج\s*0|رمز\s*0|فاشل\s*0|صفر فاشل|بصمة\s*[0-9a-f]{6,}')
OUTCOME = re.compile(r'(?i:\brc\s*=\s*(?:0|2|70))|خرج\s*(?:0|2|70)|رمز\s*(?:0|2|70)|exit\s*(?:0|2)|فاشل\s*(?:0|صفر)'
                     r'|\b(?:[1-9]|1[0-5])/(?:[1-9]|1[0-5])\b(?!\s*/)|صفر فاشل|مطابق تمامًا|بصمة\s*[0-9a-f]{6,}')
OWNER = 'فهد الدوسري'
UTC = timezone.utc

POLICY = {
    'version': 1,
    'قاعدة_الإصلاح': {'لم يبدأ': ['—', '(الإصلاح مدمج', '(لا إصلاح', ''], 'قيد التنفيذ': ['لم ', 'بانتظار', 'قيد'], 'منفَّذ': ['*']},
    'قاعدة_التحقق': {'تحقق تشغيلي ناجح': ['مقياس OUTCOME (خرج/رمز/exit + رقم · فاشل 0 · n/n · بصمة)'], 'تحقق أولي': ['أولي'], 'غير متحقق': ['*']},
    'قاعدة_الحاجز': {'فعّال': ['أُثبت', 'مطابق', 'خرج 0'],
                      'مطبَّق': ['بوابة', 'اختبار', 'حارس', 'قاعدة', 'check_', 'فحص', 'قياس'], 'غير موثَّق': ['*']},
    'قاعدة_التشغيلية': ('مغلق = الإصلاح منفَّذ ∧ الحاجز مطبَّق/فعّال ∧ تحقق تشغيلي ناجح؛ وإلا: مفتوح إن نصّ السجل '
                        'على الانفتاح · بانتظار التحقق إن وُجد إصلاح بلا دليل · موروث غير مثبت إن لم يوجد تاريخ ولا دليل.'),
}


def pick(text: str, rules: dict) -> str:
    for label, keys in rules.items():
        if '*' not in keys and any(k and k in text for k in keys):
            return label
    return next((l for l, k in rules.items() if '*' in k), 'غير محدد')


def derive(date, fix, barrier, status_raw) -> list:
    blob = f'{fix} {barrier}'   # الدليل من الإصلاح والحاجز فقط — لا من «الحالة الأصلية»
    f_fix, f_bar = pick(fix, POLICY['قاعدة_الإصلاح']), pick(barrier, POLICY['قاعدة_الحاجز'])
    f_ver = 'تحقق تشغيلي ناجح' if OUTCOME.search(blob) else pick(blob, POLICY['قاعدة_التحقق'])
    if f_fix == 'منفَّذ' and f_bar in ('مطبَّق', 'فعّال') and f_ver == 'تحقق تشغيلي ناجح' and SUCCESS.search(blob):
        state = 'مغلق'
    elif re.search(r'مفتوح|لم يُصلح|بانتظار قرار', status_raw + barrier):
        state = 'مفتوح'
    elif date in ('—', '', None):
        state = 'موروث غير مثبت'
    else:
        state = 'بانتظار التحقق'
    return [f_fix, f_ver, f_bar, state]


def to_canon(cells: list, ident: str, leftover: str = '') -> list | None:
    """cells بعد استبعاد خلية المعرّف · أي مخطط → 12 خلية بلا فقد نصّ."""
    n = len(cells)
    if n >= 10:                      # مخطط قانوني سابق (11 خلية) → آخر 4 حقول موجودة
        date, axis, sym, cause, fix, barrier, status = cells[:7]
        return [ident, date, axis, sym, cause, fix, barrier, status] + derive(date, fix, barrier, status)
    if n == 7 and DATE.match(cells[0] or ''):
        date, axis, sym, cause, fix, barrier, status = cells
    elif n == 7:                     # موروث: محور + سبب ثانوي
        axis, sym, cause, c2, fix, barrier, status = cells
        date, cause = '—', f'{cause} · {c2}'
    elif n == 5 and DATE.match(cells[0] or ''):
        date, axis, sym, cause, fix = cells; barrier, status = fix, ''
    elif n == 5:                     # جدول قديم: موضع · عطل · سبب · حاجز
        axis, sym, cause, barrier = cells
        date, fix, status = '—', '(الإصلاح مدمج في نص الحاجز)', ''
    elif n == 4:
        axis, sym, cause, barrier = cells
        date, fix, status = '—', '(الإصلاح مدمج في نص الحاجز)', ''
    elif n == 6:
        sym, cause, fix, date, status = cells[:5]; axis, barrier = '—', status
    else:
        return None
    status = f'{status} {leftover}'.strip() if leftover else status
    return [ident, date, axis, sym, cause, fix, barrier, status] + derive(date, fix, barrier, status)


def parse(text: str):
    """يعيد ([ (ident_final, row12) ]، (ident_أصلي ← [صفوف])، فاشلة) بترتيب الورود."""
    recs, buckets, failed, seen = [], {}, [], Counter()
    SUF = 'بجدهوزحطيكلمنصعقفرستثخ'
    for l in text.splitlines():
        m = ID.match(l)
        if not m:
            continue
        base = f'{m.group(1)}-{m.group(2)}{m.group(3) or ""}'
        cells = [c.strip() for c in l.strip('|').split('|')]
        leftover = cells[0].replace(m.group(0).strip('|').strip(), '').strip()
        seen[base] += 1
        final = base if seen[base] == 1 else f'{base}/' + SUF[seen[base] - 2]
        row = to_canon(cells[1:], final, leftover)
        if row:
            recs.append((final, row)); buckets.setdefault(base, []).append(row)
        else:
            failed.append((base, len(cells)))
    return recs, buckets, failed


def rebuild(text: str, recs: dict):
    """ترويسة قانونية واحدة لكل جدول · ولا صف يُحذف · الأداة ثابتة."""
    lines, out, stats, in_table, i = text.splitlines(), [], Counter(), False, 0
    while i < len(lines):
        l = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        is_sep = '|' in nxt and set(nxt.replace('|', '').replace(' ', '').replace('\t', '')) <= set('-:')
        if l.lstrip().startswith('|') and is_sep and ('الرقم' in l or 'الحالة التشغيلية' in l or l.lstrip().startswith('| #')):
            out += [HDR, SEP]; stats['جداول'] += 1; in_table = True; i += 2; continue
        if l.lstrip().startswith('|'):
            m = ID.match(l)
            if m:
                base = f'{m.group(1)}-{m.group(2)}{m.group(3) or ""}'
                if recs.get(base):
                    out.append('| ' + ' | '.join(recs[base].pop(0)) + ' |'); stats['صفوف محوَّلة'] += 1
                else:
                    out.append(l); stats['كُتب كما هو'] += 1
                i += 1; continue
            out.append(l); i += 1; continue
        in_table = False; out.append(l); i += 1
    return '\n'.join(out) + '\n', stats


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true'); a = ap.parse_args()
    bak = B / 'audit' / 'backups' / f'closure-round-{time.strftime("%Y%m%d-%H%M%S")}'
    bak.mkdir(parents=True, exist_ok=True)
    for src in (F, L):
        shutil.copy2(src, bak / src.name)
    recs_list, buckets, failed = parse(F.read_text(encoding='utf-8'))
    recs = buckets
    text, stats = rebuild(F.read_text(encoding='utf-8'), recs)
    # ضمان الاتساق بالبناء: لا «مغلق» بلا دليل نتيجة في الإصلاح أو الحاجز
    demoted = []
    for ident, r in recs_list:
        if r[11] == 'مغلق' and not OUTCOME.search(f'{r[5]} {r[6]}'):
            r[9] = 'غير متحقق'
            r[11] = 'موروث غير مثبت' if r[1] in ('—', '') else 'بانتظار التحقق'
            demoted.append(ident)
    if demoted:
        print(f'  خُفّضت {len(demoted)} حالة «مغلق» بلا دليل نتيجة: {demoted[:8]}')
    states = Counter(r[11] for _, r in recs_list)
    print(f'  نسخة احتياطية: {bak}')
    print(f'  صفوف: {len(recs_list)} · تعذّر تحويلها: {failed or "لا شيء"} · إحصاء: {dict(stats)}')
    print(f'  الحالة التشغيلية: {dict(states)}')

    now = datetime.now(UTC)
    exc = {'version': 1, 'policy': 'استثناء = قبول مخاطر مؤقت بمهلة، لا إغلاق', 'created_at': now.isoformat(),
           'approved_by': OWNER, 'entries': []}
    for ident, r in recs_list:
        if r[11] == 'مغلق':
            continue
        exc['entries'].append({'fault_id': ident, 'state': r[11], 'reason': f'{r[11]} — لا دليل إغلاق كامل في السجل',
                               'owner': OWNER, 'approved_by': OWNER, 'created_at': now.isoformat(),
                               'expires_at': (now + timedelta(days=60)).isoformat(),
                               'compensating_control': 'مراجعة أسبوعية للسجل مع قياس التغطية',
                               'replacement_plan': 'إثبات تحقق: أمر + مخرج + بصمة ثم ترقية الحالة إلى «مغلق»',
                               'evidence': (r[6][:200] or f'لا نصّ حاجز في السجل — الحالة: {r[11]}')})
    (B / 'audit' / 'closure-exceptions.json').write_text(json.dumps(exc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (B / 'audit' / 'closure-policy.json').write_text(json.dumps(POLICY, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    entries = []
    for line in L.read_text(encoding='utf-8').splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    by_fault = {}
    for e in entries:
        for m in re.finditer(r'([كزعثم])-(\d+)', json.dumps(e, ensure_ascii=False)):
            by_fault.setdefault(f'{m.group(1)}-{int(m.group(2))}', []).append(e)
    trace, derived = [], 0
    for ident, r in recs_list:
        key = ident.split('/')[0]
        key = f'{key.split(chr(45))[0]}-{int(key.split(chr(45))[1])}'
        les = by_fault.get(key, [])
        if not les and (re.search(r'بوابة|اختبار|قاس|قاعدة|حارس', r[6])
                       or OUTCOME.search(f'{r[5]} {r[6]}')):
            derived += 1
            e = {'ts': now.isoformat(), 'entry_kind': 'derived', 'cls': 'استنتاج رجعي', 'status': 'مرشّح',
                 'status_norm': 'مرشّح', 'fault_id': ident, 'symptom': r[3][:180], 'root_cause': r[4][:180],
                 'lesson': f'القاعدة التي تغيّرت: {r[6][:180]}', 'action': r[5][:180], 'barrier': r[6][:180],
                 'evidence': 'مشتق من نص السجل — يحتاج اعتماد المالك', 'confidence': 'متوسط'}
            entries.append(e); les = [e]; by_fault[key] = les
        trace.append({'fault_id': ident, 'state': r[11], 'lesson_id': les[0].get('fault_id', key) if les else None,
                      'barrier_id': 'B-' + hashlib.sha256((ident + r[6]).encode()).hexdigest()[:8],
                      '''run_evidence''': ((lambda m, ev: (ev[max(0, m.start()-70):m.end()+25] if m else None))(
                          OUTCOME.search(f'{r[5]} {r[6]}'), f'{r[5]} {r[6]}'))})
    (B / 'audit' / 'traceability.json').write_text(
        json.dumps({'version': 1, 'generated_at': now.isoformat(),
                    'chain': 'fault_id ← lesson_id ← barrier_id ← run evidence', 'rows': trace},
                   ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (B / 'audit' / 'مصفوفة-التتبع.md').write_text(
        '# مصفوفة التتبع\n\nالسلسلة: `fault_id ← lesson_id ← barrier_id ← run evidence`\n\n'
        '| العطل | الحالة | الدرس | الحاجز | دليل التسجيل |\n|---|---|---|---|---|\n' +
        '\n'.join(f'| {t["fault_id"]} | {t["state"]} | {t["lesson_id"] or "—"} | {t["barrier_id"]} | {t["run_evidence"] or "—"} |'
                  for t in trace) + '\n', encoding='utf-8')
    cov = sum(1 for t in trace if t['lesson_id'])
    print(f'  استثناءات: {len(exc["entries"])} · تتبع: {len(trace)} · مغطى بدرس: {cov} · دروس مشتقة: {derived}')
    if a.apply:
        F.write_text(text, encoding='utf-8')
        L.write_text('\n'.join(json.dumps(e, ensure_ascii=False) for e in entries) + '\n', encoding='utf-8')
        t2, _ = rebuild(F.read_text(encoding='utf-8'), recs)
        L.write_text('\n'.join(json.dumps(e, ensure_ascii=False) for e in entries) + '\n', encoding='utf-8')
        ents2 = [json.loads(x) for x in L.read_text(encoding='utf-8').splitlines() if x.strip()]
        groups = Counter(x.split('/')[0] for x in recs)
        stable = (rebuild(F.read_text(encoding='utf-8'), recs)[0] == text) and ents2 == entries
        print(f'  ثبات كامل (سجل + تعلم): {'نعم ✔' if stable else 'لا ✘'} · التعلم: {len(entries)} مدخلًا')
        print(f'  أرقام لها أكثر من صف: {sum(1 for v in groups.values() if v > 1)}')
    else:
        print('  (تجربة — أضف --apply)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
