#!/usr/bin/env python3
"""اختبارات دائمة لأدوات محور اللغة (أمر 23 أكتوبر 2026).

تُثبت ثلاثة أمور لا تُقبل بالشهادة:
  1) حارس الحفظ يرفض أي تعديل يمسّ رقمًا أو رمزًا، ويقبل التعديل اللغوي الآمن.
  2) بوابة اللغة متدرجة فعلًا: تنبيهية قبل `advisory_until` ومانعة بعده (اختبار تاريخ).
  3) التحرير التجريبي لا يغيّر ملف التقرير (لا كتابة بلا `--apply`).

الاستعمال: python3 tests/test_language_tools.py
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
FAILS = []


def check(name, ok, detail=''):
    print(f'  {"✔" if ok else "✘"} {name}' + (f' — {detail}' if detail and not ok else ''))
    if not ok:
        FAILS.append(name)


def preserved(before, after):
    with tempfile.TemporaryDirectory() as td:
        bp, ap = Path(td) / 'b.txt', Path(td) / 'a.txt'
        bp.write_text(before, encoding='utf-8')
        ap.write_text(after, encoding='utf-8')
        r = subprocess.run([sys.executable, str(B / 'tools' / 'preserve_check.py'), str(bp), str(ap)],
                           capture_output=True, text=True)
        return r.returncode == 0, (r.stdout or '').strip()


# 1) حارس الحفظ
ok, why = preserved('وصلت الناقلة إلى 26°12.34N وحمولتها 15 ألف طن.',
                    'وصلت الناقلة إلى 26°12.34N وحمولتها 16 ألف طن.')
check('الحارس يرفض تغيير رقم', not ok, why)
ok, _ = preserved('وصلت الناقلة إلى 26°12.34N وفق بلاغ UKMTO.',
                  'بلغت الناقلة 26°12.34N وفق بلاغ UKMTO.')
check('الحارس يقبل تحريرًا لغويًا آمنًا', ok)
ok, _ = preserved('أفادت UKMTO بمشاهدة قارب مسيّر.', 'أفادت UKMTO بمشاهدة زورق مسيّر.')
check('الحارس يقبل استبدال مفردة', ok)

# 2) تدريج بوابة اللغة (اختبار تاريخ): نفس التقرير قبل وبعد تاريخ الإنفاذ
rep = B / 'reports' / '2026-10-23-sectioned.md'
if rep.exists():
    for d, want in (('2026-10-23', 1), ('2026-11-01', 2)):
        r = subprocess.run([sys.executable, str(B / 'tools' / 'language_gates.py'), '--date', d],
                           capture_output=True, text=True)
        check(f'بوابة اللغة في {d} تعيد {want}', r.returncode == want, f'أعادت {r.returncode}')
else:
    check('تقرير 23 موجود لاختبار التدريج', False, 'لا ملف')

# 3) التحرير بلا --apply لا يكتب في التقرير
if rep.exists():
    h0 = hashlib.sha256(rep.read_bytes()).hexdigest()
    r = subprocess.run([sys.executable, str(B / 'tools' / 'edit_pass.py'), '--report', str(rep),
                        '--out-dir', str(B / 'audit'), '--workers', '2', '--min-chars', '100000'],
                       capture_output=True, text=True)
    h1 = hashlib.sha256(rep.read_bytes()).hexdigest()
    check('التحرير التجريبي لا يغيّر التقرير', h0 == h1)
    check('التحرير التجريبي يعيد رمز نجاح أو تحذير', r.returncode in (0, 1), f'رمز {r.returncode}')

print(f'\n  الحصيلة: {"كل الاختبارات نجحت" if not FAILS else str(len(FAILS)) + " فشل: " + " · ".join(FAILS)}')
sys.exit(1 if FAILS else 0)