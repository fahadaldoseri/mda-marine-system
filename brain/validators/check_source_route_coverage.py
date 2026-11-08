#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة تغطية مسارات المصادر — تفشل مغلقًا.

المشكلة التي أُغلقت: ثلاثة عشر مصدرًا معتمدة لم يكن لها صف في جدول التغذيات،
فلم يكن الفحص يحاولها أصلًا، وكانت تُعدّ «مرجعية يدوية» بلا برهان. النقص كان
في جدول المسارات، لا في القنوات.

القاعدة: كل مصدر معتمد يجب أن يكون له مسار معلن:
  • إمّا صف في جدول التغذيات (مسار آلي)،
  • وإمّا قيد موثَّق في MANUAL_REFERENCE بلا مسار آلي مُثبت.
وما ليس له هذا ولا ذاك ⇒ مانع.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
for _i, _a in enumerate(sys.argv):
    if _a == '--brain' and _i + 1 < len(sys.argv):
        B = Path(sys.argv[_i + 1]).resolve()
sys.path.insert(0, str(B / 'tools'))


def approved() -> list[int]:
    recs = json.loads((B / 'appendices' / 'source-reliability-40.json').read_text(encoding='utf-8'))
    return sorted(int(r[0]) for r in recs)


def routed() -> set[int]:
    import check_feeds  # noqa: WPS433
    return {int(f['num']) for f in check_feeds.feeds()}


def manual() -> set[int]:
    import source_channels  # noqa: WPS433
    return {int(x) for x in source_channels.MANUAL_REFERENCE}


def bare_except_in(path: Path) -> list[int]:
    """أسطر فيها except Exception عام في مستخرجات المحتوى (يخفي أخطاء البرمجة)."""
    bad = []
    for i, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if re.match(r'^\s*except\s+Exception\s*:', line):
            bad.append(i)
    return bad


def main() -> int:
    problems: list[str] = []
    ok, failed, manual_nums = set(), set(), manual()

    try:
        live = json.loads((B / 'feeds' / f'feeds-{_date()}.status.json').read_text(encoding='utf-8'))
        # مصدر واحد قد يكون له أكثر من صف مسار؛ المتعذّر هو ما فشلت كل مساراته لا صف واحد.
        by_num: dict[int, bool] = {}
        for f in live['checked_feeds']:
            n = int(f['num'])
            by_num[n] = by_num.get(n, False) or bool(f['ok'])
        ok = {n for n, good in by_num.items() if good}
        failed = {n for n, good in by_num.items() if not good}
        if set(live.get('manual_reference', [])) != manual_nums:
            problems.append(
                'قائمة «مرجعية يدوية» في ملف الحالة لا تطابق مصدر القنوات: '
                f"{sorted(live.get('manual_reference', []))} ≠ {sorted(manual_nums)}")
    except (OSError, KeyError, ValueError) as e:
        problems.append(f'تعذّر قراءة ملف حالة الفحص: {type(e).__name__}: {e}')

    ap, rt = set(approved()), routed()
    covered = rt | manual_nums
    missing = sorted(ap - covered)
    if missing:
        problems.append(f'مصادر معتمدة بلا مسار معلن: {missing}')
    both = sorted(rt & manual_nums)
    if both:
        problems.append(f'مصادر مُعلنة مسارًا آليًا وفي «مرجعية يدوية» معًا: {both}')

    bad = bare_except_in(B / 'tools' / 'content_extractors.py')
    if bad:
        problems.append(f'except Exception عام في مستخرجات المحتوى (أسطر {bad}) يخفي أخطاء البرمجة')

    if len(ok) + len(failed) + len(manual_nums) != len(ap):
        problems.append(
            'العدّاد لا يغطي كل المصادر المعتمدة: '
            f'{len(ok)} ناجح + {len(failed)} متعذّر + {len(manual_nums)} يدوي = '
            f'{len(ok) + len(failed) + len(manual_nums)} من {len(ap)}')

    print(f'   مسارات معلنة: {len(rt)} · مرجعية يدوية موثَّقة: {len(manual_nums)} '
          f'({sorted(manual_nums)}) · معتمدة: {len(ap)}')
    print(f'   نجح {len(ok)} · تعذّر {len(failed)} · فشل {len(problems)}')
    for p in problems:
        print(f'   ✘ {p}')
    if problems:
        return 1
    print('   ✔ تغطية المصادر كاملة ومتسقة')
    return 0


def _date() -> str:
    for i, a in enumerate(sys.argv):
        if a == '--date' and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


if __name__ == "__main__":
    args = sys.argv[1:]
    if any(a in ('--help', '-h') for a in args):
        print(__doc__)
        raise SystemExit(0)
    unknown_flags = []
    unknown_values = []
    i = 0
    while i < len(args):
        value = args[i]
        if value in ('--brain', '--date'):
            if i + 1 >= len(args) or args[i + 1].startswith('-'):
                print(f'الخيار {value} يحتاج قيمة', file=sys.stderr)
                raise SystemExit(2)
            i += 2
            continue
        if value.startswith('-'):
            unknown_flags.append(value)
        else:
            unknown_values.append(value)
        i += 1
    if unknown_flags or unknown_values:
        bad = unknown_flags[0] if unknown_flags else unknown_values[0]
        print(f'وسيط غير معروف: {bad}', file=sys.stderr)
        raise SystemExit(2)
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ولا يُبتلع.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
