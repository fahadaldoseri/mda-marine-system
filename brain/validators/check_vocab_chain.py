#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس سلسلة الاستبدال (ك-470) — يمنع أن يكون بديل آليّ لفظًا ممنوعًا.

السبب المثبت 2026-11-02: كان المحرِّر الآلي يستبدل «المصادر المستشهد بها» بـ«المصادر المذكورة»
(وهو نفسه ممنوع يُستبدل بـ«المصادر المستخدمة»)، فيُنتج نصًّا تمنعه بوابة المصطنعة ويعيد الكتلة كلها.
المعيار هنا = آلية التبديل الفعلية، لا تشابه قوائم: كل هدف تبديل آلي يُقاس على القائمة المانعة.

رموز الخروج: 0 سليم · 2 سلسلة مانعة · 70 انهيار.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RULES = BASE / "appendices" / "writing-rules.json"
COINAGES = BASE / "appendices" / "forbidden-coinages.json"


def banned_terms() -> set[str]:
    d = json.loads(COINAGES.read_text(encoding="utf-8"))
    return {str(e.get("term") or "").strip() for e in d.get("entries", []) if e.get("term")}


def applied_targets() -> list[tuple[str, str, str]]:
    """(المصدر, المفتاح, البديل) لكل تبديل آلي فعلي."""
    r = json.loads(RULES.read_text(encoding="utf-8"))
    out: list[tuple[str, str, str]] = []
    for item in r.get("autoreplace", []):
        t = str(item.get("term") or "").strip()
        rep = str(item.get("do") or item.get("replacement") or "").strip()
        if t and rep:
            out.append(("autoreplace", t, rep))
    for item in r.get("manual_only", []):
        t = str(item.get("dont") or "").strip()
        rep = str(item.get("do") or "").strip()
        if t and rep:
            out.append(("manual_only", t, rep))
    return out


def main() -> int:
    banned = banned_terms()
    bad = [(src, t, rep) for src, t, rep in applied_targets() if rep in banned]
    total = len(applied_targets())
    if bad:
        for src, t, rep in bad:
            print(f"   ✘ سلسلة استبدال ({src}): «{t}» ← «{rep}» والبديل نفسه ممنوع", file=sys.stderr)
        print(f"   النتيجة: مانع — {len(bad)} سلسلة من {total} تبديلًا آليًا", file=sys.stderr)
        return 2
    print(f"   ✔ لا سلسلة استبدال: {total} تبديلًا آليًا · {len(banned)} بندًا مانعًا — كل البدائل نهائية")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
