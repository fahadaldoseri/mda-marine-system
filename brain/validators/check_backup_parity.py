#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة مطابقة النسخة الاحتياطية: تحرس أن المستودع المدفوع = الشجرة المحلية.

الخلل الذي تمنعه (عطل ك-06 وك-07 وك-09): استثناء صامت — يُدفع المشروع ناقصًا بلا إعلان.
الوضع: --mode strict (مانع، يُستعمل بعد خطوة النسخ) | --mode advisory (تنبيه، قبل النسخ)
رموز الخروج: 0 مطابق · 1 انحراف في الوضع التنبيهي · 2 انحراف في الوضع المانع · 3 مستودع مفقود
"""

from __future__ import annotations
import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
S = Path(os.environ.get("SITE_DIR") or B.parent / "seawatch")
REPO = Path(os.environ.get("BACKUP_REPO_DIR") or B.parent / "mda-marine-system")
BSKIP_DIRS = {"__pycache__", ".git", "shots", "node_modules", ".pytest_cache", "backup-repo"}
SSKIP_DIRS = {"__pycache__", ".git", "brain-backup", "dist", "shots", "node_modules", ".pytest_cache"}
BSKIP_FILES = {"state/webhook-secret.txt", ".env", ".env.local"}
SSKIP_FILES = {".env", ".env.local", ".env.production"}
# روابط رمزية إلى شجرة الموقع: تُقارن عبر مقارنة الموقع نفسها (site) لا عبر نسخة المرآة،
# فمحتواها يعتمد على موضع الرابط لا على نسخة قديمة (ك-331).
SYMLINK_VIEWS = ("brain/web/blocks.py", "brain/web/build_report.py", "brain/web/map_gulf.py",
                 "brain/web/monthly_dashboard.py", "brain/web/verify.py")
# ملفات مولَّدة على الخادم باسم مخفي فلا تلتقطها مسحة الملفات المخفيّة، وتُعدّ زائدة في المستودع.
REPO_EXTRA_ALLOW = ("skills/.skill_versions.json",)

LOCAL_ONLY_PATTERNS = (
    "audit/backups/",                  # لقطات الإغلاق على الخادم (ك-331)
    "brain/logs/skills-sync-",         # نسخ استعادة مهارات محلية مؤقتة؛ لا تُنقل إلى المرآة
)  # الاستثناءات محصورة بالمخرجات المولّدة، ولا تشمل سجلات التشغيل العامة
SANITIZED = {"brain/appendices/telegram-chat.json", "brain/appendices/telegram-subscriptions.json",
             "brain/appendices/telegram-targets.json",
             "brain/research/styles/sources/archive-reports.html"}
# سجلّات تنمو باستمرار بعد النسخ: لا تُحسب انحرافًا
# ملفات تشغيلية تُولَّد في كل تشغيل: تُقارَن بالوجود لا بالمحتوى (قاعدة 20 أكتوبر 2026)
VOLATILE = (
    "brain/logs/",
    "brain/archive/ofac-screen-latest.json",
    "brain/audit/self-test-",
    "brain/audit/llm-review-",
    "brain/audit/llm-triage-",
    "brain/feeds/feeds-",
    "brain/state/",
)
# مخرجات مولّدة آليًا: تُستثنى من النسخ فلا تُحسب انحرافًا (عطل ك-18)
SKIP_GLOBS = ("brain/reports/docx/التقرير-اليومي-", "brain/reports/pdf/")
REPO_ONLY_PATTERNS = ("/shots/", "reports/docx/", "reports/pdf/", "backup-repo/", "__pycache__/", "site/dist/")
ALLOW_REPO_ONLY = (
    "brain/backup-repo/",  # نسخة مستودع داخلية: لا تُنسخ للخادم

    "docs/فهرس-الملفات.tsv",
    # ملفات تقيم في المستودع وحده بحكم وظيفتها، ولا نظير لها على الخادم (تسمح بذلك):
    ".gitignore",              # إعداد المستودع لا إعداد التشغيل
    "AGENTS.md",               # تعليمات الوكلاء على GitHub؛ نسخة الخادم هي CLAUDE.md
    ".github/",                # سير عمل الفحص على GitHub
)

# أسباب مكتوبة لكل مجموعة استثناء (أمر فهد 2026-10-24، البند 8).
# tests/test_parity_scope.py يمنع أي مجموعة بلا سبب مكتوب هنا، ويمنع تضييق النطاق بصمت.
GROUP_REASONS = {
    "BSKIP_DIRS": "مجلدات لا تدخل النسخة: كاش بايثون، تاريخ Git، لقطات، حِزم Node، ومستودع النسخ المحلي.",
    "SSKIP_DIRS": "مجلدات الموقع المُستثناة: كاش، تاريخ Git، نسخة محلية، مخرجات البناء dist، ولقطات.",
    "BSKIP_FILES": "ملفات سرّية داخلية لا تُنقل بحال (سرّ الويبهوك وملفات البيئة).",
    "SSKIP_FILES": "ملفات بيئة الموقع (.env وأخواتها) لا تُنقل.",
    "SKIP_GLOBS": "مخرجات مولَّدة آليًا (Word وPDF) تُعاد توليدها ولا تُتعقَّب — عطل ك-18.",
    "ALLOW_REPO_ONLY": "ملفات تعيش في المستودع وحده بحكم وظيفتها: فهرس المستودع وإعداداته وتعليمات الوكلاء وسير عمل GitHub.",
    "LOCAL_ONLY_PATTERNS": "مخرجات محلية مؤقتة محددة بالبادئة: لقطات الإغلاق ونسخ .bak التي ينشئها restore_skills؛ لا يُستثنى سجل تشغيل عام أو ملف شيفرة/بيانات.",
    "PROTECTED_PATHS": "ملف الأسرار المعتمد بقرار المالك: لا يُحذف ولا يُفرَّغ بالنسخ الاحتياطي (ك-168).",
}

# إعفاء واحد مكتوب السبب (قرار المالك 2026-10-24: حفظ الأسرار نصًّا في المستودع الخاص، ك-166 وك-168).
# لا يُخفَّف به أي فحص آخر: أي سرّ في أي ملف غير هذا يبقى انحرافًا مانعًا.
PROTECTED_PATHS = ("brain/secrets/secrets.env",)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# ملفات مهملة لا تُقارَن ولا تُزامَن في أي جذر (ك-271): يجب أن تكون الاستثناءات متناظرة
# بين المزامن والمقيّم، وإلا ظهر «انحراف مانع» كاذب.
JUNK_FILES = {".DS_Store", ".skill_versions.json"}


def manifest(root: Path, skip_dirs, skip_files, prefix: str):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip_dirs]
        rd = Path(dp).relative_to(root)
        for fn in fns:
            p = Path(dp) / fn
            if any((prefix + '/' + (rd / fn).as_posix()).startswith(g) for g in SKIP_GLOBS):
                continue
            rel = (rd / fn).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            if rel in skip_files or p.suffix == ".pyc" or fn in JUNK_FILES:
                continue
            if p.is_symlink():
                tgt = p.resolve()
                for _tree, rp in ((B, "brain"), (S, "site")):
                    try:
                        out[f"{prefix}/{rel}"] = ("link", f"{rp}/{tgt.relative_to(_tree.resolve()).as_posix()}")
                        break
                    except ValueError:
                        continue
                else:
                    out[f"{prefix}/{rel}"] = ("link", f"خارج الشجرتين: {tgt}")
            else:
                out[f"{prefix}/{rel}"] = ("file", sha(p))
    return out


def repo_manifest():
    out = {}
    # ك-160: كان المسح يعتمد مجلد العمل فيحسب ملفات غير متتبَّعة (مثل __pycache__)
    # «زائدة في المستودع». المصدر الآن ما يتتبعه Git فعلًا.
    try:
        tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"],
                                 capture_output=True, check=True).stdout.decode("utf-8")
        files = [f for f in tracked.split("\0") if f]
    except Exception:
        files = None
    if files is None:
        for dp, dns, fns in os.walk(REPO):
            dns[:] = [d for d in dns if d != ".git"]
            rd = Path(dp).relative_to(REPO)
            for fn in fns:
                files = (files or []) ; break
        files = []
    if files:
        for rel in files:
            if rel.startswith(ALLOW_REPO_ONLY):
                continue
            p = REPO / rel
            if p.is_symlink():
                # رابط إلى مجلد = اسم شجرة لا ملف محتوى؛ الشجرة المحلية لا تُدرجه
                try:
                    if p.resolve().is_dir():
                        continue
                except OSError:
                    pass
                tgt = os.path.normpath((Path(rel).parent / os.readlink(p)).as_posix())
                while tgt.startswith("./"):
                    tgt = tgt[2:]
                out[rel] = ("link", tgt)
            elif p.is_file():
                out[rel] = ("file", sha(p))
        return out
    for dp, dns, fns in os.walk(REPO):
        dns[:] = [d for d in dns if d != ".git"]
        rd = Path(dp).relative_to(REPO)
        for fn in fns:
            p = Path(dp) / fn
            rel = (rd / fn).as_posix()
            if rel.startswith(ALLOW_REPO_ONLY):
                continue
            if p.is_symlink():
                tgt = os.path.normpath((Path(rel).parent / os.readlink(p)).as_posix())
                while tgt.startswith("./"):
                    tgt = tgt[2:]
                out[rel] = ("link", tgt)
            else:
                out[rel] = ("file", sha(p))
    return out


def _inside_repo() -> bool:
    """يكتشف التشغيل من داخل نسخة من المستودع نفسه (استنساخ/Codespaces)."""
    repo = Path(__file__).resolve().parents[2]      # <repo>/brain/validators/<file>
    return (repo / "brain" / "validators").is_dir() and (repo / "site" / "generator").is_dir()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["strict", "advisory"], default="advisory")
    a = ap.parse_args()
    if _inside_repo():
        print("  ℹ أنت داخل نسخة من المستودع نفسه — لا مقارنة (المطلوب هنا: بوابات المحتوى)")
        return 0
    if not REPO.exists():
        print(f"  ⚠ لا مستودع نسخ احتياطي في: {REPO} (يُتخطّى الفحص)")
        return 3
    local = manifest(B, BSKIP_DIRS, BSKIP_FILES, "brain")
    local.update(manifest(S, SSKIP_DIRS, SSKIP_FILES, "site"))
    # عطل ك-60: المقارنة أغفلت جذر المهارات، فظهرت ملفات المستودع «زائدة» كذبًا.
    # القاعدة: كل جذر ينسخه github_backup يجب أن تدخله المقارنة بالنفس.
    sk_root = Path(os.environ["SKILLS_DIR"]) if os.environ.get("SKILLS_DIR") else (Path("/home/ubuntu/skills") if Path("/home/ubuntu/skills").is_dir() else B.parent / "skills")
    # ك-224: كانت القائمة أسماءً ثابتة، فأي مهارة جديدة في المستودع تظهر «زائدة» كذبًا
    # (vocabulary-guard-ops · self-learning-loop-ops). القاعدة الآن: كل مجلد مهارة يتتبعه
    # المستودع يُقارَن بمقابله على الخادم — تُقوّي الحارس ولا تُضعفه.
    _sk_names = set()
    try:
        _tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "skills"],
                                  capture_output=True, check=True).stdout.decode("utf-8")
        for _f in _tracked.split("\0"):
            if _f.startswith("skills/") and _f.count("/") >= 2:
                _sk_names.add(_f.split("/")[1])
    # تضييق مقصود: أعطال git المتوقعة فقط — أي خطأ آخر يظهر ولا يُبتلع.
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, UnicodeDecodeError):
        _sk_names = set()
    if not _sk_names:
        _sk_names = {"marine-news-brain", "military-arabic-editing", "macr-system", "superpowers-method"}
    # ك-351: كانت القائمة من المستودع فقط، فمهارة على الخادم غير مدفوعة لا تُقارَن إطلاقًا
    # ويظهر «مطابق» كاذبًا. القاعدة الآن: اتحاد مهارات المستودع ومهارات الخادم — فشل مغلق.
    _local_names = set()
    try:
        for _d in sorted(sk_root.iterdir()):
            if _d.is_dir() and _d.name not in {"__pycache__", ".git"}:
                _local_names.add(_d.name)
    # تضييق مقصود: أخطاء قراءة الجذر فقط — أي خطأ آخر يظهر ولا يُبتلع.
    except (OSError, PermissionError):
        _local_names = set()
    for sk in sorted(_sk_names | _local_names):
        d = sk_root / sk
        if d.is_dir():
            local.update(manifest(d, {"__pycache__", ".git"}, set(), f"skills/{sk}"))
    static = B / "backup-repo"
    if static.exists():
        for dp, dns, fns in os.walk(static):
            for fn in fns:
                p = Path(dp) / fn
                rel = (Path(dp).relative_to(static) / fn).as_posix()
                if rel.startswith(ALLOW_REPO_ONLY):
                    continue
                local[rel] = ("file", sha(p))
    repo = repo_manifest()

    drift = []
    # فحص تسرّب الأسرار: أسماء ممنوعة و/أو قيم سرية داخل المدفوع
    import re as _re
    SECRET_NAMES = {".env", ".env.local", ".env.production", "webhook-secret.txt"}
    SECRET_PAT = [
        _re.compile(r"\b\d{9,10}:[A-Za-z0-9_\-]{30,}\b"),          # توكن بوت تلغرام
        _re.compile(r'"chat_id"\s*:\s*"?\d{6,}"?'),                  # معرّف محادثة غير محجوب
        _re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                         # AWS
        _re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),             # مفاتيح خاصة
        _re.compile(r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{20,}\b"), # مفاتيح دفع
    ]
    for dp, dns, fns in os.walk(REPO):
        if ".git" in Path(dp).parts:
            continue
        for fn in fns:
            rel_scan = (Path(dp).relative_to(REPO) / fn).as_posix()
            if rel_scan in PROTECTED_PATHS:
                continue          # إعفاء مكتوب السبب: ملف الأسرار المعتمد بقرار المالك (ك-166/ك-168)
            if fn in SECRET_NAMES:
                drift.append(f"تسرّب سرّي: {Path(dp).relative_to(REPO) / fn}")
                continue
            q = Path(dp) / fn
            if q.is_symlink() or q.stat().st_size > 3_000_000:
                continue
            try:
                t = q.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "[محجوب]" in t:
                continue
            for rx in SECRET_PAT:
                if rx.search(t):
                    drift.append(f"تسرّب قيمة سرية: {Path(dp).relative_to(REPO) / fn} ({rx.pattern[:28]}…)")
                    break
    for rel, (kind, val) in sorted(local.items()):
        if rel not in repo:
            if any(rel.startswith(p) or f"/{p}" in rel for p in LOCAL_ONLY_PATTERNS):
                continue                     # لقطة احتياطية على الخادم بحكم السياسة (ك-331)
            drift.append(f"مفقود من المستودع: {rel}")
        elif repo[rel][0] != kind:
            drift.append(f"نوع مختلف (ملف/رابط): {rel}")
        elif repo[rel][1] != val:
            if rel in SANITIZED:
                continue                     # مُحجب عمدًا (تنقية أسرار)
            if rel.startswith(VOLATILE):
                continue                     # سجلّ ينمو بعد النسخ
            if rel in SYMLINK_VIEWS:
                continue                     # روابط إلى شجرة الموقع: أهدافها تختلف بموضع النسخة (ك-331)
            drift.append(f"محتوى مختلف: {rel}")
    for rel in sorted(repo):
        if rel not in local:
            if rel.startswith(ALLOW_REPO_ONLY) or any(x in rel for x in REPO_ONLY_PATTERNS):
                continue                     # داخل المستودع بحكم السياسة (لقطات/مخرجات/أرشيف) ولا يُنسخ للخادم
            if rel in REPO_EXTRA_ALLOW:
                continue                     # ملف مخفي مولَّد على الخادم (ك-331)
            drift.append(f"زائد في المستودع: {rel}")

    print(f"  الشجرة المحلية: {len(local)} · المستودع: {len(repo)} · الروابط: "
          f"{sum(1 for v in local.values() if v[0] == 'link')} محليًا")
    if not drift:
        print("  النتيجة: مطابق — المستودع يعكس الشجرة المحلية كاملة")
        return 0
    for d in drift[:200]:
        print(f"   ✘ {d}")
    if len(drift) > 12:
        print(f"   … و{len(drift) - 12} أخرى")
    if a.mode == "strict":
        print(f"  النتيجة: انحراف مانع ({len(drift)}) — النسخة الاحتياطية غير محدَّثة")
        return 2
    print(f"  النتيجة: انحراف ({len(drift)}) — تنبيه (الوضع التنبيهي قبل خطوة النسخ)")
    return 1


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
