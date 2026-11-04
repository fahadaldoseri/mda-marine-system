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
import threat_card as TC
from display_format import format_release_version, format_update_label

import blocks as BLK
import codes

_NO_PREFIX_CHANGE = {"new": "جديد", "closed": "أُغلق", "reclassified": "تصنيف تغيّر",
                     "info": "متابعة", "ongoing": "مستمر"}
HERO_MAX_CHANGES = 2
HERO_MAX_ACTIONS = 2
HERO_KPI_MODERN_FROM = "2026-10-31"

DAILY_TITLE_FIXED = "التقرير اليومي للأمن البحري والأوضاع الراهنة في المنطقة"


def first_sentence(text: str) -> str:
    """أول جملة من الفقرة التمهيدية: حتى أول نقطة يليها فراغ أو نهاية النص."""
    t = (text or "").strip()
    if not t:
        return ""
    m = re.search(r"\.(?=\s|$)", t)
    return t[: m.start()].strip() if m else t


_CARD_ARABIC_EXACT = (
    (
        "Attack:UKMTO has received a report of an incident 40NM south of Lavan Island,…",
        "أفادت الجهة البحرية البريطانية بتلقي بلاغ عن واقعة على بُعد 40 ميلًا بحريًا جنوب جزيرة لافان.",
    ),
    (
        "Combined Task Force 151 concludes counter-piracy Operation Tidal Wave 2",
        "اختتمت القوة البحرية المشتركة 151 عملية مكافحة القرصنة «الموجة المدّية 2».",
    ),
    (
        "Combined Task Force 151 concludes counter-piracy Operation Tidal Wave",
        "اختتمت القوة البحرية المشتركة 151 عملية مكافحة القرصنة «الموجة المدّية».",
    ),
)
_CARD_ARABIC_TERMS = (
    (r"(?<![A-Za-z])UKMTO(?![A-Za-z])", "مركز التجارة البحرية البريطانية"),
    (r"(?<![A-Za-z])JMIC(?![A-Za-z])", "مركز المعلومات البحرية المشترك"),
    (r"(?<![A-Za-z])IMO(?![A-Za-z])", "المنظمة البحرية الدولية"),
    (r"(?<![A-Za-z])AIS(?![A-Za-z])", "نظام التعريف الآلي"),
    (r"(?<![A-Za-z])VHF(?![A-Za-z])", "الاتصالات اللاسلكية البحرية"),
    (r"(?<![A-Za-z])Z1(?![A-Za-z])", "مضيق هرمز وخليج عُمان والخليج العربي"),
    (r"(?<![A-Za-z])Z2(?![A-Za-z])", "باب المندب والبحر الأحمر"),
    (r"(?<![A-Za-z])Z3(?![A-Za-z])", "بحر العرب"),
    (r"(?<![A-Za-z])Z4(?![A-Za-z])", "القرن الأفريقي"),
    (r"(?<![A-Za-z])Z5(?![A-Za-z])", ""),
)


def _arabic_card_text(text: str) -> str:
    """Translate meaning for the Arabic card without changing the official table."""
    value = str(text or "").strip()
    for source, target in _CARD_ARABIC_EXACT:
        value = value.replace(source, target)
    for pattern, target in _CARD_ARABIC_TERMS:
        value = re.sub(pattern, target, value)
    return value


def _arabic_count(count: int, noun: str) -> str:
    """Return a grammatically valid counter for zero, one, two, and 3+."""
    count = max(0, int(count))
    if noun == "warnings":
        if count == 0:
            return "لا تحذيرات"
        if count == 1:
            return "تحذير واحد"
        if count == 2:
            return "تحذيران"
        return f"{count} تحذيرات"
    if count == 0:
        return "لا بنود"
    if count == 1:
        return "بند واحد"
    if count == 2:
        return "بندان"
    return f"{count} بنود"


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


def screen_hero(meta, *, esc, inline, report_date, official, threat_cls,
                doc_mode=False, archived=False, card_targets=None):
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
    if doc_mode:
        h1 = codes.demote(esc(headline), report_date, official)
        sub = ""
    else:
        h1 = esc(DAILY_TITLE_FIXED)
        sub = f'<p class="sc-sub">{codes.demote(esc(headline), report_date, official)}</p>'
    eyebrow = "تقرير خاص" if doc_mode else ""

    chips = []
    gen = meta.get("generated_label") or ""
    gen_display = format_update_label(gen)
    if gen and archived == "none":
        pass  # السجل التراكمي: لا عمر إصدار يُقاس، وشريحة «آخر تحديث» تكفي
    elif gen and archived:
        chips.append(f'<span class="sc-chip sc-arch">إصدار أرشيفي · صدر <b>{esc(gen_display)}</b></span>')
    elif gen and not doc_mode:
        chips.append(f'<span class="sc-chip sc-fresh" data-gen="{esc(gen)}" hidden>عمر الإصدار <b class="sc-age"></b></span>')
    if meta.get("version"):
        chips.append(_chip("رقم الإصدار", esc(format_release_version(meta["version"]))))
    if gen and (not archived or archived == "none"):
        chips.append(_chip("آخر تحديث", esc(gen_display)))
    elif gen and doc_mode:
        chips.append(_chip("آخر تحديث", esc(gen_display)))
    if meta.get("window"):
        chips.append(_chip("فترة التغطية", esc(meta["window"])))
    # العمود الجانبي: مستوى التهديد ثم المؤشرات
    side = []
    threat = meta.get("threat_level") or ""
    dc = meta.get("decision_card") if isinstance(meta.get("decision_card"), dict) else {}
    if threat:
        _zj = TC.load_zones_site(report_date) if report_date else None
        if _zj:
            # بطاقة القطاعات الأربعة بدل البطاقة المفردة (قرار المالك 2026-10-30)
            side.append(TC.zones_card(_zj, variant="screen"))
        else:
            basis = ""
            if dc.get("basis"):
                basis = (f'<details class="sc-basis" open><summary>أساس التقدير</summary>'
                         f'<p>{esc(dc["basis"])}</p></details>')
            side.append(
                f'<div class="sc-threat {esc(threat_cls)}"><div class="sc-tl">مستوى التهديد</div>'
                f'<div class="sc-tv">{esc(threat)}</div>{basis}</div>')
    hero_kpis = meta.get("hero_kpis") or []
    if hero_kpis:
        if report_date >= HERO_KPI_MODERN_FROM:
            rows = {}
            for k in hero_kpis:
                rows.setdefault(int(k.get("row") or 1), []).append(k)
            # قرار المالك 2026-11-04: الصف الأول 4 بطاقات، والصفوف التالية 3 (أو 2 للبطاقتين الدائمتين).
            if (1 not in rows or len(rows[1]) != 4 or len(rows) < 2
                    or any(len(v) not in (2, 3, 4) for r, v in rows.items() if r != 1)):
                raise ValueError("hero_kpis: الصف الأول 4 بطاقات والصفوف التالية 3 (أو 2 للبطاقتين الدائمتين)؛ فشل مغلق")
            def _screen_tile(k):
                acc = k.get("accent", "ok")
                if acc not in ("ok", "info", "warn", "danger"):
                    acc = "ok"
                title = k.get("title", "")
                detail = k.get("detail", "")
                tag = k.get("tag", "")
                tag_html = f'<span class="sc-k-tag">{inline(tag)}</span>' if tag else ""
                return (f'<div class="sc-kpi hero-kpi acc-{acc}" data-kpi-id="{esc(k.get("id", ""))}"><div class="sc-kl">{inline(title)}{tag_html}</div>'
                        f'<div class="sc-kv bidi">{esc(k.get("value", ""))}</div>'
                        f'<div class="sc-kn">{inline(detail)}</div></div>')
            risk = meta.get("hero_risk_patterns") or []
            risk_html = ('<div class="sc-k-risk" aria-label="أنماط الخطر"><span class="sc-k-risk-label">أنماط الخطر</span>'
                         + "".join(f'<span class="sc-k-risk-tag">{inline(x)}</span>' for x in risk) + '</div>') if risk else ""
            row1 = "".join(_screen_tile(k) for k in hero_kpis if k.get("row") == 1)
            row2 = "".join(_screen_tile(k) for k in hero_kpis if k.get("row") == 2)
            side.append(f'<div class="sc-kpis hero-kpis">{risk_html}<div class="sc-kpi-row sc-kpi-row-1">{row1}</div><div class="sc-kpi-row sc-kpi-row-2">{row2}</div></div>')
        else:
            legacy_tiles = []
            for k in hero_kpis:
                acc = k.get("accent", "ok")
                if acc not in ("ok", "info", "warn", "danger"):
                    acc = "ok"
                delta = BLK.trend_html(k.get("delta")) if k.get("delta") else ""
                note = inline(k.get("note", "")) if k.get("note") else ""
                legacy_tiles.append(
                    f'<div class="sc-kpi acc-{acc}"><div class="sc-kl">{inline(k.get("label", ""))}</div>'
                    f'<div class="sc-kv bidi">{esc(k.get("value", ""))}</div>'
                    + (f'<div class="sc-kd">{delta}</div>' if delta else "")
                    + (f'<div class="sc-kn">{note}</div>' if note else "") + "</div>"
                )
            side.append(f'<div class="sc-kpis">{"".join(legacy_tiles)}</div>')

    official_cards = meta.get("official_cards") or []
    if official_cards:
        official_html = []
        for card in official_cards:
            layers = card.get("layers") or {}
            layer_html = []
            for key in ("daily", "cumulative", "updated"):
                layer = layers.get(key) or {}
                layer_html.append(
                    f'<div class="sc-official-layer"><span class="sc-official-label">{esc(layer.get("label", ""))}</span>'
                    f'<b class="sc-official-value bidi">{esc(layer.get("value", ""))}</b>'
                    f'<span class="sc-official-source">{esc(layer.get("source", "غير متاح"))}</span></div>'
                )
            badges = "".join(f'<span class="sc-k-tag">{esc(x)}</span>' for x in (card.get("badges") or []))
            extras = []
            if card.get("period"):
                extras.append(f'الفترة: {esc(card["period"])} · المتوسط: <b class="bidi">{esc(card.get("average", ""))}</b> · الأعلى: <b class="bidi">{esc(card.get("high", ""))}</b> · الأدنى: <b class="bidi">{esc(card.get("low", ""))}</b>')
            if card.get("constraint"):
                extras.append(esc(card["constraint"]))
            extra_html = "".join(f'<p class="sc-official-extra">{x}</p>' for x in extras)
            official_html.append(
                f'<article class="sc-official-card" data-official-card-id="{esc(card.get("id", ""))}">'
                f'<h3>{esc(card.get("title", ""))} {badges}</h3>'
                + (f'<p class="sc-official-basis">{esc(card["basis"])}</p>' if card.get("basis") else "")
                + (f'<p class="sc-official-basis">{esc(card.get("source_label", ""))}</p>' if card.get("source_label") else "")
                + f'<div class="sc-official-layers">{"".join(layer_html)}</div>{extra_html}</article>'
            )
        side.append(f'<section class="sc-official-cards" aria-label="المستجدات الرسمية"><h2 class="sc-h2">المستجدات الرسمية</h2><div class="sc-official-grid">{"".join(official_html)}</div></section>')

    # أهم الأخبار المتعلقة بالأمن البحري (شاشة): خلاصة مُركّزة لكل صف + العدد + رابط إلى القسم في صفحته.
    # إصلاح ك-239 (2026-10-28): كانت الصفوف تُفرَغ لأن سكربت الروابط كان يحذف الرابط عند غياب
    # القسم من الصفحة بعد نقله إلى «إضافات». القاعدة الآن: لا يُحذف أي عنصر، ويُوجَّه الرابط للصفحة البديلة.
    rows = []

    def _gist(items, limit=2, width=64):
        out = []
        for raw in items[:limit]:
            t = re.split(r"[.،؛]", _arabic_card_text(str(raw).strip()))[0].strip()
            t = re.sub(r"\s+", " ", t)
            if len(t) > width:
                # ك-497: لا يُقطع الملخص في وسط عبارة؛ يُقطع عند نهاية جملة أو
                # عند فاصل معنى، وإلا استُعملت الكلمة الأخيرة كاملة.
                cut = t[:width]
                for sep in (". ", "، ", "؛ ", ": "):
                    i = cut.rfind(sep)
                    if i >= width * 0.6:
                        cut = cut[: i + len(sep)].rstrip()
                        break
                else:
                    cut = cut.rsplit(" ", 1)[0] + "…"
                t = cut
            if t:
                out.append(t)
        return " · ".join(out)

    # البنية المعتمدة: ثلاثة صفوف فقط. كل عداد ومرساة يأتيان من الهدف المبني،
    # لا من طول حقول meta ولا من ترتيب رقمي ثابت.
    targets = dict(card_targets or {})
    changes = [c for c in (dc.get("changed") or []) if isinstance(c, str)]
    if not changes:
        changes = [c for c in (meta.get("changes") or []) if isinstance(c, str)]
    changed_count = int(targets.get("changed_count") or len(changes))
    changed_href = targets.get("changed_href") or "/additions.html#sec-00"
    changed_goto = targets.get("changed_title") or "ما تغيّر منذ التقرير السابق"
    rows.append(
        '<div class="sc-row"><div class="sc-l">خلال 24 ساعة السابقة</div>'
        f'<div class="sc-v"><p class="sc-gist">{inline(_gist(changes, limit=2))}</p>'
        f'<p class="sc-more">{_arabic_count(changed_count, "items")} · '
        f'<a href="{esc(changed_href)}" data-goto="{esc(changed_goto)}" data-alt="{esc(changed_href)}">التفاصيل</a></p></div></div>')

    warning_texts = [_arabic_card_text(x) for x in (targets.get("warning_texts") or []) if str(x).strip()]
    if not warning_texts:
        warning_texts = ["المركز البريطاني / المركز البحري المشترك"]
    warning_count = (int(targets["warning_count"]) if "warning_count" in targets
                     else len(warning_texts))
    warning_href = targets.get("warning_href") or f"/reports/{report_date}.html#sec-06"
    warning_gist = _gist(warning_texts, limit=2)
    rows.append(
        '<div class="sc-row"><div class="sc-l">التحذيرات والتنبيهات النشطة</div>'
        f'<div class="sc-v"><p class="sc-gist">{inline(warning_gist)}</p>'
        f'<p class="sc-more">{_arabic_count(warning_count, "warnings")} · '
        f'<a href="{esc(warning_href)}" data-goto="التحذيرات والتنبيهات النشطة" data-alt="{esc(warning_href)}">القسم الرسمي</a></p></div></div>')

    watch = _list_items(dc.get("watch"))
    watch_count = int(targets["watch_count"]) if "watch_count" in targets else len(watch)
    watch_href = targets.get("watch_href") or "/additions.html#sec-04-sub-02"
    watch_title = targets.get("watch_title") or "علامات الإنذار المبكر 24–72 ساعة"
    rows.append(
        '<div class="sc-row"><div class="sc-l">ما يُراقب خلال 24 ساعة</div>'
        f'<div class="sc-v"><p class="sc-gist">{inline(_gist(watch, limit=2))}</p>'
        f'<p class="sc-more">{_arabic_count(watch_count, "items")} · '
        f'<a href="{esc(watch_href)}" data-goto="{esc(watch_title)}" data-alt="{esc(watch_href)}">المؤشرات الكاملة</a></p></div></div>')
    card = ""
    if rows:
        card = (f'<section class="sc-card" aria-label="أهم الأخبار المتعلقة بالأمن البحري"><h2 class="sc-h2">أهم الأخبار المتعلقة بالأمن البحري</h2>'
                f'{"".join(rows)}</section>')

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
        + (f'<p class="sc-eyebrow">{esc(eyebrow)}</p>' if eyebrow else "")
        + f'<h2 class="sc-h1">{h1}</h2>{sub}{lede}'
        + f'<div class="sc-chips">{"".join(chips)}</div>{grid}</div>'
    )


SCREEN_CSS = """
/* ===== طبقة الشاشة: لا تُطبَّق في وسائط الطباعة ===== */
@media screen{
.masthead,.decision,.kpis{display:none}
.topbar{position:static}
.topbar-inner{padding-block:7px}
/* شريط واحد: مع شريط الموقع تنتقل أزرار الطباعة والمظهر وحجم الخط إليه ويُخفى شريط الإصدار */
body:has(.site-nav) .topbar{display:none}
.sc-hero{margin:20px 0 6px}
.sc-eyebrow{font-size:14.5px;color:var(--muted);margin:0 0 6px;text-align:center}
.sc-sub{font-size:15.5px;color:var(--ink-2);margin:0 0 10px;text-align:center;line-height:1.8}
.sc-h1{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:clamp(21px,2.05vw,28px);line-height:1.65;margin:0 0 6px;text-wrap:balance;text-align:center}
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
.sc-grid{display:flex;flex-direction:column;gap:22px;align-items:stretch}
/* بلا بطاقة قرار (السجل التراكمي): مستوى التهديد والمؤشرات في صف واحد بدل عمود يترك نصف العرض فارغًا */
.sc-grid.sc-solo{grid-template-columns:minmax(0,1fr)}
.sc-solo .sc-side{grid-template-columns:repeat(auto-fit,minmax(210px,1fr));align-items:stretch}
.sc-solo .sc-kpis{display:contents}
.sc-side{display:contents;min-width:0}
.sc-threat{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px;box-shadow:inset 0 2px 0 0 rgba(34,195,182,.55)}
.sc-tl{font-size:13.5px;color:var(--muted)}
.sc-tv{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:32px;line-height:1.45}
.sc-threat.risk-high .sc-tv{color:var(--danger)}
.sc-threat.risk-med .sc-tv{color:var(--warn)}
.sc-threat.risk-low .sc-tv{color:var(--ok)}
.sc-basis{margin-top:8px;font-size:13.5px;color:var(--muted)}
.sc-basis summary{cursor:pointer;color:var(--ink-2)}
.sc-basis p{margin:6px 0 0;line-height:1.8}
.sc-kpis{display:grid;gap:16px;direction:rtl;order:3}
.sc-official-cards{order:4;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px;min-width:0}
.sc-official-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.sc-official-card{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;text-align:right;direction:rtl;min-width:0}
.sc-official-card h3{font-family:"Noto Kufi Arabic",sans-serif;font-size:16px;line-height:1.55;margin:0 0 5px;color:var(--accent)}
.sc-official-basis,.sc-official-extra{font-size:12.5px;line-height:1.65;color:var(--muted);margin:3px 0}
.sc-official-layers{display:grid;gap:7px;margin-top:10px}
.sc-official-layer{display:grid;grid-template-columns:145px minmax(75px,auto) minmax(0,1fr);gap:8px;align-items:baseline;border-top:1px solid var(--line);padding-top:7px}
.sc-official-label{font-size:12.5px;color:var(--muted)}
.sc-official-value{font-family:"IBM Plex Mono",monospace;font-size:18px;line-height:1.35;text-align:right;direction:rtl;color:var(--ink)}
.sc-official-source{font-size:12.5px;line-height:1.5;color:var(--muted);overflow-wrap:anywhere}
/* تنسيق مضغوط مقروء لبطاقات المستجدات (قرار المالك 2026-10-31: خفض الاكتظاظ) */
.sc-official-layer{display:grid;grid-template-columns:minmax(0,auto) minmax(0,1fr);gap:2px 10px;align-items:baseline;padding:6px 0;border-top:1px dashed var(--line)}
.sc-official-layer:first-child{border-top:0}
.sc-official-label{color:var(--muted);font-size:13px}
.sc-official-value{font-weight:700}
.sc-official-source{grid-column:1 / -1;color:var(--muted);font-size:12px;line-height:1.6}
.sc-kpi-row{display:grid;gap:16px;direction:rtl}
.sc-kpi-row-1{grid-template-columns:repeat(4,minmax(0,1fr))}
.sc-kpi-row-2{grid-template-columns:repeat(4,minmax(0,1fr))}
.sc-kpi{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius);padding:12px 16px;position:relative;overflow:hidden;height:auto;min-height:148px;text-align:right;direction:rtl;display:flex;flex-direction:column}
.sc-kpi:before{content:"";position:absolute;inset-inline-start:0;top:0;bottom:0;width:3px;background:var(--accent)}
.sc-kpi.acc-info:before{background:var(--info)}.sc-kpi.acc-warn:before{background:var(--warn)}
.sc-kpi.acc-danger:before{background:var(--danger)}.sc-kpi.acc-ok:before{background:var(--ok)}
.sc-kl{font-size:14px;color:var(--muted);line-height:1.6}
.sc-k-tag{display:inline-block;margin-inline-start:6px;padding:1px 7px;border:1px solid var(--line-2);border-radius:999px;color:var(--ink-2);font-size:12px;line-height:1.4;white-space:nowrap}
.sc-kv{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:26px;line-height:1.3;text-align:right;direction:rtl}
.sc-kd{font-size:14px;color:var(--ink-2)}
.sc-kn{font-size:13px;color:var(--muted);line-height:1.7;margin-top:3px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;flex:0 0 auto}
.sc-k-risk{display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:var(--muted);font-size:12px}
.sc-k-risk-tag{border:1px solid var(--line-2);border-radius:999px;padding:1px 8px;color:var(--ink-2)}
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
  .sc-threat{order:2}.sc-card{order:1}.sc-kpis{order:3;display:grid;gap:12px}.sc-official-cards{order:4}
  .sc-solo .sc-kpis{display:grid}
  .sc-kpi-row-1,.sc-kpi-row-2{grid-template-columns:1fr;gap:12px}
  .sc-official-grid{grid-template-columns:1fr;gap:12px}
  .sc-official-layer{grid-template-columns:minmax(0,1fr) auto;gap:4px 8px}
  .sc-official-source{grid-column:1 / -1}
  .sc-row{grid-template-columns:minmax(0,1fr);gap:2px}
  .sc-list li{grid-template-columns:minmax(0,1fr);gap:3px}
  .sc-list li .sc-code{justify-self:start}
}
@media (max-width:700px){
  /* شريط الأقسام صفّ واحد قابل للتمرير بدل كتلة من الأزرار تدفع المحتوى */
  .sc-jump{flex-wrap:nowrap;overflow-x:auto;padding-bottom:4px;scrollbar-width:thin}
  .sc-jump a{flex:0 0 auto;white-space:nowrap}
  .sc-jump-hint{display:none;align-items:center;gap:2px;font-size:12.5px;color:var(--muted);padding:0 6px;flex:0 0 auto}
  .sc-toolbar.is-scroll .sc-jump-hint{display:inline-flex}
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
  // ك-317: طبقة الشاشة ثنائية اللغة — كل نص تُبنيه هذه الطبقة يأتي من قاموس اللغة نفسها،
  // فالصفحة الإنجليزية لا تعرض نصًا عربيًا حيًّا ولا تفقد أقسامها المفتوحة افتراضيًا.
  var EN = (d.documentElement.getAttribute('lang') || 'ar').toLowerCase().indexOf('en') === 0;
  var T = EN
    ? { fresh:'Current', late:'Delayed', old:'Outdated', ltHour:'less than an hour', hour:' h ago', day:' d ago', before:' · ',
        two:'2 items', many:' items', aria:'Toggle section 「{t}」', jump:'Jump to sections', openAll:'Expand all', closeAll:'Collapse all' }
    : { fresh:'حديث', late:'متأخر', old:'قديم', ltHour:'أقل من ساعة', hour:' ساعة', day:' يومًا', before:' · قبل ',
        two:'بندان', many:' بنود', aria:'طيّ قسم «{t}» أو فتحه', jump:'انتقال إلى الأقسام', openAll:'فتح الكل', closeAll:'طيّ الكل' };
  // عمر الإصدار: كلمة ولون معًا، ويُحسب عند فتح الصفحة
  var f = d.querySelector('[data-gen]');
  if (f) {
    var s = (f.getAttribute('data-gen') || '').trim();
    var m = s.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::\d{2})?\s*(?:UTC|Z)?$/);
    var t = Date.parse(m ? m[1] + 'T' + m[2] + ':00Z' : s);
    if (isNaN(t)) { f.parentNode.removeChild(f); }
    else {
      var h = Math.max(0, (Date.now() - t) / 36e5), cls, word, txt;
      if (h <= 30) { cls = 'f-ok'; word = T.fresh; }
      else if (h <= 54) { cls = 'f-warn'; word = T.late; }
      else { cls = 'f-old'; word = T.old; }
      txt = h < 1 ? T.ltHour : (h < 48 ? Math.round(h) + T.hour : Math.round(h / 24) + T.day);
      f.querySelector('.sc-age').textContent = word + T.before + txt;
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
  // والتحذيرات والتنبيهات النشطة، وسجل IMO والحوادث المؤكدة.
  var openRe = /الخلاصة|التوجيهات التشغيلية|مؤشرات الموقف|سجل الأحداث|الوقائع الجديدة|مستوى التهديد|التحذيرات والتنبيهات النشطة|سجل IMO|Summary|Operational Guidance|Situation Indicators|Event Log|Threat Level|Active warnings and advisories|IMO/;
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
    // ك-336: المعاينة عنوان توجيهي لا نسخة من نص القسم — تُقصّ عند 58 محرفًا بحدّ كلمة
    if (t && t.length > 58) { t = t.slice(0, 57).replace(/\s+\S*$/, '') + '\u2026'; }
    if (!n && !t) return null;
    var el = d.createElement('div'); el.className = 'sc-peek no-print';
    if (n > 1) { var b = d.createElement('b'); b.textContent = n === 2 ? T.two : (n + T.many); el.appendChild(b); }
    if (t) { var sp = d.createElement('span'); sp.textContent = t; el.appendChild(sp); }
    return el;
  }
  var items = [], seen = {};
  secs.forEach(function (sec) {
    var h = sec.querySelector('h2'); if (!h) return;
    var title = h.textContent.trim();
    var b = d.createElement('button');
    b.type = 'button'; b.className = 'sc-toggle no-print';
    b.setAttribute('aria-label', T.aria.replace('{t}', title));
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
    var nav = d.createElement('nav'); nav.className = 'sc-jump'; nav.setAttribute('aria-label', T.jump);
    items.forEach(function (it) {
      var a = d.createElement('a'); a.href = '#' + it.sec.id; a.textContent = it.label;
      a.addEventListener('click', function () { openSec(it.sec); });
      nav.appendChild(a);
    });
    var all = d.createElement('div'); all.className = 'sc-all';
    [[T.openAll, false], [T.closeAll, true]].forEach(function (p) {
      var b = d.createElement('button'); b.type = 'button'; b.textContent = p[0];
      b.addEventListener('click', function () { items.forEach(function (it) { setState(it.sec, it.btn, p[1]); }); });
      all.appendChild(b);
    });
    var hint = d.createElement('span'); hint.className = 'sc-jump-hint';
    hint.setAttribute('aria-hidden', 'true'); hint.textContent = '◂ ▸';
    function syncHint(){
      var over = nav.scrollWidth > nav.clientWidth + 4;
      bar.classList.toggle('is-scroll', over);
      if (!over) return;
      var atEnd = nav.scrollLeft + nav.clientWidth >= nav.scrollWidth - 4;
      var atStart = nav.scrollLeft <= 4;
      hint.textContent = atStart ? '◂ ▸' : (atEnd ? '◂' : '◂ ▸');
    }
    nav.addEventListener('scroll', syncHint, {passive:true});
    window.addEventListener('resize', syncHint);
    bar.appendChild(nav); bar.appendChild(hint); bar.appendChild(all);
    setTimeout(syncHint, 60);
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
