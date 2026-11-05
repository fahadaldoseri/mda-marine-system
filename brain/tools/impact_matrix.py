#!/usr/bin/env python3
"""مصفوفة الأثر — تجيب سؤال: إذا تغيّر هذا الملف، ما الذي قد ينكسر؟

تقرأ مصدر الحقيقة الواحد `runbook/impact-map.json`: قاعدة لكل نمط ملف تذكر الأسطح
والبوابات والاختبارات التي يجب إعادة قياسها. وأي ملف متغيّر لا قاعدة له = تغيير غير معلن.

الاستعمال:
  impact_matrix.py --from-git                      يستخرج المتغيّر من فرق Git في النظام والموقع
  impact_matrix.py --changed site/generator/build_report.py
  impact_matrix.py --require-declared --from-git    يفشل إن كان بين المتغيّر ملف غير معلن

رمز الخروج: 0 سليم · 2 تغيير غير معلن (مع --require-declared) أو مصفوفة ناقصة.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

REQUIRED = ("match", "surfaces", "gates", "tests")


def load(root: Path) -> dict:
    p = root / "runbook" / "impact-map.json"
    if not p.is_file():
        raise SystemExit(f"✘ مصفوفة الأثر غير موجودة: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    errs = []
    for i, r in enumerate(data.get("rules", [])):
        for k in REQUIRED:
            if k not in r:
                errs.append(f"قاعدة {i}: حقل ناقص {k}")
        if not isinstance(r.get("match"), list) or not r["match"]:
            errs.append(f"قاعدة {i}: match يجب أن يكون قائمة غير فارغة")
    if errs:
        raise SystemExit("✘ مصفوفة الأثر غير صالحة\n   - " + "\n   - ".join(errs))
    return data


def from_git(root: Path, site: Path) -> list[str]:
    out: list[str] = []
    for base, label, repo in ((root, "brain", root), (site, "site", site)):
        try:
            r = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", "HEAD"],
                               capture_output=True, text=True, timeout=60)
            out += [f"{label}/{x}" for x in r.stdout.split() if x]
        except Exception:  # noqa: BLE001
            continue
    return sorted(set(out))


def rule_for(rules: list[dict], path: str) -> dict | None:
    for r in rules:
        for pat in r["match"]:
            if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path.split("/", 1)[-1], pat):
                return r
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="مصفوفة الأثر")
    ap.add_argument("--root", default=".", help="جذر النظام")
    ap.add_argument("--site", default="/home/ubuntu/seawatch", help="جذر الموقع")
    ap.add_argument("--changed", nargs="*", default=[], help="ملفات متغيّرة")
    ap.add_argument("--from-git", action="store_true", help="استخراج المتغيّر من Git")
    ap.add_argument("--require-declared", action="store_true", help="فشل عند تغيير غير معلن")
    ap.add_argument("--out", help="حفظ النتيجة JSON")
    args = ap.parse_args()
    root, site = Path(args.root).resolve(), Path(args.site).resolve()

    data = load(root)
    changed = list(args.changed) + (from_git(root, site) if args.from_git else [])
    changed = sorted(set(changed))

    surfaces: set[str] = set()
    gates: set[str] = set()
    tests: set[str] = set()
    undeclared: list[str] = []
    for c in changed:
        r = rule_for(data["rules"], c)
        if not r:
            undeclared.append(c)
            continue
        surfaces |= set(r["surfaces"])
        gates |= set(r["gates"])
        tests |= set(r["tests"])

    print(f"   ملفات متغيّرة: {len(changed)}")
    for c in changed:
        r = rule_for(data["rules"], c)
        print(f"   {'•' if r else '!'} {c}" + ("" if r else "  ← غير معلن في المصفوفة"))
    print(f"   الأسطح المتأثرة ({len(surfaces)}): " + (" · ".join(sorted(surfaces)) or "—"))
    print(f"   البوابات المطلوبة ({len(gates)}): " + (" · ".join(sorted(gates)) or "—"))
    print(f"   الاختبارات المطلوبة ({len(tests)}): " + (" · ".join(sorted(tests)) or "—"))

    result = {"changed": changed, "surfaces": sorted(surfaces), "gates": sorted(gates),
              "tests": sorted(tests), "undeclared": undeclared}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if undeclared and args.require_declared:
        print(f"✘ مصفوفة الأثر: {len(undeclared)} ملفًا متغيّرًا بلا قاعدة — تغيير غير معلن")
        return 2
    print("✔ مصفوفة الأثر: كل تغيير معلن" if not undeclared else
          f"⚠ مصفوفة الأثر: {len(undeclared)} ملفًا بلا قاعدة (لم يُطلب المنع)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
