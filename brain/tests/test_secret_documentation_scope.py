#!/usr/bin/env python3
"""اختبار نطاق D035: أمثلة الفحص في التوثيق ليست قيمًا، والسر المصطنع يبقى مانعًا."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "validators/check_secrets.py"
DOCS = (
    ROOT / "notes/2026-11-06-runbook-handoff.md",
    ROOT / "docs/superpowers/plans/2026-11-06-d005-secret-gate.md",
)


def run(*args: str) -> int:
    return subprocess.run(
        [sys.executable, str(GATE), "--root", str(ROOT), *args, "--quiet"],
        capture_output=True,
        text=True,
        timeout=60,
    ).returncode


def main() -> int:
    failures = []
    for doc in DOCS:
        rc = run("--file", str(doc.relative_to(ROOT)))
        if rc != 0:
            failures.append(f"التوثيق بلا قيمة سرية يجب أن يمر: {doc.name} (rc={rc})")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        assignment = "API" + "_KEY = \"" + "A1b2C3d4E5f6G7h8I9j0K1l2" + "\"\n"
        (root / "fake-secret.txt").write_text(
            assignment, encoding="utf-8"
        )
        rc = subprocess.run(
            [sys.executable, str(GATE), "--root", str(root), "--file", "fake-secret.txt", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
        ).returncode
        if rc != 70:
            failures.append(f"السر المصطنع يجب أن يبقى مانعًا (rc={rc})")

    if failures:
        for failure in failures:
            print(f"✘ {failure}")
        return 1
    print("✔ التوثيق يمرّ والسر المصطنع يعيد 70")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
