#!/usr/bin/env python3
"""بناء شجرة النسخة الاحتياطية النظيفة لمشروع مركز الوعي بالمجال البحري.

المصادر: /home/ubuntu/brain-marine-news (النظام) و /home/ubuntu/seawatch (الموقع).
الوجهة: /home/ubuntu/mda-marine-system/{brain,site}
المستثنى: الأسرار، المخلفات، النسخ المكررة، المخرجات المولّدة، صور التدقيق المؤقتة.
ويُسجَّل كل استثناء في docs/نقل-إلى-جيت-هب.md مع السبب.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
from pathlib import Path

# ── مسارات محمولة: تُقرأ من متغيّرات البيئة، والافتراضي جذر الشجرة ──
BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
SITE = Path(os.environ.get("SITE_DIR") or BRAIN.parent / "seawatch")
HOME = BRAIN.parent
OUT = Path(os.environ.get("BACKUP_REPO_DIR") or HOME / "mda-marine-system")

# مجلدات لا تُنقل (نسبةً إلى جذر كل شجرة)
BRAIN_SKIP_DIRS = {"__pycache__", ".git", "shots", "node_modules", ".pytest_cache", "backup-repo"}
SITE_SKIP_DIRS = {"__pycache__", ".git", "brain-backup", "dist", "shots", "node_modules", ".pytest_cache"}
# ملفات لا تُنقل (نسبةً إلى جذر كل شجرة)
BRAIN_SKIP_FILES = {"state/webhook-secret.txt", ".env", ".env.local"}
SITE_SKIP_FILES = {".env", ".env.local", ".env.production"}
# ملفات تُنقل مع حجب القيم السرية داخلها
SANITIZE = {
    "brain/appendices/telegram-chat.json": [(r'"chat_id"\s*:\s*"\d+"', '"chat_id": "[محجوب]"'),
                                            (r'"bot_id"\s*:\s*"\d+"', '"bot_id": "[محجوب]"')],
    "brain/appendices/telegram-subscriptions.json": [(r'"chat_id"\s*:\s*"\d+"', '"chat_id": "[محجوب]"'),
                                                     (r'"user_id"\s*:\s*"\d+"', '"user_id": "[محجوب]"')],
    "brain/research/styles/sources/archive-reports.html": [(r'token="[^"]{20,}"', 'token="[محجوب]"')],
}
EXCLUDED_LOG: list[tuple[str, str]] = []
SYMLINKS_LOG: list[tuple[str, str]] = []

def _repo_rel_of(target: Path) -> str | None:
    """يحوّل مسار هدف الرابط في الشجرة المحلية إلى مساره داخل المستودع."""
    t = target.resolve()
    for root, prefix in ((BRAIN, "brain"), (SITE, "site")):
        try:
            return f"{prefix}/{t.relative_to(root.resolve()).as_posix()}"
        except ValueError:
            continue
    return None


def _mirror_symlink(src: Path, dst: Path, prefix: str):
    """ينشئ رابطًا رمزيًا نسبيًا في المستودع يحفظ البنية، بدل استثناء الرابط."""
    rel_target = _repo_rel_of(src)
    if not rel_target:
        EXCLUDED_LOG.append((f"{prefix}/{src.as_posix()}", "رابط خارج الشجرتين — لا يُنقل"))
        return
    depth = len(dst.relative_to(OUT).parts) - 1
    link = Path(*[".."] * depth) / rel_target
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        dst.unlink() if dst.is_symlink() or dst.is_file() else shutil.rmtree(dst)
    dst.symlink_to(link)
    SYMLINKS_LOG.append((f"{prefix}/{src.as_posix()}", f"→ {link.as_posix()}"))



def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_tree(src: Path, dst: Path, prefix: str, skip_dirs: set[str], skip_files: set[str]):
    for dp, dns, fns in os.walk(src):
        dns[:] = [d for d in dns if d not in skip_dirs]
        rel_dir = Path(dp).relative_to(src)
        for d in list(dns):
            if (Path(dp) / d).is_symlink():
                _mirror_symlink(Path(dp) / d, dst / rel_dir / d, prefix)
                dns.remove(d)
        for fn in fns:
            p = Path(dp) / fn
            rel = (rel_dir / fn).as_posix()
            if rel.startswith("./"):     # لا تستخدم lstrip: يمحو نقطة الأسرار
                rel = rel[2:]
            if rel in skip_files:
                EXCLUDED_LOG.append((f"{prefix}/{rel}", "سرّي — لا يُنقل"))
                continue
            if p.suffix == ".pyc":
                continue
            if p.is_symlink():
                _mirror_symlink(p, target, prefix)
                continue
            target = dst / rel_dir / fn
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def sanitize_all():
    for rel, subs in SANITIZE.items():
        p = OUT / rel
        if not p.exists():
            EXCLUDED_LOG.append((rel, "غير موجود — لم يُحجب"))
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        before = t
        for rx, rep in subs:
            t = re.sub(rx, rep, t)
        if t != before:
            p.write_text(t, encoding="utf-8")
            print(f"  حُجبت قيم سرية في: {rel}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for part in ("brain", "site"):
        if (OUT / part).exists():
            shutil.rmtree(OUT / part)
        (OUT / part).mkdir(parents=True)
    # الملفات الثابتة للمستودع (README · .gitignore · docs) تُنسخ من backup-repo
    static = BRAIN / "backup-repo"
    if static.exists():
        for src in static.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(static)
            dst = OUT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    copy_tree(BRAIN, OUT / "brain", "brain", BRAIN_SKIP_DIRS, BRAIN_SKIP_FILES)
    copy_tree(SITE, OUT / "site", "site", SITE_SKIP_DIRS, SITE_SKIP_FILES)
    sanitize_all()

    files = sorted(p for p in OUT.rglob("*") if p.is_file() and ".git/" not in p.as_posix())
    total = sum(p.stat().st_size for p in files)
    idx = OUT / "docs" / "فهرس-الملفات.tsv"
    idx.parent.mkdir(parents=True, exist_ok=True)
    with idx.open("w", encoding="utf-8") as f:
        f.write("المسار\tالحجم(بايت)\tآخر_تعديل\tبصمة_sha256\n")
        for p in files:
            st = p.stat()
            f.write(f"{p.relative_to(OUT).as_posix()}\t{st.st_size}\t"
                    f"{__import__('datetime').datetime.utcfromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M')}\t"
                    f"{sha256(p)}\n")
    print(f"الملفات: {len(files)} · الحجم: {total/1048576:.1f} م.ب · الفهرس: {idx.relative_to(OUT)}")
    for rel, why in EXCLUDED_LOG:
        print(f"  استُثني: {rel} — {why}")
    if SYMLINKS_LOG:
        print(f"  روابط رمزية نُقلت نسبيًا: {len(SYMLINKS_LOG)}")
        for a, b in SYMLINKS_LOG:
            print(f"    {a} {b}")


if __name__ == "__main__":
    main()
