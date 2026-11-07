#!/usr/bin/env python3
"""مزامنة محكومة من الخادم إلى مستودع المرآة — عطل ك-493.

العلّة: النسخة الاحتياطية الآلية (`tools/github_backup.sh`) تبني «بيانات فقط»،
فتبقى تعديلات الشيفرة على الخادم (بوابات · أدوات · اختبارات · مولّدات) بلا طريق
إلى المستودع، فتظهر في `check_backup_parity.py` انحرافات مانعة ولا تُغلق أبدًا.

القاعدة: هذه الأداة تنقل ما على الخادم إلى شجرة المرآة كما هو، بلا حذف وبلا
لمس `main` مباشرة؛ الدفع والدمج يقعان خارجها عبر فرع وطلب دمج. تعمل تجربةً
جافة افتراضًا، ولا تكتب إلا بـ`--apply`.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys

B = pathlib.Path(__file__).resolve().parent.parent
S = pathlib.Path(os.environ.get("SITE") or (B.parent / "seawatch"))
REPO = pathlib.Path(os.environ.get("BACKUP_REPO_DIR", B.parent / "mda-marine-system"))


def _parity_module():
    """يُحمّل أداة التماثل لإعادة استخدام قواعد الاستثناء نفسها (مصدر حكم واحد)."""
    path = B / "validators" / "check_backup_parity.py"
    spec = importlib.util.spec_from_file_location("cbp_sync", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def local_manifest() -> dict[str, pathlib.Path]:
    """يجرد ملفات الخادم بنفس قواعد أداة التماثل، ويعيد {مسار المستودع: مسار الخادم}."""
    m = _parity_module()
    out: dict[str, pathlib.Path] = {}
    out.update(m.manifest(B, m.BSKIP_DIRS, m.BSKIP_FILES, "brain"))
    out.update(m.manifest(S, m.SSKIP_DIRS, m.SSKIP_FILES, "site"))
    sk_root = pathlib.Path("/home/ubuntu/skills")
    names = set()
    try:
        tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "skills"],
                                 capture_output=True, check=True).stdout.decode("utf-8")
        for f in tracked.split("\0"):
            if f.startswith("skills/") and f.count("/") >= 2:
                names.add(f.split("/")[1])
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, UnicodeDecodeError):
        names = set()
    for d in sorted(sk_root.iterdir()):
        if d.is_dir() and d.name not in {"__pycache__", ".git"}:
            names.add(d.name)
    for sk in sorted(names):
        d = sk_root / sk
        if d.is_dir():
            out.update(m.manifest(d, {"__pycache__", ".git"}, set(), f"skills/{sk}"))
    return out


def _source_path(rel: str) -> pathlib.Path | None:
    """يعيد مسار الخادم المقابل لمسار المستودع (brain/ · site/ · skills/<name>/)."""
    if rel.startswith("brain/"):
        return B / rel[len("brain/"):]
    if rel.startswith("site/"):
        return S / rel[len("site/"):]
    if rel.startswith("skills/"):
        parts = rel.split("/")
        if len(parts) >= 3:
            return pathlib.Path("/home/ubuntu/skills") / parts[1] / "/".join(parts[2:])
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="ينفّذ النسخ فعلًا (بدونه تجربة جافة)")
    ap.add_argument("--limit", type=int, default=0, help="يحدّ عدد الملفات المنسوخة (0 = بلا حد)")
    a = ap.parse_args()

    if not REPO.is_dir():
        print(f"  ✘ مستودع المرآة غير موجود: {REPO}")
        return 2
    if (REPO / ".git").exists():
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            print("  ✘ شجرة المرآة غير نظيفة — نظّفها قبل المزامنة")
            return 2

    local = local_manifest()
    m = _parity_module()
    diff: list[tuple[str, pathlib.Path]] = []
    sanitized = set(m.SANITIZED)  # ملفات تُحفظ منقّحة في المستودع (ك-338) — لا تُنسخ بقيمها الحقيقية
    for rel, (kind, value) in sorted(local.items()):
        if kind != "file":
            continue  # الروابط تُقاس في أداة التماثل ولا تُنسخ هنا
        if rel in sanitized:
            continue  # منع تسريب معرّف المحادثة أو توكن البوت إلى المستودع
        src = _source_path(rel)
        if src is None or not src.is_file():
            continue
        dst = REPO / rel
        if not dst.is_file() or m.sha(dst) != value:
            diff.append((rel, src))

    print(f"   ملفات الخادم: {len(local)} · مختلفة أو مفقودة في المستودع: {len(diff)}")
    for rel, _ in diff[:20]:
        print("   ·", rel)
    if len(diff) > 20:
        print(f"   … و{len(diff) - 20} أخرى")

    if not a.apply:
        print("   (تجربة جافة — لا كتابة. استخدم --apply للتنفيذ)")
        return 0

    written = 0
    for rel, src in diff:
        if a.limit and written >= a.limit:
            break
        dst = REPO / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written += 1
    print(f"   ✔ نُسخ {written} ملفًا إلى المرآة (بلا حذف وبلا لمس main)")
    return 0


if __name__ == "__main__":
    sys.exit(main())