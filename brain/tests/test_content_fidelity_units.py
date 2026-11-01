#!/usr/bin/env python3
"""اختبار انحدار لوحدات إسناد المصدر المشتركة بين المولّد والحاجز."""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from source_count_units import count_phrase, count_written_attributions  # noqa: E402


def main() -> int:
    failures: list[str] = []

    generated = [
        count_phrase(1, 0),
        count_phrase(3, 1),
        count_phrase(1, 2),
        count_phrase(1, 3),
        count_phrase(1, 0),
        count_phrase(1, 1),
    ]
    expected = ["واقعة واحدة", "3 بلاغات", "حادثة واحدة", "واقعة منفردة", "واقعة واحدة", "بلاغ واحد"]
    if generated != expected:
        failures.append(f"عبارات المولّد تغيّرت: {generated!r} != {expected!r}")

    clause = "؛ ".join(generated)
    if count_written_attributions(clause) != 8:
        failures.append("الحاجز لا يحسب قائمة الوحدات الفعلية للمولّد إلى 8 إسنادات")

    line_rc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "source_counts.py"), "--date", "2026-11-01", "--line"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).returncode
    if line_rc != 0:
        failures.append(f"مولّد سطر الإسنادات أعاد رمز {line_rc}")

    if failures:
        print("  ✘ " + "\n  ✘ ".join(failures))
        return 1
    print("  ✔ وحدات الإسناد المشتركة تطابق عبارات المولّد وتحسب 8 إسنادات")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
