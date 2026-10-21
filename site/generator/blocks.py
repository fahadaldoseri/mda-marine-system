#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
كتل عرض التقرير الصباحي المنفَّذة من توصيات التحسين (الدفعات الأولى والثانية والثالثة).

كل كتلة تُبنى فقط عند وجود بياناتها في ملف الواجهة، فلا يتعطل التقرير بنقص حقل.
المصدر الوحيد للبيانات هو ملف الواجهة؛ لا استنتاج ولا تعبئة تلقائية.
"""

import html
import re

import contextvars

from codes import label as _code_label, demote as _demote  # سياسة عرض الرموز (2+5)

# بند 15 من التدقيق المستقل (19 أكتوبر 2026): كان السياق قاموسًا عالميًا على مستوى الوحدة،
# فيتسرّب بين جولات البناء أو الخيوط ويُنتج عرضًا لرمز بتاريخ جولة سابقة.
# البديل: ContextVar معزول لكل جولة، مع تفريغ صريح بعد البناء.
_EMPTY_CTX = {"date": None, "official": {}}
_CODE_CTX = contextvars.ContextVar("mda_code_ctx", default=_EMPTY_CTX)


def set_code_context(report_date=None, official=None):
    """يضبط سياق عرض الرموز: تاريخ الإصدار وخريطة الأرقام الرسمية."""
    _CODE_CTX.set({"date": report_date, "official": dict(official or {})})


def reset_code_context():
    """يُفرّغ سياق الرموز بعد انتهاء الجولة، فلا يُستعمل في جولة تالية."""
    _CODE_CTX.set(dict(_EMPTY_CTX))


def code_context():
    """السياق الفعّال في هذه الجولة (للقراءة والتشخيص)."""
    return _CODE_CTX.get()


def code_text(value):
    """يبسّط أي رمز كامل داخل نص كتلة (بطاقة القرار، ما تغيّر، التحليل...)."""
    ctx = _CODE_CTX.get()
    return _demote(value or "", ctx["date"], ctx["official"])


def code_label(code, ref="", note=""):
    """صيغة العرض: مختصرة، ومدموجة برقم البلاغ الرسمي عند وجوده."""
    ctx = _CODE_CTX.get()
    off = ctx["official"].get(str(code or ""), "")
    return _code_label(code, ref, note or off, ctx["date"])

CONF_CLASS = {"عالية": "c-high", "متوسطة": "c-med", "منخفضة": "c-low"}
CONF_CANON = {"عالية": "عالية", "مرتفعة": "عالية", "متوسطة": "متوسطة", "متوسط": "متوسطة",
              "منخفضة": "منخفضة", "ضعيفة": "منخفضة"}

KIND_LABEL = {
    "confirm": "هجوم مؤكد",
    "inter": "واقعة عسكرية",
    "suspect": "غير محسوم",
    "bg": "خلفية مستمرة",
    "watch": "مراقبة مستمرة",
}

STATUS_CLASS = {"نشط": "s-active", "مستقر": "s-stable", "مغلق": "s-closed", "قائم": "s-active"}

TREND = {"up": ("▲", "t-up"), "down": ("▼", "t-down"), "flat": ("■", "t-flat")}

# ربط علامات البنود داخل النص بأصناف الشرائط
MARK_KIND = {
    "حقيقة": "k-fact",
    "واقعة": "k-fact",
    "تقدير تحليلي": "k-est",
    "تقدير": "k-est",
    "إعلامي": "k-info",
    "إعلام": "k-info",
    "خلفية": "k-bg",
    "مراقبة": "k-watch",
}


def trend_html(delta):
    """مؤشر تغيّر مختصر لبطاقة مؤشر: {dir, text} أو نص حر."""
    if not delta:
        return ""
    if isinstance(delta, str):
        return esc(delta)
    arrow, cls = TREND.get(delta.get("dir", "flat"), TREND["flat"])
    return f'<span class="trend {cls}">{arrow}</span> {esc(delta.get("text", ""))}'


def esc(t):
    return html.escape(str(t), quote=True)


def conf_chip(value):
    """وسم درجة الثقة بالصيغة المعيارية الموحدة (عالية / متوسطة / منخفضة)."""
    if not value:
        return ""
    canon = CONF_CANON.get(str(value).strip(), None)
    if not canon:
        return ""
    return f'<span class="conf {CONF_CLASS[canon]}">ثقة {canon}</span>'


def kind_strip(kind):
    label = KIND_LABEL.get(kind)
    if not label:
        return ""
    return f'<span class="kstrip k-{kind}">{label}</span>'


# ---------------------------------------------------------------- بطاقة القرار
_PT_CODE = re.compile(r"\(\d{2}-\d{2}\)")


def _points(value: str):
    """قائمة بنود: قائمة صريحة من المصدر، أو تعداد واضح (أكواد 19-01 أو فواصل منقوطة)، وإلا None."""
    if isinstance(value, list):
        pts = [str(x).strip() for x in value if str(x).strip()]
        return pts or None
    v = (value or "").strip()
    if len(_PT_CODE.findall(v)) >= 3 and "،" in v:
        parts = [p.strip() for p in re.split(r"\s*،\s+(?=و?\s*)", v) if p.strip()]
        if len(parts) >= 3:
            return parts
    if v.count("؛") >= 2:
        parts = [p.strip() for p in re.split(r"\s*؛\s*", v) if p.strip()]
        if len(parts) >= 2:
            return parts
    return None


def decision_card(dc, inline):
    """بطاقة القرار: ما تغيّر · الخطر · التوصيات · ما يُراقب."""
    if not isinstance(dc, dict):
        return ""
    rows = [
        ("ما تغيّر", dc.get("changed"), None),
        ("مستوى الخطر", dc.get("risk"), dc.get("risk_kind")),
        ("التوصيات", dc.get("action"), None),
        ("ما يُراقب خلال 24 ساعة", dc.get("watch"), None),
    ]
    cells = []
    for label, value, kind in rows:
        if not value:
            continue
        cls = f" risk-{kind}" if kind in ("high", "med", "low") else ""
        pts = _points(value)
        if pts:
            body = '<ul class="dc-list">' + "".join(
                f"<li>{inline(code_text(p))}</li>" for p in pts
            ) + "</ul>"
        else:
            body = inline(code_text(value))
        cells.append(
            f'<div class="dc-row{cls}"><div class="dc-l">{esc(label)}</div>'
            f'<div class="dc-v">{body}</div></div>'
        )
    if not cells:
        return ""
    foot = ""
    if dc.get("basis"):
        foot = f'<div class="dc-foot">أساس التقدير: {esc(dc["basis"])}</div>'
    return (
        '<section class="decision reveal" aria-label="عام">'
        '<h2 class="dc-title">عام</h2>'
        f'<div class="dc-grid">{"".join(cells)}</div>{foot}</section>'
    )


# ------------------------------------------------------ ما تغيّر منذ التقرير السابق
def changes_block(items, inline):
    if not items:
        return ""
    rows = []
    for it in items:
        kind = it.get("kind", "info")
        label = KIND_LABEL.get(kind) or {"new": "جديد", "closed": "أُغلق", "reclassified": "تصنيف تغيّر",
                                         "info": "متابعة", "ongoing": "مستمر"}.get(kind, "")
        ref = it.get("ref") or ""
        code = it.get("code") or ""
        meta_bits = []
        if code:
            meta_bits.append(f'<bdi class="bidi ev-code">{esc(code_label(code, ref))}</bdi>')
        if ref:
            meta_bits.append(f'<bdi class="bidi">{esc(ref)}</bdi>')
        rows.append(
            f'<li class="chg c-{esc(kind)}"><span class="chg-tag">{esc(label)}</span>'
            f'<span class="chg-txt">{inline(code_text(it.get("text", "")))} '
            f'{" ".join(meta_bits)}</span></li>'
        )
    return (
        '<section class="doc pri reveal" id="sec-00" aria-labelledby="h-00">'
        '<h2 id="h-00">ما تغيّر منذ التقرير السابق</h2><div class="h-rule"></div>'
        '<p class="sec-lede">ما استُجد، وما تغيّر تصنيفه، وما أُغلق.</p>'
        f'<ul class="changes">{"".join(rows)}</ul></section>'
    )


# ------------------------------------------------------------------ جداول موحدة
class Raw(str):
    """خلية HTML جاهزة: تُدرج كما هي ولا يعاد معالجتها في _table (وإلا ظهرت الوسوم نصًّا)."""


def _table(headers, rows, inline, num_cols=()):
    if not rows:
        return ""
    head = "".join(
        f'<th scope="col"{" class=\"num\"" if i in num_cols else ""}>{esc(h)}</th>'
        for i, h in enumerate(headers)
    )
    body = []
    for r in rows:
        tds = []
        for i, c in enumerate(r):
            s = c if isinstance(c, str) else ""
            # خلية جاهزة بـHTML (مثل <bdi> أو شارة حالة) لا تُعاد معالجتها، وإلا ظهرت الوسوم نصًّا للقارئ
            # خلية تحتوي وسومًا HTML جاهزة لا تُعاد معالجتها، وإلا ظهرت الوسوم نصًّا للقارئ
            ready = isinstance(c, Raw) or ("<" in s and ">" in s)
            cell = s if i in num_cols else (s if ready else inline(s))
            cls = ' class="num"' if i in num_cols else ""
            tds.append(f"<td{cls}>{cell}</td>")
        body.append(f"<tr>{''.join(tds)}</tr>")
    return (
        '<div class="tbl-wrap"><table><thead><tr>' + head + "</tr></thead><tbody>"
        + "".join(body) + "</tbody></table></div>"
    )


def indicators_table(items, inline):
    """جدول المؤشرات: المؤشر · الحالي · السابق · الاتجاه · الدلالة."""
    if not items:
        return ""
    rows = []
    for it in items:
        arrow, tcl = TREND.get(it.get("trend", "flat"), TREND["flat"])
        rows.append([
            it.get("name", ""),
            it.get("current", ""),
            it.get("previous", ""),
            f'<span class="trend {tcl}">{arrow}</span> {inline(it.get("delta", ""))}'.strip(),
            it.get("meaning", ""),
        ])
    return (
        '<h3>جدول المؤشرات</h3><p class="blk-lede">المؤشر · اليوم · الأمس · الاتجاه · حدود الرقم.</p>'
        + _table(["المؤشر", "هذا التقرير", "تقرير أمس", "الاتجاه", "الدلالة"], rows, inline, num_cols=(1, 2))
    )


def hypotheses_table(items, inline):
    if not items:
        return ""
    rows = []
    for it in items:
        rows.append([
            inline(it.get("statement", "")),
            inline(it.get("support", "")),
            inline(it.get("against", "")),
            conf_chip(it.get("likelihood")) or esc(it.get("likelihood", "")),
        ])
    return (
        '<h3>ترجيح الاحتمالات</h3><p class="blk-lede">الاحتمال · المؤيد · المعارض · النسبة.</p>'
        + _table(["الفرضية", "المؤيد", "المعارض", "درجة الاحتمال"], rows, inline)
    )


def gaps_table(items, inline):
    if not items:
        return ""
    rows = [[it.get("gap", ""), it.get("owner", ""), it.get("impact", "")] for it in items]
    return (
        '<h3>تكليفات المتابعة</h3><p class="blk-lede">الفجوة · الجهة القادرة على حسمها · أثر استمرارها.</p>'
        + _table(["الفجوة", "الجهة القادرة على الحسم", "أثر استمرارها"], rows, inline)
    )


def event_keys_table(items, inline):
    if not items:
        return ""
    rows = []
    for it in items:
        st = str(it.get("status", "")).strip()
        cls = STATUS_CLASS.get(st, "s-stable")
        rows.append([
            Raw(f'<bdi class="bidi ev-code">{esc(code_label(it.get("code", ""), it.get("ref", ""), f'{it.get("note", "")} {it.get("title", "")}'))}</bdi>'),
            Raw(inline(it.get("title", ""))),
            Raw(inline(it.get("area", ""))),
            Raw(f'<span class="st-badge {cls}">{esc(st)}</span>'),
            Raw(inline(it.get("note", ""))),
        ])
    return (
        '<h3>تتبع الوقائع</h3><p class="blk-lede">الرمز المختصر (والكامل في «الوقائع الجديدة») · المنطقة · الحالة.</p>'
        + _table(["الرمز", "الحدث", "المنطقة", "الحالة", "ملاحظة"], rows, inline)
    )


def timeline(items, inline):
    """خط زمني لمضيق هرمز: تكرار الوقائع وتوقيتها."""
    if not items:
        return ""
    mx = max((int(it.get("count", 1)) for it in items), default=1) or 1
    rows = []
    for it in items:
        c = int(it.get("count", 1))
        w = max(6.0, c / mx * 100.0)
        kind = it.get("kind", "confirm")
        rows.append(
            '<div class="tl-row">'
            f'<div class="tl-date bidi">{esc(it.get("date", ""))}</div>'
            f'<div class="tl-track"><div class="tl-fill k-{esc(kind)}" style="--w:{w:.1f}%"></div></div>'
            f'<div class="tl-num bidi">{c}</div>'
            f'<div class="tl-lbl">{inline(it.get("label", ""))}</div>'
            "</div>"
        )
    return (
        '<div class="viz tl-viz reveal"><h3>الخط الزمني لمضيق هرمز</h3>'
        + "".join(rows)
        + '<p class="src-note">المصدر: دفتر الأحداث التراكمي. الأعداد تعني سجلات مرصودة لا هجمات مؤكدة.</p></div>'
    )


# --------------------------------------------------------------------- التذييل
def glossary(items):
    if not items:
        return ""
    # عطل ك-43: صيغة البند الواحد في كل سطر جعلت القاموس يمتد صفحة كاملة عند
    # إضافة التعريفات المعيارية، فخالف حدّ تعبئة الصفحة الأخيرة. الصيغة المدمجة
    # تحفظ كل تعريف وترشّد المساحة: البنود متتابعة تفصلها علامة ·.
    parts = " · ".join(f"<b>{esc(k)}</b>: {esc(v)}" for k, v in items.items())
    return f'<div class="glossary"><b>قاموس الرموز والمصطلحات:</b> {parts}</div>'


def reading_key():
    return (
        '<div class="rkey no-print">'
        '<span class="rkey-t">مفتاح القراءة:</span>'
        '<span class="rk k-fact">واقعة مؤكدة</span>'
        '<span class="rk k-est">تقدير تحليلي</span>'
        '<span class="rk k-info">بند إعلامي</span>'
        '<span class="rk k-bg">خلفية مستمرة</span>'
        '<span class="rk k-watch">مراقبة مستمرة</span>'
        "</div>"
    )


def classification_banner(value):
    """بانر تصنيف الإصدار: عام / مقيّد / حساس."""
    if not value:
        return ""
    v = str(value).strip()
    kind = "c-open"
    if v in ("مقيّد", "restricted"):
        kind = "c-restricted"
    elif v in ("حساس", "sensitive", "سري"):
        kind = "c-sensitive"
    return f'<div class="cls-banner {kind}">تصنيف الإصدار: {esc(v)}</div>'


def source_reliability_table(data, inline):
    """ملحق موثوقية المصادر: المستشهد بها فقط، مع السلّمين والأساس."""
    rows = data.get("rows") or []
    if not rows:
        return ""
    checked = data.get("checked") or ""
    cited = data.get("cited") or len(rows)
    head = (
        '<h3>موثوقية المصادر</h3>'
        '<p class="blk-lede">الموثوقية للجهة، والمصداقية لدرجة التصديق، والأساس سبب الدرجة.</p>'
    )
    legend = (
        '<p class="src-note">سلّم الموثوقية: <b>A</b> مطلق · <b>B</b> جيد · <b>C</b> متوسط · '
        '<b>D</b> غير موثوق · <b>E</b> غير مؤكد · <b>F</b> لا يمكن الحكم عليه — '
        'وسلّم المصداقية: <b>1</b> مؤكد من مصدر آخر · <b>2</b> يُرجَّح صدقه · <b>3</b> يُحتمل صدقه · '
        '<b>4</b> مشكوك فيه · <b>5</b> غير مُرجَّح · <b>6</b> لا يمكن الحكم عليه.</p>'
    )
    note = f'<p class="src-note">يشمل الجدول <b>{cited}</b> مصدرًا مستشهدًا به من أصل <b>{checked}</b> مصدرًا مفحوصًا في هذا التشغيل؛ المصادر غير المستشهد بها لا تُدرج.</p>'
    trs = []
    for r in rows:
        trs.append(
            "<tr>"
            f'<td>{inline(str(r.get("num","")))}</td>'
            f'<td>{inline(str(r.get("name","")))}</td>'
            f'<td class="rel">{inline(str(r.get("rel","")))}</td>'
            f'<td class="rel">{inline(str(r.get("cred","")))}</td>'
            f'<td>{inline(str(r.get("basis","")))}</td>'
            "</tr>"
        )
    table = (
        '<div class="tbl-scroll"><table class="tbl rel-tbl"><thead><tr>'
        '<th>#</th><th>المصدر</th><th>الموثوقية</th><th>المصداقية</th><th>الأساس</th>'
        '</tr></thead><tbody>' + "".join(trs) + "</tbody></table></div>"
    )
    return head + legend + note + table


def render_block(name, data, inline):
    """موزّع كتل القسم. يرجع نصًا فارغًا عند غياب البيانات أو عدم معرفة الكتلة."""
    if not data:
        return ""
    if name == "indicators":
        return indicators_table(data, inline)
    if name == "hypotheses":
        return hypotheses_table(data, inline)
    if name == "gaps":
        return gaps_table(data, inline)
    if name == "event_keys":
        return event_keys_table(data, inline)
    if name == "timeline":
        return timeline(data, inline)
    if name == "source_reliability":
        return source_reliability_table(data, inline)
    if name == "vessel_identity":
        return vessel_identity_table(data, inline)
    if name == "report_classes":
        return report_classes_table(data, inline)
    if name == "intel_analysis":
        return intel_analysis(data, inline)
    return ""


# ------------------------------------------------------------------- أنماط الكتل
STYLE_BLOCKS = """
/* ---------- بطاقة القرار ---------- */
.decision{
  margin:24px 0 6px;border:1px solid var(--line-2);border-radius:var(--radius);
  background:linear-gradient(180deg,rgba(34,195,182,.07),rgba(12,22,38,.4));padding:18px 22px 16px
}
.decision .dc-title{
  font-family:"Noto Kufi Arabic",sans-serif;font-weight:600;font-size:17px;margin:0 0 12px;color:var(--accent)
}
.dc-grid{display:grid;gap:8px}
.dc-row{display:grid;grid-template-columns:1fr;gap:2px;align-items:start}
.dc-l{font-size:12.5px;line-height:1.35;color:var(--muted);padding-top:0}
.dc-list{margin:4px 0 0;padding-inline-start:20px}
.dc-list li{margin:4px 0;line-height:1.75}
.dc-v{font-size:16px;color:var(--ink);font-weight:500}
.dc-row.risk-high .dc-v{color:var(--danger)}
.dc-row.risk-med .dc-v{color:var(--warn)}
.dc-row.risk-low .dc-v{color:var(--ok)}
.dc-foot{font-size:12.5px;color:var(--faint);margin-top:10px;border-top:1px solid var(--line);padding-top:8px}

/* ---------- مفتاح القراءة ---------- */
.rkey{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin:18px 0 0;font-size:12.5px;color:var(--muted)}
.rkey-t{color:var(--faint)}
.rk{display:inline-flex;align-items:center;gap:7px}
.rk::before{content:"";width:3px;height:14px;border-radius:2px;background:var(--muted)}
.rk.k-fact::before{background:var(--ok)}
.rk.k-est::before{background:var(--info)}
.rk.k-info::before{background:var(--muted)}
.rk.k-bg::before{background:var(--line-2)}
.rk.k-watch::before{background:var(--warn)}

/* ---------- شرائط تمييز الحقيقة والتقدير ---------- */
ul.d-kinds{list-style:none;padding-inline-start:0}
ul.d-kinds li{position:relative;padding-inline-start:14px;margin:9px 0}
ul.d-kinds li::before{content:"";position:absolute;inset-inline-start:0;top:.5em;bottom:.5em;width:3px;border-radius:2px;background:var(--line-2)}
ul.d-kinds li.k-fact::before{background:var(--ok)}
ul.d-kinds li.k-est::before{background:var(--info)}
ul.d-kinds li.k-info::before{background:var(--muted)}
ul.d-kinds li.k-bg::before{background:var(--line-2)}
ul.d-kinds li.k-watch::before{background:var(--warn)}

/* ---------- درجة الثقة ---------- */
.conf{font-size:11.5px;border-radius:999px;padding:2px 9px;border:1px solid var(--line-2);white-space:nowrap;color:var(--ink-2)}
.conf.c-high{color:#cdf6e2;background:rgba(51,208,122,.16);border-color:rgba(51,208,122,.42)}
.conf.c-med{color:#ffe8c4;background:rgba(255,176,46,.15);border-color:rgba(255,176,46,.40)}
.conf.c-low{color:#d7e7ff;background:rgba(77,157,255,.15);border-color:rgba(77,157,255,.40)}
.kstrip{font-size:11.5px;border-radius:999px;padding:2px 9px;border:1px solid var(--line-2);color:var(--ink-2);margin-inline-end:7px;white-space:nowrap}
.kstrip.k-confirm{color:#ffd9d5;background:rgba(255,93,82,.15);border-color:rgba(255,93,82,.40)}
.kstrip.k-inter{color:#d7e7ff;background:rgba(77,157,255,.15);border-color:rgba(77,157,255,.40)}
.kstrip.k-suspect{color:#ffe8c4;background:rgba(255,176,46,.15);border-color:rgba(255,176,46,.40)}

/* ---------- ما تغيّر ---------- */
ul.changes{list-style:none;padding:0;margin:0;display:grid;gap:9px}
.changes li{display:flex;gap:11px;align-items:baseline}
.chg-tag{font-size:11.5px;border-radius:999px;padding:2px 10px;border:1px solid var(--line-2);color:var(--ink-2);background:var(--panel-3);flex:0 0 auto}
.chg.c-new .chg-tag{color:#d7e7ff;background:rgba(77,157,255,.15);border-color:rgba(77,157,255,.40)}
.chg.c-closed .chg-tag{color:#cdf6e2;background:rgba(51,208,122,.15);border-color:rgba(51,208,122,.40)}
.chg.c-reclassified .chg-tag{color:#ffe8c4;background:rgba(255,176,46,.15);border-color:rgba(255,176,46,.40)}
.chg.c-ongoing .chg-tag{color:#cfd8e3;background:rgba(148,163,184,.14);border-color:rgba(148,163,184,.38)}

/* ---------- رموز الأحداث والحالات ---------- */
.ev-code{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--accent);background:rgba(34,195,182,.10);border:1px solid rgba(34,195,182,.32);border-radius:6px;padding:0 5px}
.st-badge{font-size:11.5px;border-radius:999px;padding:2px 10px;border:1px solid var(--line-2);color:var(--ink-2);white-space:nowrap}
.st-badge.s-active{color:#ffd9d5;background:rgba(255,93,82,.14);border-color:rgba(255,93,82,.38)}
.st-badge.s-stable{color:#cdf6e2;background:rgba(51,208,122,.14);border-color:rgba(51,208,122,.38)}
.st-badge.s-closed{color:var(--muted);background:var(--panel-3)}
.trend{font-size:14px}
.trend.t-up{color:var(--danger)}
.trend.t-down{color:var(--ok)}
.trend.t-flat{color:var(--muted)}
.kpi .k-d{font-size:12px;margin-top:2px;font-family:"IBM Plex Mono",monospace}

/* ---------- الخط الزمني ---------- */
.tl-viz .tl-row{display:grid;grid-template-columns:96px 1fr 46px minmax(180px,1.4fr);gap:12px;align-items:center;margin:9px 0}
.tl-date{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--muted)}
.tl-track{height:9px;border-radius:999px;background:var(--panel-3);overflow:hidden}
.tl-fill{height:100%;border-radius:999px;width:var(--w,0);animation:tl-grow 1s cubic-bezier(.22,.8,.28,1) both}
@keyframes tl-grow{from{width:0}to{width:var(--w,0)}}
.tl-fill.k-confirm{background:var(--danger)}
.tl-fill.k-inter{background:var(--info)}
.tl-fill.k-suspect{background:var(--warn)}
.tl-fill.k-bg{background:var(--muted)}
.tl-num{font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--ink);text-align:end}
.tl-lbl{font-size:13px;color:var(--ink-2)}

/* ---------- بانر التصنيف والتعريفات ---------- */
.cls-banner{border:1px solid var(--line-2);border-radius:var(--radius-sm);padding:9px 14px;font-size:13px;margin:14px 0 0;background:var(--panel-2);color:var(--ink-2)}
.cls-banner.c-restricted{color:#ffe8c4;background:rgba(255,176,46,.10);border-color:rgba(255,176,46,.42)}
.cls-banner.c-sensitive{color:#ffd9d5;background:rgba(255,93,82,.10);border-color:rgba(255,93,82,.42)}
.glossary{margin-top:12px;font-size:13px;color:var(--muted)}
.glossary ul{margin:6px 0 0;padding-inline-start:20px}
.glossary b{color:var(--ink-2)}
@media (max-width:760px){
  .dc-row{grid-template-columns:1fr;gap:2px}
  .dc-l{font-size:12.5px}
  .tl-viz .tl-row{grid-template-columns:74px 1fr 34px;grid-template-areas:"d t n" "l l l";gap:6px 10px}
  .tl-date{grid-area:d}.tl-track{grid-area:t}.tl-num{grid-area:n}.tl-lbl{grid-area:l}
}
"""

STYLE_PRINT_BLOCKS = """
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
  .tl-fill{animation:none}
  .tl-fill.k-confirm{background:#9d2b25}
  .tl-fill.k-inter{background:#1f5f9f}
  .tl-fill.k-suspect{background:#7d5200}
  .tl-fill.k-bg{background:#7f92a8}
  ul.d-kinds li::before{width:3px}
  .decision,.tl-viz,.glossary{break-inside:avoid;page-break-inside:avoid}
  .decision{animation:none}
"""

STYLE_BLOCKS = STYLE_BLOCKS + """
/* ---------- ملحق موثوقية المصادر ---------- */
.tbl-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}
.tbl-scroll .rel-tbl{min-width:640px}
.rel-tbl td:nth-child(5){max-width:420px}
@media print{.tbl-scroll{overflow:visible}.tbl-scroll .rel-tbl{min-width:0}}
.rel-tbl td.rel{
  font-family:"IBM Plex Mono",monospace;font-weight:600;text-align:center;color:var(--accent)
}
@media print{.rel-tbl{font-size:10.5px}.rel-tbl td,.rel-tbl th{padding:3px 5px}}
"""

def intel_analysis(data, inline):
    """كتلة قسم «التحليل الاستخباري» (ح1–ح12): وسم الأسلوب · الاحتمال · الثقة · سند المصدر · الافتراضات · المؤشرات · تقييم دقة الأمس."""
    if not data:
        return ""
    out = []
    rows = []
    for label, key in (("الأسلوب التحليلي", "method"), ("العبارة الاحتمالية", "probability"),
                       ("درجة الثقة", "confidence"), ("سند المصدر", "source_grade")):
        val = (data.get(key) or "").strip()
        if val:
            rows.append(f'<div class="dc-row"><div class="dc-l">{esc(label)}</div>'
                        f'<div class="dc-v">{inline(code_text(val))}</div></div>')
    if rows:
        out.append('<div class="decision"><p class="dc-title">بطاقة التقدير التحليلي</p>'
                   f'<div class="dc-grid">{"".join(rows)}</div></div>')

    asm = data.get("assumptions") or []
    if asm:
        rws = [[a.get("assumption", ""), a.get("falsifier", "")] for a in asm]
        out.append('<h3>الافتراضات المعلنة</h3><p class="blk-lede">كل افتراض معلن، وما ينقضه.</p>'
                   + _table(["الافتراض", "ما ينقضه"], rws, inline))

    inds = data.get("indicators") or []
    if inds:
        rws = [[i.get("indicator", ""), i.get("confirms", ""), i.get("refutes", ""), i.get("state", "")]
               for i in inds]
        out.append('<h3>مؤشرات التحذير المبكر</h3><p class="blk-lede">المؤشر · ما يؤكده · ما ينفيه · الحالة.</p>'
                   + _table(["المؤشر", "ما يؤكده", "ما ينفيه", "الحالة"], rws, inline))

    yr = data.get("yesterday_review") or []
    if yr:
        rws = [[y.get("estimate", ""), y.get("outcome", ""), y.get("cause", "")] for y in yr]
        out.append('<h3>تقييم دقة تقديرات الأمس</h3><p class="blk-lede">التقدير · النتيجة · السبب.</p>'
                   + _table(["التقدير السابق", "النتيجة", "السبب"], rws, inline))
    return "".join(out)


def vessel_identity_table(data, inline):
    rows = data.get("rows") if isinstance(data, dict) else data
    if not rows:
        return ""
    cols = (("name", "السفينة"), ("imo", "IMO"), ("mmsi", "MMSI"), ("flag", "العلم"), ("former", "أسماء سابقة"), ("src", "المصدر"))
    html = ['<h3 class="blk-h">هوية السفن المستشهد بها</h3>',
            '<div class="tbl-scroll"><table class="tbl rel-tbl"><thead><tr>' +
            "".join(f"<th>{h}</th>" for _, h in cols) + "</tr></thead><tbody>"]
    for r in rows:
        html.append("<tr>" + "".join(f'<td>{inline(str(r.get(k, "—")))}</td>' for k, _ in cols) + "</tr>")
    html.append("</tbody></table></div>")
    note = data.get("note") if isinstance(data, dict) else None
    if note:
        html.append(f'<p class="src-note">{inline(str(note))}</p>')
    return "".join(html)


def report_classes_table(data, inline):
    rows = data.get("rows") if isinstance(data, dict) else data
    if not rows:
        return ""
    html = ['<h3 class="blk-h">تصنيف البلاغات</h3>',
            '<p class="src-note">الأصناف منفصلة ولا تُجمع في رقم واحد.</p>',
            '<div class="tbl-scroll"><table class="tbl rel-tbl"><thead><tr>'
            '<th>الصنف</th><th>العدد</th><th>التغير عن أمس</th></tr></thead><tbody>']
    for r in rows:
        html.append("<tr><td>" + str(r.get("class", "—")) + "</td><td>" + str(r.get("count", "—")) +
                    "</td><td>" + str(r.get("delta", "—")) + "</td></tr>")
    html.append("</tbody></table></div>")
    return "".join(html)
