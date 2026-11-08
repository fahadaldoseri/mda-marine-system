#!/usr/bin/env python3
"""يسدّ ثغرة حوكمة: القناة البديلة كانت تنشر بلا فحص حكم البوابات.

- publish_fallback.sh: يفحص gates-status وgate_verdict قبل أي دفع (فشل مغلق).
- خطوة D010: تجديد البوابات المتقادمة قبل النشر بدل السقوط الصامت إلى البديلة.
"""
from __future__ import annotations

import json
import pathlib

B = pathlib.Path(__file__).resolve().parent.parent.parent
FALLBACK = B / "tools" / "publish_fallback.sh"
MANIFEST = B / "runbook" / "runbook.json"

ANCHOR = '''rm -rf "$WORK/repo" 2>/dev/null || true'''

GATE_BLOCK = '''echo "── بوابة المحرّك قبل fallback ($D) ──"
python3 "$B/tools/runbook.py" gates-status --date "$D" --root "$B" || {
  record 2 failed "" "" "engine gates incomplete"
  echo "✘ fallback مرفوض: سجل المحرّك لا يُظهر اكتمال البوابات."
  exit 2; }
python3 "$B/tools/gate_verdict.py" --date "$D" --root "$B" --delivery-step D010 \\
  --json "$B/logs/gate-verdict-$D.json" || {
  record 2 failed "" "" "blocking gate verdict"
  echo "✘ fallback مرفوض: بوابة بحكم مانع — لا نشر بديل."
  exit 2; }

rm -rf "$WORK/repo" 2>/dev/null || true'''

D010_CMD = (
    'B="$PWD"; export B SITE; '
    'python3 "$B/tools/refresh_stale_gates.py" --date {date} --root "$B" || '
    '{ echo \'✘ رُفض النشر: بوابة متقادمة لم تُجدَّد\'; exit 2; }; '
    'python3 tools/publish_channels.py publish --date {date} --root "$B"; rc=$?; exit $rc'
)


def main() -> int:
    t = FALLBACK.read_text(encoding="utf-8")
    if "gate_verdict.py" in t:
        print("   = سكربت البديل محمي مسبقًا")
    else:
        if ANCHOR not in t:
            print("   ✘ لم يُعثر على موضع الإدراج في سكربت البديل")
            return 2
        FALLBACK.write_text(t.replace(ANCHOR, GATE_BLOCK, 1), encoding="utf-8")
        print("   ✔ سكربت البديل يفحص حكم البوابات قبل الدفع")

    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for s in d.get("steps", []):
        if s.get("id") == "D010":
            s["command"] = ["bash", "-lc", D010_CMD]
            MANIFEST.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("   ✔ خطوة D010 تجدّد البوابات المتقادمة قبل النشر")
            return 0
    print("   ✘ لم تُوجد خطوة D010")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())