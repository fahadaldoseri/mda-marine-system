#!/usr/bin/env python3
"""اختبار وحدة لحلقة التعلم الذاتي (tools/skill_lessons.py).

القاعدة المُختبَرة (ك-149): لا يجوز أن يظهر درس اليوم مرتين في الكتلة — مرة في الأعلى
ومرة داخل «سجل الدروس السابق». الكتلة تُقرأ بالعين، والتكرار يوهم بدرس مكرر.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('skill_lessons', ROOT / 'tools' / 'skill_lessons.py')
sl = importlib.util.module_from_spec(spec)
sys.modules['skill_lessons'] = sl
spec.loader.exec_module(sl)

fails: list[str] = []
DATE = '2026-10-23'
SUMM = {'status': 'warn', 'exit_code': 1, 'steps': 44, 'block': 0, 'warn': 9,
        'log_dir': 'logs/gate-2026-10-23', 'report_sha16': 'b68d144ea1a183e6'}

# 1) درس اليوم لا يتكرر داخل «سجل الدروس السابق»
#    المعيار: سطر نتيجة البوابة يظهر مرة واحدة، ولا سطر بتارخ اليوم داخل التفاصيل.
#    (تنبيه: ليوم واحد سطران مشروعان: نتيجة البوابة + حالة الأعطال الجديدة.)
history = [f'- **{DATE}** — نتيجة البوابة: `warn` (رمز `1`)',
           '- **2026-10-22** — درس يوم سابق']
block = sl.build_block(DATE, SUMM, [], history)
summary_lines = [l for l in block.splitlines() if l.startswith(f'- **{DATE}** — نتيجة البوابة')]
if len(summary_lines) != 1:
    fails.append(f'سطر نتيجة البوابة ظهر {len(summary_lines)} مرة (المطلوب مرة واحدة)')
details = block.split('<details>')[-1]
if f'- **{DATE}**' in details:
    fails.append('درس اليوم مكرر داخل «سجل الدروس السابق»')
if '- **2026-10-22** — درس يوم سابق' not in block:
    fails.append('دروس الأيام السابقة اختفت من الكتلة')

# 2) الأعطال الجديدة تظهر بسطر صريح
b2 = sl.build_block(DATE, SUMM, ['ك-149'], [])
if 'ك-149' not in b2:
    fails.append('الأعطال الجديدة لا تُذكر في الكتلة')

# 3) الكتلة تحمل بصمة المخرج ورمز الخروج (دليل قبل الادعاء)
for need in ('b68d144ea1a183e6', '`1`', '44'):
    if need not in b2:
        fails.append(f'الكتلة لا تحمل {need}')

# 4) استبدال الكتلة لا يُتلف ما حولها
tpl = 'قبل\n<!-- AUTO-LESSONS:START x -->\nقديم\n<!-- AUTO-LESSONS:END -->\nبعد\n'
new = tpl[:tpl.find(sl.START)] + sl.START + ' -->\nجديد\n' + tpl[tpl.find(sl.END):]
if not (new.startswith('قبل') and new.rstrip().endswith('بعد') and 'جديد' in new):
    fails.append('استبدال الكتلة يُتلف ما حولها')

print('  القاعدة: لا تكرار لدرس اليوم · والأعطال الجديدة تُذكر · والدليل في الكتلة')
if fails:
    print('  ✘ فشل:')
    for f in fails:
        print('    ·', f)
    sys.exit(1)
print('  ✔ اختبار حلقة التعلم صحيح')
