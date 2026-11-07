#!/usr/bin/env python3
"""حارس جاهزية أدوات بوابة العبور — يفشل مغلقًا.

يتحقق من أربعة:
  1) الأدوات الست موجودة وتستجيب لـ --help (أي أنها قابلة للتنفيذ لا أسماء في وثيقة).
  2) كل أداة مذكورة في المانيفست، ومربوطة بخطوة (م-05: لا وحدة بلا مستدعٍ).
  3) سجل الانحدار فيه خمسة عشر بندًا وأطواره معلَنة، ولا معرّف مكرر.
  4) مصفوفة الأثر تغطي كل أدوات البوابة وأدواتها المانعة.

الاستعمال: python3 validators/check_gate_readiness.py [--root .] [--summary]
رمز الخروج: 0 جاهزة · 2 غير جاهزة.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOLS = ["crossing_gate.py", "surface_fingerprint.py", "number_fingerprint.py",
         "impact_matrix.py", "regression_gate.py", "gate_coverage.py"]


def check(root: Path) -> list[str]:
    errs: list[str] = []
    manifest = (root / "runbook" / "runbook.json").read_text(encoding="utf-8")

    for name in TOOLS:
        p = root / "tools" / name
        if not p.is_file():
            errs.append(f"أداة غائبة: tools/{name}")
            continue
        r = subprocess.run(["python3", str(p), "--help"], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            errs.append(f"أداة لا تستجيب لـ --help: tools/{name} (rc={r.returncode})")
        if name not in manifest:
            errs.append(f"أداة غير مربوطة بخطوة في المانيفست: tools/{name}")

    items = json.loads((root / "runbook" / "regression-items.json").read_text(encoding="utf-8"))
    order = items.get("phase_order") or []
    ids = [i["id"] for i in items.get("items", [])]
    if len(ids) != 15:
        errs.append(f"بنود سجل الانحدار {len(ids)} لا 15")
    for i in items.get("items", []):
        if str(i.get("phase")) not in order:
            errs.append(f"{i['id']}: طور غير معلن {i.get('phase')!r}")
        if i.get("kind") == "cmd" and not i.get("argv"):
            errs.append(f"{i['id']}: نوع cmd بلا أمر")
        if i.get("kind") == "manual" and not i.get("how"):
            errs.append(f"{i['id']}: نوع manual بلا طريقة قياس")
    for d in set(ids):
        if ids.count(d) > 1:
            errs.append(f"معرّف بند مكرر: {d}")

    imp = json.loads((root / "runbook" / "impact-map.json").read_text(encoding="utf-8"))
    covered = " ".join(json.dumps(r, ensure_ascii=False) for r in imp.get("rules", []))
    for name in TOOLS:
        if name not in covered:
            errs.append(f"مصفوفة الأثر لا تغطي tools/{name}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس جاهزية أدوات بوابة العبور")
    ap.add_argument("--root", default=".", help="جذر النظام")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    errs = check(root)
    if errs:
        print("✘ جاهزية أدوات البوابة: غير جاهزة")
        for e in errs:
            print(f"   - {e}")
        return 2
    if args.summary:
        print("✔ جاهزية أدوات البوابة: 6 أدوات مربوطة · 15 بند انحدار · مصفوفة أثر تغطيها")
        return 0
    print("✔ جاهزية أدوات البوابة: 6 أدوات مربوطة بخطوات · 15 بند انحدار بأطوار معلَنة · مصفوفة أثر تغطي الأدوات")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
