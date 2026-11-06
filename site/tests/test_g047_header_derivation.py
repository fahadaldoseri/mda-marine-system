#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار منع رجوع G047: الترويسة تُشتق من السجل لا من ترتيب مكتوب يدويًا."""
from __future__ import annotations

import sys
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1].parent / "brain-marine-news"
sys.path.insert(0, str(BRAIN / "tools"))
import classify_zones  # noqa: E402


def test_header_uses_registry_name_and_level_for_a_future_zone() -> None:
    registry = {
        "zones": [
            {"id": "Z1", "ar": "قطاع قديم"},
            {"id": "Z6", "ar": "ممر مستقبلي جديد"},
        ]
    }
    zone_card = {
        "overall": {"level": "مرتفع", "top_zone_id": "Z6", "top_zone": "نص قديم"},
        "zones": [
            {"id": "Z1", "name": "قطاع قديم", "level": "متوسط", "rank": 2},
            {"id": "Z6", "name": "ممر مستقبلي جديد", "level": "مرتفع", "rank": 3},
        ],
    }

    derive = getattr(classify_zones, "governed_threat_lede", None)
    assert derive is not None, "G047 needs a governed threat-header derivation function"
    assert derive(zone_card, registry) == (
        "المستوى العام مرتفع. ويظل ممر مستقبلي جديد أعلى القطاعات عند مستوى مرتفع."
    )


if __name__ == "__main__":
    test_header_uses_registry_name_and_level_for_a_future_zone()
    print("G047 header derivation: PASS")
