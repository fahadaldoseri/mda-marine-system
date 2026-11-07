#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس ب-10: معرفات الخريطة الحاكمة لا تُختصر كالنص المعروض."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generator"))
import codes  # noqa: E402
import map_gulf  # noqa: E402


def test_map_event_ids_survive_secondary_surface_demotion() -> None:
    map_gulf.REPORT_DATE = "2026-11-06"
    points = [
        {"code": "MN-2026-11-06-01", "lon": 51.30, "lat": 26.45},
        {"code": "MN-2026-11-06-02", "lon": 56.40, "lat": 26.56},
        {"code": "MN-2026-11-06-03", "lon": 56.40, "lat": 26.56},
    ]
    page = '<section><h2>التوزيع الجغرافي</h2>' + map_gulf.build_map(points) + '</section>'

    demoted = codes.demote_page(page, "2026-11-06")
    ids = re.findall(r'data-event-id="([^"]+)"', demoted)

    assert sorted(ids) == [
        "MN-2026-11-06-01",
        "MN-2026-11-06-02·MN-2026-11-06-03",
    ]
