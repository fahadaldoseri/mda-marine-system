#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
طبقة الشاشة للتقرير اليومي: القرار والخريطة فوق، والأقسام تحتها قابلة للطي.

قاعدة الأمان (قرار الشكل المجمّد v3): هذه الطبقة للشاشة فقط ولا تمسّ PDF ولا Word.
  1. كل HTML هنا بصنف no-print، فيُحجب في الطباعة ويحذفه محوّل Word.
  2. كل CSS هنا داخل @media screen، فلا أثر له على وسائط print.
  3. العناصر الأصلية (الترويسة وأهم الأخبار المتعلقة بالأمن البحري والمؤشرات) تبقى في الصفحة كما هي للطباعة،
     وتُخفى على الشاشة فقط.
  4. السكربت لا يعدّل إلا أصنافًا بالبادئة sc- وصنف sc-collapsed، وهذا الصنف لا يؤثر إلا داخل @media screen.
المصدر الوحيد للبيانات ملف الواجهة (meta). لا استنتاج ولا تعبئة.
"""

import re

import blocks as BLK
import codes

_NO_PREFIX_CHANGE = {"new": "جديد", "closed": "أُغلق", "reclassified": "تصنيف تغيّر",
                     "info": "متابعة", "ongoing": "مستمر"}
HERO_MAX_CHANGES = 2
HERO_MAX_ACTIONS = 2


from section_counts import for_title as _sec_count


def first_sentence(text: str) -> str:
    """أول جملة من الفقرة التمهيدية: حتى أول نقطة يليها فراغ أو نهاية النص."""
    t = (text or "").strip()
    if not t:
        return ""
    m = re.search(r"\.(?=\s|$)", t)
    return t[: m.start()].strip() if m else t


def _list_items(value):
    if isinstance(value, list):  # قائمة صريحة من الملف
        return [str(x).strip() for x in value if str(x).strip()]
    pts = BLK._points(value)
    if pts:
        return pts
    v = value if isinstance(value, str) else ""
    return [v.strip()] if v.strip() else []


def _chip(label, value_html, extra=""):
    return f'<span class="sc-chip{extra}">{label} <b>{value_html}</b></span>'


def screen_hero(meta, *, esc, inline, report_date, official, threat_cls, rkey_html="",
                doc_mode=False, archived=False):
    """كتلة القرار فوق الطيّ: العنوان والشرائح وحالة التهديد والمؤشرات وأهم الأخبار المتعلقة بالأمن البحري.

    doc_mode: التقارير الخاصة، وعنوانها الكامل هو العنوان الظاهر (كانت بلا عنوان على الشاشة).
    archived: إصدار غير الأحدث، فلا شارة عمر تنذر بالقِدم بل وسم أرشيفي محايد.
    """
    title = meta.get("title") or ""
    if doc_mode:
        headline = meta.get("headline") or title
    else:
        headline = meta.get("screen_headline") or first_sentence(meta.get("lede") or "") \
            or meta.get("headline") or title
    h1 = codes.demote(esc(headline), report_date, official)
    eyebrow = "تقرير خاص" if doc_mode else title

    chips = []
    gen = meta.get("generated_label") or ""
    if gen and archived == "none":
        pass  # السجل التراكمي: لا عمر إصدار يُقاس، وشريحة «آخر تحديث» تكفي
    elif gen and archived:
        chips.append(f'<span class="sc-chip sc-arch">إصدار أرشيفي · صدر <b class="bidi">{esc(gen)}</b></span>')
    elif gen and not doc_mode:
        chips.append(f'<span class="sc-chip sc-fresh" data-gen="{esc(gen)}" hidden>عمر الإصدار <b class="sc-age"></b></span>')
    if meta.get("version"):
        chips.append(_chip("رقم الإصدار", f'<span class="bidi">{esc(meta["version"])}</span>'))
    if gen and (not archived or archived == "none"):
        chips.append(_chip("آخر تحديث", f'<span class="bidi">{esc(gen)}</span>'))
    elif gen and doc_mode:
        chips.append(_chip("آخر تحديث", f'<span class="bidi">{esc(gen)}</span>'))
    if meta.get("window"):
        chips.append(_chip("فترة التغطية", esc(meta["window"])))
    appr, auto, man, cit = (meta.get("sources_approved"), meta.get("sources_checked"),
                            meta.get("sources_manual_reference_count"), meta.get("sources_cited"))
    if appr not in (None, ""):
        _parts = [f'<span class="bidi">{esc(appr)}</span> معتمدة']
        if auto not in (None, ""):
            _parts.append(f'<span class="bidi">{esc(auto)}</span> بالمسار الآلي')
        if man not in (None, ""):
            _parts.append(f'<span class="bidi">{esc(man)}</span> بالفحص اليدوي')
        chips.append(_chip("المصادر", " · ".join(_parts)))
    if cit not in (None, ""):
        chips.append(_chip("مستشهد بها", f'<span class="bidi">{esc(cit)}</span>'))

    # العمود الجانبي: مستوى التهديد ثم المؤشرات
    side = []
    threat = meta.get("threat_level") or ""
    dc = meta.get("decision_card") if isinstance(meta.get("decision_card"), dict) else {}
    if threat:
        basis = ""
        if dc.get("basis"):
            basis = (f'<details class="sc-basis"><summary>أساس التقدير</summary>'
                     f'<p>{esc(dc["basis"])}</p></details>')
        side.append(
            f'<div class="sc-threat {esc(threat_cls)}"><div class="sc-tl">مستوى التهديد</div>'
            f'<div class="sc-tv">{esc(threat)}</div>{basis}</div>')
    kp = []
    for k in meta.get("hero_kpis") or []:
        acc = k.get("accent", "ok")
        if acc not in ("ok", "info", "warn", "danger"):
            acc = "ok"
        delta = BLK.trend_html(k.get("delta")) if k.get("delta") else ""
        note = inline(k.get("note", "")) if k.get("note") else ""
        kp.append(
            f'<div class="sc-kpi acc-{acc}"><div class="sc-kl">{inline(k.get("label", ""))}</div>'
            f'<div class="sc-kv bidi">{esc(k.get("value", ""))}</div>'
            + (f'<div class="sc-kd">{delta}</div>' if delta else "")
            + (f'<div class="sc-kn">{note}</div>' if note else "") + "</div>")
    if kp:
        side.append(f'<div class="sc-kpis">{"".join(kp)}</div>')

    # أهم الأخبار المتعلقة بالأمن البحري (شاشة): خلاصة مُركّزة لكل صف + العدد + رابط إلى القسم في صفحته.
    # إصلاح ك-239 (2026-10-28): كانت الصفوف تُفرَغ لأن سكربت الروابط كان يحذف الرابط عند غياب
    # القسم من الصفحة بعد نقله إلى «إضافات». القاعدة الآن: لا يُحذف أي عنصر، ويُوجَّه الرابط للصفحة البديلة.
    rows = []

    def _gist(items, limit=2, width=64):
        out = []
        for raw in items[:limit]:
            t = re.split(r"[.،؛]", str(raw).strip())[0].strip()
            t = re.sub(r"\s+", " ", t)
            if len(t) > width:
                t = t[:width].rsplit(" ", 1)[0] + "…"
            if t:
                out.append(t)
        return " · ".join(out)

    # مصدر «ما تغيّر»: نصوص أهم الأخبار المتعلقة بالأمن البحري (سلاسل)، لا سجل التغييرات البنيوي
    changes = [c for c in (dc.get("changed") or []) if isinstance(c, str)]
    if not changes:
        changes = [c for c in (meta.get("changes") or []) if isinstance(c, str)]
    if changes:
        gist = _gist(changes, limit=2)
        total = _sec_count(meta.get("date") or meta.get("iso") or meta.get("report_date") or "", "ما تغيّر منذ التقرير السابق", default=0) or len(meta.get("changes") or []) or len(changes)
        rows.append(
            '<div class="sc-row"><div class="sc-l">ما تغيّر</div>'
            f'<div class="sc-v"><p class="sc-gist">{inline(gist)}</p>'
            f'<p class="sc-more">{total} بندًا · '
            '<a href="/additions.html#sec-00" data-goto="ما تغيّر" data-alt="/additions.html#sec-00">التفاصيل</a></p></div></div>')
    acts = _list_items(dc.get("action"))
    n_acts = _sec_count(meta.get("date") or meta.get("iso") or meta.get("report_date") or "", "التوجيهات التشغيلية", default=0) or len(acts)
    if acts:
        rows.append(
            '<div class="sc-row"><div class="sc-l">التوجيهات التشغيلية</div>'
            f'<div class="sc-v"><p class="sc-gist">{inline(_gist(acts, limit=2))}</p>'
            f'<p class="sc-more">{n_acts} بنود · '
            '<a href="/additions.html#sec-03" data-goto="التوجيهات التشغيلية" data-alt="/additions.html#sec-03">القسم الكامل</a></p></div></div>')
    watch = _list_items(dc.get("watch"))
    n_watch = _sec_count(meta.get("date") or meta.get("iso") or meta.get("report_date") or "", "مؤشرات التحذير المبكر", default=0) or len(watch)
    if watch:
        rows.append(
            '<div class="sc-row"><div class="sc-l">ما يُراقب خلال 24 ساعة</div>'
            f'<div class="sc-v"><p class="sc-gist">{inline(_gist(watch, limit=2))}</p>'
            f'<p class="sc-more">{n_watch} بنود · '
            '<a href="/additions.html#sec-07" data-goto="علامات الإنذار المبكر" data-alt="/additions.html#sec-07">المؤشرات الكاملة</a></p></div></div>')
    key = ""
    if rkey_html:
        key = rkey_html.replace('class="rkey no-print"', 'class="sc-rkey"')
    card = ""
    if rows:
        card = (f'<section class="sc-card" aria-label="أهم الأخبار المتعلقة بالأمن البحري"><h2 class="sc-h2">أهم الأخبار المتعلقة بالأمن البحري</h2>'
                f'{"".join(rows)}{key}</section>')

    grid = ""
    if side or card:
        solo = "" if card else " sc-solo"
        # قرار المالك 2026-10-28: أهم الأخبار المتعلقة بالأمن البحري في يمين الشاشة والبطاقات في اليسار (تبديل مواضع)
        grid = (f'<div class="sc-grid{solo}">{card}<div class="sc-side">{"".join(side)}</div></div>')
    lede = ""
    if doc_mode and meta.get("lede"):
        lede = f'<p class="sc-lede">{inline(meta["lede"])}</p>'
    return (
        '<div class="sc-hero no-print">'
        f'<p class="sc-eyebrow">{esc(eyebrow)}</p><h2 class="sc-h1">{h1}</h2>{lede}'
        f'<div class="sc-chips">{"".join(chips)}</div>{grid}</div>'
    )


SCREEN_CSS = """
/* ===== طبقة الشاشة: لا تُطبَّق في وسائط الطباعة ===== */
@media screen{
.masthead,.decision,.kpis,.rkey{display:none}
.topbar{position:static}
.topbar-inner{padding-block:7px}
/* شريط واحد: مع شريط الموقع تنتقل أزرار الطباعة والمظهر وحجم الخط إليه ويُخفى شريط الإصدار */
body:has(.site-nav) .topbar{display:none}
.sc-hero{margin:20px 0 6px}
.sc-eyebrow{font-size:14.5px;color:var(--muted);margin:0 0 6px}
.sc-h1{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:clamp(21px,2.05vw,28px);line-height:1.65;margin:0 0 12px;text-wrap:balance}
.sc-h1 .ltr{white-space:nowrap}
.sc-lede{font-size:15.5px;line-height:1.9;color:var(--ink-2);margin:0 0 12px;max-width:none}
.sc-chips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 20px}
.sc-chip{font-size:14px;color:var(--ink-2);border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:3px 12px}
.sc-chip b{color:var(--ink);font-weight:600}
.sc-fresh.f-ok{border-color:var(--ok);color:var(--ok)}
.sc-fresh.f-ok b{color:var(--ok)}
.sc-fresh.f-warn{border-color:var(--warn);color:var(--warn)}
.sc-fresh.f-warn b{color:var(--warn)}
.sc-fresh.f-old{border-color:var(--danger);color:var(--danger)}
.sc-fresh.f-old b{color:var(--danger)}
.sc-arch{color:var(--muted)}
.sc-grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:22px;align-items:start}
/* بلا بطاقة قرار (السجل التراكمي): مستوى التهديد والمؤشرات في صف واحد بدل عمود يترك نصف العرض فارغًا */
.sc-grid.sc-solo{grid-template-columns:minmax(0,1fr)}
.sc-solo .sc-side{grid-template-columns:repeat(auto-fit,minmax(210px,1fr));align-items:stretch}
.sc-solo .sc-kpis{display:contents}
.sc-side{display:grid;gap:12px;min-width:0}
.sc-threat{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px;box-shadow:inset 0 2px 0 0 rgba(34,195,182,.55)}
.sc-tl{font-size:13.5px;color:var(--muted)}
.sc-tv{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:32px;line-height:1.45}
.sc-threat.risk-high .sc-tv{color:var(--danger)}
.sc-threat.risk-med .sc-tv{color:var(--warn)}
.sc-threat.risk-low .sc-tv{color:var(--ok)}
.sc-basis{margin-top:8px;font-size:13.5px;color:var(--muted)}
.sc-basis summary{cursor:pointer;color:var(--ink-2)}
.sc-basis p{margin:6px 0 0;line-height:1.8}
.sc-kpis{display:grid;gap:10px}
.sc-kpi{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius);padding:12px 16px;position:relative;overflow:hidden}
.sc-kpi:before{content:"";position:absolute;inset-inline-start:0;top:0;bottom:0;width:3px;background:var(--accent)}
.sc-kpi.acc-info:before{background:var(--info)}.sc-kpi.acc-warn:before{background:var(--warn)}
.sc-kpi.acc-danger:before{background:var(--danger)}.sc-kpi.acc-ok:before{background:var(--ok)}
.sc-kl{font-size:14px;color:var(--muted);line-height:1.6}
.sc-kv{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:26px;line-height:1.3}
.sc-kd{font-size:14px;color:var(--ink-2)}
.sc-kn{font-size:13px;color:var(--muted);line-height:1.7;margin-top:3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.sc-card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:22px 26px;min-width:0;box-shadow:inset 0 2px 0 0 rgba(34,195,182,.55)}
.sc-h2{font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:19px;margin:0 0 6px;color:var(--accent)}
.sc-row{display:grid;grid-template-columns:150px minmax(0,1fr);gap:16px;padding:14px 0;border-top:1px solid var(--line)}
.sc-row:first-of-type{border-top:0}
.sc-l{font-size:13.5px;color:var(--muted);line-height:1.6;padding-top:3px}
.sc-v{font-size:15.5px;color:var(--ink);min-width:0}
.sc-list,.sc-acts,.sc-watch{list-style:none;margin:0;padding:0}
.sc-list li{display:grid;grid-template-columns:118px minmax(0,1fr);gap:12px;padding:6px 0;line-height:1.8}
.sc-code{font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--accent);background:rgba(34,195,182,.10);border:1px solid rgba(34,195,182,.32);border-radius:6px;padding:0 6px;white-space:nowrap;height:fit-content;text-align:center}
.sc-nocode{visibility:hidden}
.sc-tag{display:inline-block;font-size:13px;border-radius:999px;padding:0 9px;border:1px solid var(--line-2);color:var(--ink-2);background:var(--panel-3);margin-inline-end:4px;line-height:1.7}
.sc-acts li{display:grid;grid-template-columns:26px minmax(0,1fr);gap:10px;padding:5px 0;line-height:1.8}
.sc-acts li i{font-style:normal;font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:12.5px;background:var(--accent);color:var(--accent-ink);border-radius:6px;width:24px;height:24px;display:grid;place-items:center;margin-top:4px}
.sc-watch li{padding:5px 0;line-height:1.8}
.sc-gist{font-size:15.5px;line-height:1.75;color:var(--ink);margin:0 0 4px}
.sc-plain{color:var(--accent);display:inline-block;padding:3px 0;min-height:24px}
.sc-more{font-size:14px;margin:6px 0 0}
.sc-more a{color:var(--accent);text-decoration:underline;text-underline-offset:3px;display:inline-block;padding:3px 0;min-height:24px}
.sup-banner a{display:inline-block;padding:3px 0;min-height:24px}
.sc-rkey{display:flex;gap:16px;flex-wrap:wrap;font-size:14px;color:var(--muted);margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}
.sc-rkey .rkey-t{color:var(--muted)}
/* الأقسام القابلة للطي */
.sc-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:26px 0 14px}
.sc-jump{display:flex;gap:6px;flex-wrap:wrap;flex:1 1 360px}
.sc-jump a{font-size:14px;color:var(--ink-2);text-decoration:none;border:1px solid var(--line);background:var(--panel);padding:3px 12px;border-radius:999px;min-height:28px;display:inline-flex;align-items:center}
.sc-jump a:hover,.sc-jump a:focus-visible{border-color:var(--accent);color:var(--accent);outline:none}
.sc-all{display:flex;gap:6px}
.sc-all button{font:inherit;font-size:13.5px;cursor:pointer;color:var(--ink);background:var(--panel-2);border:1px solid var(--line-2);border-radius:8px;padding:4px 14px;min-height:32px}
.sc-toggle{position:absolute;top:18px;inset-inline-end:22px;font:inherit;font-size:20px;line-height:1;cursor:pointer;color:var(--accent);background:var(--panel-3);border:1px solid var(--line-2);border-radius:8px;width:34px;height:34px;padding:0}
.sc-toggle:before{content:"−"}
.sc-toggle[aria-expanded="false"]:before{content:"+"}
section.doc{position:relative}
.sc-toggle:focus-visible,.sc-all button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
section.doc.sc-collapsed > *:not(h2):not(.sc-toggle):not(.sc-peek){display:none}
section.doc.sc-collapsed{padding-bottom:12px}
section.doc > h2{cursor:pointer}
/* معاينة القسم المطوي: عدّ البنود وأول سطر، بلا مساس بنص العنوان (فهرس PDF) */
.sc-peek{display:none}
section.doc.sc-collapsed > .sc-peek{display:flex;gap:10px;align-items:baseline;margin:4px 0 0;padding-inline-end:48px;color:var(--muted);font-size:14.5px;line-height:1.8}
.sc-peek b{flex:0 0 auto;font-weight:600;font-size:13px;color:var(--accent);border:1px solid var(--line-2);background:var(--panel-3);border-radius:999px;padding:0 10px}
.sc-peek span{min-width:0;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
/* المظهر النهاري للخريطة والأرقام: قيم الخريطة النهارية كانت معرّفة للطباعة فقط فتبقى الخريطة داكنة وتسمياتها غير مقروءة */
body.daylight{
  --map-sea:#f7fafc;--map-land:#d6e0ea;--map-coast:#64809b;--map-border:#96a7b9;
  --map-grid:#d3dce6;--map-grid-lbl:#5a7086;--map-label:#20303f;--map-country:#5a7086;
  --map-sea-label:#4f657c;--map-strait:#8a2b25;
}
body.daylight .sc-acts li i{color:#ffffff}
body.daylight .sc-tag{color:#31465c}
/* إصلاح الخطوط على الشاشة: isolate_ltr يلفّ IBM داخل CSS فيبطل الإعلان ويسقط النص إلى Times New Roman */
body{font-family:"IBM Plex Sans Arabic","Noto Kufi Arabic","Segoe UI",Tahoma,system-ui,sans-serif}
.kpi .k-v,section.doc code,td.num,th.num,.bar-row .bv,.mp-grid-lbl,.mp-events .mp-num,.lg-num,.cite-ref,.ev-code,.kpi .k-d,.tl-date,.tl-num,.rel-tbl td.rel{font-family:"IBM Plex Mono",ui-monospace,monospace}
.mp-places text{font-family:"IBM Plex Sans Arabic","Noto Kufi Arabic",sans-serif}
/* قراءة أوضح بكثافة معتدلة */
.chip,.tag,.ev-code,.conf,.kstrip,.chg-tag,.st-badge{font-size:13.5px}
.kpi .k-l,.kpi .k-n,.brand-sub{font-size:13.5px}
.lg-num{font-size:12.5px;width:22px;height:22px}
.cite-ref{font-size:12.5px}
.sn-name em,.ar-risk,.hc-tag{font-size:12.5px}
.foot a,.foot-note a,.sc-foot a,.glossary a{display:inline-block;padding:3px 0}
@media (max-width:1000px){
  /* الجوال: مستوى التهديد ثم أهم الأخبار المتعلقة بالأمن البحري ثم المؤشرات (القرار قبل الأرقام) */
  .sc-grid,.sc-grid.sc-solo{display:flex;flex-direction:column;gap:14px}
  .sc-side{display:contents}
  .sc-threat{order:1}.sc-card{order:2}.sc-kpis{order:3;display:grid;gap:10px}
  .sc-solo .sc-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
  .sc-row{grid-template-columns:minmax(0,1fr);gap:2px}
  .sc-list li{grid-template-columns:minmax(0,1fr);gap:3px}
  .sc-list li .sc-code{justify-self:start}
}
@media (max-width:700px){
  /* شريط الأقسام صفّ واحد قابل للتمرير بدل كتلة من الأزرار تدفع المحتوى */
  .sc-jump{flex-wrap:nowrap;overflow-x:auto;padding-bottom:4px;scrollbar-width:thin}
  .sc-jump a{flex:0 0 auto;white-space:nowrap}
  .sc-card{padding:18px 16px}
  .sc-threat{padding:16px}
  .sc-tv{font-size:28px}
}
}
/* الحركة: عند طيّ الأقسام على الشاشة يبدأ الرسم المتحرّك لحظة التحويل إلى الطباعة فيلتقطه PDF ناقصًا
   (شريط الخط الزمني). الحالة النهائية هي المقصودة، وهي ما كانت تُلتقط قبل الطيّ. */
@media print{.tl-fill{animation:none}}

"""

SCREEN_JS = r"""
(function(){
  var d = document;
  // عمر الإصدار: كلمة ولون معًا، ويُحسب عند فتح الصفحة
  var f = d.querySelector('[data-gen]');
  if (f) {
    var s = (f.getAttribute('data-gen') || '').trim();
    var m = s.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::\d{2})?\s*(?:UTC|Z)?$/);
    var t = Date.parse(m ? m[1] + 'T' + m[2] + ':00Z' : s);
    if (isNaN(t)) { f.parentNode.removeChild(f); }
    else {
      var h = Math.max(0, (Date.now() - t) / 36e5), cls, word, txt;
      if (h <= 30) { cls = 'f-ok'; word = 'حديث'; }
      else if (h <= 54) { cls = 'f-warn'; word = 'متأخر'; }
      else { cls = 'f-old'; word = 'قديم'; }
      txt = h < 1 ? 'أقل من ساعة' : (h < 48 ? Math.round(h) + ' ساعة' : Math.round(h / 24) + ' يومًا');
      f.querySelector('.sc-age').textContent = word + ' · قبل ' + txt;
      f.className += ' ' + cls; f.hidden = false;
    }
  }
  // الأقسام القابلة للطي: بلا سكربت تبقى كلها مفتوحة
  var main = d.querySelector('main'); if (!main) return;
  var secs = [].slice.call(main.querySelectorAll(':scope > section.doc'));
  // تُفتح الخلاصة والتوجيهات ومؤشرات الموقف وسجل الأحداث في كل نوع من الصفحات،
  // فإن لم يوجد شيء منها فُتح القسم الأول. (ك-298: سجل الأحداث صار في التقرير اليومي،
  // فلا يُعرض مطويًا فيُحجب المحتوى عن القارئ.)
  // ك-304: تُفتح أيضًا الأقسام التي طلب المالك إدراجها في التقرير اليومي: مستوى التهديد،
  // والتحذيرات والنشرات الرسمية، وسجل IMO والحوادث المؤكدة.
  var openRe = /الخلاصة|التوجيهات التشغيلية|مؤشرات الموقف|سجل الأحداث|الوقائع الجديدة|مستوى التهديد|التحذيرات والنشرات الرسمية|سجل IMO/;
  function setState(sec, btn, collapsed) {
    sec.classList.toggle('sc-collapsed', collapsed);
    btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  }
  // نص العنصر بمسافة بين أجزائه، وما كان رمزًا أو معرّفًا لاتينيًا يُعزل اتجاهيًا فلا ينقلب ترتيبه
  function flat(el) {
    var w = d.createTreeWalker(el, NodeFilter.SHOW_TEXT), out = [], n;
    while ((n = w.nextNode())) {
      var tx = n.textContent.replace(/\s+/g, ' ').trim(); if (!tx) continue;
      var iso = n.parentElement && n.parentElement.closest('bdi,.ltr,.bidi,.ev-code');
      out.push(iso ? '\u2066' + tx + '\u2069' : tx);
    }
    return out.join(' ');
  }
  // معاينة القسم المطوي: عدّ البنود وأول سطر من نص القسم نفسه، بلا استنتاج
  function peekOf(sec) {
    var n = sec.querySelectorAll(':scope > ul > li, :scope > ol > li, :scope > .tbl-wrap tbody tr, :scope > table tbody tr').length;
    var first = sec.querySelector(':scope > p:not(.sec-lede), :scope > ul > li, :scope > ol > li, :scope > .tbl-wrap tbody tr, :scope > table tbody tr');
    var t = first ? flat(first) : '';
    if (!n && !t) return null;
    var el = d.createElement('div'); el.className = 'sc-peek no-print';
    if (n > 1) { var b = d.createElement('b'); b.textContent = n === 2 ? 'بندان' : (n <= 10 ? n + ' بنود' : n + ' بندًا'); el.appendChild(b); }
    if (t) { var sp = d.createElement('span'); sp.textContent = t; el.appendChild(sp); }
    return el;
  }
  var items = [], seen = {};
  secs.forEach(function (sec) {
    var h = sec.querySelector('h2'); if (!h) return;
    var title = h.textContent.trim();
    var b = d.createElement('button');
    b.type = 'button'; b.className = 'sc-toggle no-print';
    b.setAttribute('aria-label', 'طيّ قسم «' + title + '» أو فتحه');
    if (sec.id) b.setAttribute('aria-controls', sec.id);
    var pk = peekOf(sec); if (pk) sec.appendChild(pk);
    sec.appendChild(b);
    b.addEventListener('click', function () { setState(sec, b, !sec.classList.contains('sc-collapsed')); });
    h.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('a,button')) return;
      setState(sec, b, !sec.classList.contains('sc-collapsed'));
    });
    setState(sec, b, !openRe.test(title));
    seen[title] = (seen[title] || 0) + 1;
    items.push({sec: sec, btn: b, title: title, label: seen[title] > 1 ? title + ' (' + seen[title] + ')' : title});
  });
  function openSec(sec) {
    items.forEach(function (it) { if (it.sec === sec) setState(sec, it.btn, false); });
  }
  if (items.length && !items.some(function (it) { return !it.sec.classList.contains('sc-collapsed'); })) {
    setState(items[0].sec, items[0].btn, false);
  }
  if (items.length) {
    var bar = d.createElement('div'); bar.className = 'sc-toolbar no-print';
    var nav = d.createElement('nav'); nav.className = 'sc-jump'; nav.setAttribute('aria-label', 'انتقال إلى الأقسام');
    items.forEach(function (it) {
      var a = d.createElement('a'); a.href = '#' + it.sec.id; a.textContent = it.label;
      a.addEventListener('click', function () { openSec(it.sec); });
      nav.appendChild(a);
    });
    var all = d.createElement('div'); all.className = 'sc-all';
    [['فتح الكل', false], ['طيّ الكل', true]].forEach(function (p) {
      var b = d.createElement('button'); b.type = 'button'; b.textContent = p[0];
      b.addEventListener('click', function () { items.forEach(function (it) { setState(it.sec, it.btn, p[1]); }); });
      all.appendChild(b);
    });
    bar.appendChild(nav); bar.appendChild(all);
    main.parentNode.insertBefore(bar, main);
  }
  // روابط «كاملة» في أهم الأخبار المتعلقة بالأمن البحري — القاعدة: لا يُحذف أي عنصر (منع إفراغ الصف)
  [].forEach.call(d.querySelectorAll('[data-goto]'), function (a) {
    var key = a.getAttribute('data-goto');
    var hit = items.filter(function (it) { return it.title.indexOf(key) >= 0; })[0];
    if (hit) {
      a.href = '#' + hit.sec.id;
      a.addEventListener('click', function () { openSec(hit.sec); });
      return;
    }
    var alt = a.getAttribute('data-alt');
    if (alt) { a.href = alt; return; }
    var plain = d.createElement('span');
    plain.className = 'sc-plain';
    plain.textContent = a.textContent;
    a.parentNode.replaceChild(plain, a);
  });
  // رابط مباشر إلى قسم مطوي: يُفتح
  if (location.hash) {
    var tg = d.getElementById(location.hash.slice(1));
    items.forEach(function (it) { if (it.sec === tg || (tg && it.sec.contains(tg))) openSec(it.sec); });
  }
})();
"""
