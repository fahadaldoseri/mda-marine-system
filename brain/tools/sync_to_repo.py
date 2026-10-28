#!/usr/bin/env python3
"""مزامنة الدماغ إلى مرآة المستودع بلا أي أداة خارجية (بديل rsync الدائم).
الاستخدام: python3 tools/sync_to_repo.py --brain <dir> --repo <dir>/brain [--dry-run] [--allow-delete]

حارس فشل مغلق (ك-269): لا حذف جماعي ولا حذف خارج نطاق الدماغ بلا --allow-delete.
"""
import argparse, filecmp, shutil
from pathlib import Path

EXCLUDE_DIRS = {'.git', 'secrets', 'state', '__pycache__', 'shots', '.pytest_cache'}
EXCLUDE_FILES = {'telegram-chat.json', 'telegram-targets.json', 'telegram-subscriptions.json'}
EXCLUDE_GLOBS = ('*.pyc', '*.tmp', 'telegram*.json')
DELETE_MAX = 20          # سقف الحذف في التشغيل العادي


def skip(p: Path) -> bool:
    """استثناء بالمسار لا بالاسم فقط: أي مجلد محظور في أي مستوى يُستثنى بمحتواه."""
    if any(part in EXCLUDE_DIRS for part in p.parts):
        return True
    if p.is_dir():
        return False
    if p.name in EXCLUDE_FILES:
        return True
    return any(p.match(g) for g in EXCLUDE_GLOBS)


def plan(src: Path, dst: Path) -> dict:
    """يحسب الخطة بلا تنفيذ: جديد · محدَّث · محذوف (قائمة المسارات)."""
    add, upd, dele = [], [], []
    for p in src.rglob('*'):
        if skip(p) or p.is_dir():
            continue
        rel = p.relative_to(src); t = dst / rel
        if not t.exists():
            add.append(rel)
        elif not filecmp.cmp(p, t, shallow=False):
            upd.append(rel)
    for t in dst.rglob('*'):
        if skip(t) or t.is_dir():
            continue
        if not (src / t.relative_to(dst)).exists():
            dele.append(t.relative_to(dst))
    return {'add': add, 'upd': upd, 'del': dele}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--allow-delete', action='store_true',
                    help='السماح بالحذف الجماعي أو خارج نطاق الدماغ بعد مراجعة الخطة')
    a = ap.parse_args()
    src, dst = Path(a.brain), Path(a.repo)
    if not src.is_dir():
        raise SystemExit(f'✘ SYNC_GUARD: مصدر غير موجود {src}')
    if not dst.is_dir():
        raise SystemExit(f'✘ SYNC_GUARD: هدف غير موجود {dst}')

    p = plan(src, dst)
    top_src = {x.name for x in src.iterdir()}
    outside = [d for d in p['del'] if d.parts and d.parts[0] not in top_src]

    if outside:
        print(f'  ✘ SYNC_GUARD: {len(outside)} ملفًا خارج نطاق المصدر سيُحذف (مثال: {outside[:3]})')
    if len(p['del']) > DELETE_MAX:
        print(f'  ✘ SYNC_GUARD: الحذف {len(p["del"])} ملفًا يتجاوز السقف {DELETE_MAX}')
    blocked = (bool(outside) or len(p['del']) > DELETE_MAX) and not a.allow_delete
    if blocked:
        print('  ⛔ مُنع الحذف — راجع الخطة ثم أعد التشغيل بـ --allow-delete إن كان الحذف مقصودًا')
        print(f'     جديد={len(p["add"])} · محدَّث={len(p["upd"])} · محذوف={len(p["del"])}')
        return 2

    copied = updated = removed = 0
    for rel in p['add'] + p['upd']:
        t = dst / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        if not a.dry_run:
            shutil.copy2(src / rel, t)
        copied += 1 if rel in p['add'] else 0
        updated += 1 if rel in p['upd'] else 0
    for rel in p['del']:
        if not a.dry_run:
            (dst / rel).unlink()
        removed += 1
    print(f'  المزامنة: جديد={copied} · محدَّث={updated} · محذوف={removed} · {"تجربة" if a.dry_run else "منفّذ"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
