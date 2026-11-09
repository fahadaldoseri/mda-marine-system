#!/usr/bin/env python3
"""تسليح صفوف سجل الأعطال بأوامر دليل حقيقية قابلة للتنفيذ.

القاعدة الحاكمة: لا يُسلَّح الصف إلا بأمر يشير إلى ملف/أداة **موجود فعلًا** في المستودع،
وإلا بُقي في قائمة «بلا أمر» ليُعالج باستثناء مؤرّخ بسبب مكتوب — لا دليل شكلي.

الاستخدام:
  python3 arm_evidence_from_log.py --root . --size 39 --out commands-E1.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

TOKEN = re.compile(r'(?:validators|tests|tools|generator|skills)/[\w\u0600-\u06FF./-]+\.(?:py|sh)')
BASENAME = re.compile(r'\b([A-Za-z_][\w-]*\.(?:py|sh|json))\b')
DIRS = ('validators', 'tests', 'tools', 'generator')


def repo_index(root: pathlib.Path) -> dict[str, pathlib.Path]:
    index: dict[str, pathlib.Path] = {}
    for d in DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for p in base.rglob('*'):
            if p.is_file() and p.suffix in ('.py', '.sh'):
                index.setdefault(p.name, p)
    return index


def read_rows(root: pathlib.Path) -> dict[str, list[str]]:
    log = root / 'audit' / 'سجل-الأعطال-والثغرات.md'
    rows: dict[str, list[str]] = {}
    for line in log.read_text(encoding='utf-8').splitlines():
        if line.startswith('| ك-'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 12:
                rows[cells[0]] = cells
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--size', type=int, default=39)
    ap.add_argument('--out', default='audit/measurements/batches/commands-E1.json')
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    index = repo_index(root)
    rows = read_rows(root)
    pending_file = root / 'audit/measurements/batches/no-command-rows-2.json'
    pending = json.loads(pending_file.read_text(encoding='utf-8'))['rows'] if pending_file.exists() else list(rows)

    armed: dict[str, str] = {}
    unarmed: list[str] = []
    for fid in pending:
        cells = rows.get(fid)
        if not cells:
            continue
        blob = ' '.join(cells[4:11])
        rel = next((t for t in TOKEN.findall(blob) if (root / t).exists()), None)
        if rel:
            armed[fid] = f'timeout 120 python3 {rel}'
            continue
        base = next((n for n in BASENAME.findall(blob) if n in index), None)
        if base:
            armed[fid] = f'timeout 120 python3 {index[base].relative_to(root)}'
            continue
        unarmed.append(fid)

    batch = dict(list(armed.items())[:a.size])
    (root / a.out).write_text(json.dumps({'commands': batch}, ensure_ascii=False, indent=1), encoding='utf-8')
    rest = list(armed.keys())[a.size:] + unarmed
    (root / 'audit/measurements/batches/no-command-rows-2.json').write_text(
        json.dumps({'rows': rest}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'   مسلَّح هذه الدفعة: {len(batch)} · مسلَّح مؤجَّل: {max(0, len(armed) - a.size)} · بلا دليل: {len(unarmed)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())