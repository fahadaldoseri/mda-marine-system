#!/usr/bin/env python3
"""حارس مرجع آلية العمل المولَّد — يفشل مغلقًا.

يمنع أربعة أمور:
  1) أن يُعدَّل المرجع أو المقارنة يدويًّا بلا إعادة توليد.
  2) أن يكون مجموع البنود في المرجع مخالفًا لمجموع `runbook/phases.json`.
  3) أن يتكرر معرّف بند أو تنقص حقوله أو تكون حالته خارج القيم المعلنة.
  4) أن يُحذف المرجع أو المقارنة.

الاستعمال: python3 validators/check_reference_generated.py [--root .]
رمز الخروج: 0 سليم · 2 خلل.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
import json as _json
def _declared_or_die(root):
    m = root / "runbook" / "reference-manifest.json"
    if not m.exists():
        raise SystemExit("✘ عقد مسارات المرجع مفقود: runbook/reference-manifest.json")
    d = _json.loads(m.read_text(encoding="utf-8"))
    miss = [v for v in [d["templates"]["header"], d["templates"]["sections_dir"]] if not (root / v).exists()]
    if miss:
        raise SystemExit("✘ مسار معلن في العقد غير موجود: " + " · ".join(miss))
    return d

TOOL = "tools/build_workflow_reference.py"


def _load_tool(root: Path):
    spec = importlib.util.spec_from_file_location("bwr", root / TOOL)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس مرجع آلية العمل المولَّد")
    ap.add_argument("--root", default=".", help="جذر المشروع")
    ap.add_argument("--summary", action="store_true", help="سطر واحد فقط")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    tool_path = root / TOOL
    if not tool_path.is_file():
        print(f"✘ مرجع آلية العمل: المولّد غير موجود ({TOOL})")
        return 2
    mod = _load_tool(root)
    rc = mod.cmd_check(root)
    if rc != 0:
        return rc
    if not args.summary:
        print("   المرجع والمقارنة مولَّدان ولا تعارض بينهما وبين phases.json")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
