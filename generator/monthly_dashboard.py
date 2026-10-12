#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
لوحة المؤشرات الشهرية (التوصية إ5) — تُبنى من دفتر الأحداث التراكمي بلا استنتاج.

الاستخدام:
  python3 monthly_dashboard.py <دفتر الأحداث.json> <مخرجات.html> [عنوان]

المبادئ: كل رقم قابل للتتبع إلى سجل في الدفتر، ولا يُحسب مؤشر لا وجود له في البيانات.
"""

import html
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

AREA_KEYS = ["مضيق هرمز", "خليج عُمان", "الخليج العربي", "بحر العرب", "البحر الأحمر", "باب المندب", "خليج عدن"]
MONTHS_AR = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
             7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}


def esc(t):
    return html.escape(str(t or ""), quote=True)


def area_of(location):
    for k in AREA_KEYS:
        if k in location:
            return k
    return "مواقع أخرى"


def build(ledger_path, out_path, title):
    d = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    events = d.get("events") or []
    per_month = Counter()
    per_area = Counter()
    per_class = Counter()
    per_area_month = defaultdict(Counter)
    conf = Counter()
    for e in events:
        ds = str(e.get("date_start") or "")[:7]
        if not ds:
            continue
        a = area_of(str(e.get("location") or ""))
        per_month[ds] += 1
        per_area[a] += 1
        per_class[str(e.get("classification") or "غير مصنف")] += 1
        per_area_month[ds][a] += 1
        lvl = str(e.get("confidence_level") or "غير محدد")
        conf[lvl] += 1

    total = len(events)
    months = sorted(per_month)
    mx = max(per_month.values()) if per_month else 1

    rows_month = "".join(
        f'<div class="row"><span class="lbl bidi">{m}</span>'
        f'<span class="bar"><i style="width:{per_month[m]/mx*100:.1f}%"></i></span>'
        f'<span class="num bidi">{per_month[m]}</span></div>'
        for m in months
    )
    mx_area = max(per_area.values()) if per_area else 1
    rows_area = "".join(
        f'<div class="row"><span class="lbl">{esc(a)}</span>'
        f'<span class="bar alt"><i style="width:{c/mx_area*100:.1f}%"></i></span>'
        f'<span class="num bidi">{c}</span></div>'
        for a, c in per_area.most_common()
    )
    rows_class = "".join(
        f'<tr><td>{esc(k)}</td><td class="num bidi">{v}</td></tr>' for k, v in per_class.most_common()
    )
    rows_conf = "".join(
        f'<tr><td>{esc(k)}</td><td class="num bidi">{v}</td></tr>' for k, v in conf.most_common()
    )

    html_out = f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>
:root{{--bg:#050a12;--panel:#0c1626;--line:#1d2e4a;--ink:#e9f0f9;--ink2:#b9c8dc;--muted:#7e93ab;--accent:#22c3b6}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif;line-height:1.9}}
.wrap{{max-width:980px;margin:0 auto;padding:38px 20px 70px}}
h1{{font-size:26px;margin:0 0 6px}}h2{{font-size:18px;color:var(--accent);margin:30px 0 12px}}
p.lede{{color:var(--muted);margin:0 0 20px;font-size:14px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0}}
.k{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}}
.k b{{display:block;font-size:24px;font-family:"IBM Plex Mono",monospace}}
.k span{{color:var(--muted);font-size:13px}}
.row{{display:grid;grid-template-columns:150px 1fr 54px;gap:12px;align-items:center;margin:8px 0}}
.lbl{{font-size:13.5px;color:var(--ink2)}}
.bar{{height:9px;background:#101d31;border-radius:99px;overflow:hidden}}
.bar i{{display:block;height:100%;background:var(--accent)}}
.bar.alt i{{background:#4d9dff}}
.num{{font-family:"IBM Plex Mono",monospace;font-size:13px;text-align:end}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
th,td{{padding:9px 12px;border-bottom:1px solid var(--line);font-size:14px;text-align:start}}
th{{background:#0f1d33;color:var(--ink2);font-weight:600}}
td.num{{text-align:end;font-family:"IBM Plex Mono",monospace}}
.foot{{color:var(--muted);font-size:12.5px;margin-top:26px;border-top:1px solid var(--line);padding-top:14px}}
</style></head><body><div class="wrap">
<h1>{esc(title)}</h1>
<p class="lede">لوحة مبنية من دفتر الأحداث التراكمي: {len(months)} شهرًا، {total} سجلًا. لا تُقرأ الأعداد كهجمات مؤكدة.</p>
<div class="kpis">
<div class="k"><b class="bidi">{total}</b><span>إجمالي السجلات</span></div>
<div class="k"><b class="bidi">{len(months)}</b><span>الأشهر المغطاة</span></div>
<div class="k"><b class="bidi">{per_area.get("مضيق هرمز",0)}</b><span>سجلات مضيق هرمز</span></div>
<div class="k"><b class="bidi">{len(per_class)}</b><span>أنواع تصنيف</span></div>
</div>
<h2>السجلات بحسب الشهر</h2>{rows_month}
<h2>التوزيع الجغرافي</h2>{rows_area}
<h2>التصنيف</h2><table><thead><tr><th>التصنيف</th><th>العدد</th></tr></thead><tbody>{rows_class}</tbody></table>
<h2>درجة الثقة المسجلة</h2><table><thead><tr><th>المستوى</th><th>العدد</th></tr></thead><tbody>{rows_conf}</tbody></table>
<div class="foot">المصدر: {esc(Path(ledger_path).name)} — أُنشئت في {date.today().isoformat()}.</div>
</div></body></html>"""
    Path(out_path).write_text(html_out, encoding="utf-8")
    return {"months": len(months), "events": total, "top_area": per_area.most_common(1)[:1]}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("الاستخدام: monthly_dashboard.py <ledger.json> <out.html> [title]")
        raise SystemExit(2)
    title = sys.argv[3] if len(sys.argv) > 3 else "لوحة المؤشرات الشهرية — أمن الملاحة"
    info = build(sys.argv[1], sys.argv[2], title)
    print("dashboard:", info)