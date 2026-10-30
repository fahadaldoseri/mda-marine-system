#!/usr/bin/env python3
"""تصنيف مسارات المستودع إلى «شيفرة وقواعد» (مصدرها GitHub) و«بيانات» (مصدرها الخادم) — appendices/code-paths.json.

الأوامر:
  code_paths.py classify PATH [PATH...]     يطبع code أو data أو ؟ لكل مسار (نسبةً إلى جذر المستودع)
  code_paths.py check [--root REPO]          يفشل (رمز 2) إن وُجد مسار متتبَّع في git لا يطابق code ولا data
المكتبة: classify(rel_path, spec) تستعملها apply_from_github.py وgithub_backup.py.
"""
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

SPEC_RELS = ("brain/appendices/code-paths.json", "appendices/code-paths.json")
RUNNABLE = 70  # فشل مغلق: تعذّر التحقق (لا يُعد نجاحًا ولا مخالفة)


class SpecNotFound(Exception):
    """لم أجد مواصفات تصنيف المسارات — تُعالَج كفشل مغلق لا كنجاح."""


def _spec_path(root):
    for rel in SPEC_RELS:
        q = Path(root) / rel
        if q.is_file():
            return q
    return None


def is_git_repo(d):
    return (Path(d) / ".git").exists()


def discover_root(start):
    """يبحث عن جذر المستودع الحاوي للمواصفات: نقطة البداية، ثم الآباء، ثم الأشقاء."""
    start = Path(start).resolve()
    for d in [start, *start.parents]:
        if _spec_path(d) and is_git_repo(d):
            return d
    for base in [start, *start.parents][:3]:
        if not base.is_dir():
            continue
        for sib in sorted(base.iterdir()):
            try:
                if sib.is_dir() and is_git_repo(sib) and _spec_path(sib):
                    return sib
            except OSError:
                continue
    return None


def load_spec(repo_root):
    """تحمّل المواصفات من جذر المستودع أو من مجلد الدماغ نفسه (تخطيطان)."""
    q = _spec_path(repo_root)
    if q is None:
        raise SpecNotFound(
            "لم أجد appendices/code-paths.json في "
            + " أو ".join(str(Path(repo_root) / r) for r in SPEC_RELS))
    return json.loads(q.read_text(encoding="utf-8"))






def _match(rel, pat):
    if pat.endswith("/**"):
        return rel == pat[:-3] or rel.startswith(pat[:-2])
    return fnmatch.fnmatchcase(rel, pat)


def classify(rel, spec):
    rel = rel[2:] if rel.startswith("./") else rel
    if any(_match(rel, p) for p in spec["code"]):
        return "code"
    if any(_match(rel, p) for p in spec["data"]):
        return "data"
    return None


def tracked_files(repo_root):
    try:
        out = subprocess.run(["git", "-C", str(repo_root), "ls-files", "-z"],
                             capture_output=True, check=True, timeout=120).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise SpecNotFound(f"تعذّر قراءة ملفات git في {repo_root}: {type(e).__name__}") from e
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def check(repo_root):
    try:
        spec = load_spec(repo_root)
        files = tracked_files(repo_root)
    except SpecNotFound as e:
        print(f"✘ تعذّر التحقق (فشل مغلق {RUNNABLE}): {e}")
        return RUNNABLE
    bad = [f for f in files if classify(f, spec) is None]
    for f in bad:
        print(f"✘ مسار غير مصنَّف (أضفه إلى code أو data في {repo_root}/appendices/code-paths.json): {f}")
    if not bad:
        print(f"✔ كل مسارات المستودع ({len(files)}) مصنَّفة · الجذر: {repo_root}")
    return 2 if bad else 0


def main():
    a = sys.argv[1:]
    if any(x in ("--help", "-h") for x in a):
        print(__doc__)
        return 0
    unknown = [x for x in a if x.startswith("-") and x != "--root"]
    if unknown:
        print(f"وسيط غير معروف: {unknown[0]}", file=sys.stderr)
        return 2
    if a.count("--root") > 1 or ("--root" in a and a.index("--root") + 1 >= len(a)):
        print("الاستخدام: code_paths.py [--root REPO] check|classify ...", file=sys.stderr)
        return 2
    if not a:
        print(__doc__)
        return 0
    brain_dir = Path(__file__).resolve().parent.parent
    root = brain_dir
    if "--root" in a:
        i = a.index("--root")
        root = Path(a[i + 1])
        del a[i:i + 2]
    else:
        found = discover_root(brain_dir)
        if found is None:
            print(f"✘ تعذّر التحقق (فشل مغلق {RUNNABLE}): لم أجد مستودعًا فيه appendices/code-paths.json "
                  f"انطلاقًا من {brain_dir}")
            return RUNNABLE
        root = found
    if a[0] == "check":
        return check(root)
    if a[0] == "classify":
        try:
            spec = load_spec(root)
        except SpecNotFound as e:
            print(f"✘ تعذّر التحقق (فشل مغلق {RUNNABLE}): {e}")
            return RUNNABLE
        for p in a[1:]:
            print(f"{classify(p, spec) or '؟'}\t{p}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
