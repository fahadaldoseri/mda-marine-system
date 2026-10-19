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
import sys
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
S = Path(os.environ.get("SITE_DIR") or B.parent / "seawatch")
REPO = Path(os.environ.get("BACKUP_REPO_DIR") or B.parent / "mda-marine-system")
BSKIP_DIRS = {"__pycache__", ".git", "shots", "node_modules", ".pytest_cache", "backup-repo"}
SSKIP_DIRS = {"__pycache__", ".git", "brain-backup", "dist", "shots", "node_modules", ".pytest_cache"}
BSKIP_FILES = {"state/webhook-secret.txt", ".env", ".env.local"}
SSKIP_FILES = {".env", ".env.local", ".env.production"}
SANITIZED = {"brain/appendices/telegram-chat.json", "brain/appendices/telegram-subscriptions.json",
             "brain/appendices/telegram-targets.json",
             "brain/research/styles/sources/archive-reports.html"}
# سجلّات تنمو باستمرار بعد النسخ: لا تُحسب انحرافًا
VOLATILE = ("brain/logs/",)
ALLOW_REPO_ONLY = ("docs/فهرس-الملفات.tsv",)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def manifest(root: Path, skip_dirs, skip_files, prefix: str):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip_dirs]
        rd = Path(dp).relative_to(root)
        for fn in fns:
            p = Path(dp) / fn
            rel = (rd / fn).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            if rel in skip_files or p.suffix == ".pyc":
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["strict", "advisory"], default="advisory")
    a = ap.parse_args()
    if not REPO.exists():
        print(f"  ⚠ لا مستودع نسخ احتياطي في: {REPO} (يُتخطّى الفحص)")
        return 3
    local = manifest(B, BSKIP_DIRS, BSKIP_FILES, "brain")
    local.update(manifest(S, SSKIP_DIRS, SSKIP_FILES, "site"))
    static = B / "backup-repo"
    if static.exists():
        for dp, dns, fns in os.walk(static):
            for fn in fns:
                p = Path(dp) / fn
                rel = (Path(dp).relative_to(static) / fn).as_posix()
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
            drift.append(f"مفقود من المستودع: {rel}")
        elif repo[rel][0] != kind:
            drift.append(f"نوع مختلف (ملف/رابط): {rel}")
        elif repo[rel][1] != val:
            if rel in SANITIZED:
                continue                     # مُحجب عمدًا (تنقية أسرار)
            if rel.startswith(VOLATILE):
                continue                     # سجلّ ينمو بعد النسخ
            drift.append(f"محتوى مختلف: {rel}")
    for rel in sorted(repo):
        if rel not in local:
            drift.append(f"زائد في المستودع: {rel}")

    print(f"  الشجرة المحلية: {len(local)} · المستودع: {len(repo)} · الروابط: "
          f"{sum(1 for v in local.values() if v[0] == 'link')} محليًا")
    if not drift:
        print("  النتيجة: مطابق — المستودع يعكس الشجرة المحلية كاملة")
        return 0
    for d in drift[:12]:
        print(f"   ✘ {d}")
    if len(drift) > 12:
        print(f"   … و{len(drift) - 12} أخرى")
    if a.mode == "strict":
        print(f"  النتيجة: انحراف مانع ({len(drift)}) — النسخة الاحتياطية غير محدَّثة")
        return 2
    print(f"  النتيجة: انحراف ({len(drift)}) — تنبيه (الوضع التنبيهي قبل خطوة النسخ)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
