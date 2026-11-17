#!/usr/bin/env python3
"""فجوات النقل الموثقة بقرار المالك (قرار 2026-11-17).

أيام بقيت بياناتها على خادم Manus ولم تُنقل إلى المستودع. ليست «لا واقعة»
ولا «بلا مادة»: هي أيام لم تُفحص في هذا النظام، ويُعلَن ذلك صراحةً.
الملف: ``cumulative-2026/migration-gaps.json`` بصيغة
``{"migration_gaps": [{"from", "to", "reason", "decided_by", "decision_date"}]}``.
غياب الملف = لا فجوات. أي حقل ناقص أو مدى غير صالح = فشل مغلق.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

REL = Path("cumulative-2026") / "migration-gaps.json"
REQUIRED = ("from", "to", "reason", "decided_by", "decision_date")


def load_gap_dates(root: Path) -> set[str]:
    path = Path(root) / REL
    if not path.exists():
        return set()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"فجوة نقل: تعذر قراءة {path}: {exc}") from exc
    gaps = value.get("migration_gaps") if isinstance(value, dict) else None
    if not isinstance(gaps, list):
        raise RuntimeError(f"فجوة نقل: بنية غير صالحة في {path}")
    dates: set[str] = set()
    for index, gap in enumerate(gaps, 1):
        if not isinstance(gap, dict):
            raise RuntimeError(f"فجوة نقل #{index} ليست كائنًا: {path}")
        missing = [k for k in REQUIRED if not str(gap.get(k) or "").strip()]
        if missing:
            raise RuntimeError(f"فجوة نقل #{index} ناقصة {missing}: {path}")
        try:
            start = dt.date.fromisoformat(gap["from"])
            end = dt.date.fromisoformat(gap["to"])
            dt.date.fromisoformat(gap["decision_date"])
        except ValueError as exc:
            raise RuntimeError(f"فجوة نقل #{index} بتاريخ غير صالح: {exc}") from exc
        if start > end:
            raise RuntimeError(f"فجوة نقل #{index}: البداية بعد النهاية")
        day = start
        while day <= end:
            dates.add(day.isoformat())
            day += dt.timedelta(days=1)
    return dates
