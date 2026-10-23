#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة فصل فضاءات الرموز: MN- للوقائع · EST- للتقديرات — ومنع إعادة الإسناد.

القاعدة الملزمة (19 أكتوبر 2026):
1. كل رمز `EST-YYYY-MM-DD-NN` في نص الإصدار أو واجهته **مسجَّل** في
   `appendices/estimate-code-map.json`، وإلا فمخالفة مانعة.
2. كل رمز `MN-YYYY-MM-DD-NN` في نص الإصدار **موجود** في
   `appendices/event-code-map.json` أو في `event_keys` بواجهة الإصدار، وإلا فمخالفة مانعة.
3. الفضاء الصحيح: رمز EST- داخل «الوقائع الجديدة» مخالفة مانعة (التقدير ليس واقعة)،
   ورمز MN- كامل داخل أقسام التحليل والاحتمالات والخلاصة تنبيه (يُستعمل الرمز المختصر).
4. لا إعادة إسناد: إن ظهر تعارض في خريطة الرموز (`code_conflicts`) أو ارتبط رمز واحد
   بأكثر من معنى في سجل الدمج، فمخالفة مانعة.

الاستخدام:
    python3 validators/check_code_spaces.py --date 2026-10-19
السلّم: 0 نجاح · 1 تنبيهات · 2 مخالفة مانعة
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parents[1]
EST_RE = re.compile(r"EST-\d{4}-\d{2}-\d{2}-\d{2}")
MN_RE = re.compile(r"MN-\d{4}-\d{2}-\d{2}-\d{2}")

FACTS_HEAD = "الوقائع الجديدة"
ANALYSIS_HEADS = ("التحليل الاستخباري", "الاحتمالات ونسبة الحوادث إلى جهات", "الاحتمالات والإسناد", "الخلاصة", "مؤشرات الموقف")


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def sections(md: str) -> dict[str, str]:
    out: dict[str, list[str]] = {}
    cur = "المقدمة"
    for line in md.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out.setdefault(cur, [])
        out.setdefault(cur, []).append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--meta", default=None)
    a = ap.parse_args()

    report = Path(a.report) if a.report else B / "reports" / f"{a.date}-sectioned.md"
    meta = Path(a.meta) if a.meta else B / "web" / "meta" / f"{a.date}.json"
    est_map = load(B / "appendices" / "estimate-code-map.json", {})
    ev_map = load(B / "appendices" / "event-code-map.json", {})
    ledger = load(B / "cumulative-2026" / "event-ledger-master.json", {})
    m = load(meta, {})

    est_known = set((est_map.get("codes") or {}).keys())
    mn_known = set((ev_map.get("codes") or {}).keys()) | {k.get("code") for k in (m.get("event_keys") or [])}

    if not report.exists():
        print(f"النتيجة: مصدر الإصدار غير موجود — {report}")
        return 2
    md = report.read_text(encoding="utf-8")
    secs = sections(md)

    blocks, warns, lines = [], [], []
    est_in_text = sorted(set(EST_RE.findall(md)))
    mn_in_text = sorted(set(MN_RE.findall(md)))

    unknown_est = [c for c in est_in_text if c not in est_known]
    if unknown_est:
        blocks.append(f"رموز تقديرات غير مسجَّلة في estimate-code-map: {unknown_est}")
    unknown_mn = [c for c in mn_in_text if c not in mn_known]
    if unknown_mn:
        blocks.append(f"رموز وقائع غير مسجَّلة في event-code-map أو event_keys: {unknown_mn}")

    for title, body in secs.items():
        if title == FACTS_HEAD and EST_RE.search(body):
            blocks.append(f"رمز تقدير EST- داخل «{FACTS_HEAD}» — التقدير ليس واقعة: {sorted(set(EST_RE.findall(body)))}")
        if any(title.startswith(h) for h in ANALYSIS_HEADS) and MN_RE.search(body):
            warns.append(f"رمز واقعة كامل MN- داخل «{title}» — يُستعمل الرمز المختصر: {sorted(set(MN_RE.findall(body)))}")

    conflicts = ev_map.get("code_conflicts") or []
    if conflicts:
        blocks.append(f"تعارض في خريطة الرموز (إعادة إسناد محتملة): {conflicts[:3]}")
    unmapped = [u for u in (ev_map.get("unmapped") or []) if isinstance(u, str)]
    if unmapped:
        warns.append(f"رموز بلا ربط في الخريطة: {unmapped[:3]}")
    if len(ledger.get("records", []) or []) and not ledger.get("events"):
        blocks.append("الدفتر التراكمي بلا قائمة سجلات موحّدة (events)")

    print(f"=== بوابة فصل فضاءات الرموز — {a.date} ===")
    print(f"  EST- في النص: {len(est_in_text)} · مسجَّل: {len(est_known)}")
    print(f"  MN- في النص: {len(mn_in_text)} · مسجَّل: {len(mn_known)}")
    for b in blocks:
        print(f"  ✘ {b}")
    for w in warns:
        print(f"  ◐ {w}")
    if blocks:
        print("  النتيجة: مخالفة مانعة — لا تسليم حتى الإصلاح.")
        return 2
    if warns:
        print("  النتيجة: اجتياز مع تنبيهات.")
        return 1
    print("  النتيجة: اجتياز — الفضاءان مفصولان ولا رمز بلا سجل.")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)