#!/usr/bin/env python3
"""اعتماد بصمة CSS الحالية بعد موافقة المالك، مع أثر قابل للتدقيق."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


class AdoptionError(RuntimeError):
    """خطأ مانع يمنع اعتماد قفل غير موثّق."""


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def resolve_arg(value: str, brain: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else brain / path


def extract_print_css(source: str) -> str:
    """استخراج أول كتلة @media print بتوازن الأقواس."""
    start = source.find("@media print")
    if start < 0:
        raise AdoptionError("لم يُعثر على @media print في مصدر النمط")
    opening = source.find("{", start)
    if opening < 0:
        raise AdoptionError("كتلة @media print بلا قوس افتتاح")
    depth = 0
    for index in range(opening, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AdoptionError("كتلة @media print غير مكتملة")


def discover_current(brain: Path) -> tuple[Path, str]:
    preferred = [
        brain / "web" / "build_report.py",
        brain / "site" / "generator" / "build_report.py",
    ]
    candidates = [p for p in preferred if p.is_file()]
    if not candidates:
        candidates = [
            p for p in brain.rglob("build_report.py")
            if "/archive/" not in p.as_posix() and "/logs/" not in p.as_posix()
        ]
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if "@media print" in text:
            return path, extract_print_css(text)
    raise AdoptionError("لم يُعثر على مصدر build_report.py يحوي @media print؛ مرّر --current")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def parse_date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise AdoptionError(f"التاريخ يجب أن يكون YYYY-MM-DD: {value}") from exc


def main() -> int:
    ap = argparse.ArgumentParser(description="اعتماد قفل CSS بعد موافقة المالك")
    ap.add_argument("--brain", required=True, help="جذر المشروع")
    ap.add_argument("--frozen", required=True, help="ملف CSS المقفل")
    ap.add_argument("--profile", required=True, help="ملف تعريف القفل JSON")
    ap.add_argument("--current", help="ملف مصدر يحوي @media print؛ الافتراضي اكتشاف build_report.py")
    ap.add_argument("--approved-by", required=True, help="اسم/هوية صاحب القرار")
    ap.add_argument("--reason", required=True, help="سبب التغيير")
    ap.add_argument("--evidence", required=True, help="أثر القياس أو رابط/مسار دليل حي")
    ap.add_argument("--date", required=True, help="تاريخ القرار YYYY-MM-DD")
    args = ap.parse_args()

    brain = Path(args.brain).expanduser().resolve()
    frozen = resolve_arg(args.frozen, brain)
    profile = resolve_arg(args.profile, brain)
    if not brain.is_dir():
        raise AdoptionError(f"جذر المشروع غير موجود: {brain}")
    if not frozen.is_file():
        raise AdoptionError(f"ملف القفل غير موجود: {frozen}")
    if not profile.is_file():
        raise AdoptionError(f"ملف profile غير موجود: {profile}")
    if not args.approved_by.strip() or not args.reason.strip() or not args.evidence.strip():
        raise AdoptionError("لا اعتماد بلا approved-by وreason وevidence غير فارغة")
    decision_date = parse_date(args.date)

    old_css = frozen.read_text(encoding="utf-8")
    old_sha = sha16(old_css)
    if args.current:
        source = Path(args.current).expanduser()
        if not source.is_absolute():
            source = brain / source
        if not source.is_file():
            raise AdoptionError(f"مصدر النمط غير موجود: {source}")
        current_source, current_css = source, extract_print_css(source.read_text(encoding="utf-8"))
    else:
        current_source, current_css = discover_current(brain)
    new_sha = sha16(current_css)
    if old_sha == new_sha:
        print(f"لا تغيير: البصمة الحالية والمعتمدة متطابقتان ({new_sha})")
        print(f"المصدر: {current_source}")
        return 0

    superseded = frozen.parent / f"SUPERSEDED-{old_sha}{frozen.suffix or '.css'}"
    if superseded.exists() and superseded.read_bytes() != frozen.read_bytes():
        raise AdoptionError(f"نسخة SUPERSEDED موجودة بمحتوى مختلف: {superseded}")
    if not superseded.exists():
        shutil.copyfile(frozen, superseded)

    try:
        data = json.loads(profile.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdoptionError(f"profile ليس JSON صالحًا: {profile}") from exc
    if not isinstance(data, dict):
        raise AdoptionError("profile يجب أن يكون كائن JSON")
    changes = data.setdefault("changes", [])
    if not isinstance(changes, list):
        raise AdoptionError("profile.changes يجب أن تكون قائمة")
    record = {
        "date": decision_date,
        "from": old_sha,
        "to": new_sha,
        "reason": args.reason.strip(),
        "approved_by": args.approved_by.strip(),
        "evidence": args.evidence.strip(),
    }
    data["print_css_sha16"] = new_sha
    changes.append(record)

    atomic_write(frozen, current_css)
    atomic_write(profile, json.dumps(data, ensure_ascii=False, indent=1) + "\n")

    # تحقق بعد الكتابة: لا نعلن اعتمادًا قبل إثبات الملفين والبصمة.
    written_sha = sha16(frozen.read_text(encoding="utf-8"))
    profile_after = json.loads(profile.read_text(encoding="utf-8"))
    if written_sha != new_sha or profile_after.get("print_css_sha16") != new_sha:
        raise AdoptionError("فشل تحقق ما بعد الكتابة: القفل وprofile غير متطابقين")

    print("اعتماد بصمة النمط: تم")
    print(f"من: {old_sha}")
    print(f"إلى: {new_sha}")
    print(f"نسخة سابقة: {superseded}")
    print(f"المصدر: {current_source}")
    print(f"المعتمد: {args.approved_by.strip()}")
    print(f"التاريخ: {decision_date}")
    print(f"الدليل: {args.evidence.strip()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AdoptionError as exc:
        print(f"مانع: {exc}")
        raise SystemExit(2)
