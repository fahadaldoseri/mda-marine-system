#!/usr/bin/env python3
"""يمنح القناة الأساسية مهلة انتشار محدودة قبل الحكم بالفشل والانتقال للبديلة.

السبب: بناء Cloudflare Pages يستغرق عشرات الثواني بعد الدفع، فكان التحقق الفوري
يفشل ويسجّل القناة البديلة «الناجحة» — وصفٌ يخالف واقع القناة الأساسية التي تخدم
البناء نفسه بعد لحظات.
"""
from __future__ import annotations

import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "publish_channels.py"

OLD = '''            url = cloudflare_report_url(date, base)
            live = verify_live_url(url, date, min_bytes=PAGES_MIN_BYTES, expected_sha256=local_sha)
            record = build_publish_record('''

NEW = '''            url = cloudflare_report_url(date, base)
            live = verify_live_url(url, date, min_bytes=PAGES_MIN_BYTES, expected_sha256=local_sha)
            waited = 0
            for delay in PAGES_PROPAGATION_DELAYS:
                if live.get("ok"):
                    break
                time.sleep(delay)
                waited += delay
                live = verify_live_url(url, date, min_bytes=PAGES_MIN_BYTES, expected_sha256=local_sha)
            if waited:
                live["propagation_wait_seconds"] = waited
            record = build_publish_record('''

CONST_ANCHOR = "PAGES_MIN_BYTES"
CONST_LINE = (
    "PAGES_PROPAGATION_DELAYS = (15, 20, 25, 30, 40, 50)  "
    "# مهلة انتشار بناء القناة الأساسية قبل الحكم بالفشل (ثوانٍ)\n"
)


def main() -> int:
    t = P.read_text(encoding="utf-8")
    changed = False
    if "PAGES_PROPAGATION_DELAYS" not in t:
        lines = t.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(CONST_ANCHOR):
                lines.insert(i, CONST_LINE)
                changed = True
                break
        t = "".join(lines)
    if "import time" not in t:
        t = t.replace("import subprocess", "import subprocess\nimport time", 1)
        changed = True
    if "propagation_wait_seconds" not in t:
        if OLD not in t:
            print("   ✘ لم يُعثر على موضع التحقق الأساسي")
            return 2
        t = t.replace(OLD, NEW, 1)
        changed = True
    P.write_text(t, encoding="utf-8")
    print("   ✔ تغيّر الملف" if changed else "   = لا تغيير (مطبَّق مسبقًا)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())