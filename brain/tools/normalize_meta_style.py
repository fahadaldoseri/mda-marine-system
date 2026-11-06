#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تطبيع صياغة ملفات واجهة التقارير قبل عرضها.

المصدر الحاكم للبيانات يبقى ملف الواجهة الناتج من W020؛ هذه الأداة لا تستخرج
حقائق ولا تغيّر أرقامًا، بل تطبق إصلاحات تركيبية معلنة على كل القيم النصية.

الاستخدام:
  python3 tools/normalize_meta_style.py --date 2026-11-06 --dry-run
  python3 tools/normalize_meta_style.py --date 2026-11-06 --apply
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRAIN = Path(os.environ.get("BRAIN_DIR") or ROOT)

# إصلاحات جملة كاملة، لا استبدال لفظ منفرد؛ يحافظ كل بديل على المعنى والوقائع.
REWRITES: tuple[tuple[str, str], ...] = (
    (
        "لا تؤكد المواد أضرارًا متعددة أو تعطيلًا كاملًا للممر.",
        "لا تُثبت المواد أضرارًا متعددة أو تعطيلًا كاملًا للممر.",
    ),
    (
        "128 حادثة مؤكدة؛ لا قراءة أحدث في مواد اليوم.",
        "128 حادثة مؤكدة؛ لم يرد تحديث أحدث في مواد اليوم.",
    ),
    (
        "24 وفاة بين البحّارة؛ لا قراءة أحدث في مواد اليوم.",
        "24 وفاة بين البحّارة؛ لم يرد تحديث أحدث في مواد اليوم.",
    ),
    (
        "لا قراءة أحدث في مواد اليوم.",
        "لا تتوفر قراءة أحدث في مواد اليوم.",
    ),
    (
        "يبقى الخبر نقلًا إعلاميًا بلا أصل رسمي ظاهر في المواد.",
        "الخبر نقل إعلامي بلا أصل رسمي ظاهر في المواد.",
    ),
    (
        "يبقى الخبر قيد المتابعة ولا يثبت قرارًا نافذًا أو مهمة محددة.",
        "الخبر قيد المتابعة ولا يثبت قرارًا نافذًا أو مهمة محددة.",
    ),
)


def _rewrite(value: Any, changes: list[dict[str, str]]) -> Any:
    if isinstance(value, str):
        out = value
        for before, after in REWRITES:
            if before in out:
                out = out.replace(before, after)
                changes.append({"before": before, "after": after})
        return out
    if isinstance(value, list):
        return [_rewrite(item, changes) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite(item, changes) for key, item in value.items()}
    return value


def normalize_object(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """يعيد نسخة مطبّعة وقائمة تغييرات؛ لا يعدّل الكائن المدخل."""
    changes: list[dict[str, str]] = []
    normalized = _rewrite(copy.deepcopy(data), changes)
    if not isinstance(normalized, dict):  # حماية عقدية، لا تحدث مع مدخل JSON صالح
        raise TypeError("ملف الواجهة يجب أن يكون كائن JSON")
    return normalized, changes


def normalize_path(path: Path, apply: bool) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"ملف الواجهة ليس كائن JSON: {path}")
    normalized, changes = normalize_object(data)
    if apply and changes:
        path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    path = BRAIN / "web" / "meta" / f"{args.date}.json"
    if not path.is_file():
        print(f"✘ ملف الواجهة غير موجود: {path}")
        return 2
    changes = normalize_path(path, apply=args.apply)
    action = "طُبّق" if args.apply else "سيُطبّق"
    print(f"{action} تطبيع واجهة {args.date}: {len(changes)} تغييرًا")
    for change in changes:
        print(f"  · «{change['before']}» ← «{change['after']}»")
    if not args.apply:
        print("(فحص فقط — لم تُكتب بيانات الواجهة؛ استخدم --apply للتنفيذ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
