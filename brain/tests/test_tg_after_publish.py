#!/usr/bin/env python3
"""رسالة تلغرام اليومية لا تسبق النشر (قرار المالك بفتح D030، 19 نوفمبر 2026).

- في `tools/publish_site.sh --telegram` يقع فحص «رابط التقرير يعيد 200» قبل أول استدعاء لـtelegram_send.py.
- D030 مفعّلة، وD031 (إعادة الإرسال) وD033 (تنبيه الوصول) تبقيان معطلتين.
"""
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]


def main() -> int:
    fails = []
    sh = (B / "tools" / "publish_site.sh").read_text(encoding="utf-8")
    block = sh[sh.index('if [ "$MODE" = telegram ]; then\n  OUT='):]
    live = block.find("report-not-live")
    send = block.find("telegram_send.py")
    if live < 0:
        fails.append("لا فحص حي لرابط التقرير قبل الإرسال")
    elif send < 0 or live > send:
        fails.append("فحص الرابط الحي يأتي بعد الإرسال")
    steps = {s["id"]: s for s in json.loads((B / "runbook" / "runbook.json").read_text(encoding="utf-8"))["steps"]}
    if steps["D030"].get("disabled"):
        fails.append("D030 ما زالت معطلة")
    for sid in ("D031", "D033"):
        if not steps[sid].get("disabled"):
            fails.append(f"{sid} فُعّلت بلا أمر من المالك")
    for f in fails:
        print("✘", f)
    if not fails:
        print("✔ الرسالة لا تُرسل قبل أن يعيد رابط التقرير 200، وD030 وحدها مفعّلة")
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
