#!/usr/bin/env python3
"""اختبار عقد بطاقات ملخص تلغرام: RED قبل إصلاح D030 ثم GREEN بعده.

يختبر أكثر من شكل محتمل للبطاقات، مع اعتماد عنوان البطاقة من السجل الحاكم
عندما لا يضع ملف الواجهة label صريحًا.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("make_tg_digest", ROOT / "tools" / "make_tg_digest.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def render(hero_kpis):
    meta = json.loads((ROOT / "web/meta/2026-11-06.json").read_text(encoding="utf-8"))
    meta["hero_kpis"] = hero_kpis
    return MOD.build(meta, "2026-11-06", "https://example.test")


def test_fallback_delivery_note_contains_verified_url_and_manus_outage():
    meta = json.loads((ROOT / "web/meta/2026-11-06.json").read_text(encoding="utf-8"))
    text = MOD.build(
        meta,
        "2026-11-07",
        "https://raw.githack.com/fahadaldoseri/seawatch-live/main",
        delivery_note=(
            "القناة الأساسية (منصة Manus) معطّلة مؤقتًا؛ "
            "أُرسل التقرير عبر القناة البديلة."
        ),
    )
    assert "https://raw.githack.com/fahadaldoseri/seawatch-live/main/reports/2026-11-07.html" in text
    assert "القناة الأساسية (منصة Manus) معطّلة مؤقتًا" in text


def main() -> int:
    # المعرّفات المعروفة تأخذ الاسم المختصر «الاسم: العدد» (اختيار فهد، 19 نوفمبر)؛
    # والاختبار يثبت أن القيمة تُقرأ من كل أشكال البطاقة.
    cases = [
        (
            "شكل اليوم: title/value مع بطاقة بلا label",
            [
                {"id": "qualifying-incidents", "title": "وقائع مستوفية", "value": "2"},
                {"id": "unconfirmed-narratives", "title": "روايات لم تتأكد", "value": "2"},
            ],
            ("الوقائع المحتسبة: 2", "روايات غير مؤكدة: 2"),
        ),
        (
            "شكل مستقبلي: display_label/current",
            [
                {"id": "ukmto-reports", "display_label": "بلاغات جديدة", "current": 3},
                {"id": "qualifying-incidents", "display_label": "وقائع مؤهلة", "current": 4},
            ],
            ("البلاغات الرسمية: 3", "الوقائع المحتسبة: 4"),
        ),
        (
            "حاوية بطاقات مستقبلية مع fallback من السجل الحاكم",
            {"cards": [
                {"id": "qualifying-incidents", "value": "5"},
                {"id": "unconfirmed-narratives", "count": 6},
            ]},
            ("الوقائع المحتسبة: 5", "روايات غير مؤكدة: 6"),
        ),
    ]
    failures = []
    for name, cards, expected in cases:
        try:
            text = render(cards)
        except Exception as exc:  # RED يلتقط KeyError/TypeError قبل الإصلاح
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        for needle in expected:
            if needle not in text:
                failures.append(f"{name}: missing {needle!r}")
    if failures:
        for failure in failures:
            print(f"✘ {failure}")
        return 1
    print(f"✔ {len(cases)}/{len(cases)} أشكال بطاقات ملخص تلغرام مقبولة")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
