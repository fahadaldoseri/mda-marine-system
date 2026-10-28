#!/usr/bin/env python3
"""بوابة إغلاق حلقة التعلم — فشل مغلق حقيقي.

المبدأ: كل عطل إما **مفحوص ومغلق بدليل**، أو **مستثنى صراحةً بمهلة**. وما دون ذلك = منع.
لا يُعدّ غياب التاريخ استثناءً (وهو الخلل الذي كان يسمح بنجاح صامت).
أي خطأ داخلي = رمز 70 (منع) لا تجاوز.

الاستخدام: python3 validators/check_closure.py [--brain DIR] [--json]
الرموز: 0 = مجتاز · 2 = منع · 70 = انهيار داخلي (منع أيضًا).
"""
import argparse, json, re, sys, traceback
from datetime import datetime, timezone
from pathlib import Path

# ── جذر محمول (بوابة قابلية النقل) ──
import os as _os
from pathlib import Path as _Path
_P = _Path(__file__).resolve()
_C = [_P.parents[i] for i in range(1, min(6, len(_P.parents)))]
def _brain_root():
    e = _os.environ.get("BRAIN_DIR")
    if e and _Path(e).is_dir():
        return _Path(e)
    for r in _C:
        c = r / "brain-marine-news"
        if (c / "reports").is_dir():
            return c
    for r in _C:
        if (r / "reports").is_dir():
            return r
    return _C[0] / "brain-marine-news"
BRAIN = _brain_root()


STATES = {'مغلق', 'مفتوح', 'بانتظار التحقق', 'موروث غير مثبت', 'أعيد فتحه'}
EXC_FIELDS = ['fault_id', 'state', 'reason', 'owner', 'approved_by', 'created_at', 'expires_at',
              'compensating_control', 'replacement_plan', 'evidence']
OUTCOME = re.compile(r'خرج\s*(?:0|2|70)|رمز\s*(?:0|2|70)|exit\s*(?:0|2)|فاشل\s*(?:0|صفر)'
                     r'|\b(?:[1-9]|1[0-5])/(?:[1-9]|1[0-5])\b(?!\s*/)|صفر فاشل|مطابق تمامًا|بصمة\s*[0-9a-f]{6,}')
IDENT = re.compile(r'^\|\s*([كزعثم])-(\d+)(/[بجدهوزحطيكلمنصعقفرستثخ]+)?\s*\|')


def load_rows(brain: Path):
    f = brain / 'audit' / 'سجل-الأعطال-والثغرات.md'
    rows = {}
    for line in f.read_text(encoding='utf-8').splitlines():
        m = IDENT.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) != 12:
            rows[f'{m.group(1)}-{m.group(2)}{m.group(3) or ""}'] = {'__width__': len(cells), 'cells': cells}
        else:
            rows[cells[0]] = {'state': cells[11], 'repair': cells[8], 'verify': cells[9], 'barrier': cells[10],
                              'barrier_text': cells[6], 'cells': cells}
    return rows


def load_exceptions(brain: Path):
    p = brain / 'audit' / 'closure-exceptions.json'
    if not p.exists():
        return {}, ['ملف الاستثناءات غير موجود: audit/closure-exceptions.json']
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        return {}, [f'ملف الاستثناءات غير قابل للقراءة: {e}']
    exc, errs = {}, []
    if d.get('version') != 1:
        errs.append('نسخة الملف غير معروفة')
    for e in d.get('entries', []):
        missing = [k for k in EXC_FIELDS if not e.get(k)]
        if missing:
            errs.append(f'استثناء ناقص الحقول ({", ".join(missing)}): {e.get("fault_id")}')
            continue
        try:
            exp = datetime.fromisoformat(e['expires_at'])
        except ValueError:
            errs.append(f'تاريخ انتهاء غير صالح: {e.get("fault_id")}')
            continue
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        e['__expired__'] = exp < datetime.now(timezone.utc)
        if e['fault_id'] in exc:
            errs.append(f'معرّف مستثنى مكرّر: {e["fault_id"]}')
        exc[e['fault_id']] = e
    return exc, errs


def check(brain: Path):
    fails, notes = [], []
    rows = load_rows(brain)
    exc, errs = load_exceptions(brain)
    fails += errs
    if not rows:
        fails.append('لم يُقرأ أي صف من سجل الأعطال')
    for ident, r in rows.items():
        if '__width__' in r:
            fails.append(f'{ident}: مخطط غير قانوني ({r["__width__"]} عمودًا بدل 12)')
            continue
        if r['state'] not in STATES:
            fails.append(f'{ident}: حالة غير معروفة «{r["state"]}»')
        if r['state'] == 'مغلق':
            if r['repair'] != 'منفَّذ':
                fails.append(f'{ident}: حالة «مغلق» وإصلاحه ليس «منفَّذ»')
            if r['verify'] != 'تحقق تشغيلي ناجح':
                fails.append(f'{ident}: حالة «مغلق» بلا تحقق تشغيلي')
            if r['barrier'] not in ('مطبَّق', 'فعّال'):
                fails.append(f'{ident}: حالة «مغلق» بلا حاجز مطبَّق')
        else:
            e = exc.get(ident)
            if not e:
                fails.append(f'{ident}: غير مغلق وبلا استثناء صريح (حالته {r["state"]})')
            elif e.get('__expired__'):
                fails.append(f'{ident}: استثناء منتهي الصلاحية')
    known = set(rows)
    for ident in exc:
        if ident not in known:
            fails.append(f'استثناء لمعرّف غير موجود في السجل: {ident}')
    # الدروس والحاجز ودليل التشغيل لكل مغلق
    tr = brain / 'audit' / 'traceability.json'
    if not tr.exists():
        fails.append('مصفوفة التتبع غير موجودة: audit/traceability.json')
    else:
        t = json.loads(tr.read_text(encoding='utf-8'))
        idx = {r['fault_id']: r for r in t.get('rows', [])}
        for ident, r in rows.items():
            if '__width__' in r:
                continue
            row = idx.get(ident)
            if not row:
                fails.append(f'{ident}: لا صف في مصفوفة التتبع')
            elif r['state'] == 'مغلق':
                def _nrm(x):
                    x = (x or '').split('/')[0]
                    return f'{x.split(chr(45))[0]}-{int(x.split(chr(45))[1])}' if re.match(r'^[كزعثم]-\d+$', x) else x
                lis = _nrm(row.get('lesson_id'))
                base = _nrm(ident)
                bid = row.get('barrier_id') or ''
                ev = (row.get('run_evidence') or '').strip()
                if lis != base:
                    fails.append(f'{ident}: مغلق بلا درس مطابق')
                if not re.match(r'^B-[0-9a-f]{8}$', bid):
                    fails.append(f'{ident}: مغلق بمعرّف حاجز غير صالح')
                if not OUTCOME.search(ev):
                    fails.append(f'{ident}: مغلق بدليل غير قابل لإعادة التشغيل («{ev[:40]}»)')
        notes.append(f'مصفوفة التتبع: {len(idx)} صفًا')
    closed = sum(1 for r in rows.values() if r.get('state') == 'مغلق')
    counts = {'مفحوص': len(rows), 'مغلق': closed, 'مستثنى': len(exc), 'فاشل': len(fails)}
    return counts, fails, notes


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--brain', default=str(BRAIN))
    ap.add_argument('--json', action='store_true'); a = ap.parse_args()
    try:
        counts, fails, notes = check(Path(a.brain))
    except Exception:
        print('✗ انهيار داخلي في بوابة الإغلاق — منع')
        traceback.print_exc()
        return 70
    if a.json:
        print(json.dumps({'counts': counts, 'fails': fails, 'notes': notes}, ensure_ascii=False))
    else:
        for n in notes:
            print(f'  {n}')
        print(f'  مفحوص: {counts["مفحوص"]} · مغلق: {counts["مغلق"]} · مستثنى: {counts["مستثنى"]} · فاشل: {counts["فاشل"]}')
        for f in fails[:25]:
            print(f'  ✗ {f}')
        if len(fails) > 25:
            print(f'  … و{len(fails) - 25} ملاحظة أخرى')
        print('  النتيجة: مجتاز' if not fails else '  النتيجة: منع — الحلقة غير مغلقة')
    return 0 if not fails else 2


if __name__ == '__main__':
    raise SystemExit(main())
