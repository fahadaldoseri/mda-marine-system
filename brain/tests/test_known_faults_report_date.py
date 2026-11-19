#!/usr/bin/env python3
"""الاستثناء يُختار بتاريخ التقرير لا بتاريخ التشغيل (19 نوفمبر 2026).

كان known_faults يقيس الصلاحية بتاريخ اليوم، فإعادة توليد تقرير 18 نوفمبر يوم 19
غيّرت سطر إفصاحه (فشل المعجم المشتق وك-617). موجب: تقرير 18 يأخذ بند يوم 18 أيًّا
كان يوم التشغيل. سالبان: تقرير 26 لا يأخذ بند 19–25 المنتهي، وتقرير 19 لا يأخذ بند 18.
"""
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(B / "tools"))
from known_faults import classify_component, degraded_components  # noqa: E402

mark = json.loads((B / "logs" / "pipeline-2026-11-18.json").read_text(encoding="utf-8"))
feeds = [c for c in degraded_components(mark) if c[0] == "feeds"]
assert feeds, "لا مكوّن تغذيات متدهور في علامة 18 نوفمبر"
comp, st, text, items = feeds[0]


def entry(day):
    r = classify_component(comp, st, text, items, today=day)
    return r["allowed"], r["entry_id"]


fails = 0
for day, want in (("2026-11-18", (True, "owner-declared-2026-11-18-feeds")),
                  ("2026-11-19", (True, "owner-declared-2026-11-19-25-feeds")),
                  ("2026-11-25", (True, "owner-declared-2026-11-19-25-feeds"))):
    got = entry(day)
    ok = got == want
    fails += not ok
    print(("  ✔" if ok else "  ✘"), day, got)
got = entry("2026-11-26")
ok = got[0] is False
fails += not ok
print(("  ✔" if ok else "  ✘"), "2026-11-26 (بعد انتهاء البند) يمنع", got)
sys.exit(1 if fails else 0)
