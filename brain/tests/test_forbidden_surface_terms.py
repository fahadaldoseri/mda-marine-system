#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار حاجز الألفاظ المانعة على المتن والواجهة والصفحة.

الحالتان المطلوبتان:
- موجب: أسطح يومية نظيفة تمر برمز 0.
- سالب: حقن «نافذة» في الصفحة يمنع برمز 2.
- سالب مستقل: مدقق القائمة السوداء نفسه يمنع اللفظ في probe.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
VALIDATOR = B / "validators" / "check_forbidden_surface_terms.py"
STYLE = B / "validators" / "check_style.py"
DATE = "2026-10-31"


def run_validator(brain: Path, site: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--date",
            DATE,
            "--brain",
            str(brain),
            "--site",
            str(site),
        ],
        cwd=B,
        capture_output=True,
        text=True,
    )


def make_fixture(root: Path) -> tuple[Path, Path]:
    brain = root / "brain"
    site = root / "site"
    (brain / "web" / "meta").mkdir(parents=True)
    (brain / "reports").mkdir()
    (brain / "appendices").mkdir()
    (site / "sources" / "meta").mkdir(parents=True)
    (site / "sources" / "reports").mkdir(parents=True)
    (site / "dist" / "reports").mkdir(parents=True)
    shutil.copy2(B / "appendices" / "style-blacklist.json", brain / "appendices" / "style-blacklist.json")
    clean_meta = {"detail": "خلال فترة التغطية"}
    clean_report = "# تقرير\n\nنص زمني سليم خلال فترة التغطية.\n"
    clean_html = "<!doctype html><html lang=\"ar\"><body>خلال فترة التغطية</body></html>\n"
    (brain / "web" / "meta" / f"{DATE}.json").write_text(
        json.dumps(clean_meta, ensure_ascii=False), encoding="utf-8"
    )
    (brain / "reports" / f"{DATE}-sectioned.md").write_text(clean_report, encoding="utf-8")
    (site / "sources" / "meta" / f"{DATE}.json").write_text(
        json.dumps(clean_meta, ensure_ascii=False), encoding="utf-8"
    )
    (site / "sources" / "reports" / f"{DATE}-sectioned.md").write_text(clean_report, encoding="utf-8")
    (site / "dist" / "reports" / f"{DATE}.html").write_text(clean_html, encoding="utf-8")
    return brain, site


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="forbidden-surface-") as d:
        root = Path(d)
        brain, site = make_fixture(root)
        positive = run_validator(brain, site)
        if positive.returncode == 0:
            print("  ✓ الأسطح النظيفة تمر (0)")
        else:
            failures.append("الموجب النظيف")
            print("  ✘ الأسطح النظيفة لم تمر:", (positive.stdout + positive.stderr).strip())

        page = site / "dist" / "reports" / f"{DATE}.html"
        page.write_text(page.read_text(encoding="utf-8") + " نافذة", encoding="utf-8")
        negative = run_validator(brain, site)
        if negative.returncode == 2 and "نافذة" in (negative.stdout + negative.stderr):
            print("  ✓ حقن اللفظ في الصفحة يُمنع (2)")
        else:
            failures.append("السالب على الصفحة")
            print("  ✘ السالب لم يمنع:", (negative.stdout + negative.stderr).strip())

        probe = root / "probe.md"
        probe.write_text("# اختبار\n\nخلال نافذة التقرير.\n", encoding="utf-8")
        style = subprocess.run(
            [sys.executable, str(STYLE), str(probe)],
            cwd=B,
            capture_output=True,
            text=True,
        )
        if style.returncode == 2 and "نافذة" in (style.stdout + style.stderr):
            print("  ✓ مدقق القائمة السوداء يمنع نافذة (2)")
        else:
            failures.append("السالب المباشر للقائمة")
            print("  ✘ مدقق القائمة لم يمنع نافذة:", (style.stdout + style.stderr).strip())
    print(f"الحصيلة: {len(failures)} فشل")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
