#!/usr/bin/env python3
"""اختبار قرار جمع مصادر الواقعة: موجب، منع التكرار، ومنع المقتطف الناقص."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from merge_event_sources import MergeEventSourcesError, merge_event_records  # noqa: E402


def main() -> int:
    rows = [
        {
            "code": "MN-2026-11-04-01",
            "source": "المصدر ألف",
            "source_excerpt": "بلاغ عن واقعة في المضيق",
            "title": "واقعة في المضيق",
        },
        {
            "code": "MN-2026-11-04-02",
            "duplicate_of": "MN-2026-11-04-01",
            "source": "المصدر باء",
            "source_excerpt": "بلاغ عن واقعة في المضيق مع تحديد الموقع",
            "title": "نسخة مكررة",
        },
        {
            "code": "MN-2026-11-04-03",
            "duplicate_of": "MN-2026-11-04-01",
            "source": "المصدر ألف",
            "source_excerpt": "بلاغ عن واقعة في المضيق",
            "title": "نسخة مكررة للمصدر نفسه",
        },
    ]
    merged, report = merge_event_records(rows)
    canonical = merged[0]
    assert canonical["source"] == "المصدر ألف, المصدر باء", canonical["source"]
    assert [item["name"] for item in canonical["sources"]] == ["المصدر ألف", "المصدر باء"]
    assert all(item["excerpt"] for item in canonical["sources"])
    assert report["title_regeneration_required_codes"] == ["MN-2026-11-04-01"]

    try:
        merge_event_records([
            {"code": "MN-2026-11-04-01", "source": "مصدر بلا مقتطف"},
        ])
    except MergeEventSourcesError:
        pass
    else:
        raise AssertionError("الاسم بلا مقتطف يجب أن يُرفض فشلًا مغلقًا")

    _, repeat_report = merge_event_records([
        {"code": "MN-2026-11-04-11", "source": "المصدر ألف", "source_excerpt": "النص نفسه"},
        {
            "code": "MN-2026-11-04-12",
            "duplicate_of": "MN-2026-11-04-11",
            "source": "المصدر ألف",
            "source_excerpt": "النص نفسه",
        },
    ])
    assert repeat_report["title_regeneration_required_codes"] == []

    print("  ✔ جمع مصدرين مختلفين بلا تكرار مع مقتطفين محفوظين")
    print("  ✔ الاسم المكرر لا يتكرر، ولا يعيد العنوان عند تكرار النص نفسه")
    print("  ✔ الاسم بلا مقتطف مرفوض")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
