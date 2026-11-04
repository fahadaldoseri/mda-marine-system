#!/usr/bin/env python3
"""اختبار محلي لتصنيف نتيجة المسار البديل: 403 فشل و200 المحتوى الحقيقي نجاح."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from source_alternatives import classify_probe  # noqa: E402


def main() -> int:
    good = classify_probe(200, b"<rss><item><title>official item</title></item></rss>")
    assert good["result"] == "نجح" and good["content_chars"] > 0
    blocked = classify_probe(403, b"Attention Required")
    assert blocked["result"] == "فشل" and "403" in blocked["reason"]
    challenge = classify_probe(200, b"human verification required")
    assert challenge["result"] == "فشل"
    print("  ✔ تصنيف HTTP 200 مع مادة حقيقية نجاح")
    print("  ✔ HTTP 403 وصفحة التحقق فشل مفصح عنه")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
