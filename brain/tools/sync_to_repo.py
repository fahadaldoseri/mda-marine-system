#!/usr/bin/env python3
"""مزامنة الدماغ إلى مرآة المستودع بلا أي أداة خارجية (بديل rsync الدائم).
الاستخدام: python3 tools/sync_to_repo.py --brain <dir> --repo <dir>/brain [--dry-run]"""
import argparse, filecmp, shutil
from pathlib import Path

EXCLUDE_DIRS = {'.git', 'secrets', '__pycache__', 'shots', '.pytest_cache'}
EXCLUDE_FILES = {'telegram-chat.json', 'telegram-targets.json', 'telegram-subscriptions.json'}
EXCLUDE_GLOBS = ('*.pyc', '*.tmp', 'telegram*.json')

def skip(p: Path) -> bool:
    if p.is_dir():
        return p.name in EXCLUDE_DIRS
    if p.name in EXCLUDE_FILES:
        return True
    return any(p.match(g) for g in EXCLUDE_GLOBS)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain', required=True); ap.add_argument('--repo', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    src, dst = Path(a.brain), Path(a.repo)
    if not src.is_dir():
        raise SystemExit(f'✘ SYNC_GUARD: مصدر غير موجود {src}')
    copied = updated = removed = 0
    for p in src.rglob('*'):
        if skip(p):
            continue
        rel = p.relative_to(src); t = dst / rel
        if p.is_dir():
            t.mkdir(parents=True, exist_ok=True); continue
        t.parent.mkdir(parents=True, exist_ok=True)
        if not t.exists():
            if not a.dry_run: shutil.copy2(p, t)
            copied += 1
        elif not filecmp.cmp(p, t, shallow=False):
            if not a.dry_run: shutil.copy2(p, t)
            updated += 1
    for t in list(dst.rglob('*')):
        if skip(t) or t.is_dir():
            continue
        if not (src / t.relative_to(dst)).exists():
            if not a.dry_run: t.unlink()
            removed += 1
    print(f'  المزامنة: جديد={copied} · محدَّث={updated} · محذوف={removed} · {"تجربة" if a.dry_run else "منفّذ"}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
