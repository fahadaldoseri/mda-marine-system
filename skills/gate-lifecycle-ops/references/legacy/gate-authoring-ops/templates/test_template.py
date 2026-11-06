#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار عقد البوابة: السليم يمر، والمخالف والمفقود يمنعان فشلًا مغلقًا."""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

GATE_FILE = Path(__file__).resolve().parents[1] / "validators" / "__GATE_MODULE_FILE__"
spec = importlib.util.spec_from_file_location("generated_gate", GATE_FILE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"تعذّر تحميل البوابة: {GATE_FILE}")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
violations = gate.violations

passed = 0
failed = 0


def check(condition: bool, label: str) -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✔ {label}")
    else:
        failed += 1
        print(f"  ✘ {label}")


def fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, Path, Path]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    brain = root / "brain"
    site = root / "site"
    pdf = root / "report.pdf"
    brain.mkdir()
    site.mkdir()
    marker = f"{gate.SCOPE_MARKER}\nمخرج قابل للقياس"
    (brain / "gate-measurement.txt").write_text(marker, encoding="utf-8")
    (site / "gate-measurement.txt").write_text(marker, encoding="utf-8")
    pdf.write_text(marker, encoding="utf-8")
    return temp, brain, site, pdf


def run() -> int:
    global passed, failed
    print(f"اختبار البوابة: {gate.GATE_NAME}")

    temp, brain, site, pdf = fixture()
    try:
        check(
            violations(date_value="2026-10-28", brain=brain, site=site, pdf=pdf) == [],
            "مدخل سليم يجتاز",
        )
    finally:
        temp.cleanup()

    temp, brain, site, pdf = fixture()
    try:
        (site / "gate-measurement.txt").write_text("مخرج مخالف بلا وسم النطاق", encoding="utf-8")
        check(
            bool(violations(date_value="2026-10-28", brain=brain, site=site, pdf=pdf)),
            "مدخل مخالف يُمنع",
        )
    finally:
        temp.cleanup()

    temp, brain, site, pdf = fixture()
    try:
        pdf.unlink()
        check(
            bool(violations(date_value="2026-10-28", brain=brain, site=site, pdf=pdf)),
            "مدخل مفقود يُمنع فشلًا مغلقًا",
        )
    finally:
        temp.cleanup()

    temp, brain, site, pdf = fixture()
    try:
        pdf.write_text("", encoding="utf-8")
        check(
            bool(violations(date_value="2026-10-28", brain=brain, site=site, pdf=pdf)),
            "مدخل غير قابل للقياس يُمنع فشلًا مغلقًا",
        )
    finally:
        temp.cleanup()

    print(f"نجح {passed} · فشل {failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(run())
