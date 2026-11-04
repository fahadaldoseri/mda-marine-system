#!/usr/bin/env python3
"""اختبار سطر تغطية التغذيات: عدّ الصفوف ودليل الفشل المغلق."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from source_coverage_line import CoverageError, build_coverage, write_meta  # noqa: E402


def fixture(root: Path, *, bad_status_num: int | None = None) -> None:
    (root / "feeds").mkdir(parents=True)
    (root / "web" / "meta").mkdir(parents=True)
    feeds = [
        {"num": 1, "name": "مصدر ناجح", "ok": True, "url": "https://example.test/1"},
        {"num": 2, "name": "مصدر محجوب", "ok": False, "block_reason": "HTTP 403"},
    ]
    failed_num = bad_status_num if bad_status_num is not None else 2
    status = {
        "date": "2026-11-04",
        "checked": 2,
        "ok": 1,
        "failed": 1,
        "checked_feeds": [{"num": 1, "ok": True}, {"num": 2, "ok": False}],
        "failed_attempts": [{"num": failed_num, "name": "مصدر محجوب", "error": "HTTP 403"}],
    }
    (root / "feeds" / "feeds-2026-11-04.json").write_text(json.dumps(feeds, ensure_ascii=False), encoding="utf-8")
    (root / "feeds" / "feeds-2026-11-04.status.json").write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
    (root / "web" / "meta" / "2026-11-04.json").write_text(json.dumps({"keep": "as-is"}, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="coverage-line-") as tmp:
        root = Path(tmp)
        fixture(root)
        coverage = build_coverage(root, "2026-11-04")
        assert coverage["line"] == "فحص المصادر: 1 ناجحًا من 2 · 1 محجوبة", coverage["line"]
        assert coverage["blocked"][0]["name"] == "مصدر محجوب"
        write_meta(root, "2026-11-04", coverage)
        meta = json.loads((root / "web" / "meta" / "2026-11-04.json").read_text(encoding="utf-8"))
        assert meta["keep"] == "as-is" and meta["source_coverage"]["blocked_count"] == 1

    with tempfile.TemporaryDirectory(prefix="coverage-line-negative-") as tmp:
        root = Path(tmp)
        fixture(root, bad_status_num=999)
        try:
            build_coverage(root, "2026-11-04")
        except CoverageError as exc:
            assert "999" in str(exc)
        else:
            raise AssertionError("رقم الحالة بلا صف مسند في feeds يجب أن يمنع البناء")

    print("  ✔ السطر والكتابة المستقلة للواجهة يحفظان الحقول القائمة")
    print("  ✔ رقم بلا سند في ملف التغذية مرفوض فشلًا مغلقًا")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
