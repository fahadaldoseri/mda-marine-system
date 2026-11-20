#!/usr/bin/env python3
"""قاعدة العدد في قسم «حالة المصادر والإفصاح» (ملاحظة الاختبار الحي، 20 نوفمبر 2026).

الخلل المقيس: «تعذّرت 1 تغذية من أصل 60» و«تعذّرت 5 تغذية»، و«للمصدرين» مهما كان العدد.
القاعدة: الرقم يبقى مكتوبًا (تماثل الأرقام مع الإنجليزية)، والمعدود يوافق العدد، ولكل سطر مقابل إنجليزي.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
SITE = Path(os.environ.get("SITE_DIR") or B.parent / "site")
sys.path.insert(0, str(B / "tools"))
sys.path.insert(0, str(SITE / "generator"))
import source_counts  # noqa: E402
import i18n_en  # noqa: E402

FAILS = []


def expect(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAILS.append(msg)


def section(failed, checked, manual=(), attempts=()):
    with tempfile.TemporaryDirectory() as d:
        old = source_counts.B
        source_counts.B = Path(d)
        (Path(d) / "feeds").mkdir()
        (Path(d) / "feeds" / "feeds-2030-01-01.status.json").write_text(json.dumps(
            {"items": 120, "manual_reference": list(manual),
             "failed_attempts": [{"num": n} for n in attempts]}), encoding="utf-8")
        try:
            return source_counts.sources_state_section("2030-01-01", {"checked": checked, "failed": failed})
        finally:
            source_counts.B = old


def lines(text):
    return [ln for ln in text.split("\n\n")[1:] if ln.strip()]


def main() -> int:
    bad = re.compile(r"تعذّرت\s+\d+\s+تغذية|(?<!\d)([3-9]|10)\s+تغذية\b|للمصدرين\s+\d+\s+—\s+العدد\s+(?!2\b)")
    cases = [(1, 60, ("7",), ("3",)), (2, 60, ("7", "8"), ("3", "4")), (5, 60, ("7", "8", "9"), ("3", "4", "9")),
             (11, 60, (), ()), (4, 5, (), ())]
    for failed, checked, manual, attempts in cases:
        t = section(failed, checked, manual, attempts)
        expect(not bad.search(t), f"تعذّر {failed} من {checked}: لا مخالفة لقاعدة العدد")
        expect(f"تعذّرت {failed} من أصل {checked} " in t, f"الرقمان {failed} و{checked} مكتوبان (تماثل الأرقام)")
        for ln in lines(t):
            expect(i18n_en.localize_patterns(ln.strip()) is not None, f"مقابل إنجليزي: {ln.strip()[:60]}")
    t = section(1, 60, ("7",), ("3",))
    expect("للمصدر 7 — العدد 1." in t and "مسار المصدر 3 " in t, "المفرد: «للمصدر» و«مسار المصدر»")
    t = section(5, 5)
    expect("فُحصت 5 تغذيات من 5 تغذيات." in t and "من أصل 5 تغذيات." in t, "3–10 جمع: «تغذيات»")
    t = section(5, 60, ("7", "8", "9"), ("3", "4", "9"))
    expect("للمصادر 7، 8، 9 — العدد 3." in t and "مسارات المصادر 3، 4، 9 " in t, "فوق الاثنين: «للمصادر» و«مسارات»")
    print(f"الحصيلة: فشل {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
