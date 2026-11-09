#!/usr/bin/env python3
"""بوابة المفردات المبسطة — تنبيهية حتى الموافقة الصريحة (قرار صاحب القرار 2026-10-23).

الغرض: كشف الألفاظ الصعبة أو المنقولة حرفيًا التي لها بديل يومي واضح في
appendices/simplified-vocabulary.json، وطبعه مع البديل. لا يمنع التسليم قبل أن يعتمد
صاحب القرار القائمة صريحًا (حالة `proposed` ⇒ تحذير · حالة `approved` ⇒ مانع).

الاستخدام: python3 validators/check_vocabulary.py --md reports/2026-10-23-sectioned.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
VOCAB = B / "appendices" / "simplified-vocabulary.json"

# ك-591: مطابقة على حدود الكلمة العربية بعد إسقاط التشكيل والتطويل.
# لا تُطابق «سند» داخل «تُسند»، ولا تُعتبر لاحقة/سابقة كلمة قائمة بذاتها.
_AR_LETTER = "\u0621-\u064a\u0671-\u06d3"
_TASHKEEL = "\u064b-\u0652\u0670\u0640\u06d6-\u06dc\u0640"


def _strip_tashkeel(value: str) -> str:
    import re as _re
    return _re.sub(f"[{_TASHKEEL}]", "", value or "")


def _word_hit(hard: str, text: str) -> bool:
    import re as _re
    hard_n = _strip_tashkeel(hard).strip()
    if not hard_n:
        return False
    pattern = f"(?<![{_AR_LETTER}]){_re.escape(hard_n)}(?![{_AR_LETTER}])"
    return _re.search(pattern, _strip_tashkeel(text)) is not None


def _alternative(it: dict) -> str:
    """البديل من السجل الحاكم: alternative/easy/simple أو الحقل المعتمد plain."""
    easy = it.get("alternative") or it.get("easy") or it.get("simple")
    if easy:
        return str(easy)
    plain = it.get("plain")
    if isinstance(plain, list):
        return "؛ ".join(str(x) for x in plain if str(x).strip())
    return str(plain or "")


def entries() -> tuple[list[dict], str]:
    if not VOCAB.exists():
        return [], "missing"
    d = json.loads(VOCAB.read_text(encoding="utf-8"))
    items = d.get("items") or d.get("entries") or d.get("terms") or []
    status = "approved" if str(d.get("status")) in ("canonical", "approved") else str(d.get("status") or "proposed")
    return items, status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    a = ap.parse_args()
    p = Path(a.md)
    if not p.exists():
        print(f"  ✘ لا نص تقرير: {p}")
        return 2
    text = p.read_text(encoding="utf-8")
    items, status = entries()
    if not items:
        print("  · لا قائمة مفردات مبسطة بعد — لا فحص")
        return 0

    hits: list[tuple[str, str]] = []
    for it in items:
        hard = it.get("as_written") or it.get("term") or it.get("hard") or ""
        easy = _alternative(it)
        if hard and _word_hit(hard, text):
            hits.append((hard, easy))

    if not hits:
        print(f"  ✓ لا لفظ صعب من القائمة المبسطة في المتن ({len(items)} بندًا · الحالة {status})")
        return 0

    for hard, easy in hits:
        print(f"  • «{hard}» → البديل اليومي: «{easy}»")
    if status == "approved":
        print(f"النتيجة: {len(hits)} لفظًا يحتاج تبديلًا — مانع (القائمة معتمدة)")
        return 2
    print(f"النتيجة: {len(hits)} لفظًا يحتاج تبديلًا — تنبيهي (القائمة لم تُعتمد بعد)")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)