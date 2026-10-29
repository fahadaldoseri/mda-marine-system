#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد صفحة التقرير الصباحي (نسخة الويب / HTTPS) — Marine News Brain.

الاستخدام:
  python3 build_report.py --md <تقرير.md> --out <صفحة.html> --meta <meta.json>

المبدأ: المصدر الوحيد للحقيقة هو ملف Markdown + ملف meta. لا يُعدَّل الناتج يدويًا.

الإصلاحات المدمجة بعد مراجعة التصميم والمراجعة التقنية:
- ألوان الطباعة تُعاد تعريفها كاملة (لا وراثة ألوان النمط الداكن).
- المحتوى مرئي افتراضيًا؛ الحركة تحسين اختياري عند توفر JavaScript.
- أعمدة المخطط بأعراض ثابتة واتجاه معزول (LTR isolate) بلا التفاف.
- عزل كل قيمة لاتينية/رقمية مركبة بـ bdi لمنع اضطراب الاتجاه في العربية.
- روابط المصادر صارت قابلة للنقر من تعريفات Markdown.
- منع التجاوز الأفقي على الجوال، وإصلاح تباين النمط النهاري.
- هروب صفات HTML بشكل صحيح، وفحوص مدخلات تفشل برسالة واضحة.
- تسلسل عناوين صحيح، scope للأعمدة، aria-hidden للأيقونات، وحالة تركيز ظاهرة.
- قواعد كسر صفحات صحيحة للجداول والبطاقات، وأحجام طباعة لا تقل عن 10.5pt.
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone

# الاسم المعتمد للتقرير اليومي
DAILY_TITLE = "التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة"
from pathlib import Path


class BuildError(Exception):
    pass


import blocks as BLK
import codes  # سياسة عرض رموز الأحداث (كامل مرة واحدة، ومختصر مدموج برقم البلاغ)
import screen_layer as SCR  # طبقة الشاشة: القرار فوق الطيّ، للشاشة فقط (لا تمسّ الطباعة)


# ----------------------------------------------------------------------------
# نظام التصميم — «غرفة عمليات بحرية»: داكن، فيروزي واحد، بلا زخرفة
# ----------------------------------------------------------------------------
DESIGN_TOKENS = """
  --bg:#050a12;
  --bg-2:#08101c;
  --panel:#0c1626;
  --panel-2:#101d31;
  --panel-3:#152441;
  --line:#1d2e4a;
  --line-2:#28405f;
  --ink:#e9f0f9;
  --ink-2:#c3d2e6;
  --muted:#8ba0bd;
  --faint:#5f7899;
  --accent:#22c3b6;
  --accent-ink:#04120f;
  --info:#4d9dff;
  --danger:#ff5d52;
  --warn:#ffb02e;
  --ok:#33d07a;
  --shadow-2:0 10px 30px -14px rgba(0,0,0,.7);
  --radius:12px;
  --radius-sm:8px;
  --map-sea:#06111f;
  --map-land:#22375a;
  --map-coast:#5b7ba6;
  --map-border:#33507a;
  --map-grid:#16273f;
  --map-grid-lbl:#54749c;
  --map-label:#dbe6f4;
  --map-country:#7f97b8;
  --map-sea-label:#4f6f96;
  --map-strait:#ffd9d5;
"""
DESIGN_TOKENS = ":root{" + DESIGN_TOKENS + "}"

FONT_LINK = "/assets/fonts/fonts.css"

SECTION_ICONS = {
    "الخلاصة": "flag",
    "الوقائع الجديدة": "alert",
    "سجل الأحداث": "alert",
    "التحذيرات والنشرات الرسمية": "broadcast",
    "سجل IMO": "ledger",
    "مؤشرات الموقف": "gauge",
    "التوزيع الجغرافي للوقائع": "map",
    "خريطة الوقائع": "map",
    "الحركة الملاحية والتكدس": "route",
    "مستوى التهديد": "shield",
    "الاحتمالات ونسبة الحوادث إلى جهات": "scale",
    "قراءة الموقف وتحليل المؤشرات": "intel",
    "التوجيهات التشغيلية": "gear",
    "الخلفية القائمة": "history",
    "ما لم يُحسم": "gap",
    "المصادر والمراجع": "source",
}

SECTION_HINTS = {
    "ما تغيّر منذ التقرير السابق": "ما استُجد، وما تغيّر تصنيفه، وما أُغلق.",
    "الخلاصة": "الموقف ومستوى التهديد والإجراء المقترح في ثلاثة أسطر.",
    "التوزيع الجغرافي للوقائع": "أين تركّزت الوقائع، وحصيلة IMO حسب القطاعات.",
    "مؤشرات الموقف": "الأرقام، ومقارنتها بتقرير أمس، وحدود كل رقم.",
    "مستوى التهديد": "التقييم الرسمي، والتقدير التحليلي، وحدود الثقة.",
    "التوجيهات التشغيلية": "ما يُنفَّذ قبل العبور والرسو وأثناء الحادث.",
    "الوقائع الجديدة": "الوقائع الأمنية الجديدة خلال فترة التغطية، مفصولًا عن الخلفية.",
    "سجل الأحداث": "الوقائع الأمنية الجديدة خلال فترة التغطية، مرتّبة بالرمز والتوقيت.",
    "التحذيرات والنشرات الرسمية": "حالة الجهات الرسمية خلال فترة التقرير.",
    "سجل IMO": "الحصيلة الرسمية التراكمية، وآخر إدخال ظاهر.",
    "قراءة الموقف وتحليل المؤشرات": "وصف النمط والافتراضات والفرضيات ومؤشرات التحذير المبكر.",
    "الاحتمالات ونسبة الحوادث إلى جهات": "من قد يكون مسؤولًا، بلا جزم وبلا نسبة بلا دليل.",
    "الحركة الملاحية والتكدس": "حركة المضيق والرسو من مصادر معلنة فقط.",
    "ما لم يُحسم": "ما لا يزال مجهولًا، وما يلزم متابعته في التقرير التالي.",
    "الخلفية القائمة": "وقائع أقدم لا يزال أثرها مؤثرًا على التشغيل.",
    "المصادر والمراجع": "حالة المصادر المفحوصة، وروابط المراجع المستشهد بها.",
}
# أقسام تُمنح تمييزًا بصريًا محسوبًا: خلاصة القرار + الإجراء المطلوب
PRIORITY_SECTIONS = ("الخلاصة", "التوجيهات التشغيلية")

# ── إخفاء أقسام من إصدار التقرير (الويب والطباعة معًا) — قرار المالك 2026-10-21 ──
# القاعدة: الإخفاء يُنفَّذ هنا مرة واحدة فيخدم الويب وPDF وWord، ولا تُحذف البيانات
# من ملف الواجهة ولا من دفتر الأحداث (تبقى للأرشيف والفحوص).
HIDDEN_SECTIONS = set()  # تُقرأ من سياسة Brain وحدها (ك-86/ك-91) — لا قائمة مزدوجة
HIDDEN_BLOCKS = set()  # تُقرأ من السياسة
ADDITIONS_SECTIONS = []  # أقسام صفحة «إضافات» (قرار المالك 2026-10-28) بترتيبها المعتمد
ADDITIONS_FROM = ""  # تاريخ سريان النقل؛ الإصدارات الأقدم في الأرشيف لا تتأثر


def load_section_policy(meta_path=None):
    """سياسة الأقسام من مصادرها الواحدة في Brain؛ تُنسخ إلى sources/ عند المزامنة."""
    global HIDDEN_SECTIONS, HIDDEN_BLOCKS, ADDITIONS_SECTIONS, ADDITIONS_FROM
    cands = []
    if meta_path:
        mp = Path(meta_path).resolve()
        ps = list(mp.parents)
        if len(ps) > 2:
            cands.append(ps[2] / "sources" / "report-sections-policy.json")
        if len(ps) > 1:
            cands.append(ps[1] / "appendices" / "report-sections-policy.json")
    cands.append(Path(__file__).resolve().parent.parent / "sources" / "report-sections-policy.json")
    for c in cands:
        try:
            if c.is_file():
                d = json.loads(c.read_text(encoding="utf-8"))
                HIDDEN_SECTIONS = set(d.get("hidden_sections") or [])
                HIDDEN_BLOCKS = set(d.get("hidden_blocks") or [])
                ADDITIONS_SECTIONS = list(d.get("additions_sections") or [])
                ADDITIONS_FROM = str(d.get("additions_effective_from") or "")
                print(f"سياسة الأقسام: {c} · محذوف {len(HIDDEN_SECTIONS)} · كتل {len(HIDDEN_BLOCKS)}",
                      file=sys.stderr)
                return c
        except Exception:
            continue
    return None


# _POLICY_LOADED_AT_IMPORT: تحميل السياسة عند الاستيراد، فلا يبقى أي افتراضي مزدوج
try:
    load_section_policy()
except Exception as _e:  # noqa: BLE001
    print(f"تعذّر تحميل سياسة الأقسام: {_e}", file=sys.stderr)


def _hidden(title: str) -> bool:
    return any(h in title for h in HIDDEN_SECTIONS)

INCIDENT_SECTION_KEYS = ("سجل الأحداث", "الوقائع الجديدة", "الوقائع", "الوقائع الأمنية")

ICON_PATHS = {
    "flag": "M4 3h9l-1.2 3H19v8h-8.2L9.6 11H6v9H4z",
    "alert": "M12 3l9 16H3zM12 8v6M12 16.4v1.2",
    "broadcast": "M12 10.5a2 2 0 100 4 2 2 0 000-4zM7.8 7.6a6.2 6.2 0 000 8.8M16.2 7.6a6.2 6.2 0 010 8.8M5 4.8a10 10 0 000 14.4M19 4.8a10 10 0 010 14.4",
    "ledger": "M5 3h11l3 3v15H5zM8 9h8M8 13h8M8 17h5",
    "gauge": "M12 20a8 8 0 110-16 8 8 0 010 16zM12 12l4-3",
    "map": "M9 4l6 2 5-2v14l-5 2-6-2-5 2V6zM9 4v14M15 6v14",
    "route": "M6 4v9a4 4 0 004 4h5M15 17l-2-2M15 17l-2 2M18 4a2 2 0 11-.001 4.001A2 2 0 0118 4z",
    "shield": "M12 3l7 3v6c0 4.4-2.9 7.6-7 9-4.1-1.4-7-4.6-7-9V6z",
    "scale": "M12 4v16M6 8h12M6 8l-3 6h6zM18 8l-3 6h6z",
    "intel": "M12 5c5 0 9 4 9 7s-4 7-9 7-9-4-9-7 4-7 9-7zM12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z",
    "gear": "M12 15.5a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM12 2l1.6 2.3 2.8-.4.5 2.7 2.6 1.2-1.1 2.6 1.1 2.6-2.6 1.2-.5 2.7-2.8-.4L12 22l-1.6-2.3-2.8.4-.5-2.7-2.6-1.2L5.6 13 4.5 10.4l2.6-1.2.5-2.7 2.8.4z",
    "history": "M12 7v5l3 2M3.5 12a8.5 8.5 0 1 0 2.6-6.1M3 4v4h4",
    "gap": "M4 12h5M15 12h5M12 4v5M12 15v5",
    "source": "M4 6h16M4 12h16M4 18h10",
}

LINK_RULE = """
/* ── تمييز الروابط داخل النص (WCAG 2.1 AA — 1.4.1) ──
   عطل ك-72: تساوي الخصوصية يُحسم بالترتيب، فالقاعدة تُركَّب آخر كل الأنماط لتفوز. */
.site-nav a,.sn-links a,.sn-foot a,.foot a,footer a,.glossary a,p a,li a,td a,
.src a,.src-note a,.cite-ref{text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px}
"""
STYLE = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-padding-top:74px}
body{
  margin:0;background:var(--bg);color:var(--ink);
  font-family:"IBM Plex Sans Arabic","Noto Kufi Arabic","Segoe UI","Tahoma",system-ui,sans-serif;
  font-size:16.5px;line-height:1.95;text-rendering:optimizeLegibility;
}
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(1100px 520px at 88% -12%, rgba(34,195,182,.09), transparent 60%),
    radial-gradient(900px 480px at 6% 4%, rgba(77,157,255,.06), transparent 62%);
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
section.doc p,section.doc li,.card p,.src,.foot,.notice,blockquote{overflow-wrap:anywhere}
a:focus-visible,.btn:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:4px}
.wrap{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:0 22px 90px}

/* عزل القيم اللاتينية والرقمية المركبة داخل سياق عربي */
bdi,.bidi{direction:ltr;unicode-bidi:isolate}
.k-v,.chip b,.cite-ref,.bar-row .bv,td.num,th.num{direction:ltr;unicode-bidi:isolate;white-space:nowrap}
.ev-code,.bidi.ev-code{direction:ltr;unicode-bidi:isolate;white-space:nowrap}  /* رمز الحدث لا يُكسر بين سطرين */
a.bidi{white-space:normal}
.eng{direction:ltr;unicode-bidi:plaintext;overflow-wrap:anywhere}

/* ---------- الشريط العلوي ---------- */
.topbar{
  position:sticky;top:0;z-index:30;backdrop-filter:blur(14px);
  background:linear-gradient(180deg,rgba(6,11,20,.95),rgba(6,11,20,.82));
  border-bottom:1px solid var(--line);
}
.topbar-inner{max-width:1180px;margin:0 auto;padding:11px 22px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:11px;min-width:0}
.brand-mark{
  width:34px;height:34px;border-radius:10px;flex:0 0 auto;display:grid;place-items:center;
  background:rgba(34,195,182,.10);border:1px solid var(--line-2);color:var(--accent)
}
.brand-mark svg{width:19px;height:19px}
.brand-title{font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:15px;line-height:1.4}
.brand-sub{font-size:12px;color:var(--muted);line-height:1.4}
.topbar-spacer{flex:1 1 auto}
.tb-meta{display:flex;gap:9px;align-items:center;flex-wrap:wrap}
.chip{
  font-size:12px;color:var(--ink-2);border:1px solid var(--line);
  background:var(--panel);border-radius:999px;padding:5px 11px
}
.chip b{color:var(--ink);font-weight:600}
.btn{
  font:inherit;font-size:12.5px;cursor:pointer;color:var(--ink);
  background:var(--panel-2);border:1px solid var(--line-2);border-radius:8px;
  padding:7px 13px;transition:background .18s ease,transform .18s ease
}
.btn:hover{background:var(--panel-3)}
.btn:active{transform:translateY(1px)}
.btn-primary{background:var(--accent);color:var(--accent-ink);border-color:transparent;font-weight:600}
.btn-primary:hover{background:#2ad4c6}

/* ---------- الترويسة ---------- */
.masthead{padding:34px 0 6px;display:flex;gap:22px;align-items:flex-end;flex-wrap:wrap}
.masthead h1{
  font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;
  font-size:clamp(26px,3.4vw,40px);line-height:1.3;margin:0 0 8px;
  flex:0 0 100%;width:100%;text-align:center
}
.masthead > div:not(.threat){flex:1 0 100%}
.masthead .lede{color:var(--ink-2);font-size:15px;max-width:none;margin:0}
.masthead-meta{display:flex;gap:9px;flex-wrap:wrap;margin-top:14px}
.threat{
  margin-inline-start:0;margin-inline-end:auto;text-align:center;border-radius:var(--radius);
  border:1px solid var(--line-2);background:var(--panel);padding:14px 20px;min-width:172px
}
.threat .lbl{font-size:12px;color:var(--muted)}
.threat .val{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:23px;line-height:1.45;margin-top:2px}
.threat.risk-high .val{color:var(--danger)}
.threat.risk-med .val{color:var(--warn)}
.threat.risk-low .val{color:var(--ok)}

/* ---------- شريط المؤشرات ---------- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0 8px}
.kpi{
  background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius);
  padding:15px 16px;position:relative;overflow:hidden
}
.kpi em{position:absolute;inset-inline-start:0;top:0;bottom:0;width:3px;background:var(--accent)}
.kpi.acc-info em{background:var(--info)}
.kpi.acc-warn em{background:var(--warn)}
.kpi.acc-danger em{background:var(--danger)}
.kpi.acc-ok em{background:var(--ok)}
.kpi .k-l{font-size:12.5px;color:var(--muted);line-height:1.6;min-height:2.6em}
.kpi .k-v{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:30px;line-height:1.25;margin-top:3px;font-variant-numeric:tabular-nums}
.kpi .k-n{font-size:12px;color:var(--muted);line-height:1.7;margin-top:4px}

.notice{
  display:flex;gap:12px;align-items:flex-start;margin:20px 0 6px;padding:13px 16px;
  border:1px solid var(--line);border-inline-start:3px solid var(--accent);
  border-radius:var(--radius-sm);background:rgba(34,195,182,.05);
  font-size:13.5px;color:var(--ink-2)
}
.notice svg{width:18px;height:18px;color:var(--accent);flex:0 0 auto;margin-top:5px}

/* ---------- الأقسام ---------- */
main{margin-top:30px;display:grid;gap:18px;min-width:0}
section.doc{
  background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px 24px 10px;min-width:0;max-width:100%;scroll-margin-top:74px
}
section.doc.pri{box-shadow:inset 0 2px 0 0 rgba(34,195,182,.55)}
section.doc > h2{
  font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:21px;line-height:1.5;
  margin:0 0 4px;display:flex;align-items:center;gap:11px
}
section.doc > h2 .ico{width:24px;height:24px;flex:0 0 auto;display:grid;place-items:center;color:var(--accent)}
section.doc > h2 .ico svg{width:18px;height:18px}
.h-rule{height:1px;background:var(--line);margin:8px 0 12px}
section.doc h3{
  font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:16.5px;
  margin:22px 0 6px;line-height:1.6;color:var(--ink)
}
section.doc p{margin:10px 0;color:var(--ink-2)}
section.doc strong{color:var(--ink);font-weight:600}
section.doc code{font-family:"IBM Plex Mono",monospace;font-size:.92em;color:var(--ink);background:var(--panel-3);padding:1px 5px;border-radius:4px}
ul,ol{margin:10px 0;padding-inline-start:22px;color:var(--ink-2)}
li{margin:7px 0}
section.doc ul ul{margin:6px 0;padding-inline-start:18px}
section.doc ul ul li{margin:4px 0;font-size:.96em;color:var(--ink-2)}
li::marker{color:var(--accent)}
blockquote{
  margin:16px 0;padding:12px 16px;border-inline-start:3px solid var(--accent);
  background:rgba(34,195,182,.055);border-radius:0 var(--radius-sm) var(--radius-sm) 0;
  color:var(--ink-2);font-size:15px
}
hr{border:0;border-top:1px solid var(--line);margin:20px 0}

/* ---------- بطاقات الوقائع ---------- */
.cards{display:grid;gap:14px;margin:16px 0 20px}
.card{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:16px 18px}
.card-head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.card-head h3{font-family:"Noto Kufi Arabic",sans-serif;font-size:16px;font-weight:600;margin:0;line-height:1.6;color:var(--ink)}
.tag{font-size:11.5px;border-radius:999px;padding:3px 10px;border:1px solid var(--line-2);color:var(--ink-2);background:var(--panel-3);white-space:nowrap}
.tag.t-confirm{color:#ffd7d3;background:rgba(255,93,82,.16);border-color:rgba(255,93,82,.42)}
.tag.t-suspect{color:#ffe6bd;background:rgba(255,176,46,.15);border-color:rgba(255,176,46,.40)}
.tag.t-inter{color:#d5e6ff;background:rgba(77,157,255,.15);border-color:rgba(77,157,255,.40)}
.card p{font-size:15px;margin:8px 0}

/* ---------- الجداول ---------- */
.tbl-wrap{overflow-x:auto;margin:16px 0 22px;border:1px solid var(--line);border-radius:var(--radius-sm);max-width:100%}
table{width:100%;border-collapse:collapse;font-size:14.5px;min-width:480px}
thead th{
  background:var(--panel-3);color:var(--ink);font-weight:600;text-align:start;
  padding:11px 13px;border-bottom:1px solid var(--line-2);white-space:nowrap
}
tbody td{padding:10px 13px;border-bottom:1px solid var(--line);color:var(--ink-2);vertical-align:top}
tbody tr:last-child td{border-bottom:0}
tbody tr:nth-child(even){background:rgba(255,255,255,.015)}
tbody tr:hover{background:rgba(34,195,182,.05)}
td.num,th.num{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;text-align:end;white-space:nowrap;color:var(--ink)}
tbody tr.total td{background:rgba(34,195,182,.09);color:var(--ink);font-weight:600}

/* ---------- المخططات ---------- */
.viz{margin:18px 0 24px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:18px}
.viz h3{
  margin:0 0 14px;font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;
  font-size:15px;color:var(--ink-2)
}
.bar-row{display:grid;grid-template-columns:minmax(150px,1.05fr) 3fr 108px;gap:14px;align-items:center;margin:11px 0}
.bar-row .bl{font-size:13.5px;color:var(--ink-2);line-height:1.55}
.bar-track{height:9px;border-radius:999px;background:var(--panel-3);overflow:hidden}
.bar-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#1fbfb2,#5ad6c8);width:var(--w,0);animation:grow 1s cubic-bezier(.22,.8,.28,1) both}
@keyframes grow{from{width:0}}
.bar-row .bv{font-family:"IBM Plex Mono",monospace;font-size:12.5px;text-align:end;color:var(--ink);font-variant-numeric:tabular-nums}
.viz .src-note{font-size:12.5px;color:var(--muted);margin:12px 0 0}

/* ---------- خريطة الوقائع ---------- */
.map-wrap{border:1px solid var(--line-2);border-radius:var(--radius-sm);overflow:hidden;background:var(--map-sea);margin-top:6px}
.map-svg{display:block;width:100%;height:auto;max-width:100%}
.mp-sea-bg{fill:var(--map-sea)}
.mp-grid line{stroke:var(--map-grid);stroke-width:.7;vector-effect:non-scaling-stroke}
.mp-grid-lbl{font-family:"IBM Plex Mono",monospace;font-size:11px;fill:var(--map-grid-lbl);direction:ltr;unicode-bidi:isolate}
.mp-land path{fill:var(--map-land);stroke:var(--map-coast);stroke-width:1.2;vector-effect:non-scaling-stroke}
.mp-borders path{fill:none;stroke:var(--map-border);stroke-width:.9;stroke-dasharray:6 5;vector-effect:non-scaling-stroke}
.mp-places text{font-family:"IBM Plex Sans Arabic","Noto Kufi Arabic",sans-serif;dominant-baseline:middle;text-anchor:middle}
.mp-port-dot{fill:var(--map-label)}
.mp-port-lbl{fill:var(--map-label);font-size:14px;direction:rtl;unicode-bidi:isolate}
.mp-country{fill:var(--map-country);font-size:15px;letter-spacing:.5px}
.mp-sea-lbl{fill:var(--map-sea-label);letter-spacing:.8px}
.mp-sea-lg{font-size:19px}
.mp-sea-sm{font-size:15px;font-weight:600;fill:var(--map-strait);letter-spacing:0}
.mp-events .mp-halo{fill:var(--mk);opacity:.22}
.mp-events .mp-dot{fill:var(--mk);stroke:var(--bg);stroke-width:2.2;vector-effect:non-scaling-stroke}
.mp-events .mp-num{font-family:"IBM Plex Mono",monospace;font-size:9.5px;font-weight:600;fill:#fff;text-anchor:middle}
.map-keys{font-size:12.5px;color:var(--faint);margin:12px 0 0}
.map-legend{list-style:none;display:grid;gap:7px;margin:14px 0 0;padding:0}
.map-legend li{display:flex;gap:10px;align-items:baseline;font-size:13.5px;color:var(--ink-2);margin:0}
.lg-num{font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:600;color:#fff;background:var(--mk);border-radius:999px;width:19px;height:19px;display:grid;place-items:center;flex:0 0 auto}
/* ---------- خريطة الشاشة العليا: للشاشة فقط، تُحجب في الطباعة وWord بصنف no-print ---------- */
.hero-map{margin:22px 0 6px}
.hmap{margin:0;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:18px}
.hmap h3{margin:0 0 14px;font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:15px;color:var(--ink-2)}
.hmap .blk-lede,.hmap-keys,.hmap-panel .src-note{display:none}
.hmap-wrap{position:relative;border:1px solid var(--line-2);border-radius:var(--radius-sm);overflow:hidden;background:var(--map-sea)}
/* التكبير بجانب الخريطة لا فوقها: الشريحة كانت تحجب الخليج العربي (البحرين وقطر) */
.hmap-wrap{display:grid;grid-template-columns:minmax(0,2.4fr) minmax(0,1fr);align-items:start}
.hmap-zoom{border-inline-start:1.5px solid var(--accent);background:var(--map-sea);min-width:0;align-self:stretch;display:flex;flex-direction:column}
.hmap-zsvg{display:block;width:100%;height:auto}
.hz-cap{font-size:13px;color:var(--ink-2);background:var(--panel);padding:4px 10px;border-top:1px solid var(--line-2);margin-top:auto}
@media (max-width:1000px){.hmap-wrap{grid-template-columns:minmax(0,1fr)}.hmap-zoom{border-inline-start:0;border-top:1.5px solid var(--accent)}}
.hmap-svg{display:block;width:100%;height:auto;max-width:100%}
/* خريطة الشاشة: علامات وتسميات أكبر قليلًا للقراءة من مسافة */
.hmap-svg .mp-dot{r:9.5px}
.hmap-svg .mp-halo{r:17px}
.hmap-svg .mp-events .mp-num{font-size:12.5px}
.hmap .mp-grid-lbl{font-size:12.5px}
.hmap .mp-port-lbl{font-size:15.5px}
.hmap .mp-country{font-size:16.5px}
.hmap-legend{list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 30px;margin:16px 0 0;padding:0}
.hmap-legend li{display:block;position:relative;padding-inline-start:34px;font-size:14px;line-height:1.85;color:var(--ink-2);margin:0}
.hmap-legend .lg-num{position:absolute;inset-inline-start:0;top:3px}
.hmap-legend .bidi{color:var(--muted);font-size:13px;white-space:nowrap}
@media (max-width:760px){.hmap-legend{grid-template-columns:minmax(0,1fr)}}
/* الجوال: الخريطة الرئيسية تُصغَّر كثيرًا فتكبر العلامات والتسميات لتبقى مقروءة (التفصيل في لوحة التكبير) */
@media (max-width:700px){
  .hmap-svg .mp-dot{r:13px}.hmap-svg .mp-halo{r:20px}.hmap-svg .mp-events .mp-num{font-size:15px}
  .hmap-svg .mp-port-lbl{font-size:25px}.hmap-svg .mp-country{font-size:27px}
  .hmap-svg .mp-sea-lg{font-size:31px}.hmap-svg .mp-sea-sm{font-size:25px}.hmap-svg .mp-grid-lbl{display:none}
}
/* ---------- الاستشهادات ---------- */
.cite-ref{
  display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:11.5px;
  color:var(--accent);background:rgba(34,195,182,.10);border:1px solid rgba(34,195,182,.34);
  border-radius:6px;padding:0 5px;margin-inline-start:3px;vertical-align:1px
}
.cite-ref:hover{background:rgba(34,195,182,.22);text-decoration:none}

/* ---------- المصادر ---------- */
.src-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin:14px 0 22px}
.src{border:1px solid var(--line);border-radius:var(--radius-sm);background:var(--panel-2);padding:11px 13px;font-size:13.5px;color:var(--ink-2)}
.src b{display:block;color:var(--ink);font-weight:600;font-size:14px;margin-bottom:3px}
.src .st{font-size:12px;color:var(--muted)}
.src.s-ok{border-inline-start:3px solid var(--ok)}
.src.s-none{border-inline-start:3px solid var(--info)}
.src.s-fail{border-inline-start:3px solid var(--danger)}
/* ---------- سجل الأحداث (قرار المالك 2026-10-29) ---------- */
.ev-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px;margin:16px 0 10px}
.ev{position:relative;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel-2);padding:14px 16px 13px;overflow:hidden}
.ev::before{content:"";position:absolute;inset-inline-start:0;top:0;bottom:0;width:3px;background:var(--info)}
.ev.b-official::before{background:var(--ok)}
.ev.b-media::before{background:#d9a441}
.ev.b-deny::before{background:var(--danger)}
.ev-top{display:flex;align-items:center;gap:8px;margin-bottom:9px;flex-wrap:wrap}
.ev-idx{font-variant-numeric:tabular-nums;font-size:12px;line-height:1;color:var(--muted);border:1px solid var(--line-2);border-radius:6px;padding:3px 6px}
.ev-code{font-size:12px;color:var(--muted);letter-spacing:.02em}
.ev-badge{margin-inline-start:auto;font-size:11.5px;line-height:1;padding:4px 10px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink-2)}
.ev.b-official .ev-badge{border-color:rgba(34,195,182,.45);color:var(--ok)}
.ev.b-media .ev-badge{border-color:rgba(217,164,65,.5);color:#e0b45f}
.ev.b-deny .ev-badge{border-color:rgba(214,86,86,.45);color:#e88}
.ev-what{margin:0;font-size:15.5px;line-height:1.8;color:var(--ink)}
.ev-meta{margin:10px 0 0;padding-top:8px;border-top:1px dashed var(--line);font-size:12.5px;line-height:1.75;color:var(--muted)}
.ev-meta .ev-k{display:block;font-size:11.5px;color:var(--muted);opacity:.85;margin-bottom:2px}
.ev-meta .ev-mv{display:block;color:var(--ink-2)}
@media (max-width:820px){.ev-grid{grid-template-columns:1fr}}

/* ---------- التذييل ---------- */
.foot{margin-top:34px;padding:20px 22px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);color:var(--muted);font-size:13.5px}
.foot b{color:var(--ink-2)}
/* قواعد العرض المعتمدة 12 أكتوبر 2026 (تعديلات المعاينة) — للتراجع: احذف السطرين التاليين */
.foot{display:none}
.method-note{display:none}

/* ---------- الحركة: دخول لطيف بالـCSS فقط، والمحتوى مرئي دائمًا ---------- */
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.masthead,.kpis{animation:rise .55s cubic-bezier(.22,.8,.28,1) both}
@media (prefers-reduced-motion: reduce){
  .masthead,.kpis,.bar-fill{animation:none}
}

@media (max-width:760px){
  body{font-size:16px}
  .wrap{padding:0 14px 70px}
  section.doc{padding:18px 15px 8px}
  .threat{margin-inline-start:0;width:100%}
  .bar-row{grid-template-columns:1fr auto;grid-template-areas:"l v" "t t";gap:6px 10px}
  .bar-row .bl{grid-area:l}
  .bar-row .bv{grid-area:v;text-align:start}
  .bar-track{grid-area:t;width:100%}
  table{font-size:14px}
}

/* ==================== نمط الطباعة A4 ==================== */
@page{size:A4;margin:14mm 12mm}
/* ---------- قواعد عرض معتمدة من تعديلات المعاينة (12 أكتوبر 2026) ---------- */
.notice,
.map-panel .src-note,
.map-keys,
.decision .dc-foot{display:none}

.sec-lede{font-size:13px;color:var(--muted);margin:0 0 16px;line-height:1.7;max-width:76ch}
.blk-lede{font-size:12.5px;color:var(--faint);margin:-6px 0 10px;line-height:1.6}

@media print{
  /* ك-255: بطاقة القرار على خلفية بيضاء في الطباعة */
  .card, .decision, .dc, .blk, .blk *{background-image:none !important}
  .card, .decision, .dc{background:#fff !important}
  /* ك-245: منع انقسام مفتاح الخريطة بين صفحتين في PDF */
  .map-key, .map-legend, .key-box, .mx-key,
  /* عطل 2026-10-28: كتلة الخريطة+المفتاح (~130–215مم) لا تجتمع في صفحة فتترك فراغًا مانعًا.
     الحكم: الكتلة تنقسم بين الرسم والمفتاح، وكلٌّ منهما لا ينقسم. */
  .print-map{break-inside:auto !important;page-break-inside:auto !important}
  /* الإطار نفسه ينقسم: الرسم (95مم) يبقى صحيحًا، والمفتاح يبقى كاملًا في صفحة واحدة */
  .print-map .hmap-wrap{break-inside:auto !important;page-break-inside:auto !important;overflow:visible !important}
  .print-map .hmap-svg{break-inside:avoid !important;page-break-inside:avoid !important}
  .print-map .hmap-legend{break-inside:avoid !important;page-break-inside:avoid !important}
  /* ك-245: المفتاح كامل في عمود واحد، وتلتصق كتلة الخريطة بذيل المحتوى */
  .print-map{display:block !important}
  .print-map .hmap-wrap{overflow:hidden !important}
  /* لا يُقيَّد ارتفاع الخريطة: القيد يقلّص عرضها فيسقط فحص العرض (70%) — ك-256 */
  .print-map .hmap-keys{display:block !important;margin:1.2mm 0 0;font-size:7.8pt;line-height:1.25}
  /* عطل 2026-10-28: المفتاح بعمود واحد بلغ 95مم فلم تجتمع الخريطة معه في صفحة،
     فبقي فراغ مانع (176مم). القرار: عمودان في الطباعة — المفتاح يبقى كاملًا وغير منقسم
     داخل الكتلة (break-inside:avoid) وتنخفض كتلته إلى ما يقارب النصف. */
  /* ك-298ج: المفتاح (36مم) لم يجد متسعًا في ذيل صفحة الخريطة فهبط لصفحة شبه فارغة.
     الحكم: ستة أعمدة وخط أصغر قليلًا — المفتاح يبقى كاملًا ويستقر في مكانه. */
  .print-map .hmap-legend{grid-template-columns:repeat(6,minmax(0,1fr)) !important;columns:6 !important;column-gap:2.6mm !important;gap:0 !important;margin:1mm 0 0}
  .print-map .hmap-legend li{break-inside:avoid !important;page-break-inside:avoid !important;margin:0 0 .15mm !important;font-size:6.5pt !important;line-height:1.12 !important}
  .print-map-distribution{break-inside:avoid !important;page-break-inside:avoid !important;margin-top:2mm}
  .print-map-distribution h3{font-size:10pt;margin:1.5mm 0 1mm}
  .print-map-distribution .dist-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.5mm}
  .print-map-distribution .dist-card{display:block !important;width:auto !important;margin:0 !important;padding:1.3mm 1.7mm;border:1px solid #cfd8e3;border-radius:1.2mm;background:#fff;color:#20303f;font-size:7.7pt;line-height:1.25;break-inside:avoid;page-break-inside:avoid}
  .print-map-distribution .dist-card b{display:block;color:#0a1524;font-size:8pt;margin-bottom:.5mm}
  .print-map-distribution .dist-card span{display:block}

  :root{
    --ink:#0a1524;--ink-2:#20303f;--muted:#4b5e73;--faint:#5c728c;
    --line:#8d9bad;--line-2:#5d6f84;--panel:#fff;--panel-2:#fff;--panel-3:#eef2f7;
    --accent:#0b6f66;--info:#1f5f9f;--danger:#9d2b25;--warn:#7d5200;--ok:#166b45;
    /* لوحة خريطة الطباعة المعتمدة (حزمة design-v1 — قرار المالك 2026-10-23): بحر أبيض ويابسة رمادية */
    --map-sea:#ffffff;--map-land:#dfe4ea;--map-coast:#3f4f63;--map-border:#7b8796;
    --map-grid:#d3d9e0;--map-grid-lbl:#4b5e73;--map-label:#0a1524;--map-country:#4b5e73;
    --map-sea-label:#4b5e73;--map-strait:#9d2b25;--map-marker-ring:#ffffff;--map-marker-ink:#ffffff;
  }
  body{background:#fff;color:#111;font-size:10.8pt;line-height:1.62}
  /* لا تُطبع المصادر والمراجع ولا ملحق موثوقية المصادر في نسخة PDF */
  #sec-16{display:none !important}
  p,li,blockquote,.sec-lede,.blk-lede,.note{orphans:3;widows:3}
  /* اقتصاد الورق: تُقاس الخريطة على ارتفاع صفحة واحدة مع عنوانها */
  /* الخريطة ينقسم إطارها فقط بين الرسم والمفتاح، فلا تبقى ورقة شبه فارغة */
  .map-viz{break-inside:auto;page-break-inside:auto}
  .map-viz svg{max-height:100mm;height:auto;break-inside:avoid;page-break-inside:avoid}
  .map-legend{break-inside:avoid;page-break-inside:avoid}
  /* إجبار: كتلة الخريطة تنقسم بين الرسم والمفتاح مهما وردت قاعدة أخصّ */
  #sec-03 .map-viz, .map-viz{break-inside:auto !important;page-break-inside:auto !important}
  .map-viz svg{break-inside:avoid !important;page-break-inside:avoid !important}
  .map-viz{padding:1.2mm 1.2mm}
  /* لا يُقسَّم مفتاح hmap في الطباعة؛ النسخة المطبوعة تعلن عمودًا واحدًا صراحةً */
  .map-legend{columns:2;column-gap:8mm}
  .map-legend li{break-inside:avoid;margin:0 0 1.4mm;font-size:9pt;line-height:1.45}
  .map-legend .lg-txt{font-size:9pt}
  .map-caption,.map-viz figcaption{margin-top:1.5mm;line-height:1.4}
  /* كثافة الصفحة: تقليل حشو الخلايا لتصبح الكتلة على مقاس الورقة */
  tbody td{padding:1.5mm 2.2mm !important}
  .sec-lede{margin:0 0 10px;line-height:1.55}
  section.doc{padding:0 0 3mm}
  .rmk,.glossary{break-inside:avoid;page-break-inside:avoid}
  /* انضباط بصري: خطوط فاصلة رقيقة بدل تظليل الصفوف */
  tbody tr:nth-child(even){background:#fff !important}
  tbody td{border-bottom:.4pt solid #e2e8f0}
  .kpi,.viz,.src,.card,.notice,.threat,.chip,.decision,.bar-track{border-radius:2.4mm}
  .threat{display:inline-block;min-width:52mm}
  .mp-events text{font-size:13.5px}
  /* أرقام علامات الخريطة: لا بد من تخصيص أعلى لأن قاعدة الشاشة أخصّ */
  .mp-events .mp-num{font-size:15px}
  .mp-events text{font-size:15px}
  /* لا تباعد أحرف على العربية داخل الخريطة (يفكّ الاتصال) */
  .mp-country,.mp-sea-lbl,.mp-port-lbl{letter-spacing:0}
  /* لا يُترك عنوان قسم في نهاية صفحة ومحتواه في التالية */
  .h-rule,.sec-lede{break-after:avoid;page-break-after:avoid}
  /* ضغط الغلاف: تقليل الفراغ في الصفحة الأولى */
  .masthead{padding:0 0 4mm}
  .masthead h1{margin:0 0 3mm}
  .threat{padding:4mm 6mm}
  .kpis{margin-top:3mm}
  .cls-banner{margin-top:3mm}
  body::before{display:none}
  .topbar,.no-print{display:none !important}
  .wrap{max-width:none;padding:0}
  a{color:#0a1524;text-decoration:none}
  section.doc{background:#fff;border:0;border-top:1px solid #cfd8e3;border-radius:0;padding:0 0 5mm;box-shadow:none;break-inside:auto;page-break-inside:auto}
  section.doc.pri{border-top:2px solid #0b6f66}
  section.doc > h2{font-size:13pt;color:#0a1524;break-after:avoid;page-break-after:avoid}
  section.doc > h2 .ico{display:none}
  section.doc h3{color:#0a1524;font-size:11pt;break-after:avoid;page-break-after:avoid}
  section.doc p,section.doc li,tbody td,.card p{color:#20303f}
  .masthead h1{color:#0a1524;font-size:21pt}
  .kpi,.viz,.src,.foot,.card,.notice{background:#fff;border-color:#cfd8e3;box-shadow:none}
  .kpi .k-v{color:#0a1524}
  .threat{background:#fff;border-color:#cfd8e3}
  .chip{background:#f6f8fb;border-color:#cfd8e3;color:#31465c}
  .chip b{color:#0a1524}
  .cite-ref{color:#0a1524;background:#f2f5f9;border-color:#b8c4d1}
  .tag{color:#31465c;background:#f6f8fb;border-color:#b8c4d1}
  .tag.t-confirm{color:#7a1d1a;background:#fff1f0;border-color:#c77973}
  .tag.t-suspect{color:#7c5000;background:#fff7e6;border-color:#c9a24f}
  .tag.t-inter{color:#1d4f87;background:#edf4ff;border-color:#8bb1dd}
  thead th{background:#eef2f7;color:#0a1524}
  .viz{background:#fbfcfe}
  .bar-track{background:#e6ecf3}
  .bar-fill{background:#0f8f86;animation:none}
  .masthead,.kpis{animation:none}
  .map-wrap{border-color:#c3cedb}
  .mp-events .mp-dot{stroke:#fff}
  .map-viz{break-inside:auto;page-break-inside:auto}
  .bar-row .bl,.bar-row .bv,.viz h3,.viz .src-note,.src,.src b,.src .st,.foot,.kpi .k-l,.kpi .k-n,.notice,.chip,.cite-ref,.tag{font-size:10.5pt;line-height:1.6}
  /* ك-256: البطاقات الكبيرة تنقسم بين الصفحات لتصفير الفراغ الداخلي؛ البطاقات الصغيرة تبقى موحّدة. */
  .card,.viz,.src,.table-row{break-inside:auto;page-break-inside:auto}
     /* ك-298: سجل الأحداث — عمود واحد وثبات البطاقة في الطباعة */
     /* ك-298ب: الشبكة لا تنقسم في طباعة Chromium — تُحوّل كتلًا عادية لتتدفّق البطاقات */
     .ev-grid{display:block;margin:5mm 0 0}
     .ev{display:block;margin:0 0 3mm;padding:3.4mm 4mm 3mm;break-inside:avoid;page-break-inside:avoid;opacity:1 !important;transform:none !important;animation:none !important;border-color:#c3cedb;background:#fff}
     .ev::before{width:4px;background:#0f8f86}
     .ev.b-media::before{background:#b8860b}
     .ev.b-deny::before{background:#9aa8ba}
     .ev-what{font-size:10pt;line-height:1.55;color:#12203a;margin:0}
     .ev-top{margin-bottom:1.6mm}
     .ev-meta{margin-top:1.8mm;padding-top:1.4mm}
     .ev-meta{font-size:9.5pt;color:#4a5b73;border-top-color:#dbe3ec}
     .ev-idx,.ev-code,.ev-badge{font-size:9pt;color:#4a5b73;border-color:#c3cedb}
  .kpi,.glossary,.rmk{break-inside:avoid;page-break-inside:avoid}
  .tbl-wrap{overflow:visible;break-inside:auto;page-break-inside:auto}
  table{min-width:0;font-size:10.5pt}
  thead{display:table-header-group}
  tbody tr{break-inside:avoid;page-break-inside:avoid}
  html.js .reveal{opacity:1 !important;transform:none !important;transition:none !important}

  .decision{background:#fff;border-color:#c3cedb}
  .decision .dc-title{color:#0b6f66}
  .dc-v{color:#0a1524}
  .dc-row.risk-high .dc-v{color:#9d2b25}
  .dc-row.risk-med .dc-v{color:#7d5200}
  .dc-row.risk-low .dc-v{color:#166b45}
  .dc-foot,.rkey,.glossary{color:#4b5e73}
  .conf,.kstrip,.chg-tag,.st-badge,.ev-code,.cls-banner{font-size:10.5pt;background:#f6f8fb;border-color:#b8c4d1;color:#31465c}
  .conf.c-high{color:#14603f;background:#edfaf3;border-color:#7cc4a0}
  .conf.c-med{color:#7c5000;background:#fff8ea;border-color:#cfa95a}
  .conf.c-low{color:#1d4f87;background:#eff5ff;border-color:#8bb1dd}
  .kstrip.k-confirm,.st-badge.s-active{color:#7a1d1a;background:#fff1f0;border-color:#c77973}
  .kstrip.k-inter,.chg.c-new .chg-tag{color:#1d4f87;background:#edf4ff;border-color:#8bb1dd}
  .kstrip.k-suspect,.chg.c-reclassified .chg-tag,.cls-banner.c-restricted{color:#7c5000;background:#fff7e6;border-color:#c9a24f}
  .chg.c-closed .chg-tag,.st-badge.s-stable{color:#14603f;background:#edfaf3;border-color:#7cc4a0}
  .ev-code{color:#0b6f66;background:#effaf8;border-color:#7fc9c0}
  .tl-track{background:#e6ecf3}
  .tl-fill.k-confirm{background:#9d2b25}
  .tl-fill.k-inter{background:#1f5f9f}
  .tl-fill.k-suspect{background:#7d5200}
  .tl-fill.k-bg{background:#7f92a8}
  ul.d-kinds li::before{width:3px}
  .decision,.glossary{break-inside:avoid;page-break-inside:avoid}
  /* كتل التحليل الطويلة تُقسَّم بدل إفراغ ورقة كاملة */
  .tl-viz,.viz,.card{break-inside:auto !important;page-break-inside:auto !important}
  .tl-viz .tl-row,.viz svg,.card .kpi{break-inside:avoid;page-break-inside:avoid}
  .decision{animation:none}

  /* ===== سياسة التدفّق الموحّدة: تمنع الفراغات الداخلية (قرار 18 أكتوبر 2026) =====
     القاعدة: القِطَع الصغيرة محمية من الانقسام، والحاويات الكبيرة تتدفّق بحرية.
     فتُملأ كل ورقة قبل الانتقال، ولا تُدفع الكتل الكبيرة لإفراغ نصف ورقة. */
  *{break-inside:auto !important;page-break-inside:auto !important}
  tr,.kpi,.map-legend li,.glossary li,.dc-row,.ev-item,.chg-item{break-inside:avoid !important;page-break-inside:avoid !important}
  section.doc > h2,section.doc h3,section.doc h4,.h-rule,.sec-lede{break-after:avoid !important;page-break-after:avoid !important}
  thead{display:table-header-group}
  thead tr{break-after:avoid;page-break-after:avoid}
  p,li{orphans:2;widows:2}
  .map-viz svg{max-height:145mm !important;width:100%;height:auto;break-inside:avoid !important}
  .map-legend,.map-viz,.tbl-wrap,.changes,.decision,.viz,.card{break-inside:auto !important;page-break-inside:auto !important}
  /* ك-235: قاعدة مكرّرة كانت تنقض السطر 601 (auto) وتُعيد avoid، فتُنقل كتلة الخريطة كاملة فتُخلّف
     فراغًا قد يبلغ 206 مم في الصفحة السابقة. الرسم نفسه يبقى غير قابل للتجزئة (avoid على svg)،
     والحاوية والمفتاح يتدفّقان فيكتمل امتلاء الورقة. */
  .map-viz{break-inside:auto !important;page-break-inside:auto !important}
  /* Chromium لا يجزّئ حاويات grid/flex بين الصفحات، فتتدفّق هنا بترتيب inline-block
     يحفظ هيئة العمودين/البطاقات نفسها، مع السماح بالانقسام بين الصفحات */
  .wrap,.changes,.dc-grid,.kpis,.masthead,.map-legend,.src-grid,.glossary,.tl-viz,.viz,.card,.decision{display:block !important}
  .kpis > *,.masthead > *,.map-legend > li,.glossary > li,.src-grid > *{display:inline-block !important;vertical-align:top !important;width:48.5% !important;margin:0 0 2.5mm 1% !important;box-sizing:border-box !important}
  .dc-grid > *,.dc-row{display:block !important;width:100% !important}
  /* ك-103: الوسم يُعوَّم والمحتوى كتلة قابلة للانقسام — فلا يُترك عنوان أو بطاقة يتيمة ولا فراغ أسفل الغلاف */
  .dc-row::after{content:"";display:block;clear:both}
  .dc-row > *:first-child{float:inline-start !important;display:block !important;width:26% !important}
  .dc-row > *:last-child{display:block !important;width:auto !important;margin-inline-start:27% !important}
  .changes > *{display:block !important;width:100% !important}
  .viz > *,.card > *{box-sizing:border-box}
  /* ضغط تباعد الأقسام: يوفّر نحو 40 مم فتنتقل نهاية التقرير إلى صفحتها السابقة */
  section.doc{padding:0 0 2.5mm !important}
  section.doc > h2{margin:3mm 0 1.5mm !important}
  .sec-lede{margin:0 0 2mm !important}
  .h-rule{margin:1mm 0 2mm !important}
  /* تشخيص: إلغاء كل قواعد منع الكسر لتحديد مصدر الفراغات */
  *{break-after:auto !important;break-before:auto !important}
  body,p,li,td,th{line-height:1.36 !important}
  /* overflow مخفي يمنع Chromium من تقسيم الحاوية بين الصفحات فتُدفع كاملة وتُفرّغ الورقة */
  *{overflow:visible !important}
  .map-viz svg{max-height:145mm !important;width:100%;height:auto}
  .masthead > div:not(.threat){display:block !important;width:100% !important;margin:0 !important}
  .masthead h1{width:100% !important}
  /* الغلاف ينتهي عند شريط التصنيف: أهم الأخبار المتعلقة بالأمن البحري تبدأ صفحة جديدة (يمنع العنوان اليتيم والفراغ) */
  .decision{break-inside:avoid !important;page-break-inside:avoid !important}
  .map-viz svg{max-height:145mm !important;width:100%;height:auto}
  /* القاعدة الأخص تأتي بعد سياسة التدفق العامة حتى لا تنقضها */
  .print-map{break-inside:avoid !important;page-break-inside:avoid !important}
  .print-map .hmap-wrap{break-inside:avoid !important;page-break-inside:avoid !important;overflow:hidden !important}
  .print-map .hmap-wrap{grid-template-columns:minmax(0,6fr) minmax(0,1fr) !important}
  .print-map .hmap-zoom{border-inline-start:1.5px solid var(--accent) !important;border-top:0 !important}
  /* عطل 2026-10-28: قاعدتان متعارضتان للمفتاح (عمود/عمودان) — أُلغيت الثانية.
     الحكم الواحد: عمودان في الطباعة، والكتلة لا تنقسم. */
  .print-map .hmap-legend{grid-template-columns:repeat(4,minmax(0,1fr)) !important;columns:4 !important;column-gap:3.5mm !important}
  .print-map .hmap-keys{display:block !important}
  /* محاذاة مضبوطة: تُغلق فراغات الجانبين في الفقرات والقوائم، ولا تمسّ العناوين والبطاقات */
  section.doc p,section.doc li,.sec-lede,.masthead .lede,.glossary li,.src-grid li,
  /* تصفير فقرات المتن والعناوين التمهيدية (قرار المالك 2026-10-22): يمنع الفراغ الجانبي */
  .sec-lede,section.doc p,.masthead p,.blk-lede,.note{text-align:justify !important;text-align-last:start !important;hyphens:none !important}
  /* لا يُترك عنوان بطاقة أو قسم وحده أسفل ورقة بلا مضمون (عطل ك-103) */
  section.decision > .dc-title,.card > h3,.viz > h3,section.doc > h2{break-after:avoid !important;page-break-after:avoid !important}
  .dc-grid,.dc-row,.dc-v,.dc-v ul{break-inside:auto !important;page-break-inside:auto !important}
  .dc-list li{break-inside:avoid !important;page-break-inside:avoid !important}
  /* تصفير كامل المتن بما فيه قيم أهم الأخبار المتعلقة بالأمن البحري (ك-105): البوابة تفحص الصفحة بوسائط print */
  .dc-list li,.chg-list li,.ev-list li,.map-caption,footer.foot,
  .dc-v,.dc-row,.dc-grid,.kv-v,.glossary li,.src-grid li{text-align:justify !important;
    text-align-last:start !important;hyphens:none !important;word-spacing:normal !important}
  section.doc h2,section.doc h3,section.doc h4,.h-rule,.chip,.kpi,.tag,.st-badge,
  .map-legend li,.conf,.cls-banner,.threat,.toc li,.ev-code{text-align:start !important}
  .map-panel{padding:2mm 2.5mm !important}
  .map-legend{margin-top:1.5mm !important}
  .map-legend li{margin:0 0 1mm !important;font-size:8.4pt !important;line-height:1.3 !important}
  .kpis > *{width:32% !important;padding:1.6mm 2mm !important;margin:0 0 1.5mm 1% !important}
  .kpis .k-v{font-size:14pt !important;margin:0.5mm 0 !important}
  .kpis .k-l{font-size:8.6pt !important;line-height:1.25 !important;min-height:0 !important}
  .kpis .k-m{font-size:7.6pt !important;line-height:1.25 !important}
  .dc-grid{gap:1.5mm !important}
  section.doc{font-size:10.2pt !important}
}

}

"""

SCRIPT = """
(function(){
  var pb = document.getElementById('btn-print');
  if(pb) pb.addEventListener('click', function(){ window.print(); });
  var tb = document.getElementById('btn-theme');
  if(tb) tb.addEventListener('click', function(){
    var on = document.body.classList.toggle('daylight');
    tb.textContent = on ? 'النمط الليلي' : 'النمط النهاري';
  });
})();
"""

# النمط النهاري: تباين مصحّح (كل نص صغير داكن على خلفية فاتحة)
DAYLIGHT = """
body.daylight{
  --bg:#eef2f7;--bg-2:#e7edf4;--panel:#ffffff;--panel-2:#ffffff;--panel-3:#eef2f7;
  --line:#d3dce7;--line-2:#b9c6d6;--ink:#0b1a2b;--ink-2:#31465c;--muted:#5a7086;--faint:#6b7f94;
  --accent:#0b6f66;--info:#1f5f9f;--danger:#a32a24;--warn:#8a5a00;--ok:#176b46;
}
body.daylight::before{display:none}
body.daylight .topbar{background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(255,255,255,.85))}
body.daylight .btn-primary{background:#0b6f66;color:#ffffff}
body.daylight .cite-ref{color:#0b6f66;background:rgba(11,111,102,.07);border-color:rgba(11,111,102,.30)}
body.daylight .tag{color:#31465c;background:#f2f5f9;border-color:#c4d0dd}
body.daylight .tag.t-confirm{color:#7a1d1a;background:#fff1f0;border-color:#c77973}
body.daylight .tag.t-suspect{color:#7c5000;background:#fff7e6;border-color:#c9a24f}
body.daylight .tag.t-inter{color:#1d4f87;background:#edf4ff;border-color:#8bb1dd}
body.daylight .threat.risk-high .val{color:#a32a24}
body.daylight .map-legend li,body.daylight .lg-num{color:#31465c}
body.daylight .lg-num{color:#ffffff}
body.daylight .map-keys{color:#5a7086}
body.daylight .kpi em{opacity:.95}
"""


# ----------------------------------------------------------------------------
# أدوات
# ----------------------------------------------------------------------------
def esc(t) -> str:
    """هروب كامل يشمل علامات الاقتباس — صالح للنص وللصفات."""
    return html.escape(str(t), quote=True)


def isolate_dtg(t: str) -> str:
    """ك-171: عزل نطاقات DTG داخل bdi فلا ينعكس ترتيبها في سياق RTL."""
    import re as _re
    return _re.sub(r"(?<![\w\d])(\d{6}Z\s*[–-]\s*\d{6}Z)(?![\w])",
                   lambda m: f'<bdi class="bidi" dir="ltr">{m.group(1)}</bdi>', t)


def bdi(t: str) -> str:
    return f'<bdi class="bidi">{esc(t)}</bdi>'


def normalize_digits(s: str) -> str:
    """توحيد الأرقام العربية-الهندية والفارسية إلى أرقام لاتينية."""
    ar = "0123456789"
    fa = "۰۱۲۳۴۵۶۷۸۹"
    for i, d in enumerate(ar):
        s = s.replace(d, str(i))
    for i, d in enumerate(fa):
        s = s.replace(d, str(i))
    return s


def inline(text: str, defs: dict = None) -> str:
    """تحويل العناصر المضمّنة: عريض، مائل، كود، روابط، استشهادات."""
    t = esc(text)
    t = isolate_dtg(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)([^*\n]+?)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(
        r"\[([^\]]+)\]\((https?://[^\)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        t,
    )
    # استشهادات [n] — تصبح رابطًا إن وُجد تعريف للمصدر
    def cite(m):
        n = m.group(1)
        url = (defs or {}).get(n)
        if url:
            return (
                f'<a class="cite-ref bidi" href="{esc(url)}" target="_blank" '
                f'rel="noopener noreferrer">[{n}]</a>'
            )
        return f'<span class="cite-ref bidi">[{n}]</span>'

    t = re.sub(r"(?<![\w\]])\[(\d{1,3})\](?!\()", cite, t)
    # عزل معرفات الحوادث المرقمة مثل #164 لمنع انقلابها داخل النص العربي
    t = re.sub(r"(?<![\w#])#(\d{1,4})(?![\w])", r'<bdi class="bidi">#\1</bdi>', t)
    # وسم درجة الثقة المعيارية [ثقة: عالية|متوسطة|منخفضة]
    t = re.sub(
        r"\[ثقة:\s*(عالية|مرتفعة|متوسطة|متوسط|منخفضة|ضعيفة)\]\s*",
        lambda m: BLK.conf_chip(m.group(1)),
        t,
    )
    # روابط عارية داخل النص
    t = re.sub(
        r"(?<![\"'>=])(https?://[^\s<]+?)(?=[\s،۔.,)]|$)",
        r'<a class="bidi" href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        t,
    )
    return t


def icon(name: str) -> str:
    d = ICON_PATHS.get(name, ICON_PATHS["source"])
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        f'<path d="{d}"/></svg>'
    )


def split_table_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_sep(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s\-\:\|]+\|", line.strip()))


def cell_is_numeric(c: str) -> bool:
    c = normalize_digits(c.strip())
    return bool(re.fullmatch(r"[-+–]?[\d\.,]+%?", c))


def render_table(rows, defs):
    header, body = rows[0], rows[1:]
    if not any(h.strip() for h in header):
        raise BuildError("وجدت جدولًا بلا رؤوس أعمدة.")
    out = ['<div class="tbl-wrap"><table>', '<thead><tr>']
    for h in header:
        cls = "num" if cell_is_numeric(h) and header.index(h) > 0 else ""
        out.append(f'<th scope="col"{f" class=\"{cls}\"" if cls else ""}>{inline(h, defs)}</th>')
    out.append("</tr></thead><tbody>")
    for r in body:
        if len(r) != len(header):
            r = (r + [""] * len(header))[: len(header)]
        is_total = any("المجموع" in c for c in r)
        cls = ' class="total"' if is_total else ""
        out.append(f"<tr{cls}>")
        for i, c in enumerate(r):
            txt = inline(c, defs)
            if i > 0 and cell_is_numeric(c):
                out.append(f'<td class="num">{txt}</td>')
            else:
                out.append(f"<td>{txt}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def classify(text: str):
    """وسم البطاقة من التصنيف الصريح في النص نفسه؛ لا يُضيف معلومة."""
    m = re.search(r"التصنيف\s*:?\**\s*(.{0,90})", text)
    if m:
        seg = m.group(1)
        if re.search(r"هجوم\s*(مؤكد|مثبت)", seg):
            return ("هجوم مؤكد", "t-confirm")
        if re.search(r"تفاعل عسكري|تعطيل", seg):
            return ("واقعة عسكرية", "t-inter")
        if re.search(r"لم يتم التأكيد بعد|نشاط مشبوه|غير مؤكد|غير مثبت", seg):
            return ("لم يتم التأكيد بعد", "t-suspect")
        if re.search(r"خلفية|ليست واقعة", seg):
            return ("لا جديد", "t-bg")
    if re.search(r"هجوم\s*(مؤكد|مثبت)", text):
        return ("هجوم مؤكد", "t-confirm")
    if re.search(r"تفاعل عسكري|قوات عسكرية|تعطيل", text):
        return ("واقعة عسكرية", "t-inter")
    if re.search(r"نشاط مشبوه|لم يتم التأكيد بعد|مجهول", text):
        return ("لم يتم التأكيد بعد", "t-suspect")
    return ("خلفية", "t-bg")


def render_cards(blocks, defs):
    out = ['<div class="cards">']
    for head, body in blocks:
        joined = " ".join(body)
        tag_txt, tag_cls = classify(head + " " + joined)
        out.append('<div class="card reveal"><div class="card-head">')
        out.append(f'<span class="tag {tag_cls}">{esc(tag_txt)}</span>')
        out.append(f"<h3>{inline(head, defs)}</h3></div>")
        for ln in body:
            if ln.strip():
                out.append(f"<p>{inline(ln, defs)}</p>")
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)


def render_geo_viz(rows, defs):
    data = []
    for r in rows[1:]:
        if len(r) < 3 or "المجموع" in r[0]:
            continue
        pct_raw = normalize_digits(r[2]).replace(".", ".").replace(",", ".")
        m = re.search(r"\d+(?:\.\d+)?", pct_raw)
        if not m:
            continue
        pct = float(m.group(0))
        count = normalize_digits(re.sub(r"[^\d]", "", normalize_digits(r[1]))) or "—"
        data.append((r[0], pct, count))
    if not data:
        raise BuildError("جدول التوزيع الجغرافي للوقائع موجود لكن لا توجد صفوف رقمية قابلة للقراءة.")
    mx = max(d[1] for d in data) or 1
    rows_html = []
    for label, pct, count in data:
        w = max(2.0, pct / mx * 100.0)
        rows_html.append(
            '<div class="bar-row">'
            f'<div class="bl">{inline(label, defs)}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="--w:{w:.1f}%"></div></div>'
            f'<div class="bv bidi">{esc(count)} · {pct:.1f}%</div>'
            "</div>"
        )
    return (
        '<div class="viz reveal"><h3>حصيلة IMO حسب المنطقة</h3><p class="blk-lede">نسب الحوادث المؤكدة على قطاعات النطاق.</p>'
        + "\n".join(rows_html)
        + '<p class="src-note">المصدر: جدول التوزيع الجغرافي للوقائع في هذا التقرير. النسب لا تمثل أعداد هجمات مستقلة.</p></div>'
    )


def render_source_cards(rows, defs):
    if len(rows) < 2:
        return ""
    htxt = " ".join(rows[0])
    if not re.search(r"حالة|الفحص|المصدر|مصدر", htxt) or "القطاع" in htxt:
        return ""
    cards = ['<div class="src-grid">']
    for r in rows[1:]:
        if len(r) < 2:
            continue
        joined = " ".join(r)
        if re.search(r"تعذر|فشل|حجب", joined):
            cls, status = "s-fail", "تعذر الوصول"
        elif re.search(r"مفحوص|فُحص|فحص", joined):
            cls, status = "s-ok", "فُحص"
        else:
            cls, status = "s-none", "لا واقعة جديدة"
        note = r[-1] if len(r) > 2 else ""
        cards.append(
            f'<div class="src {cls}"><b>{inline(r[0], defs)}</b>'
            f'<span class="st">{esc(status)} — {inline(note, defs)}</span></div>'
        )
    cards.append("</div>")
    return "\n".join(cards)
# ----------------------------------------------------------------------------
# سجل الأحداث (قرار المالك 2026-10-29: نقل القسم إلى التقرير اليومي + تصميم بطاقات)
# ----------------------------------------------------------------------------
def is_events_table(header) -> bool:
    """جدول الوقائع/سجل الأحداث: رأس فيه «ما حدث» أو («الرمز» + «حالة التأكيد»)."""
    htxt = " ".join(header)
    return ("ما حدث" in htxt) or ("الرمز" in htxt and "حالة التأكيد" in htxt)

EVENT_BADGES = (
    (("نفي", "نفت", "نفى"), "b-deny"),
    (("نقل", "إعلامي", "رواية", "غير مؤكد", "لم يتأكد"), "b-media"),
    (("رسمي", "بلاغ"), "b-official"),
)

def event_badge(value: str):
    """شارة الحالة من نص «حالة التأكيد»: نفي · نقل إعلامي · بلاغ رسمي · قيد التثبّت."""
    v = (value or "").strip()
    for keys, cls in EVENT_BADGES:
        if any(k in v for k in keys):
            return cls, v
    return "b-info", (v or "قيد التثبّت")

def render_events_grid(rows, defs):
    """بطاقة لكل واقعة: شفرة وشارة حالة، ثم نص الحدث بسطر قراءة مريح، ثم المصدر والموقع والوقت."""
    body = [r for r in rows[1:] if len(r) >= 2 and r[0].strip()]
    if not body:
        return ""
    out = [f'<div class="ev-grid" data-count="{len(body)}">']
    for idx, r in enumerate(body, 1):
        code = r[0].strip()
        what = r[1].strip() if len(r) > 1 else ""
        meta = r[2].strip() if len(r) > 2 else ""
        cls, label = event_badge(r[3] if len(r) > 3 else "")
        meta_html = ""
        if meta:
            meta_html = (
                '<p class="ev-meta"><span class="ev-k">المصدر والموقع والوقت</span>'
                f'<span class="ev-mv">{inline(meta, defs)}</span></p>'
            )
        out.append(
            f'<article class="ev reveal {cls}" id="ev-{idx:02d}">'
            f'<div class="ev-top"><span class="ev-idx bidi">{idx:02d}</span>'
            f'<span class="ev-code ltr">{esc(code)}</span>'
            f'<span class="ev-badge">{esc(label)}</span></div>'
            f'<p class="ev-what">{inline(what, defs)}</p>'
            f"{meta_html}</article>"
        )
    out.append("</div>")
    return "\n".join(out)


# ----------------------------------------------------------------------------
# تحويل Markdown
# ----------------------------------------------------------------------------
def parse_ref_defs(md: str):
    """تعريفات المراجع [n]: https://..."""
    defs = {}
    for m in re.finditer(r"^\s*\[(\d{1,3})\]:\s*(\S+)", md, flags=re.M):
        defs.setdefault(m.group(1), m.group(2).strip("<>"))
    return defs


def parse_sections(md: str):
    sections, cur = [], None
    for ln in md.split("\n"):
        m = re.match(r"^##\s+(.*)$", ln)
        if m:
            cur = {"title": m.group(1).strip(), "lines": []}
            sections.append(cur)
            continue
        if ln.startswith("# ") and cur is None:
            continue
        if cur is not None:
            cur["lines"].append(ln)
    return sections


def is_incident_section(title: str) -> bool:
    return any(k in title for k in INCIDENT_SECTION_KEYS)


def render_section_body(title: str, lines, defs, doc_mode: bool = False):
    out, cards = [], []
    incident = is_incident_section(title)

    def flush():
        if cards:
            out.append(render_cards(cards, defs))
            cards.clear()

    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        s = ln.strip()

        if s.startswith("|") and i + 1 < n and is_sep(lines[i + 1]):
            flush()
            rows = [split_table_row(s)]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_table_row(lines[i]))
                i += 1
            htxt = " ".join(rows[0])
            if doc_mode:
                # وضع الوثيقة (التقارير الخاصة): يُعرض الجدول جدولًا كاملًا بكل أعمدته
                out.append(render_table(rows, defs))
                continue
            if "القطاع" in htxt or re.search(r"النسبة", htxt):
                out.append(render_geo_viz(rows, defs))
            if is_events_table(rows[0]):
                # ك-298: جدول الوقائع يجب أن يُصيّر بطاقاته، فكروت الحالة كانت تُسقط عمود «ما حدث»
                out.append(render_events_grid(rows, defs))
                continue
            sc = render_source_cards(rows, defs)
            if sc:
                out.append(sc)
                continue
            out.append(render_table(rows, defs))
            continue

        m3 = re.match(r"^###\s+(.*)$", s)
        if m3:
            if incident:
                cards.append((m3.group(1).strip(), []))
                i += 1
                continue
            flush()
            out.append(f"<h3>{inline(m3.group(1).strip(), defs)}</h3>")
            i += 1
            continue

        if re.match(r"^####\s+", s):
            flush()
            out.append(f"<h3>{inline(re.sub(r'^####\s+', '', s), defs)}</h3>")
            i += 1
            continue

        if cards:
            if s.startswith("#"):
                flush()
                continue
            if s:
                cards[-1][1].append(s)
            i += 1
            continue

        if re.match(r"^\s*[-*]\s+", ln):
            flush()
            items, kinds, sub = [], False, []

            def _close_sub():
                if items and sub:
                    items[-1] = items[-1][:-5] + "<ul>" + "".join(sub) + "</ul></li>"
                    sub.clear()

            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                indent = len(lines[i]) - len(lines[i].lstrip())
                raw = re.sub(r"^\s*[-*]\s+", "", lines[i].strip())
                mk = re.match(r"^\[(حقيقة|واقعة|تقدير تحليلي|تقدير|إعلامي|إعلام|خلفية|مراقبة)\]\s*", raw)
                cls = ""
                if mk:
                    cls = ' class="' + BLK.MARK_KIND.get(mk.group(1), "") + '"'
                    kinds = True
                    raw = raw[mk.end():]
                item = f"<li{cls}>{inline(raw, defs)}</li>"
                if indent >= 2 and items:
                    sub.append(item)
                else:
                    _close_sub()
                    items.append(item)
                i += 1
            _close_sub()
            cls_ul = ' class="d-kinds"' if kinds else ""
            out.append(f"<ul{cls_ul}>" + "".join(items) + "</ul>")
            continue

        if re.match(r"^\s*\d+[\.\)]\s+", ln):
            flush()
            items, kinds = [], False
            while i < n and re.match(r"^\s*\d+[\.\)]\s+", lines[i]):
                raw = re.sub(r"^\s*\d+[\.\)]\s+", "", lines[i].strip())
                mk = re.match(r"^\[(حقيقة|واقعة|تقدير تحليلي|تقدير|إعلامي|إعلام|خلفية|مراقبة)\]\s*", raw)
                cls = ""
                if mk:
                    cls = ' class="' + BLK.MARK_KIND.get(mk.group(1), "") + '"'
                    kinds = True
                    raw = raw[mk.end():]
                items.append(f"<li{cls}>{inline(raw, defs)}</li>")
                i += 1
            cls_ol = ' class="d-kinds"' if kinds else ""
            out.append(f"<ol{cls_ol}>" + "".join(items) + "</ol>")
            continue

        if s.startswith(">"):
            flush()
            q = []
            while i < n and lines[i].strip().startswith(">"):
                q.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(q), defs)}</blockquote>")
            continue

        if re.match(r"^---+$", s):
            flush()
            out.append("<hr>")
            i += 1
            continue

        if s:
            flush()
            para = [s]
            i += 1
            while i < n and lines[i].strip() and not re.match(
                r"^(#|\||>|\s*[-*]\s|\s*\d+[\.\)]\s|---)", lines[i].strip()
            ):
                para.append(lines[i].strip())
                i += 1
            text = " ".join(para)
            # فقرة المنهج الداخلي تُعرض مخفية: تبقى في المصدر ولا تظهر للقارئ
            cls = ' class="method-note"' if text.lstrip("*").startswith("منهج الحالة") else ""
            out.append(f"<p{cls}>{inline(text, defs)}</p>")
            continue

        i += 1

    flush()
    return "\n".join(out)


# ----------------------------------------------------------------------------
# التحقق من meta
# ----------------------------------------------------------------------------
def validate_meta(meta: dict):
    if not isinstance(meta, dict):
        raise BuildError("ملف الواجهة (meta) يجب أن يكون كائن JSON.")
    kpis = meta.get("hero_kpis", [])
    if not isinstance(kpis, list):
        raise BuildError("الحقل hero_kpis يجب أن يكون قائمة في ملف الواجهة.")
    for k in kpis:
        if not isinstance(k, dict):
            raise BuildError("كل عنصر في hero_kpis يجب أن يكون كائنًا يحتوي label و value.")
        if "label" not in k or "value" not in k:
            raise BuildError("عنصر في hero_kpis ينقصه label أو value.")
    if "threat_level" in meta and not isinstance(meta["threat_level"], str):
        raise BuildError("الحقل threat_level يجب أن يكون نصًا.")
    return meta


def derive_intel_source_grade(meta: dict) -> str:
    """يبني سند التحليل من سجل موثوقية المصادر المولَّد، لا من نص يدوي في meta."""
    reliability = meta.get("source_reliability") or {}
    rows = reliability.get("rows") if isinstance(reliability, dict) else None
    if not isinstance(rows, list):
        return ""
    grades = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        rel = str(row.get("rel") or "").strip().upper()
        cred = str(row.get("cred") or "").strip()
        if not name or not re.fullmatch(r"[A-F]", rel) or cred not in set("123456"):
            continue
        item = f"{name} {rel}/{cred}"
        if item not in seen:
            grades.append(item)
            seen.add(item)
    return " · ".join(grades)


def render_intel_review_notes(meta: dict, inline) -> str:
    """يضيف سطري المراجعة اللذين يجب أن يظهرا أسفل كتلة التحليل."""
    if not isinstance(meta.get("intel_analysis"), dict):
        return ""
    return (
        '<p class="rmk"><strong>المراجعة النظيرة:</strong> '
        + inline("الفصل بين الوقائع والتقديرات وربط التقديرات بسند المصدر.")
        + "</p>"
    )


def threat_class(threat: str) -> str:
    if re.search(r"مرتفع|حرج|شديد|عال", threat):
        return "risk-high"
    if re.search(r"متوسط|جوهري", threat):
        return "risk-med"
    return "risk-low"


# ----------------------------------------------------------------------------
# البناء
# ----------------------------------------------------------------------------
def hero_map(map_html: str, *, print_mode: bool = False, extra_html: str = "") -> str:
    """نسخة خريطة الوقائع للشاشة فقط، تظهر أعلى الصفحة (قرار فهد 22 أكتوبر 2026).

    الصنف no-print يحجبها في PDF، وWord يحذفه (STRIP_SELECTORS). أصنافها مغايرة لأصناف
    الخريطة الأصلية (hmap بدل map-viz/map-wrap/map-legend) حتى لا تلتقطها أدوات الطباعة
    والتصدير التي تختار بتلك الأصناف أول عنصر في الصفحة. تُخفى عن قارئ الشاشة
    (aria-hidden) لأن الخريطة الأصلية في قسمها هي المرجع.
    """
    h = map_html
    for old, new in (("viz map-viz reveal", "hmap"), ("map-panel", "hmap-panel"), ("map-wrap", "hmap-wrap"),
                     ("map-svg", "hmap-svg"), ("map-legend", "hmap-legend"), ("map-keys", "hmap-keys")):
        h = h.replace(old, new)
    if extra_html:
        head, tail = h.rsplit("</div>", 1)
        h = head + extra_html + "</div>" + tail
    if print_mode:
        return f'<section class="print-map" aria-label="خريطة الوقائع ومفتاحها">{h}</section>'
    return f'<section class="hero-map no-print" aria-hidden="true">{h}</section>'


def render_print_distribution_cards(sections, defs) -> str:
    """بطاقات توزيع صغيرة تُوضع أسفل مفتاح خريطة PDF عند نقل القسم إلى الإضافات."""
    for sec in sections:
        if "التوزيع الجغرافي" not in sec.get("title", ""):
            continue
        lines = sec.get("lines") or []
        for i, ln in enumerate(lines[:-1]):
            if not (ln.strip().startswith("|") and is_sep(lines[i + 1])):
                continue
            rows = [split_table_row(ln)]
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(split_table_row(lines[j]))
                j += 1
            cards = []
            for row in rows[1:]:
                if len(row) < 2 or not row[0].strip():
                    continue
                detail = " · ".join(x for x in row[1:4] if x.strip())
                cards.append(
                    '<div class="dist-card">'
                    f'<b>{inline(row[0], defs)}</b><span>{inline(detail, defs)}</span>'
                    '</div>'
                )
            if cards:
                return (
                    '<div class="print-map-distribution" aria-label="بطاقات التوزيع الجغرافي">'
                    '<h3>بطاقات التوزيع الجغرافي</h3>'
                    '<div class="dist-cards">' + "".join(cards) + '</div></div>'
                )
    return ""


def build(md_path: Path, out_path: Path, meta: dict, doc_mode: bool = False, mode: str = "report"):
    """mode='report' يُخفي أقسام «إضافات» (السياسة الحاكمة) · mode='additions' يعرضها وحدها بترتيبها."""
    md = md_path.read_text(encoding="utf-8")
    defs = parse_ref_defs(md)
    sections = parse_sections(md)
    if not sections:
        raise BuildError(
            "لم يُعثر على أي قسم بعنوان من المستوى الثاني (##) في الملف المصدر. "
            "تأكد من حفظ التقرير بأقسام بصيغة Markdown صحيحة."
        )
    validate_meta(meta)
    # سياسة عرض الرموز (2+5): كامل مرة واحدة في «الوقائع الجديدة»، ومختصر مدموج برقم البلاغ الرسمي في بقية المواضع
    _mdate = re.search(r"(\d{4}-\d{2}-\d{2})", md_path.name)
    report_date = _mdate.group(1) if _mdate else ""
    official = codes.official_map(meta)
    BLK.set_code_context(report_date, official)
    try:
        import map_gulf as _mg
        _mg.REPORT_DATE = report_date
    except Exception:
        pass

    # ترتيب الأقسام بالأهمية: القرار والصورة ← الوقائع ← التحليل ← الدعم
    # (الترتيب مستقر، والأقسام غير المعروفة تبقى في آخرها)
    order = [
        "ما تغيّر",         "الخلاصة",         "أهم الأخبار المتعلقة بالأمن البحري",         "التوزيع الجغرافي للوقائع",
        "مؤشرات الموقف",         "مستوى التهديد",         "التوجيهات التشغيلية",         "سجل الأحداث",         "الوقائع الجديدة",
        "التحذيرات والنشرات",         "سجل IMO",         "قراءة الموقف وتحليل المؤشرات",         "الاحتمالات",         "الحركة الملاحية والتكدس",
        "ما لم يُحسم",         "المراقبة المستمرة",         "الخلفية القائمة",         "المصادر والمراجع",

    ]

    def _order_key(sec):
        for i, k in enumerate(order):
            if k in sec["title"]:
                return i
        return len(order)

    if mode == "additions":
        # قرار المالك 2026-10-28: هذه الأقسام تُعرض في صفحة «إضافات» وحدها بترتيب السياسة
        _add = ADDITIONS_SECTIONS or []
        sections = [x for x in sections if any(k in x["title"] for k in _add)]
        _key = lambda sec: next((i for i, k in enumerate(_add) if k in sec["title"]), len(_add))
        sections = sorted(sections, key=_key)
    else:
        # ك-229: نقل الأقسام يسري من تاريخ القرار؛ الأرشيف قبله يبقى كما نُشر بلا فقد محتوى
        _hidset = set(HIDDEN_SECTIONS)
        if ADDITIONS_FROM and report_date and report_date < ADDITIONS_FROM:
            for _a in ADDITIONS_SECTIONS:
                _hidset.discard(_a)
        sections = [x for x in sections if not any(h in x["title"] for h in _hidset)]
        sections = sorted(sections, key=_order_key)
    source_sections = list(parse_sections(md))
    # كتل خاصة بكل قسم: خريطة عنوان القسم إلى اسم الكتلة
    blocks_map = meta.get("blocks") or {}
    block_data = {k: meta.get(k) for k in ("indicators", "hypotheses", "gaps", "event_keys", "timeline", "source_reliability", "vessel_identity", "report_classes", "intel_analysis")}
    intel_data = block_data.get("intel_analysis")
    if isinstance(intel_data, dict):
        intel_data = dict(intel_data)
        derived_grade = derive_intel_source_grade(meta)
        if derived_grade:
            intel_data["source_grade"] = derived_grade
        block_data["intel_analysis"] = intel_data
    if not isinstance(blocks_map, dict):
        blocks_map = {}

    # خريطة الوقائع: تُبنى من إحداثيات معلَنة في ملف الواجهة فقط
    map_html = ""
    mp = meta.get("map") or {}
    if isinstance(mp, dict) and mp.get("points"):
        try:
            from map_gulf import build_map

            map_html = build_map(mp["points"], mp.get("caption"), mp.get("inset"))
        except Exception as e:  # لا يُسقط فشل الخريطة بناء التقرير
            print(f"تنبيه: تعذر توليد الخريطة ({e})", file=sys.stderr)
            map_html = ""

    hero_map_html = ""
    print_map_html = ""
    if map_html and not doc_mode:
        try:
            from map_gulf import build_map as _build_map_hero

            _hero_map_source = _build_map_hero(mp["points"], mp.get("caption"), mp.get("inset"), zoom=True)
            hero_map_html = hero_map(_hero_map_source)
            if mode == "additions":
                print_map_html = hero_map(_hero_map_source, print_mode=True)
        except Exception as e:  # لا يُسقط فشل الخريطة بناء التقرير
            print(f"تنبيه: تعذر توليد خريطة الشاشة العليا ({e})", file=sys.stderr)

    # شريط المؤشرات
    kpi_html = ""
    kpis = meta.get("hero_kpis", [])
    if kpis:
        tiles = []
        for k in kpis:
            acc = k.get("accent", "ok")
            if acc not in ("ok", "info", "warn", "danger"):
                acc = "ok"
            tiles.append(
                f'<div class="kpi acc-{acc} reveal"><em></em>'
                f'<div class="k-l">{inline(k.get("label", ""))}</div>'
                f'<div class="k-v bidi">{esc(k.get("value", ""))}</div>'
                + (f'<div class="k-d">{BLK.trend_html(k.get("delta"))}</div>' if k.get("delta") else "")
                + f'<div class="k-n">{inline(k.get("note", ""))}</div></div>'
            )
        kpi_html = '<div class="kpis">' + "".join(tiles) + "</div>"

    # خريطة الملحق: تُلحق في نهاية «إضافات» فقط (صفحتها الكاملة بلا فراغ قبلها).
    appendix_map = print_map_html if mode == "additions" else ""
    # عطل 2026-10-28 (فراغ 176مم في الصفحة السابقة للخريطة): تُدرج خريطة الملحق قبل
    # «ما لم يُحسم» فتشارك صفحتها بقيّة المحتوى، ويستقرّ الذيل في الصفحة الأخيرة بلا فراغ.
    _appendix_map_marker = "\u0000"  # لا يطابق شيئًا: الخريطة تُلحق آخر الملحق
    threat = meta.get("threat_level", "")
    tcls = threat_class(threat) if threat else ""

    # قاموس الرموز والمصطلحات: يُطبع قسمًا مستقلًا بعد الخلاصة.
    # عطل ك-36: كان في تذييل الصفحة، وأنماط الطباعة تخفي التذييل، فغاب عن PDF تمامًا.
    glossary_html = ("" if _hidden("قاموس الرموز والمصطلحات")
                     else BLK.glossary(meta.get("glossary")))

    # قائمة الأقسام المخفية تُطبع للسجل مرة واحدة (تتبّع القرار لا التخمين)
    _hid = sorted(HIDDEN_SECTIONS)
    print("أقسام مُخفاة من الإصدار: " + " · ".join(_hid), file=sys.stderr)

    body = []
    for idx, sec in enumerate(sections):
        t = sec["title"]
        ic = SECTION_ICONS.get(t, "source")
        pri = " pri" if any(p in t for p in PRIORITY_SECTIONS) else ""
        body.append(f'<section class="doc{pri} reveal" id="sec-{idx + 1:02d}" aria-labelledby="h-{idx + 1:02d}">')
        if appendix_map and _appendix_map_marker in t:
            body.append(appendix_map)
            appendix_map = ""
        body.append(
            f'<h2 id="h-{idx + 1:02d}"><span class="ico">{icon(ic)}</span>{inline(t, defs)}</h2>'
            '<div class="h-rule"></div>'
            + (f'<p class="sec-lede">{esc(SECTION_HINTS[t])}</p>' if SECTION_HINTS.get(t) else "")
        )
        section_html = render_section_body(t, sec["lines"], defs, doc_mode)
        if not codes.is_primary(t):
            section_html = codes.demote(section_html, report_date, official)
        if map_html and "التوزيع الجغرافي للوقائع" in t:
            # نسخة الإضافات المطبوعة تستخدم hmap بصفحة مستقلة ومفتاح كامل؛ لا تُكرر map-viz القديمة.
            if mode == "additions" and print_map_html:
                # أبقِ النص نفسه، لكن أخّر الفقرة التفسيرية الأخيرة بصريًا كي تتسع
                # كتلة الخريطة ذات المفتاح الكامل في الصفحة التالية بلا ورقة شبه فارغة.
                tail_para = ""
                m = re.search(r"(<p>.*?</p>)\s*$", section_html, flags=re.S)
                if m:
                    tail_para = m.group(1)
                    section_html = section_html[:m.start()]
                # عطل 2026-10-28: إدراج الخريطة داخل القسم يترك فراغًا كبيرًا في الصفحة
                # السابقة لها (الخريطة تحتاج صفحة كاملة). القرار: تُلحق الخريطة ومفتاحها في
                # نهاية ملحق الإضافات (صفحتها الكاملة)، ويُستكمل ما قبلها بمحتوى الأقسام.
                section_html = section_html + tail_para
            else:
                section_html = section_html + map_html
        for key, bname in blocks_map.items():
            if key in t:
                for _bn in str(bname).split('+'):
                    if _bn in HIDDEN_BLOCKS:
                        continue
                    if block_data.get(_bn):
                        section_html += BLK.render_block(_bn, block_data[_bn], inline)
                        if _bn == "intel_analysis":
                            section_html += render_intel_review_notes(meta, inline)
        # عطل ك-72: تنبيه القسم كان داخل حلقة كتل المؤشرات فيتكرر بعددها (6 مرات في إصدار 20 أكتوبر).
        # القاعدة: تنبيه القسم يُكتب مرة واحدة في مستوى القسم لا داخل حلقة عناصره.
        if "الحركة" in t:
            section_html += '<p class="src-note">قراءة اتجاه الحركة والتكدس من مسار المتابعة المعتمد؛ ويُعرض اسم المنصة ودقة بياناتها في مراجع التقرير على الموقع. يُؤخذ في الحساب مدة التحديث (20 دقيقة) واحتمال انقطاع الإرسال أو التزييف.</p>'
        if "التوزيع الجغرافي" in t:
            section_html += '<p class="src-note">تحذيرات IHO/NAVAREA تُربط بإحداثياتها عند توفرها؛ والويب لا يستبدل البث الملاحي المعتمد.</p>'
        body.append(section_html)
        body.append("</section>")
        if "الخلاصة" in t and glossary_html:
            body.append(
                '<section class="doc reveal" id="sec-glossary" aria-labelledby="h-glossary">'
                '<h2 id="h-glossary"><span class="ico">' + icon("source") + '</span>قاموس الرموز والمصطلحات</h2>'
                '<div class="h-rule"></div>'
                '<p class="sec-lede">تعريفات الرموز والمصطلحات المستخدمة في هذا التقرير.</p>'
                + glossary_html + "</section>")

    title = meta.get("title") or DAILY_TITLE
    sub = meta.get("subtitle") or ""
    generated = meta.get("generated_label") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    chips = []
    if meta.get("version"):
        chips.append(f'<span class="chip">رقم الإصدار <b>{esc(meta["version"])}</b></span>')
    if generated:
        chips.append(f'<span class="chip">آخر تحديث <b class="bidi">{esc(generated)}</b></span>')
    if meta.get("window"):
        win = esc(meta["window"])
        _m = re.match(r'^(\S+Z\s*[–-]\s*\S+Z)\s*(.*)$', win)
        if _m:
            win = f'<bdi class="bidi" dir="ltr">{_m.group(1)}</bdi> {_m.group(2)}'
        chips.append(f'<span class="chip">فترة التغطية <b>{win}</b></span>')
    if meta.get("sources_approved") not in (None, ""):
        chips.append(f'<span class="chip">المصادر المعتمدة <b class="bidi">{esc(meta["sources_approved"])}</b></span>')
    if meta.get("sources_checked") not in (None, ""):
        chips.append(f'<span class="chip">بالمسار الآلي <b class="bidi">{esc(meta["sources_checked"])}</b></span>')
    if meta.get("sources_manual_reference_count") not in (None, ""):
        chips.append(f'<span class="chip">بالفحص اليدوي <b class="bidi">{esc(meta["sources_manual_reference_count"])}</b></span>')
    if meta.get("sources_cited") not in (None, ""):
        chips.append(f'<span class="chip">مصادر مستشهد بها <b class="bidi">{esc(meta["sources_cited"])}</b></span>')

    notice_html = ""
    if meta.get("notice"):
        notice_html = f'<div class="notice">{icon("shield")}<div>{inline(meta["notice"], defs)}</div></div>'

    threat_html = ""
    if threat:
        threat_html = (
            f'<div class="threat {tcls}"><div class="lbl">مستوى التهديد</div>'
            f'<div class="val">{esc(threat)}</div></div>'
        )

    date_label = meta.get("date_label") or ""
    cls_html = BLK.classification_banner(meta.get("classification"))
    decision_html = "" if mode == "additions" else BLK.decision_card(meta.get("decision_card"), inline)
    rkey_html = BLK.reading_key() if any("[" in l and "]" in l for l in md.split("\n")) else ""
    # سياسة الأقسام 2026-10-28: «ما تغيّر» منقول إلى صفحة «إضافات»
    if mode == "additions":
        changes_html = BLK.changes_block(meta.get("changes"), inline)
    else:
        _adds_live = bool(ADDITIONS_SECTIONS) and (not ADDITIONS_FROM or not report_date
                                              or report_date >= ADDITIONS_FROM)
        changes_html = ("" if (_adds_live and _hidden("ما تغيّر"))
                        else BLK.changes_block(meta.get("changes"), inline))
    screen_hero_html = "" if mode == "additions" else SCR.screen_hero(
        meta, esc=esc, inline=inline, report_date=report_date, official=official,
        threat_cls=tcls, rkey_html=rkey_html, doc_mode=doc_mode,
        archived=meta.get("screen_archived") or False)
    ledger_html = (
        f'<div class="glossary">السجل التراكمي: '
        f'<a class="bidi" href="{esc(meta["ledger_url"])}" target="_blank" rel="noopener noreferrer">{esc(meta["ledger_url"])}</a></div>'
        if meta.get("ledger_url") else ""
    )
    doc = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}{f' — {esc(date_label)}' if date_label else ''}</title>
<meta name="description" content="{esc(meta.get("description") or "تقرير أمني بحري يومي")}">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="referrer" content="no-referrer">
<script>document.documentElement.className='js';</script>
<link rel="stylesheet" href="{FONT_LINK}">
<style>{DESIGN_TOKENS}{STYLE}{BLK.STYLE_BLOCKS}{DAYLIGHT}{LINK_RULE}</style>
</head>
<body>
<div class="topbar no-print">
  <div class="topbar-inner">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">{icon("shield")}</div>
      <div class="brand-txt">
        <div class="brand-title">{esc(title)}</div>
        <div class="brand-sub">{esc(sub)}</div>
      </div>
    </div>
    <div class="topbar-spacer"></div>
    <div class="tb-meta">
      {f'<span class="chip">{esc(date_label)}</span>' if date_label else ''}
      <button class="btn" id="btn-theme" type="button">النمط النهاري</button>
      <button class="btn btn-primary" id="btn-print" type="button">طباعة / PDF</button>
    </div>
  </div>
</div>

<div class="wrap">
  <header class="masthead">
    <h1>{esc(meta.get("headline") or title)}</h1>
    {threat_html}
    <div>
      <p class="lede">{codes.demote(esc(meta.get("lede") or ""), report_date, official)}</p>
      <div class="masthead-meta">{"".join(chips)}</div>
    </div>
  </header>

  {cls_html}
  {decision_html}
  {kpi_html}
  {screen_hero_html}
  {hero_map_html}
  {notice_html}
  {rkey_html}

  <main>
    {changes_html}
    {"".join(body)}
    {appendix_map}
  </main>

  <footer class="foot">
    <b>ملاحظة مهنية:</b> {inline(meta.get("footer_note") or "هذا التقرير يعتمد على المصادر المعلنة فقط. لا تُجمع البلاغات كعدد هجمات، ولا يُنسب أي فعل إلى جهة إلا وفق مصدر رسمي مباشر.", defs)}
    <br><b>وقت الإصدار:</b> <bdi class="bidi">{esc(generated)}</bdi> — <b>المرجع الزمني:</b> UTC.
    {ledger_html}
  </footer>
</div>
<script>{SCRIPT}</script>
</body>
</html>"""
    # سياسة عرض الرموز (2+5): تبسيط شامل لكل ما هو خارج قسم الوقائع
    doc = codes.demote_page(doc, report_date, official)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = isolate_ltr(doc)
    # طبقة الشاشة تُحقن بعد العزل: isolate_ltr يعمل على نص كل ما بين الوسوم فيفسد CSS وJS (مثل UTC وأسماء الخطوط)
    doc = doc.replace("</style>", SCR.SCREEN_CSS + "</style>", 1)
    # العنوان في وسم title نص صرف: isolate_ltr يلفّ الأسماء اللاتينية فيه بوسوم span فتظهر وسومًا في تبويب المتصفح
    doc = re.sub(r"<title>.*?</title>",
                 lambda m: re.sub(r'</?span[^>]*>', "", m.group(0)), doc, count=1, flags=re.S)
    doc = doc.replace("</body>", f"<script>{SCR.SCREEN_JS}</script>\n</body>", 1)
    out_path.write_text(doc, encoding="utf-8")
    return out_path, len(sections)


LTR_PATTERNS = [
    r"\b\d{6}Z\s*[–—-]\s*\d{6}Z\b",                         # نطاق الفترة كاملًا في عزل واحد
    r"\b\d{4,6}Z(?:\s+[A-Z]{3}\s*\d{2})?\b",                       # DTG: 180400Z OCT 26
    r"\b\d{1,3}[-°]\d{1,2}(?:\.\d+)?['′]?\s*[NS]\b",               # 26-16.8N
    r"\b[NS]\s?\d{1,3}[°-]\d{1,2}(?:\.\d+)?['′]?",                  # N 057°40.65′
    r"\b\d{1,3}[-°]\d{1,2}(?:\.\d+)?['′]?\s*[EW]\b",               # 056-08.6E
    r"\b[EW]\s?\d{1,3}[°-]\d{1,2}(?:\.\d+)?['′]?",                  # E 21.48°
    r"\b(?:MN|EST)-\d{4}-\d{2}-\d{2}-\d{2}\b",  # رمز واقعة أو تقدير كاملًا في كتلة LTR واحدة
    r"\bIMO\s?\d{6,7}\b", r"\bMMSI\s?\d{8,9}\b",
    r"\bUKMTO\s?\d{2,3}\s?[-–]\s?\d{2}\b", r"\bNAVAREA\s+[IVX]+\s+\d{2,3}/\d{2}\b",
    r"\b\d{2,3}/\d{2}\b", r"\b[A-Z][A-Z0-9]{2,}(?:\s+[A-Z0-9]{2,})*\b",
]
_LTR_RE = None
_PERIOD_RE = re.compile(r"^\d{6}Z\s*[–—-]\s*\d{6}Z$")


def isolate_ltr(html: str) -> str:
    """يغلّف المعرّفات والأوقات والإحداثيات والأسماء اللاتينية بكتلة LTR معزولة.

    يمنع انقلاب ترتيب الإحداثيات والرموز عند العرض في سياق عربي RTL.
    """
    global _LTR_RE
    if _LTR_RE is None:
        _LTR_RE = re.compile("|".join(f"(?:{p})" for p in LTR_PATTERNS))
    kept = []

    def _keep_bdi(m):
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"

    # لا نعيد تغليف bdi الموجود، خصوصًا شريحة الفترة التي يجب أن تبقى عزلًا واحدًا.
    protected = re.sub(
        r'<bdi\b[^>]*\bdir=["\']ltr["\'][^>]*>.*?</bdi>|'
        r'<bdi\b[^>]*\bclass=["\'][^"\']*\bbidi\b[^"\']*["\'][^>]*>.*?</bdi>',
        _keep_bdi,
        html,
        flags=re.S,
    )
    parts = re.split(r"(<[^>]+>)", protected)

    def _wrap(m):
        raw = re.sub(r"\s*([–—-])\s*", r"\1", m.group(0))
        if _PERIOD_RE.fullmatch(raw):
            return f'<bdi class="bidi" dir="ltr">{raw}</bdi>'
        return f'<span class="ltr">{m.group(0)}</span>'

    for k, part in enumerate(parts):
        if not part or part.startswith("<"):
            continue
        parts[k] = _LTR_RE.sub(_wrap, part)
    out = "".join(parts)
    return re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--meta", required=True, help="ملف بيانات الواجهة (إلزامي)")
    a = ap.parse_args()
    md_path = Path(a.md)
    if not md_path.exists():
        print(f"خطأ: ملف التقرير غير موجود: {md_path}", file=sys.stderr)
        return 2
    meta_path = Path(a.meta)
    if not meta_path.exists():
        print(f"خطأ: ملف الواجهة غير موجود: {meta_path}", file=sys.stderr)
        return 2
    load_section_policy(meta_path)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"خطأ: ملف الواجهة ليس JSON صالحًا ({e}).", file=sys.stderr)
        return 2
    try:
        p, count = build(md_path, Path(a.out), meta)
    except BuildError as e:
        print(f"فشل البناء: {e}", file=sys.stderr)
        return 3
    finally:
        # بند 15 (19 أكتوبر 2026): تفريغ سياق الرموز بعد كل جولة بناء،
        # فلا يتسرّب تاريخ إصدار إلى جولة تالية عند بناء عدة تقارير في العملية نفسها.
        BLK.reset_code_context()
    print(f"OK {p} ({p.stat().st_size} bytes, {count} أقسام)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
