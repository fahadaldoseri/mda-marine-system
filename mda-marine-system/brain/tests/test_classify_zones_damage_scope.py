#!/usr/bin/env python3
"""اختبار قاعدة سلم التهديد: الضرر يجب أن يخص واقعة الهجوم المؤكدة نفسها."""

from tools.classify_zones import rank_of_zone


def test_attack_damage_must_be_same_confirmed_incident():
    rows = [
        {
            "code": "A",
            "incident_group": "attack-a",
            "qualifying": True,
            "confirmation": "confirmed",
            "title": "هجوم على سفينة في المضيق",
            "source_excerpt": "بلاغ رسمي عن واقعة.",
        },
        {
            "code": "B",
            "incident_group": "fire-b",
            "qualifying": True,
            "confirmation": "probable",
            "title": "حريق سفينة وإجلاء طاقمها",
            "source_excerpt": "نقل مهني عن حريق على متن سفينة.",
        },
    ]
    levels = {
        "حرج": {"rank": 5},
        "مرتفع جدًا": {"rank": 4},
        "مرتفع": {"rank": 3},
        "متوسط": {"rank": 2},
        "منخفض": {"rank": 1},
    }

    result = rank_of_zone(rows, levels, ["Z1", "Z2", "Z3", "Z4"])

    assert result["attack_with_damage"] is False
    assert result["level"] == "مرتفع"
