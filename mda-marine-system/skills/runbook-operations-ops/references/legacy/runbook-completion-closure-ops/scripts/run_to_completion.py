#!/usr/bin/env python3
"""قيادة الكتيب من حالة توقف إلى آخر خطوة، بتشخيص حيّ لكل توقف.

يعيد تشغيل `tools/runbook.py run --date <date>` حلقةً حتى يصل إلى:
  0  = اكتملت كل الخطوات
  10 = الخطوة بانتظار الوكيل (يطبع نصّها كما هو لتنفيذها وحدها)
  2  = توقف (يطبع الخطوة المتوقفة وذيل سجلها وتصنيفًا أوليًا للسبب)

لا يعدّل شيئًا في المشروع: قراءة وتشغيل فقط. أي إصلاح يبقى قرارًا واعيًا بعد قراءة التصنيف.

الاستعمال:
  python3 run_to_completion.py --date 2026-10-30
  python3 run_to_completion.py --date 2026-10-30 --max-loops 6 --status-only
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

# بصمات الأسباب الشائعة ← التصنيف وإلى أين ينظر المُصلح
SIGNATURES = [
    ('انحراف مانع', 'تماثل', 'شيفرة الخادم ليست في المستودع: زامن عبر فرع ثم طلب دمج (server-repo-parity-ops)'),
    ('انحراف (', 'تماثل', 'انحراف تنبيهي: اقرأ القائمة كاملة؛ الزوائد في المستودع لا تُحذف بلا قرار'),
    ('بلا ترجمة', 'ترجمة', 'نصوص عربية بلا مدخل في sources/i18n/en/glossary.json ← أكمل المعجم ثم أعد البناء'),
    ('بصمة النص', 'حارس بصمة النص', 'أعد التسجيل بعد اكتمال التصحيحات: tools/text_hash_guard.py --record'),
    ('بصمة المتن', 'حارس بصمة النص', 'أعد التسجيل بعد اكتمال التصحيحات: tools/text_hash_guard.py --record'),
    ('حارس بصمة', 'حارس بصمة النص', 'أعد التسجيل بعد اكتمال التصحيحات: tools/text_hash_guard.py --record'),
    ('غير مُستدعى', 'ربط بوابة', 'مدقق غير مربوط ببوابة التسليم: اربطه بخطوة في runbook.json ثم أعد توليد الكتيب'),
    ('فجوة', 'طباعة', 'فراغ داخلي في PDF: قياس التدفق ثم إصلاح الانكسار (print-layout-gate-ops)'),
    ('بصمة الطباعة', 'طباعة', 'بصمة مقفلة قديمة: إعادة تجميد بسبب ودليل موثّق'),
    ('لا يطابق المانيفست', 'مانيفست', 'أعد توليد الكتيب: python3 tools/runbook.py handbook'),
    ('اختبارات', 'اختبارات', 'اقرأ أول بند فاشل في الحزمة ثم أصلح سببه لا الاختبار'),
    ('غير موجود في النسخة الاحتياطية', 'ترتيب', 'شغّل النسخة الاحتياطية ثم أعد الخطوة بـ --redo <STEP>'),
    ('منع التسليم', 'بوابة أسطح/لغة', 'سطح واحد يخالف بوابة الأسلوب: أصلح السطح المذكور ثم أعد البوابة'),
    ('تحذير إنفاذ', 'ربط بوابة', 'مدقق معروف لكنه غير مربوط بخطوة تسليم: اربطه في runbook.json ثم handbook'),
    ('التماثل مكسور', 'مهارات', 'نسخة المهارة مبتورة: شغّل tools/restore_skills.sh ثم أعد الخطوة'),
    ('عدّ الإسنادات', 'أمانة المحتوى', 'سطر الإسناد في المتن لا يطابق الدفتر: صحّح المتن ثم أعد توليد المعجم'),
    ('رمز مختصر', 'فضاءات الرموز', 'أدرج الرمز المختصر لكل حدث مستشهد به في التحليل وفق سياسة الرموز'),
    ('لا ترد 200', 'نشر/انتشار', 'انتشار متأخر: أعد خطوة التحقق الحي بانتظار متكرر بلا تعديل التقرير'),
    ('لم ترد 200', 'نشر/انتشار', 'انتشار متأخر: أعد خطوة التحقق الحي بانتظار متكرر بلا تعديل التقرير'),
    ('رمز الخروج 70', 'انهيار مدقق', 'مدقق انهار (فشل مغلق): شغّل المدقق نفسه يدويًا لقراءة الأثر ثم أصلحه'),
    ('لم تبدأ', 'ترتيب', 'خطوة لاحقة لم تبدأ لأن سابقتها لم تكتمل: أكمل المتوقفة أولًا'),
]

# عيّنات حقيقية من الجولات ← تُستخدم في --selftest لإثبات أن التصنيف يميّز الأصناف
SAMPLES = [
    ('✘ توقف عند D040: رمز الخروج 2\n  انحراف مانع: 8 بنود', 'تماثل'),
    ('بناء النسخة الإنجليزية: نصوص عربية بلا ترجمة (13)', 'ترجمة'),
    ('حارس بصمة النص: بصمة المتن لا تطابق', 'حارس بصمة النص'),
    ('مدقق check_repo_secrets.py غير مُستدعى في بوابة التسليم', 'ربط بوابة'),
    ('فجوة داخلية 47.9 مم في الصفحة 7', 'طباعة'),
    ('الكتيب لا يطابق المانيفست: أعد توليده', 'مانيفست'),
    ('تقرير اليوم غير موجود في النسخة الاحتياطية', 'ترتيب'),
    ('أمانة المحتوى: عدّ الإسنادات (17) لا يطابق الدفتر', 'أمانة المحتوى'),
    ('التماثل مكسور: skills/marine-news-brain/SKILL.md', 'مهارات'),
    ('منع التسليم: تقرير اليوم بلا رمز مختصر في التحليل', 'فضاءات الرموز'),
    ('مدقق منهار — رمز الخروج 70', 'انهيار مدقق'),
    ('كل المسارات لم ترد 200 — PDF حي مختلف', 'نشر/انتشار'),
    ('نص عادي بلا أي بصمة معروفة', ''),
]

STEP_RE = re.compile(r'▶\s+([A-Z0-9]+)\s+—')
FAIL_RE = re.compile(r'توقف عند\s+([A-Z0-9]+)')


def utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def classify(text: str) -> list[tuple[str, str]]:
    out = []
    for sig, kind, action in SIGNATURES:
        if sig in text:
            out.append((kind, action))
    return out


def step_prompt(brain: pathlib.Path, step: str) -> str:
    try:
        d = json.loads((brain / 'runbook' / 'runbook.json').read_text(encoding='utf-8'))
    except Exception:
        return ''
    found: list[dict] = []

    def walk(o):
        if isinstance(o, dict):
            if o.get('id') == step:
                found.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(d)
    if not found:
        return ''
    return json.dumps(found[0], ensure_ascii=False, indent=1)[:4000]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--brain', default='/home/ubuntu/brain-marine-news')
    ap.add_argument('--site', default='/home/ubuntu/seawatch')
    ap.add_argument('--audit', default='')
    ap.add_argument('--max-loops', type=int, default=12)
    ap.add_argument('--timeout', type=int, default=1700)
    ap.add_argument('--status-only', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        bad = 0
        for text, want in SAMPLES:
            got = [k for k, _ in classify(text)]
            ok = (want in got) if want else (not got)
            print(f'{"✔" if ok else "✘"} متوقّع {want or "بلا تصنيف"} ← وجد {got or "بلا تصنيف"}')
            bad += 0 if ok else 1
        print(f'النتيجة: {len(SAMPLES) - bad}/{len(SAMPLES)} مطابق' + (' — التصنيف يحتاج تشديدًا' if bad else ''))
        return 1 if bad else 0

    brain = pathlib.Path(a.brain)
    audit = pathlib.Path(a.audit) if a.audit else pathlib.Path(f'/home/ubuntu/audit-{a.date}')
    audit.mkdir(parents=True, exist_ok=True)
    state = audit / f'run-to-completion-{a.date}.json'

    if a.status_only:
        r = subprocess.run(['python3', 'tools/runbook.py', 'status', '--date', a.date],
                           cwd=brain, capture_output=True, text=True)
        print(r.stdout[-3000:] or r.stderr[-1500:])
        return 0

    records = []
    for i in range(1, a.max_loops + 1):
        log = audit / f'run-{a.date}-loop{i}.log'
        with log.open('w', encoding='utf-8') as fh:
            p = subprocess.run(
                ['python3', 'tools/runbook.py', 'run', '--date', a.date],
                cwd=brain, stdout=fh, stderr=subprocess.STDOUT, timeout=a.timeout)
        rc = p.returncode
        txt = log.read_text(encoding='utf-8', errors='replace')
        tail = '\n'.join(txt.strip().splitlines()[-14:])
        step = ''
        m = FAIL_RE.search(txt)
        if m:
            step = m.group(1)
        else:
            steps = STEP_RE.findall(txt)
            step = steps[-1] if steps else ''
        rec = {'loop': i, 'utc': utc(), 'rc': rc, 'step': step, 'log': str(log),
               'tail': tail[-1200:]}
        records.append(rec)
        state.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding='utf-8')

        print(f'\n══ حلقة {i} · رمز {rc} · الخطوة {step or "—"} ══')
        print(tail)

        if rc == 0:
            print('\n✔ اكتملت كل الخطوات — شغّل scripts/round_close_check.sh لجمع أدلة الإغلاق.')
            return 0
        if rc == 10:
            print(f'\n⏸ الخطوة {step} بانتظار الوكيل — نفّذ نصّها وحدها ثم:')
            print(f'   python3 tools/runbook.py complete {step} --date {a.date}')
            print('   ثم أعد هذا المشغّل. النصّ كما هو في المانيفست:')
            print(step_prompt(brain, step))
            return 10
        if rc == 2:
            print(f'\n✘ توقف عند {step}. سجل الخطوة: logs/runbook/{a.date}/{step}.log')
            lp = brain / 'logs' / 'runbook' / a.date / f'{step}.log'
            lp_text = ''
            if lp.is_file():
                lp_full = lp.read_text(encoding='utf-8', errors='replace')
                lp_text = lp_full
                lt = lp_full.strip().splitlines()[-12:]
                print('   ── ذيل سجل الخطوة ──')
                for line in lt:
                    print('   ' + line[:180])
            hits = classify(txt + '\n' + lp_text)
            if hits:
                print('   ── تصنيف أولي ──')
                for kind, action in hits:
                    print(f'   · {kind}: {action}')
            else:
                print('   ── لا تصنيف معروف ──')
                print(f'   اقرأ السبب كاملًا:  sed -n "1,200p" logs/runbook/{a.date}/{step}.log')
                print(f'   اقرأ تعريف الخطوة: python3 tools/runbook.py status --date {a.date}  (ثم grep "{step}" runbook/runbook.json)')
                print('   وبعد فهم السبب: أضف بصمته إلى جدول SIGNATURES في هذه المهارة حتى يُصنَّف تلقائيًا في المرة القادمة.')
            print('   بعد الإصلاح: أعد الخطوة نفسها بـ --redo أو أعد هذا المشغّل.')
            return 2
        print(f'\n⚠ رمز غير متوقع ({rc}) — اقرأ السجل كاملًا: {log}')
        return rc
    print('\n⚠ بلغت الحد الأقصى للحلقات بلا اكتمال — راجع ملف الحالة: ' + str(state))
    return 3


if __name__ == '__main__':
    sys.exit(main())
