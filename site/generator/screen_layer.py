#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
طبقة الشاشة للتقرير اليومي: القرار والخريطة فوق، والأقسام تحتها قابلة للطي.

قاعدة الأمان (قرار الشكل المجمّد v3): هذه الطبقة للشاشة فقط ولا تمسّ PDF ولا Word.
  1. كل HTML هنا بصنف no-print، فيُحجب في الطباعة ويحذفه محوّل Word.
  2. كل CSS هنا داخل @media screen، فلا أثر له على وسائط print.
  3. العناصر الأصلية (الترويسة وبطاقة القرار والمؤشرات) تبقى في الصفحة كما هي للطباعة،
     وتُخفى على الشاشة فقط.
  4. السكربت لا يعدّل إلا أصنافًا بالبادئة sc- وصنف sc-collapsed، وهذا الصنف لا يؤثر إلا داخل @media screen.
المصدر الوحيد للبيانات ملف الواجهة (meta). لا استنتاج ولا تعبئة.
"""

import re

import blocks as BLK
import codes

_NO_PREFIX_CHANGE = {"new": "جديد", "closed": "أُغلق", "reclassified": "تصنيف تغيّر",
                     "info": "متابعة", "ongoing": "مستمر"}
HERO_MAX_CHANGES = 5
HERO_MAX_ACTIONS = 3


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


def screen_hero(meta, *, esc, inline, report_date, official, threat_cls, rkey_html=""):
    """كتلة القرار فوق الطيّ: العنوان والشرائح وحالة التهديد والمؤشرات وبطاقة القرار."""
    title = meta.get("title") or ""
    headline = meta.get("screen_headline") or first_sentence(meta.get("lede") or "") \
        or meta.get("headline") or title
    h1 = codes.demote(esc(headline), report_date, official)

    chips = []
    gen = meta.get("generated_label") or ""
    if gen:
        chips.append(f'<span class="sc-chip sc-fresh" data-gen="{esc(gen)}" hidden>عمر الإصدار <b class="sc-age"></b></span>')
    if meta.get("version"):
        chips.append(_chip("رقم النسخة", f'<span class="bidi">{esc(meta["version"])}</span>'))
    if gen:
        chips.append(_chip("آخر تحديث", f'<span class="bidi">{esc(gen)}</span>'))
    if meta.get("window"):
        chips.append(_chip("فترة التغطية", esc(meta["window"])))
    chk, cit = meta.get("sources_checked"), meta.get("sources_cited")
    if chk not in (None, "") and cit not in (None, ""):
        chips.append(_chip("المصادر", f'<span class="bidi">{esc(cit)}</span> من <span class="bidi">{esc(chk)}</span>'))
    elif chk not in (None, ""):
        chips.append(_chip("مصادر مفحوصة", f'<span class="bidi">{esc(chk)}</span>'))

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

    # بطاقة القرار
    rows = []
    changes = meta.get("changes") or []
    if changes:
        lis = []
        for it in changes[:HERO_MAX_CHANGES]:
            kind = it.get("kind", "info")
            lab = BLK.KIND_LABEL.get(kind) or _NO_PREFIX_CHANGE.get(kind, "")
            ref, code = it.get("ref") or "", it.get("code") or ""
            code_html = (f'<bdi class="sc-code bidi">{esc(BLK.code_label(code, ref))}</bdi>'
                         if code else '<span class="sc-code sc-nocode"></span>')
            tag = f'<span class="sc-tag sc-k-{esc(kind)}">{esc(lab)}</span> ' if lab else ""
            lis.append(f'<li>{code_html}<span>{tag}{inline(BLK.code_text(it.get("text", "")))}</span></li>')
        more = ""
        if len(changes) > HERO_MAX_CHANGES:
            more = f'<p class="sc-more"><a href="#sec-00" data-goto="ما تغيّر">كل ما تغيّر ({len(changes)})</a></p>'
        rows.append(f'<div class="sc-row"><div class="sc-l">ما تغيّر</div>'
                    f'<div class="sc-v"><ul class="sc-list">{"".join(lis)}</ul>{more}</div></div>')
    acts = _list_items(dc.get("action"))
    if acts:
        lis = "".join(f'<li><i>{n}</i><span>{inline(BLK.code_text(a))}</span></li>'
                      for n, a in enumerate(acts[:HERO_MAX_ACTIONS], 1))
        more = ""
        if len(acts) > HERO_MAX_ACTIONS:
            more = (f'<p class="sc-more"><a href="#" data-goto="التوجيهات التشغيلية">'
                    f'التوجيهات كاملة ({len(acts)})</a></p>')
        rows.append(f'<div class="sc-row"><div class="sc-l">التوجيهات التشغيلية</div>'
                    f'<div class="sc-v"><ol class="sc-acts">{lis}</ol>{more}</div></div>')
    watch = _list_items(dc.get("watch"))
    if watch:
        lis = "".join(f'<li>{inline(BLK.code_text(w))}</li>' for w in watch)
        rows.append(f'<div class="sc-row"><div class="sc-l">ما يُراقب خلال 24 ساعة</div>'
                    f'<div class="sc-v"><ul class="sc-watch">{lis}</ul></div></div>')
    key = ""
    if rkey_html:
        key = rkey_html.replace('class="rkey no-print"', 'class="sc-rkey"')
    card = ""
    if rows:
        card = (f'<section class="sc-card" aria-label="بطاقة القرار"><h2 class="sc-h2">بطاقة القرار</h2>'
                f'{"".join(rows)}{key}</section>')

    grid = ""
    if side or card:
        grid = (f'<div class="sc-grid"><div class="sc-side">{"".join(side)}</div>{card}</div>')
    return (
        '<div class="sc-hero no-print">'
        f'<p class="sc-eyebrow">{esc(title)}</p><h1 class="sc-h1">{h1}</h1>'
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
.sc-h1{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:clamp(23px,2.7vw,32px);line-height:1.6;margin:0 0 12px;text-wrap:balance}
.sc-chips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 20px}
.sc-chip{font-size:14px;color:var(--ink-2);border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:3px 12px}
.sc-chip b{color:var(--ink);font-weight:600}
.sc-fresh.f-ok{border-color:var(--ok);color:var(--ok)}
.sc-fresh.f-ok b{color:var(--ok)}
.sc-fresh.f-warn{border-color:var(--warn);color:var(--warn)}
.sc-fresh.f-warn b{color:var(--warn)}
.sc-fresh.f-old{border-color:var(--danger);color:var(--danger)}
.sc-fresh.f-old b{color:var(--danger)}
.sc-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:22px;align-items:start}
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
.sc-more{font-size:14px;margin:6px 0 0}
.sc-more a{color:var(--accent);text-decoration:underline;text-underline-offset:3px}
.sc-rkey{display:flex;gap:16px;flex-wrap:wrap;font-size:14px;color:var(--muted);margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}
.sc-rkey .rkey-t{color:var(--faint)}
/* الأقسام القابلة للطي */
.sc-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:26px 0 14px}
.sc-jump{display:flex;gap:6px;flex-wrap:wrap;flex:1 1 360px}
.sc-jump a{font-size:14px;color:var(--ink-2);text-decoration:none;border:1px solid var(--line);background:var(--panel);padding:2px 12px;border-radius:999px}
.sc-jump a:hover,.sc-jump a:focus-visible{border-color:var(--accent);color:var(--accent);outline:none}
.sc-all{display:flex;gap:6px}
.sc-all button{font:inherit;font-size:13.5px;cursor:pointer;color:var(--ink);background:var(--panel-2);border:1px solid var(--line-2);border-radius:8px;padding:4px 12px}
.sc-toggle{position:absolute;top:20px;inset-inline-end:22px;font:inherit;font-size:18px;line-height:1;cursor:pointer;color:var(--accent);background:var(--panel-3);border:1px solid var(--line-2);border-radius:8px;width:30px;height:30px;padding:0}
.sc-toggle:before{content:"−"}
.sc-toggle[aria-expanded="false"]:before{content:"+"}
section.doc{position:relative}
.sc-toggle:focus-visible,.sc-all button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
section.doc.sc-collapsed > *:not(h2):not(.sc-toggle){display:none}
section.doc.sc-collapsed{padding-bottom:12px}
section.doc > h2{cursor:default}
/* قراءة أوضح بكثافة معتدلة */
.chip,.tag,.ev-code,.conf,.kstrip,.chg-tag,.st-badge{font-size:13.5px}
.kpi .k-l,.kpi .k-n,.brand-sub{font-size:13.5px}
@media (max-width:1000px){
  .sc-grid{grid-template-columns:minmax(0,1fr)}
  .sc-row{grid-template-columns:minmax(0,1fr);gap:2px}
  .sc-list li{grid-template-columns:minmax(0,1fr);gap:3px}
  .sc-list li .sc-code{justify-self:start}
}
@media (max-width:700px){
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
  var openRe = /التوجيهات التشغيلية|مؤشرات الموقف/;
  function setState(sec, btn, collapsed) {
    sec.classList.toggle('sc-collapsed', collapsed);
    btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  }
  var items = [];
  secs.forEach(function (sec) {
    var h = sec.querySelector('h2'); if (!h) return;
    var b = d.createElement('button');
    b.type = 'button'; b.className = 'sc-toggle no-print';
    b.setAttribute('aria-label', 'طيّ القسم أو فتحه');
    sec.appendChild(b);
    b.addEventListener('click', function () { setState(sec, b, !sec.classList.contains('sc-collapsed')); });
    setState(sec, b, !openRe.test(h.textContent));
    items.push({sec: sec, btn: b, title: h.textContent.trim()});
  });
  function openSec(sec) {
    items.forEach(function (it) { if (it.sec === sec) setState(sec, it.btn, false); });
  }
  if (items.length) {
    var bar = d.createElement('div'); bar.className = 'sc-toolbar no-print';
    var nav = d.createElement('nav'); nav.className = 'sc-jump'; nav.setAttribute('aria-label', 'انتقال إلى الأقسام');
    items.forEach(function (it) {
      var a = d.createElement('a'); a.href = '#' + it.sec.id; a.textContent = it.title;
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
  // روابط «كاملة» في بطاقة القرار
  [].forEach.call(d.querySelectorAll('[data-goto]'), function (a) {
    var key = a.getAttribute('data-goto');
    var hit = items.filter(function (it) { return it.title.indexOf(key) >= 0; })[0];
    if (!hit) { a.parentNode.removeChild(a); return; }
    a.href = '#' + hit.sec.id;
    a.addEventListener('click', function () { openSec(hit.sec); });
  });
  // رابط مباشر إلى قسم مطوي: يُفتح
  if (location.hash) {
    var tg = d.getElementById(location.hash.slice(1));
    items.forEach(function (it) { if (it.sec === tg || (tg && it.sec.contains(tg))) openSec(it.sec); });
  }
})();
"""
