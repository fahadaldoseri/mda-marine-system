#!/usr/bin/env python3
"""فرز الاستثناءات المؤقتة في حلقة الإغلاق وبناء خطة معالجة قبل المهلة.

الاستثناء ليس إغلاقًا: صف بلا دليل إغلاق يبقى «مستثنى» بمهلة ومالك. هذه الأداة
تصنّف كل استثناء حسب **قابلية إغلاقه بالقياس** ثم تُنتج خطة دفعات وميزانية زمنية
تنتهي عند أقرب مهلة مسجّلة، وتكتب مخرَجين: JSON للقياس وMarkdown للتسليم.

الاستخدام:
  python3 tools/triage_closure_exceptions.py --root . [--write] [--json-only]
رموز الخروج: 0 نجح الفرز · 2 تعذّر القياس (ملفات مفقودة)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

EXC = 'audit/closure-exceptions.json'
LOG = 'audit/سجل-الأعطال-والثغرات.md'
OUT_JSON = 'audit/measurements/exceptions-triage-{date}.json'
OUT_MD = 'audit/خطة-معالجة-الاستثناءات.md'

CMD_HINT = re.compile(r'(python3 |bash |pytest |pgrep |curl |check_|validators/|tools/|\.py\b|rc=|خرج )')
ID_CELL = re.compile(r'^[^\s|]+$')


def read_rows(log_path: pathlib.Path) -> dict[str, list[str]]:
    """يقرأ صفوف سجل الأعطال: المعرّف ← خلاياه (12 عمودًا)."""
    rows: dict[str, list[str]] = {}
    for line in log_path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('|') or line.startswith('|---') or line.startswith('| ---'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 8 or not ID_CELL.match(cells[0]) or cells[0] in ('الرقم', 'رقم'):
            continue
        rows[cells[0]] = cells
    return rows


def classify(cells: list[str]) -> tuple[str, str]:
    """يصنّف الصف: قابل للإغلاق بقياس · يحتاج دليلًا تاريخيًا · بلا نصّ حاجز."""
    fix = cells[5] if len(cells) > 5 else ''
    barrier = cells[6] if len(cells) > 6 else ''
    text = f'{fix} {barrier}'
    if len(text.strip()) < 40 or set(text.strip()) <= set('—-'):
        return 'بلا نصّ حاجز', 'لا إصلاح ولا حاجز مكتوب: يلزم قرار مالك (إصلاح أو قبول مخاطر دائم)'
    if CMD_HINT.search(text):
        return 'قياس جاهز', 'الأمر معلن في السجل: يُشغَّل ويُسجَّل مخرَجه وبصمته ثم يُرقّى الصف إلى «مغلق»'
    return 'يحتاج دليلًا تاريخيًا', 'الوصف بلا أمر قابل للتشغيل: يُستخرج دليل تاريخي أو يُعاد توليد الحاجز قابلًا للقياس'


def main() -> int:
    ap = argparse.ArgumentParser(description='فرز الاستثناءات وخطة المعالجة')
    ap.add_argument('--root', default='.')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--json-only', action='store_true')
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    exc_p, log_p = root / EXC, root / LOG
    if not exc_p.is_file() or not log_p.is_file():
        print(f'✘ ملف مفقود: {exc_p if not exc_p.is_file() else log_p}')
        return 2

    data = json.loads(exc_p.read_text(encoding='utf-8'))
    entries = data['entries']
    rows = read_rows(log_p)
    today = dt.date.today()
    expires = sorted({e['expires_at'][:10] for e in entries if e.get('expires_at')})
    deadline = dt.date.fromisoformat(expires[0]) if expires else today + dt.timedelta(days=60)
    days_left = max((deadline - today).days, 0)

    buckets: dict[str, list[dict]] = {}
    axes: dict[str, int] = {}
    states: dict[str, int] = {}
    for e in entries:
        cells = rows.get(e['fault_id'], [])
        kind, action = classify(cells)
        axis = cells[2] if len(cells) > 2 else 'غير معروف'
        axes[axis] = axes.get(axis, 0) + 1
        states[e.get('state', 'غير محدّد')] = states.get(e.get('state', 'غير محدّد'), 0) + 1
        buckets.setdefault(kind, []).append({
            'fault_id': e['fault_id'], 'axis': axis, 'state': e.get('state'),
            'expires_at': e.get('expires_at', '')[:10], 'owner': e.get('owner'),
            'disposition': action, 'has_row': bool(cells),
        })

    ready = len(buckets.get('قياس جاهز', []))
    need_ev = len(buckets.get('يحتاج دليلًا تاريخيًا', []))
    no_text = len(buckets.get('بلا نصّ حاجز', []))
    target_weekly = -(-ready // max(int(days_left / 7) or 1, 1)) if ready else 0

    summary = {
        'date': today.isoformat(), 'total': len(entries), 'deadline': deadline.isoformat(),
        'days_left': days_left, 'measured_ready': ready, 'needs_evidence': need_ev,
        'no_text': no_text, 'rows_missing_in_log': sum(1 for v in buckets.values() for x in v if not x['has_row']),
        'weekly_target_for_measurable': target_weekly, 'axes': axes, 'states': states,
        'buckets': {k: [x['fault_id'] for x in v] for k, v in buckets.items()},
    }

    out_json = root / OUT_JSON.format(date=today.isoformat())
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'   الاستثناءات: {len(entries)} · المهلة: {deadline} · المتبقي: {days_left} يومًا')
    print(f'   قياس جاهز: {ready} · يحتاج دليلًا: {need_ev} · بلا نصّ حاجز: {no_text}')
    print(f'   الهدف الأسبوعي القابل للقياس: {target_weekly} صفًا')

    if a.json_only:
        return 0

    lines = [
        f'# خطة معالجة الاستثناءات المؤقتة — {today.isoformat()}',
        '',
        f'- إجمالي الاستثناءات: **{len(entries)}** · المهلة المسجّلة: **{deadline.isoformat()}** (المتبقي {days_left} يومًا).',
        f'- قياس جاهز: **{ready}** · يحتاج دليلًا تاريخيًا: **{need_ev}** · بلا نصّ حاجز: **{no_text}**.',
        f'- صفوف بمعرّف غير موجود في سجل الأعطال: **{summary["rows_missing_in_log"]}**.',
        f'- الهدف الأسبوعي القابل للقياس: **{target_weekly}** صفًا حتى المهلة.',
        '',
        '## التوزيع على المحاور',
        '',
        '| المحور | العدد |',
        '| --- | --- |',
        *[f'| {k} | {v} |' for k, v in sorted(axes.items(), key=lambda x: -x[1])[:15]],
        '',
        '## الدفعات',
        '',
        f'1. **دفعة القياس ({ready})**: تُشغَّل الأوامر المعلنة في عمود «التشديد والحالة» وتُسجَّل مخرجاتها وبصمتها، ثم يُرقّى الصف إلى «مغلق» بعقد الدليل.',
        f'2. **دفعة الدليل التاريخي ({need_ev})**: تُستخرج لكل صف حجة أو أثر أو قياس تاريخي؛ وإن تعذّر، يُعاد توليد الحاجز قابلًا للقياس (أمر + مخرَج).',
        f'3. **دفعة القرار ({no_text})**: صف بلا إصلاح ولا حاجز مكتوب — قرار مالك بين إصلاح جذري أو قبول مخاطر دائم مسجَّل بسبب.',
        '',
        '## الضوابط',
        '',
        '- لا يُحوَّل استثناء إلى «مغلق» بالتحرير: الإغلاق يحتاج أمرًا ومخرَجًا وبصمة كما في `skills/rerun-step-to-live-parity-ops/references/closure-evidence-contract.md`.',
        '- الميزانية تُقاس أسبوعيًا بأداة الفرز نفسها، وتُقارَن بالخط السابق في `audit/measurements/exceptions-triage-*.json`.',
        '- `validators/check_exceptions_burndown.py` يمنع: زيادة عدد الاستثناءات، أو بقاء استثناء تنتهي مهلته خلال 30 يومًا بلا إغلاق.',
        '',
        '## تفصيل الصفوف',
        '',
        '| المعرّف | المحور | الحالة | المهلة | التصرف |',
        '| --- | --- | --- | --- | --- |',
    ]
    for kind in ('قياس جاهز', 'يحتاج دليلًا تاريخيًا', 'بلا نصّ حاجز'):
        for x in sorted(buckets.get(kind, []), key=lambda y: y['fault_id'])[:400]:
            lines.append(f"| {x['fault_id']} | {x['axis']} | {x['state']} | {x['expires_at']} | {x['disposition']} |")
    (root / OUT_MD).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'   كُتب: {OUT_MD} و{OUT_JSON.format(date=today.isoformat())}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
