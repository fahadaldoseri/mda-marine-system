#!/usr/bin/env python3
"""اختبار نطاق فاحص التماثل وأسبابه — أمر فهد 2026-10-24 (البنود 5 و8).

يمنع ثلاثة أشياء:
  1) مجموعة استثناء في الفاحص بلا سبب مكتوب في GROUP_REASONS.
  2) خروج أي ملف من النطاق بصمت: عدد الملفات المقارَنة لا يقلّ عن الأرضية 1682.
  3) حذف ملف الأسرار المعتمد من قائمة الحماية.
رمز الخروج: 0 سليم · 1 مخالفة.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
V = B / "validators" / "check_backup_parity.py"
FLOOR = 1682


def groups(src: str) -> set[str]:
    found = set()
    for name in ("BSKIP_DIRS", "SSKIP_DIRS", "BSKIP_FILES", "SSKIP_FILES", "SKIP_GLOBS", "ALLOW_REPO_ONLY"):
        if re.search(rf"^{name}\s*=", src, re.M):
            found.add(name)
    return found


def main() -> int:
    src = V.read_text(encoding="utf-8")
    reasons = re.search(r"GROUP_REASONS\s*=\s*\{(.*?)\n\}", src, re.S)
    if not reasons:
        print("  ✘ لا يوجد GROUP_REASONS في فاحص التماثل")
        return 1
    declared = set(re.findall(r'"([A-Z_]+)":', reasons.group(1)))
    missing = sorted(groups(src) - declared)
    if missing:
        print("  ✘ مجموعات استثناء بلا سبب مكتوب: " + " · ".join(missing))
        return 1
    print(f"  ✔ كل مجموعات الاستثناء لها سبب مكتوب: {len(declared)}")

    r = subprocess.run([sys.executable, str(V), "--mode", "strict"],
                       capture_output=True, text=True, timeout=600)
    out = r.stdout
    if r.returncode == 3:
        # بيئة بلا مستودع نسخ (مثل النسخة المعزولة): لا نطاق للمقارنة — ليس تضييقًا
        print("  · لا مستودع نسخ احتياطي في هذه البيئة — يُتخطّى فحص النطاق")
        return 0
    m = re.search(r"الشجرة المحلية:\s*(\d+)", out)
    if not m:
        print("  ✘ لم يطبع الفاحص عدد ملفات النطاق")
        return 1
    count = int(m.group(1))
    if count < FLOOR:
        print(f"  ✘ تضييق صامت للنطاق: {count} ملفًا مقابل الأرضية {FLOOR}")
        return 1
    print(f"  ✔ نطاق التماثل {count} ملفًا ≥ الأرضية {FLOOR}")

    if "secrets/secrets.env" not in src:
        print("  ✘ ملف الأسرار المعتمد ليس في قائمة الحماية")
        return 1
    print("  ✔ ملف الأسرار المعتمد محمي من الحذف في النسخ الاحتياطي")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())