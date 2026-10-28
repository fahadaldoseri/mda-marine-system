#!/usr/bin/env python3
"""فهرس التقارير: ما في المستودع وما يجب أن يكون في الأرشيف الخاص على جهاز المالك (appendices/reports-archive.json).

يولّد docs/reports-index.md ليعرف أي محرك ذكاء أين يجد أي تقرير سابق. لا يحذف شيئًا:
`--plan` يطبع ما تجاوز مدة الاحتفاظ ويصلح للنقل إلى الجهاز (النقل نفسه بيد المالك).
الاستعمال: python3 tools/reports_index.py [--today YYYY-MM-DD] [--plan]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)


def scan():
    days = {}
    for p in sorted((B / "reports").glob("*-sectioned.md")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-sectioned\.md$", p.name)
        if m:
            days.setdefault(m.group(1), {})["md"] = True
    for p in (B / "web" / "meta").glob("*.json") if (B / "web" / "meta").is_dir() else []:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", p.name):
            days.setdefault(p.stem, {})["meta"] = True
    dd = B / "reports" / "docx"
    for p in dd.glob("*.docx") if dd.is_dir() else []:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
        if m:
            days.setdefault(m.group(1), {})["docx"] = True
    for p in dd.glob("*.pdf") if dd.is_dir() else []:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
        if m:
            days.setdefault(m.group(1), {})["pdf"] = True
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today")
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()
    cfg = json.loads((B / "appendices" / "reports-archive.json").read_text(encoding="utf-8"))
    today = dt.date.fromisoformat(a.today) if a.today else dt.datetime.now(dt.timezone.utc).date()
    keep = int(cfg["retain_days_in_repo"])
    days = scan()
    old = sorted(d for d in days if (today - dt.date.fromisoformat(d)).days > keep)
    if a.plan:
        print(f"تجاوزت {keep} يومًا ({len(old)}): " + (" ".join(old) if old else "لا شيء"))
        return 0
    dev = cfg["device_archive"]
    L = ["# فهرس التقارير", "",
         f"> مولَّد بـ`tools/reports_index.py` بتاريخ {today}. لا يُعدَّل يدويًا.", "",
         f"- **في المستودع:** آخر {keep} يومًا.",
         f"- **الأرشيف الخاص (جهاز المالك):** {dev.get('path') or dev.get('status', 'غير محدد بعد')}",
         f"- **تسمية الملفات:** {dev.get('naming', '')}", "",
         "| التاريخ | النص | الواجهة | PDF | Word | الموضع |", "|---|---|---|---|---|---|"]
    for d in sorted(days, reverse=True):
        x = days[d]
        where = "المستودع" if d not in old else "الأرشيف الخاص (يجب نقله)"
        L.append(f"| {d} | {'✔' if x.get('md') else '—'} | {'✔' if x.get('meta') else '—'} | {'✔' if x.get('pdf') else '—'} | {'✔' if x.get('docx') else '—'} | {where} |")
    out = B / "docs" / "reports-index.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"✔ {out} — {len(days)} يومًا، منها {len(old)} تتجاوز مدة الاحتفاظ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
