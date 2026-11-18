#!/usr/bin/env python3
"""بناء شجرة النسخة الاحتياطية النظيفة لمشروع مركز الوعي بالمجال البحري.

المصادر: /home/ubuntu/brain-marine-news (النظام) و /home/ubuntu/seawatch (الموقع).
الوجهة: /home/ubuntu/mda-marine-system/{brain,site}
المستثنى: الأسرار، المخلفات، النسخ المكررة، المخرجات المولّدة، صور التدقيق المؤقتة.
ويُسجَّل كل استثناء في docs/نقل-إلى-جيت-هب.md مع السبب.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import re
import shutil
from pathlib import Path

# ── مسارات محمولة: تُقرأ من متغيّرات البيئة، والافتراضي جذر الشجرة ──
BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
SITE = Path(os.environ.get("SITE_DIR") or BRAIN.parent / "seawatch")
HOME = BRAIN.parent
OUT = Path(os.environ.get("BACKUP_REPO_DIR") or HOME / "mda-marine-system")
# مصدر المهارات: SKILLS_DIR ← مسار الخادم إن وُجد ← skills/ في جذر المستودع
SKILLS_SRC = (Path(os.environ["SKILLS_DIR"]) if os.environ.get("SKILLS_DIR")
              else Path("/home/ubuntu/skills") if (os.access("/home/ubuntu/skills", os.R_OK | os.X_OK) and Path("/home/ubuntu/skills").is_dir()) else OUT / "skills")

# مجلدات لا تُنقل (نسبةً إلى جذر كل شجرة)
BRAIN_SKIP_DIRS = {"__pycache__", ".git", "shots", "node_modules", ".pytest_cache", "backup-repo"}
SITE_SKIP_DIRS = {"__pycache__", ".git", "brain-backup", "dist", "shots", "node_modules", ".pytest_cache"}
# أرشيفات التطبيق مؤقتة وليست أصولًا؛ لا تُعاد إلى المرآة.
SKIP_DIR_GLOBS = {
    "brain": ("logs/apply-*",),
    "site": (),
    "skills": (),
}
# ملفات لا تُنقل (نسبةً إلى جذر كل شجرة)
BRAIN_SKIP_FILES = {"state/webhook-secret.txt", ".env", ".env.local"}
SITE_SKIP_FILES = {".env", ".env.local", ".env.production"}
# ملفات تُنقل مع حجب القيم السرية داخلها
SANITIZE = {
    "brain/appendices/telegram-chat.json": [(r'"chat_id"\s*:\s*"\d+"', '"chat_id": "[محجوب]"'),
                                            (r'"bot_id"\s*:\s*"\d+"', '"bot_id": "[محجوب]"')],
    "brain/appendices/telegram-targets.json": [(r'"chat_id"\s*:\s*"?-?\d+"?', '"chat_id": "[محجوب]"'),
                                               (r'"user_id"\s*:\s*"?\d+"?', '"user_id": "[محجوب]"')],
    "brain/appendices/telegram-subscriptions.json": [(r'"chat_id"\s*:\s*"\d+"', '"chat_id": "[محجوب]"'),
                                                     (r'"user_id"\s*:\s*"\d+"', '"user_id": "[محجوب]"')],
    "brain/research/styles/sources/archive-reports.html": [(r'token="[^"]{20,}"', 'token="[محجوب]"')],
}
# أنماط لا تُتعقَّب: مخرجات يُعاد توليدها آليًا فتتعارض عند كل سحب
SKIP_GLOBS = {
    "brain": ("reports/docx/التقرير-اليومي-*.docx", "reports/docx/التقرير-اليومي-*.pdf",
              "reports/pdf/*"),
}
EXCLUDED_LOG: list[tuple[str, str]] = []
CODE_DRIFT: list[str] = []      # شيفرة الخادم تختلف عن GitHub: لم تُنسخ
CODE_NEW: list[str] = []        # شيفرة جديدة على الخادم غير موجودة في GitHub: نُسخت وتُعلَن
SPEC: dict | None = None        # appendices/code-paths.json (نسخة GitHub أولًا، وإلا نسخة الخادم)
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
    rel_repo = dst.relative_to(OUT)          # مسار الرابط داخل المستودع
    depth = len(rel_repo.parent.parts)       # عدد درجات الصعود حتى جذر المستودع
    link = Path(*[".."] * depth) / rel_target
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        dst.unlink() if dst.is_symlink() or dst.is_file() else shutil.rmtree(dst)
    dst.symlink_to(link)
    SYMLINKS_LOG.append((rel_repo.as_posix(), f"→ {link.as_posix()}"))



def project_skills() -> tuple[str, ...]:
    """قائمة مهارات المشروع من مصدرها الواحد (restore_skills.sh) — إصلاح ك-150.

    كانت هنا قائمة مكتوبة بيد تختلف عن قائمة المزامنة، ومجلد skills يُمحى قبل النسخ،
    فحُذفت مهارة أُضيفت حديثًا من المستودع. القاعدة: قائمة واحدة ومصدر واحد.
    """
    fallback = ("marine-news-brain", "military-arabic-editing", "macr-system", "superpowers-method")
    try:
        txt = (Path(__file__).resolve().parent / "restore_skills.sh").read_text(encoding="utf-8")
        m = re.search(r'OUR_SKILLS="([^"]+)"', txt)
        if m:
            names = tuple(m.group(1).split())
            if names:
                return names
    except OSError:
        pass
    return fallback


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_code(prefix: str, rel: str) -> bool:
    """هل المسار شيفرة/قواعد مصدرها GitHub (لا يكتبها النسخ الاحتياطي فوق المستودع)؟"""
    if SPEC is None:
        return False
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import code_paths
    return code_paths.classify(f"{prefix}/{rel}", SPEC) == "code"


def copy_tree(src: Path, dst: Path, prefix: str, skip_dirs: set[str], skip_files: set[str], skip_dir_globs=()):
    import fnmatch
    for dp, dns, fns in os.walk(src):
        rel_dir = Path(dp).relative_to(src)
        dns[:] = [d for d in dns if d not in skip_dirs and not any(
            fnmatch.fnmatch((rel_dir / d).as_posix(), g) for g in skip_dir_globs
        )]
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
            if any(fnmatch.fnmatch(rel, _g) for _g in SKIP_GLOBS.get(prefix, ())):
                EXCLUDED_LOG.append((f"{prefix}/{rel}", "مُولَّد آليًا — يُعاد توليده ولا يُتعقَّب"))
                continue
            target = dst / rel_dir / fn
            if p.is_symlink():                 # يُنشأ الرابط في مساره الصحيح
                _mirror_symlink(p, target, prefix)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if is_code(prefix, rel):
                if target.exists():
                    if sha256(target) != sha256(p):
                        CODE_DRIFT.append(f"{prefix}/{rel}")   # GitHub يفوز؛ الانحراف يُعلَن ولا يُدفع
                    continue
                CODE_NEW.append(f"{prefix}/{rel}")
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
    global SPEC
    OUT.mkdir(parents=True, exist_ok=True)
    for cand in (OUT / "brain" / "appendices" / "code-paths.json", BRAIN / "appendices" / "code-paths.json"):
        if cand.is_file():
            SPEC = json.loads(cand.read_text(encoding="utf-8"))
            break
    # يُمحى من النسخة ما صُنِّف بيانات فقط (فيعكس حذف الخادم)، وتبقى الشيفرة كما في GitHub
    for part in ("brain", "site", "skills"):
        d = OUT / part
        if d.exists():
            for f in sorted(d.rglob("*"), reverse=True):
                rel = f.relative_to(d).as_posix()
                if (f.is_file() or f.is_symlink()) and not is_code(part, rel):
                    f.unlink()
                elif f.is_dir() and not any(f.iterdir()):
                    f.rmdir()
        d.mkdir(parents=True, exist_ok=True)
    # الملفات الثابتة للمستودع (README · .gitignore · docs) تُنسخ من backup-repo
    static = BRAIN / "backup-repo"
    if static.exists():
        for src in static.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(static)
            dst = OUT / rel
            if dst.exists() and SPEC is not None:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                import code_paths
                if code_paths.classify(rel.as_posix(), SPEC) == "code":
                    continue   # README و.gitignore و docs: GitHub مصدرها
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    copy_tree(BRAIN, OUT / "brain", "brain", BRAIN_SKIP_DIRS, BRAIN_SKIP_FILES, SKIP_DIR_GLOBS["brain"])
    copy_tree(SITE, OUT / "site", "site", SITE_SKIP_DIRS, SITE_SKIP_FILES, SKIP_DIR_GLOBS["site"])
    # مهارات المشروع — تُنسخ مع النظام ليبقى المرجع حديثًا على أي جهاز.
    # القائمة تُقرأ من restore_skills.sh (مصدر واحد) لا من قائمة ثانية هنا (ك-150).
    for sk in project_skills():
        src = SKILLS_SRC / sk
        if src.exists():
            copy_tree(src, OUT / "skills" / sk, "skills", {"__pycache__", ".git"}, set(), SKIP_DIR_GLOBS["skills"])
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
                    f"{__import__('datetime').datetime.fromtimestamp(st.st_mtime, __import__('datetime').timezone.utc).strftime('%Y-%m-%d %H:%M')}\t"
                    f"{sha256(p)}\n")
    print(f"الملفات: {len(files)} · الحجم: {total/1048576:.1f} م.ب · الفهرس: {idx.relative_to(OUT)}")
    for rel, why in EXCLUDED_LOG:
        print(f"  استُثني: {rel} — {why}")
    for rel in CODE_DRIFT:
        print(f"  انحراف شيفرة: {rel} — نسخة الخادم تختلف عن GitHub ولم تُنسخ (طبّق apply_from_github أو انقل التعديل إلى GitHub)")
    for rel in CODE_NEW:
        print(f"  شيفرة جديدة من الخادم: {rel} — نُسخت (غير موجودة في GitHub)")
    if CODE_DRIFT or CODE_NEW:
        al = BRAIN / "logs" / "alerts"
        al.mkdir(parents=True, exist_ok=True)
        (al / f"code-drift-{__import__('datetime').date.today().isoformat()}.txt").write_text(
            "\n".join([f"drift {r}" for r in CODE_DRIFT] + [f"new {r}" for r in CODE_NEW]) + "\n", encoding="utf-8")
    if SYMLINKS_LOG:
        print(f"  روابط رمزية نُقلت نسبيًا: {len(SYMLINKS_LOG)}")
        for a, b in SYMLINKS_LOG:
            print(f"    {a} {b}")


if __name__ == "__main__":
    main()
