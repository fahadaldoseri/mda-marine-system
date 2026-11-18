#!/usr/bin/env python3
"""اختبار وحدة لتكامل قائمة المهارات بين المزامنة والنسخ الاحتياطي.

العطل المُختبَر (ك-150): `tools/github_backup.py` كان يحمل قائمة مهارات مكتوبة بيده،
بينما `tools/restore_skills.sh` يحمل قائمة أخرى. فحين أُضيفت مهارة جديدة إلى المزامنة
لم تُضف إلى النسخ، فحذفها النسخ الاحتياطي من المستودع (لأنه يمحو مجلد skills أولًا).
القاعدة: قائمة واحدة، ومصدر واحد للحقيقة.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
restore = (B / 'tools' / 'restore_skills.sh').read_text(encoding='utf-8')
backup = (B / 'tools' / 'github_backup.py').read_text(encoding='utf-8')

fails: list[str] = []

m = re.search(r'OUR_SKILLS="([^"]+)"', restore)
if not m:
    print('  ✘ لم أجد OUR_SKILLS في restore_skills.sh')
    sys.exit(1)
sync_skills = set(m.group(1).split())

# 1) النسخ الاحتياطي يقرأ القائمة من مصدرها لا من قائمة مكتوبة بيده
if 'OUR_SKILLS' not in backup and 'restore_skills.sh' not in backup:
    fails.append('github_backup.py لا يقرأ قائمة المهارات من restore_skills.sh (قائمة ثانية مكتوبة بيده)')

import os
SKILLS = Path(os.environ['SKILLS_DIR']) if os.environ.get('SKILLS_DIR') else (
    Path('/home/ubuntu/skills') if (os.access('/home/ubuntu/skills', os.R_OK | os.X_OK) and Path('/home/ubuntu/skills').is_dir()) else Path(__file__).resolve().parent.parent.parent / 'skills')
# 2) كل مهارة في المزامنة موجودة فعلًا في مجلد المهارات
for sk in sorted(sync_skills):
    if not (SKILLS / sk).is_dir():
        fails.append(f'المهارة {sk} مذكورة في المزامنة وغير موجودة في مجلد المهارات')

# 3) المهارات المذكورة حرفيًا في النسخ الاحتياطي لا تتجاوز قائمة المزامنة
literal = set(re.findall(r'"((?:marine|military|macr|superpowers)[a-z-]*)"', backup))
extra = literal - sync_skills
if extra:
    fails.append(f'مهارات في النسخ الاحتياطي وغير موجودة في المزامنة: {sorted(extra)}')

# 4) المهارة الجديدة مذكورة في المزامنة (حرس ضد نسيانها)
if 'superpowers-method' not in sync_skills:
    fails.append('مهارة superpowers-method ليست في قائمة المزامنة')

print('  القاعدة: قائمة مهارات واحدة — المزامنة والنسخ الاحتياطي لا يفترقان')
print('  المهارات في المزامنة:', ' · '.join(sorted(sync_skills)))
if fails:
    print('  ✘ فشل:')
    for f in fails:
        print('    ·', f)
    sys.exit(1)
print('  ✔ قائمة المهارات موحّدة بين المزامنة والنسخ الاحتياطي')
