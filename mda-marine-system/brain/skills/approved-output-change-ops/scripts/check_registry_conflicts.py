#!/usr/bin/env python3
"""كشف بند واحد محظور ومطلوب في سجلين حاكمين مختلفين."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path


class RegistryError(RuntimeError):
    """خطأ في سجل لا يجوز تحويله إلى «لا تعارض»."""


def resolve_arg(value: str, brain: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else brain / path


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[\u0640\u064b-\u0652\u0670\u200b-\u200f\u202a-\u202e\u2066-\u2069]", "", value)
    return re.sub(r"\s+", " ", value).strip().casefold()


def read_terms(path: Path, role: str) -> dict[str, str]:
    if not path.is_file():
        raise RegistryError(f"ملف السجل غير موجود: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"تعذّر قراءة JSON للسجل: {path}") from exc

    values: list[str] = []

    def visit(obj: object, key: str = "") -> None:
        if isinstance(obj, str):
            if key in {"term", "word", "phrase", "value", "required", "forbidden"}:
                values.append(obj)
            return
        if isinstance(obj, list):
            for item in obj:
                visit(item, key)
            return
        if isinstance(obj, dict):
            # في simplified-vocabulary يكون term هو اللفظ الممنوع وplain هو البديل
            # المطلوب. عند وجود plain لا تُدخل term في مجموعة المطلوبين.
            if role == "required" and isinstance(obj.get("plain"), (str, list)):
                visit(obj["plain"], "required")
            elif isinstance(obj.get("term"), str):
                values.append(obj["term"])
            elif isinstance(obj.get("word"), str):
                values.append(obj["word"])
            elif isinstance(obj.get("phrase"), str):
                values.append(obj["phrase"])
            for child_key, child in obj.items():
                if child_key not in {"term", "plain", "reason", "source", "replacement", "note", "updated", "version", "status"}:
                    visit(child, child_key)

    visit(data)
    result: dict[str, str] = {}
    for value in values:
        key = normalize(value)
        if key and key not in result:
            result[key] = " ".join(value.split())
    return result


def default_required(brain: Path) -> Path:
    for candidate in (
        brain / "appendices" / "required-vocabulary.json",
        brain / "appendices" / "simplified-vocabulary.json",
        brain / "appendices" / "glossary-standard.json",
    ):
        if candidate.is_file():
            return candidate
    return brain / "appendices" / "required-vocabulary.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="فحص تعارض السجلات الحاكمة للمفردات")
    ap.add_argument("--brain", required=True, help="جذر المشروع")
    ap.add_argument("--frozen", required=True, help="ملف CSS المقفل؛ يثبت سياق الإصدار")
    ap.add_argument("--profile", required=True, help="profile المقفل؛ يثبت سياق الإصدار")
    ap.add_argument("--forbidden", action="append", help="سجل الممنوع؛ يمكن تكراره")
    ap.add_argument("--required", action="append", help="سجل المطلوب؛ يمكن تكراره")
    args = ap.parse_args()

    brain = Path(args.brain).expanduser().resolve()
    frozen = resolve_arg(args.frozen, brain)
    profile = resolve_arg(args.profile, brain)
    if not brain.is_dir():
        raise RegistryError(f"جذر المشروع غير موجود: {brain}")
    if not frozen.is_file() or not profile.is_file():
        raise RegistryError("لا يعمل الفحص بلا --frozen و--profile موجودين")

    forbidden_paths = [resolve_arg(x, brain) for x in (args.forbidden or ["appendices/forbidden-coinages.json"])]
    required_paths = [resolve_arg(x, brain) for x in (args.required or [str(default_required(brain).relative_to(brain))])]
    forbidden: dict[str, list[str]] = {}
    required: dict[str, list[str]] = {}
    for path in forbidden_paths:
        for key, value in read_terms(path, "forbidden").items():
            forbidden.setdefault(key, []).append(f"{path}: {value}")
    for path in required_paths:
        for key, value in read_terms(path, "required").items():
            required.setdefault(key, []).append(f"{path}: {value}")

    conflicts = sorted(set(forbidden) & set(required))
    print("فحص تعارض السجلات الحاكمة للمفردات")
    print(f"الممنوع: {len(forbidden)} بندًا · المطلوب: {len(required)} بندًا")
    print(f"القفل sha16: {hashlib.sha256(frozen.read_bytes()).hexdigest()[:16]}")
    print(f"profile sha16: {hashlib.sha256(profile.read_bytes()).hexdigest()[:16]}")
    if conflicts:
        print(f"التعارضات: {len(conflicts)}")
        for key in conflicts:
            print(f"  ✗ {required[key][0]} مطلوب، و{forbidden[key][0]} ممنوع")
        print("النتيجة: مانع — لا يُعتمد السجلان معًا")
        return 2
    print("التعارضات: 0")
    print("النتيجة: لا تعارض ✓")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegistryError as exc:
        print(f"مانع: {exc}")
        raise SystemExit(70)
