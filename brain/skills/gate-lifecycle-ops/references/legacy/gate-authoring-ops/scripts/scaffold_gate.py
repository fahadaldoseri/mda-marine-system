#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ولّد بوابة واختبارها من قوالب gate-authoring-ops."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TEMPLATES = HERE / "templates"


def slugify(value: str) -> str:
    slug = re.sub(r"[^\w]+", "_", value, flags=re.UNICODE).strip("_").lower()
    slug = re.sub(r"_+", "_", slug)
    if slug.startswith("check_"):
        slug = slug[6:]
    if not slug:
        raise ValueError("الاسم لا ينتج اسم ملف صالحًا")
    return slug


def literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description="توليد بوابة فحص واختبارها")
    parser.add_argument("--name", required=True, help="اسم البوابة أو slug")
    parser.add_argument("--description", required=True, help="وصف ما تمنعه البوابة")
    parser.add_argument("--scope", required=True, help="نطاق القياس الذي تحرسه البوابة")
    parser.add_argument("--output-dir", required=True, help="مجلد نسخة العمل")
    parser.add_argument("--force", action="store_true", help="استبدل الملفات الموجودة")
    args = parser.parse_args()

    try:
        slug = slugify(args.name)
        if not args.description.strip() or not args.scope.strip():
            raise ValueError("الوصف والنطاق لا يجوز أن يكونا فارغين")
        output = Path(args.output_dir).expanduser().resolve()
        validators = output / "validators"
        tests = output / "tests"
        gate_path = validators / f"check_{slug}.py"
        test_path = tests / f"test_{slug}.py"
        if not args.force and (gate_path.exists() or test_path.exists()):
            raise FileExistsError("الملف المولّد موجود؛ استخدم --force للاستبدال")

        gate_template = (TEMPLATES / "gate_template.py").read_text(encoding="utf-8")
        test_template = (TEMPLATES / "test_template.py").read_text(encoding="utf-8")
        replacements = {
            "__GATE_NAME_LITERAL__": literal(args.name),
            "__GATE_DESCRIPTION_LITERAL__": literal(args.description),
            "__GATE_SCOPE_LITERAL__": literal(args.scope),
            "__GATE_MODULE_FILE__": gate_path.name,
        }
        gate_text = render(gate_template, replacements)
        test_text = render(test_template, replacements)
        validators.mkdir(parents=True, exist_ok=True)
        tests.mkdir(parents=True, exist_ok=True)
        gate_path.write_text(gate_text, encoding="utf-8")
        test_path.write_text(test_text, encoding="utf-8")
        gate_path.chmod(gate_path.stat().st_mode | 0o111)
        test_path.chmod(test_path.stat().st_mode | 0o111)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"منع: تعذّر توليد البوابة: {exc}")
        return 2

    print(f"أُنشئت البوابة: {gate_path}")
    print(f"أُنشئ الاختبار: {test_path}")
    print("الخطوات التالية:")
    print("  1) خصّص violations() لقاعدة المجال، مع إبقاء الفشل المغلق وأسباب المنع الحرفية.")
    print(f"  2) اربط البوابة في tests/run_checks.sh: python3 scripts/wire_into_runner.py --runner <runner> --gate {gate_path} --label \"{args.description}\"")
    print("  3) شغّل القياس الحقيقي على --date و--brain و--site و--pdf، وسجّل الأمر ورمز الخروج.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
