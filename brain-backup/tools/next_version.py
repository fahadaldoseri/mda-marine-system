#!/usr/bin/env python3
"""رقم النسخة — توليد وتحقق.

الاصطلاح المعتمد (13 أكتوبر 2026): «و ب YY/MM/NN»
  «و ب» = اختصار اسم الجهة: مركز الوعي بالمجال البحري (ثابت في كل الإصدارات)
  YY    = السنة (آخر خانتين)
  MM    = الشهر
  NN    = رقم الإصدار المتسلسل داخل الشهر — يبدأ 1 عند كل شهر جديد (وكل سنة جديدة)، ويتقدّم 1 كل إصدار

الاستخدام:
  python3 tools/next_version.py [التاريخ]            # يطبع رقم النسخة المتوقع
  python3 tools/next_version.py --check [التاريخ]    # يتحقق أن رقم نسخة اليوم صحيح (رمز خروج 1 عند الفشل)
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
import json, re, sys, datetime
from pathlib import Path

B = Path(f'{BRAIN}')
PREFIX = 'و ب '
PAT = re.compile(r'^و ب (\d{2})/(\d{2})/(\d+)(?:\s*—.*)?$')


def editions():
    """كل الإصدارات المسجّلة: (التاريخ، السنة، الشهر، المتسلسل)."""
    out = []
    for p in sorted((B / 'web' / 'meta').glob('*.json')):
        if not re.match(r'^\d{4}-\d{2}-\d{2}\.json$', p.name):
            continue
        m = PAT.match(json.loads(p.read_text(encoding='utf-8')).get('version', '').strip())
        if m:
            out.append((p.stem, int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return out


def next_version(date=None):
    date = date or datetime.date.today().isoformat()
    y, m = int(date[:4]) % 100, int(date[5:7])
    prev = [e for e in editions() if e[0] < date]
    same_month = [e for e in prev if (e[1], e[2]) == (y, m)]
    # تصفير المتسلسل عند كل شهر جديد (ويشمل السنة الجديدة)
    nn = (max(same_month, key=lambda e: e[0])[3] + 1) if same_month else 1
    return f'{PREFIX}{y:02d}/{m:02d}/{nn}', nn


def check(date=None):
    date = date or datetime.date.today().isoformat()
    expect, nn = next_version(date)
    path = B / 'web' / 'meta' / f'{date}.json'
    if not path.exists():
        print(f'  ✘ لا ملف واجهة لتاريخ {date}')
        return 1
    v = json.loads(path.read_text(encoding='utf-8')).get('version', '').strip()
    mm = PAT.match(v)
    if not mm:
        print(f'  ✘ رقم النسخة «{v}» لا يطابق الصيغة «و ب YY/MM/NN»')
        return 1
    y, m = int(date[:4]) % 100, int(date[5:7])
    if (int(mm.group(1)), int(mm.group(2))) != (y, m):
        print(f'  ✘ رقم النسخة «{v}» لا يوافق سنة/شهر تاريخ الإصدار {date}')
        return 1
    ok = v == expect
    print(f'  {"✔" if ok else "✘"} رقم نسخة {date}: «{v}» — المتوقع «{expect}»')
    return 0 if ok else 1


def precheck(date=None):
    """فحص قبل الكتابة: يتحقق أن الترقيم سيأتي متسلسلًا بلا فجوة (بلا حاجة لملف اليوم)."""
    date = date or datetime.date.today().isoformat()
    expect, nn = next_version(date)
    eds = editions()
    if any(e[0] == date for e in eds):
        print(f'  ! إصدار مسجّل لتاريخ {date} بالفعل — تحقق من منع التكرار')
        return 0
    y, m = int(date[:4]) % 100, int(date[5:7])
    same = [e for e in eds if (e[1], e[2]) == (y, m)]
    if same:
        last = max(same, key=lambda e: e[0])
        if nn != last[3] + 1:
            print(f'  ✘ المتسلسل غير متصل: آخر إصدار {last[3]} والمتوقع {nn}')
            return 1
    elif nn != 1:
        print(f'  ✘ أول إصدار في الشهر يجب أن يكون 1 لا {nn}')
        return 1
    print(f'  ✔ الترقيم متسلسل · {len(eds)} إصدارًا مسجّلًا · التالي ليوم {date}: «{expect}»')
    return 0


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--precheck' in sys.argv:
        sys.exit(precheck(args[0] if args else None))
    if '--check' in sys.argv:
        sys.exit(check(args[0] if args else None))
    v, nn = next_version(args[0] if args else None)
    print(f'  رقم النسخة التالي: «{v}»  (المتسلسل داخل الشهر: {nn})')
