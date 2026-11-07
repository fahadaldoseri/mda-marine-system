#!/usr/bin/env python3
"""اختبار bootstrap لعلامة pipeline.

يعمل في مشروع مؤقت: الغياب يُنشئ علامة عبر write_mark ثم يحدّث المكوّن،
أما JSON التالف فيبقى فشلًا مغلقًا برمز 2.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DATE = "2026-10-31"


def run_case(mark_text: str | None):
    top = Path(tempfile.mkdtemp(prefix="mark-bootstrap-"))
    root = top / "brain"
    for rel in ("tools", "templates", "appendices", "feeds", "logs"):
        (root / rel).mkdir(parents=True)
    for name in ("mark_components.py", "write_mark.py", "source_counts.py"):
        shutil.copy(HERE / "tools" / name, root / "tools" / name)
    shutil.copy(HERE / "templates" / "mark-schema.json", root / "templates" / "mark-schema.json")
    shutil.copy(HERE / "appendices" / "sources-manifest.json", root / "appendices" / "sources-manifest.json")
    (root / "feeds" / f"feeds-{DATE}.status.json").write_text(
        json.dumps({"checked": 1, "ok": 1, "failed": 0, "failed_feeds": []}), encoding="utf-8"
    )
    mark = root / "logs" / f"pipeline-{DATE}.json"
    if mark_text is not None:
        mark.write_text(mark_text, encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(root / "tools" / "mark_components.py"), "--date", DATE, "--component", "feeds"],
        cwd=root, capture_output=True, text=True,
    )
    return top, mark, p


def main() -> int:
    top, mark, p = run_case(None)
    try:
        assert p.returncode == 0, p.stdout + p.stderr
        data = json.loads(mark.read_text(encoding="utf-8"))
        assert data.get("created_by") == "mark_components", data
        assert data["feeds"]["status"] == "ok", data
        print("  ✔ غياب العلامة: bootstrap موثق ويحدّث feeds")
    finally:
        shutil.rmtree(top)

    top, mark, p = run_case("{\"broken\":")
    try:
        assert p.returncode == 2, (p.returncode, p.stdout, p.stderr)
        assert mark.read_text(encoding="utf-8") == "{\"broken\":"
        print("  ✔ JSON تالف: الفشل المغلق بقي برمز 2")
    finally:
        shutil.rmtree(top)
    return 0


if __name__ == "__main__":
    main()
