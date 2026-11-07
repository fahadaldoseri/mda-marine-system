#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس سلسلة الاستبدال في أنماط الأسلوب (عطل ك-488).

السبب: بوابة الأسلوب اقترحت بديلًا للتركيب المعلّق «يبقى»، وكان البديل المقترح «ما زال»
نفسه لفظًا ممنوعًا في بوابة عيوب الصياغة. فدار المستخدم في حلقة: إصلاح يرجع مانعًا.

القاعدة المقيسة: لا يجوز أن يكون بديل أي نمط ممنوع لفظًا ممنوعًا في السجل نفسه.
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BLACKLIST = ROOT / "appendices" / "style-blacklist.json"
PROSE_BAN = ROOT / "appendices" / "style-blacklist.json"


def _iter_patterns(obj):
    if isinstance(obj, dict):
        if obj.get("replacement"):
            yield obj
        for v in obj.values():
            yield from _iter_patterns(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_patterns(v)


def _banned_literals(data: dict) -> list[str]:
    """الألفاظ المانعة في السجل نفسه: قائمة blocking والقائمة الرقابية watch."""
    out = []
    for key in ("blocking", "watch"):
        for item in data.get(key) or []:
            if isinstance(item, dict) and isinstance(item.get("term"), str):
                out.append(item["term"])
            elif isinstance(item, str):
                out.append(item)
    return out


def _clashes(data: dict) -> list[tuple]:
    banned = _banned_literals(data)
    found = []
    for pat in _iter_patterns(data):
        rep = str(pat.get("replacement") or "").strip()
        if not rep:
            continue
        own = str(pat.get("term") or pat.get("pattern") or "").strip()
        for b in banned:
            b = str(b).strip()
            if not b:
                continue
            if b == own:
                # توسعة إرشادية للفظ نفسه، لا تعارضًا بين سجلين.
                continue
            if b == rep or re.search(rf"(?<![\w\u0600-\u06FF]){re.escape(b)}(?![\w\u0600-\u06FF])", rep):
                found.append((pat.get("id") or pat.get("term") or "?", rep, b))
    return found


def test_replacements_are_not_banned() -> None:
    data = json.loads(BLACKLIST.read_text(encoding="utf-8"))
    clashes = _clashes(data)
    assert not clashes, f"بدائل ممنوعة داخل سجل الأنماط: {clashes}"


def test_detector_catches_known_clash() -> None:
    """ضبط سالب: الكاشف يمسك التعارض حين يعود البديل الممنوع."""
    sample = {"blocking": [{"term": "ما زال", "replacement": "ظلّ"}],
              "patterns": [{"id": "hanging_yabqa", "pattern": "يبقى", "replacement": "ما زال"}]}
    assert _clashes(sample), "الكاشف لم يمسك تعارضًا معلومًا — الحارس لا يفيد"


if __name__ == "__main__":
    test_replacements_are_not_banned()
    print("   ✔ لا بديل ممنوع داخل سجل الأنماط")
    test_detector_catches_known_clash()
    print("   ✔ الكاشف يمسك التعارض المعلوم (ضبط سالب)")
    print("حارس سلسلة الاستبدال في أنماط الأسلوب: نجاح")
