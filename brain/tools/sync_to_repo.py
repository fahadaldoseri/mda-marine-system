#!/usr/bin/env python3
"""مزامنة أصول المشروع إلى مرآة المستودع بلا أي أداة خارجية (بديل rsync الدائم).

الاستخدام:
  python3 tools/sync_to_repo.py --brain <dir> --repo <dir>/brain [--dry-run] [--allow-delete]
  python3 tools/sync_to_repo.py --brain <dir> --repo <dir>/brain \
      --site /home/ubuntu/seawatch --repo-site <dir>/site \
      --skills /home/ubuntu/skills --repo-skills <dir>/skills

حارس فشل مغلق (ك-269): لا حذف جماعي ولا حذف خارج نطاق المصدر بلا --allow-delete.

عطل 2026-10-28 (انحراف التماثل المتكرر): الأداة كانت تغطي شجرة الدماغ وحدها، فكانت
مرآتا الموقع والمهارات تنحرفان كل يوم ويظهر «انحراف مانع» في المقيّم. القاعدة الآن:
كل جذر يقيسه مقيّم التماثل (brain · site · skills) له مزامنة في الأمر نفسه.
"""
import argparse, filecmp, shutil
from pathlib import Path

EXCLUDE_DIRS = {'.git', 'secrets', 'state', '__pycache__', 'shots', '.pytest_cache'}
EXCLUDE_FILES = {'telegram-chat.json', 'telegram-targets.json', 'telegram-subscriptions.json'}
EXCLUDE_GLOBS = ('*.pyc', '*.tmp', 'telegram*.json')
DELETE_MAX = 20          # سقف الحذف في التشغيل العادي
SITE_EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'logs'}
SKILLS_EXCLUDE_DIRS = {'.git', '__pycache__'}


def skip(p: Path, dirs: set, files: set = EXCLUDE_FILES, globs=EXCLUDE_GLOBS) -> bool:
    """استثناء بالمسار لا بالاسم فقط: أي مجلد محظور في أي مستوى يُستثنى بمحتواه."""
    if any(part in dirs for part in p.parts):
        return True
    if p.is_dir():
        return False
    if p.name in files:
        return True
    return any(p.match(g) for g in globs)


def plan(src: Path, dst: Path, dirs: set, files: set, globs) -> dict:
    """يحسب الخطة بلا تنفيذ: جديد · محدَّث · محذوف (قائمة المسارات)."""
    add, upd, dele = [], [], []
    for p in src.rglob('*'):
        if skip(p, dirs, files, globs) or p.is_dir():
            continue
        rel = p.relative_to(src); t = dst / rel
        if not t.exists():
            add.append(rel)
        elif not filecmp.cmp(p, t, shallow=False):
            upd.append(rel)
    for t in dst.rglob('*'):
        if skip(t, dirs, files, globs) or t.is_dir():
            continue
        if not (src / t.relative_to(dst)).exists():
            dele.append(t.relative_to(dst))
    return {'add': add, 'upd': upd, 'del': dele}


def run_pair(label: str, src: Path, dst: Path, a) -> int:
    """يزامن زوجًا واحدًا (مصدر ← مرآة) بحارس الحذف نفسه. يُعيد رمز الخروج."""
    if not src.is_dir():
        raise SystemExit(f'✘ SYNC_GUARD: مصدر غير موجود {src}')
    if not dst.is_dir():
        raise SystemExit(f'✘ SYNC_GUARD: هدف غير موجود {dst}')

    p = plan(src, dst, a.exclude_dirs, a.exclude_files, a.exclude_globs)
    top_src = {x.name for x in src.iterdir()}
    outside = [d for d in p['del'] if d.parts and d.parts[0] not in top_src]

    if outside:
        print(f'  ✘ SYNC_GUARD[{label}]: {len(outside)} ملفًا خارج نطاق المصدر سيُحذف (مثال: {outside[:3]})')
    if len(p['del']) > DELETE_MAX:
        print(f'  ✘ SYNC_GUARD[{label}]: الحذف {len(p["del"])} ملفًا يتجاوز السقف {DELETE_MAX}')
    blocked = (bool(outside) or len(p['del']) > DELETE_MAX) and not a.allow_delete
    if blocked:
        print(f'  ⛔ [{label}] مُنع الحذف — راجع الخطة ثم أعد التشغيل بـ --allow-delete إن كان الحذف مقصودًا')
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
    print(f'  المزامنة[{label}]: جديد={copied} · محدَّث={updated} · محذوف={removed} · '
          f'{"تجربة" if a.dry_run else "منفّذ"}')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--site', help='جذر موقع seawatch على الخادم')
    ap.add_argument('--repo-site', help='مجلد site في المستودع')
    ap.add_argument('--skills', help='جذر المهارات على الخادم')
    ap.add_argument('--repo-skills', help='مجلد skills في المستودع')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--allow-delete', action='store_true',
                    help='السماح بالحذف الجماعي أو خارج نطاق المصدر بعد مراجعة الخطة')
    a = ap.parse_args()

    a.exclude_dirs, a.exclude_files, a.exclude_globs = EXCLUDE_DIRS, EXCLUDE_FILES, EXCLUDE_GLOBS
    rc = run_pair('brain', Path(a.brain), Path(a.repo), a)

    if a.site and a.repo_site:
        a.exclude_dirs = SITE_EXCLUDE_DIRS
        a.exclude_files = set()
        a.exclude_globs = ('*.pyc', '*.tmp')
        rc = max(rc, run_pair('site', Path(a.site), Path(a.repo_site), a))
    elif bool(a.site) != bool(a.repo_site):
        print('  ✘ SYNC_GUARD: يجب تمرير --site و--repo-site معًا'); return 2

    if a.skills and a.repo_skills:
        a.exclude_dirs = SKILLS_EXCLUDE_DIRS
        a.exclude_files = set()
        a.exclude_globs = ('*.pyc', '*.tmp')
        rc = max(rc, run_pair('skills', Path(a.skills), Path(a.repo_skills), a))
    elif bool(a.skills) != bool(a.repo_skills):
        print('  ✘ SYNC_GUARD: يجب تمرير --skills و--repo-skills معًا'); return 2

    return rc


if __name__ == '__main__':
    raise SystemExit(main())