#!/usr/bin/env python3
"""قارن شجرتي أصول حاكمة دون أي كتابة.

الرموز: 0 تطابق، 1 نقص/انحراف، 2 وسيط أو جذر غير صالح.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="قارن مجلدًا محليًا بمجلد مرآة: الأسطر والبصمة والملفات الناقصة.",
        epilog="لا يكتب السكربت أي ملف؛ يعيد 1 عند أي فرق و0 عند التطابق.",
    )
    ap.add_argument("local", type=Path, help="جذر الأصول المحلي")
    ap.add_argument("mirror", type=Path, help="جذر مرآة الأصول")
    return ap


def inventory(root: Path) -> dict[str, Path]:
    """أعد الملفات العادية دون اتباع الروابط الرمزية أو تعديل الشجرة."""
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            files[path.relative_to(root).as_posix()] = path
    return files


def measure(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    digest = hashlib.sha256(data).hexdigest()
    return lines, digest


def short(digest: str | None) -> str:
    return digest[:16] if digest else "—"


def main(argv: list[str] | None = None) -> int:
    ap = parser()
    args = ap.parse_args(argv)
    local, mirror = args.local.expanduser(), args.mirror.expanduser()
    if not local.is_dir() or not mirror.is_dir():
        missing = []
        if not local.is_dir():
            missing.append(f"المحلي غير موجود أو ليس مجلدًا: {local}")
        if not mirror.is_dir():
            missing.append(f"المرآة غير موجودة أو ليست مجلدًا: {mirror}")
        for message in missing:
            print(f"✘ {message}")
        return 2

    try:
        local_files = inventory(local)
        mirror_files = inventory(mirror)
        paths = sorted(set(local_files) | set(mirror_files))
        differences: list[tuple[str, str, str, str]] = []
        equal = 0
        for rel in paths:
            lp, mp = local_files.get(rel), mirror_files.get(rel)
            if lp is None:
                ml, md = measure(mp)  # type: ignore[arg-type]
                differences.append(("ناقص محليًا", rel, "—", f"{ml}/{short(md)}"))
            elif mp is None:
                ll, ld = measure(lp)
                differences.append(("ناقص في المرآة", rel, f"{ll}/{short(ld)}", "—"))
            else:
                ll, ld = measure(lp)
                ml, md = measure(mp)
                if (ll, ld) == (ml, md):
                    equal += 1
                else:
                    differences.append(("منحرف", rel, f"{ll}/{short(ld)}", f"{ml}/{short(md)}"))
    except OSError as exc:
        print(f"✘ تعذر قراءة شجرة المقارنة: {exc}")
        return 2

    print("=== مقارنة الأصول الحاكمة — قراءة فقط ===")
    print(f"محلي: {local}")
    print(f"مرآة: {mirror}")
    print("| الحالة | المسار | المحلي (أسطر/بصمة16) | المرآة (أسطر/بصمة16) |")
    print("|---|---|---:|---:|")
    if differences:
        for status, rel, local_value, mirror_value in differences:
            print(f"| {status} | `{rel}` | {local_value} | {mirror_value} |")
    else:
        print("| مطابق | — | — | — |")
    print(
        f"الملفات: محلي {len(local_files)} · مرآة {len(mirror_files)} · "
        f"مطابق {equal} · فروق {len(differences)}"
    )
    if differences:
        print("النتيجة: مانع — أعد الأصول ثم أعد القياس")
        return 1
    print("النتيجة: مطابق — لا فروق")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
