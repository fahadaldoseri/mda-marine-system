#!/usr/bin/env python3
"""حلقة التعلم الذاتي لمهارة superpowers-method.

تُستدعى في نهاية tools/final_gate.sh بعد كتابة الخلاصة. لا تمنع ولا تُعدّل أي بوابة:
تقرأ نتيجة التشغيل وتسجّل الدروس وتُحدّث كتلة «الدروس المتراكمة» في ملف المهارة.

الأوامر:
    python3 tools/skill_lessons.py --date 2026-10-23
    python3 tools/skill_lessons.py --date 2026-10-23 --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = Path('/home/ubuntu/skills/superpowers-method/SKILL.md')
SKILL_MIRROR = ROOT / 'skills' / 'superpowers-method' / 'SKILL.md'
FAULTS = ROOT / 'audit' / 'سجل-الأعطال-والثغرات.md'
LOG = ROOT / 'memory' / 'learning-log.jsonl'
START = '<!-- AUTO-LESSONS:START'
END = '<!-- AUTO-LESSONS:END -->'


def sha16(path: Path) -> str:
    if not path.exists():
        return '—'
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def gate_summary(date: str) -> dict:
    """يقرأ نتيجة البوابة: gate.json ثم report.txt."""
    d = ROOT / 'logs' / f'gate-{date}'
    out = {'status': None, 'exit_code': None, 'steps': None, 'block': 0, 'warn': 0,
           'log_dir': str(d), 'report_sha16': sha16(d / 'report.txt')}
    gj = d / 'gate.json'
    if gj.exists():
        try:
            g = json.loads(gj.read_text(encoding='utf-8'))
            out['status'] = g.get('status')
            out['exit_code'] = g.get('exit_code')
            steps = g.get('steps') or []
            out['steps'] = len(steps)
            out['block'] = sum(1 for s in steps if str(s.get('verdict') or s.get('result')) == 'block')
            out['warn'] = sum(1 for s in steps if str(s.get('verdict') or s.get('result')) == 'warn')
        except (json.JSONDecodeError, OSError):
            pass
    rep = d / 'report.txt'
    if rep.exists():
        t = rep.read_text(encoding='utf-8', errors='ignore')
        if out['steps'] is None:
            out['steps'] = len([l for l in t.splitlines() if l.strip()])
        out['block'] = out['block'] or len(re.findall(r'\bblock\b', t))
        out['warn'] = out['warn'] or len(re.findall(r'\bwarn\b', t))
    return out


def fault_ids() -> list[str]:
    """يستخرج معرّفات الأعطال من سجل الأعطال."""
    if not FAULTS.exists():
        return []
    t = FAULTS.read_text(encoding='utf-8', errors='ignore')
    return sorted(set(re.findall(r'ك-\d{3}', t)))


def known_faults_in_lessons() -> set[str]:
    """المعطّلات المسجَّلة سابقًا في كتلة الدروس أو في سجل التعلم."""
    seen: set[str] = set()
    if SKILL.exists():
        seen |= set(re.findall(r'ك-\d{3}', SKILL.read_text(encoding='utf-8', errors='ignore')))
    if LOG.exists():
        seen |= set(re.findall(r'ك-\d{3}', LOG.read_text(encoding='utf-8', errors='ignore')))
    return seen


def append_log(entry: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + '\n')


def update_lessons(block: str) -> bool:
    """يستبدل كتلة الدروس في ملف المهارة (ونسختها في المستودع إن وُجدت)."""
    changed = False
    for path in (SKILL, SKILL_MIRROR):
        if not path.exists():
            continue
        t = path.read_text(encoding='utf-8')
        i, j = t.find(START), t.find(END)
        if i == -1 or j == -1:
            continue
        new = t[:i] + START + ' — تُحدَّث آليًا بـ tools/skill_lessons.py ولا تُحرَّر يدويًا -->\n' + block + '\n' + t[j:]
        if new != t:
            path.write_text(new, encoding='utf-8')
            changed = True
    return changed


def build_block(date: str, summ: dict, new_faults: list[str], history: list[str]) -> str:
    lines = ['## 5) الدروس المتراكمة', '',
             f'- **{date}** — نتيجة البوابة: `{summ["status"]}` (رمز `{summ["exit_code"]}`) · '
             f'خطوات: {summ["steps"]} · مانع: {summ["block"]} · تحذير: {summ["warn"]} · '
             f'بصمة `report.txt`: `{summ["report_sha16"]}`']
    if new_faults:
        lines.append(f'- **{date}** — أعطال جديدة دخلت السجل: {" · ".join(new_faults)} — القاعدة المطلوبة: لكل عطل منها قاعدة مانعة في بوابة أو مكتبة.')
    else:
        lines.append(f'- **{date}** — لا عطل جديد في السجل.')
    # ك-149: لا يُعاد درس اليوم داخل «سجل الدروس السابق»، والتكرار يُزال.
    seen: set[str] = set()
    prev: list[str] = []
    for h in history:
        s = h.strip()
        if s.startswith(f'- **{date}**') or s in seen or not s:
            continue
        seen.add(s)
        prev.append(h)
    lines += ['', '<details><summary>سجل الدروس السابق</summary>', '']
    lines += prev or ['_لا دروس سابقة._']
    lines += ['', '</details>']
    return '\n'.join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    summ = gate_summary(a.date)
    seen = known_faults_in_lessons()
    new_faults = [f for f in fault_ids() if f not in seen]

    history: list[str] = []
    if SKILL.exists():
        t = SKILL.read_text(encoding='utf-8')
        i, j = t.find(START), t.find(END)
        if i != -1 and j != -1:
            old = t[i:j]
            history = [l for l in old.splitlines()
                       if l.strip().startswith('- **') and l.strip() not in ('- **', '')]
    entry = {
        'ts_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'date': a.date,
        'skill': 'superpowers-method',
        'kind': 'حلقة تعلم ذاتية',
        'gate_status': summ['status'],
        'gate_exit': summ['exit_code'],
        'steps': summ['steps'],
        'block': summ['block'],
        'warn': summ['warn'],
        'new_faults': new_faults,
        'report_sha16': summ['report_sha16'],
    }
    if a.dry_run:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0

    append_log(entry)
    block = build_block(a.date, summ, new_faults, history[:40])
    # ك-495: نتيجة كل تشغيل تُدوَّن في سجل تشغيل مستقل، لا في أصل المهارة الحاكم؛
    # كتابتها في المهارة كانت تُنشئ انحراف تماثل بعد كل بوابة (عطل متكرر).
    status_log = ROOT / 'logs' / 'gate-status.md'
    status_log.parent.mkdir(parents=True, exist_ok=True)
    with status_log.open('a', encoding='utf-8') as fh:
        fh.write(f'\n<!-- {entry["ts_utc"]} -->\n' + block + '\n')
    # المهارة تُحدَّث فقط عند درس جديد حقيقي (عطل جديد يدخل السجل).
    changed = update_lessons(block) if new_faults else False
    print(f'  • حلقة التعلم: نتيجة {summ["status"]} · أعطال جديدة: {len(new_faults)}'
          f'{" · حُدّثت كتلة الدروس" if changed else ""}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
