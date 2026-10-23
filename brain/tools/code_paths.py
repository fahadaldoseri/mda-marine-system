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

SPEC_REL = "brain/appendices/code-paths.json"


def load_spec(repo_root):
    return json.loads((Path(repo_root) / SPEC_REL).read_text(encoding="utf-8"))


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
    out = subprocess.run(["git", "-C", str(repo_root), "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def check(repo_root):
    spec = load_spec(repo_root)
    bad = [f for f in tracked_files(repo_root) if classify(f, spec) is None]
    for f in bad:
        print(f"✘ مسار غير مصنَّف (أضفه إلى code أو data في {SPEC_REL}): {f}")
    if not bad:
        n = len(tracked_files(repo_root))
        print(f"✔ كل مسارات المستودع ({n}) مصنَّفة")
    return 2 if bad else 0


def main():
    a = sys.argv[1:]
    root = Path(__file__).resolve().parent.parent.parent
    if "--root" in a:
        i = a.index("--root")
        root = Path(a[i + 1])
        del a[i:i + 2]
    if not a:
        print(__doc__)
        return 0
    if a[0] == "check":
        return check(root)
    if a[0] == "classify":
        spec = load_spec(root)
        for p in a[1:]:
            print(f"{classify(p, spec) or '؟'}\t{p}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
