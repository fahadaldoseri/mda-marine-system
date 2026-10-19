#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد الموقع الدائم لمركز الوعي بالمجال البحري.

الاستخدام:
  python3 generator/build_site.py [--site-root /path/to/site] [--check]

يعيد استخدام المولّد الحالي (build_report.py + blocks.py + map_gulf.py + monthly_dashboard.py)
ويبني مجلد النشر dist/ كاملًا:
  dist/index.html                     الرئيسية والأرشيف
  dist/reports/<YYYY-MM-DD>.html      التقارير اليومية
  dist/reports/cumulative-2026.html   السجل التراكمي
  dist/reports/monthly-2026-10.html   اللوحة الشهرية
  dist/manus-routes.json              بيان المسارات
  dist/favicon.svg

قاعدة المصادر: كل تقرير يومي يحتاج زوجًا: sources/reports/<التاريخ>-sectioned.md
و sources/meta/<التاريخ>.json. أي زوج ناقص يُسجَّل ويُتجاوز بلا إسقاط البناء.
"""

import argparse
import json
import re
import sys
from datetime import date
from html import escape as esc
from pathlib import Path

# الاسم المعتمد للتقرير اليومي (قرار صاحب القرار — 18 أكتوبر 2026)
DAILY_TITLE = "التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة"
DAILY_PLACEHOLDERS = ['التقرير الصباحي اليومي', 'التقرير اليومي', 'التقرير اليومي لأمن الملاحة', 'تقرير أمن الملاحة']

SOURCES_MANIFEST = Path('/home/ubuntu/brain-marine-news/appendices/sources-manifest.json')


def approved_source_count(fallback: int = 40) -> int:
    """عدد المصادر المعتمد — مصدر واحد للحقيقة (بند ٨ من تدقيق 19 أكتوبر 2026)."""
    try:
        return int(json.loads(SOURCES_MANIFEST.read_text(encoding='utf-8'))['approved_source_count'])
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return fallback


def daily_headline(meta: dict) -> str:
    """عنوان الإصدار اليومي المعتمد، مع احترام أي عنوان مخصّص غير عام."""
    value = (meta.get("headline") or meta.get("subtitle") or "").strip()
    return value if value not in DAILY_PLACEHOLDERS else DAILY_TITLE


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_report  # noqa: E402
import monthly_dashboard  # noqa: E402
import site_chrome  # noqa: E402

AR_MONTHS = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
             7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="8" fill="#04120f"/>
<path d="M16 5l8 3.4v6.9c0 5-3.3 8.7-8 10.3-4.7-1.6-8-5.3-8-10.3V8.4z" fill="none" stroke="#22c3b6" stroke-width="1.8" stroke-linejoin="round"/>
<path d="M16 14v6" stroke="#22c3b6" stroke-width="1.8" stroke-linecap="round"/>
<path d="M12.8 16.4h6.4" stroke="#22c3b6" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""


def ar_date(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return f"{d} {AR_MONTHS[m]} {y}"
    except Exception:
        return iso


def risk_of(meta: dict):
    dc = meta.get("decision_card") or {}
    kind = str(dc.get("risk_kind") or "").strip().lower()
    label = str(dc.get("risk") or meta.get("threat_level") or "").strip()
    if kind not in ("high", "med", "low"):
        kind = {"مرتفع": "high", "متوسط": "med", "منخفض": "low"}.get(label, "")
    return label or "غير محدد", kind or "med"


RESTRICTED_CLASSES = {"مقيّد", "حساس"}


def is_restricted(meta) -> bool:
    """الإصدار المقيّد أو الحساس لا يُنشر على الموقع العام."""
    return str((meta or {}).get("classification", "عام")).strip() in RESTRICTED_CLASSES


def discover(site_root: Path):
    """يجمع أزواج التقارير اليومية من مجلد المصادر."""
    reports, warnings = [], []
    meta_dir = site_root / "sources" / "meta"
    rep_dir = site_root / "sources" / "reports"
    for md in sorted(rep_dir.glob("*-sectioned.md")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", md.name)
        if not m:
            continue
        iso = m.group(1)
        meta_path = meta_dir / f"{iso}.json"
        if not meta_path.exists():
            warnings.append(f"تقرير بلا ملف واجهة: {md.name}")
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            warnings.append(f"ملف واجهة غير صالح {meta_path.name}: {e}")
            continue
        reports.append({"iso": iso, "md": md, "meta": meta})
    reports.sort(key=lambda r: r["iso"], reverse=True)
    return reports, warnings


def _flat(value) -> str:
    """حقول بطاقة القرار قد تكون نصًّا أو قائمة نقاط — تُسطَّح للعرض المختصر."""
    if isinstance(value, list):
        return " · ".join(str(x).strip() for x in value if str(x).strip())
    return (value or "").strip()


def build_reports(site_root: Path, dist: Path, reports, warnings):
    out_dir = dist / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    built = []
    for r in reports:
        target = out_dir / f"{r['iso']}.html"
        try:
            _, count = build_report.build(r["md"], target, r["meta"])
        except Exception as e:  # بناء تقرير واحد لا يُسقط الموقع
            warnings.append(f"فشل بناء {r['iso']}: {e}")
            continue
        html = target.read_text(encoding="utf-8")
        html = site_chrome.inject(html, active="report", note=f"إصدار {ar_date(r['iso'])}")
        target.write_text(html, encoding="utf-8")
        risk, kind = risk_of(r["meta"])
        built.append({
            "iso": r["iso"], "label": r["meta"].get("date_label") or ar_date(r["iso"]),
            "risk": risk, "risk_kind": kind,
            "headline": daily_headline(r["meta"]),
            "changed": _flat((r["meta"].get("decision_card") or {}).get("changed")),
            "action": _flat((r["meta"].get("decision_card") or {}).get("action")),
            "sections": count, "size": target.stat().st_size,
        })
    return built


def build_cumulative(site_root: Path, dist: Path, warnings):
    md = site_root / "sources" / "reports" / "cumulative.md"
    meta_p = site_root / "sources" / "meta" / "cumulative.json"
    if not (md.exists() and meta_p.exists()):
        warnings.append("مصدر السجل التراكمي غير متاح، تُجاوز الصفحة")
        return None
    target = dist / "reports" / "cumulative-2026.html"
    try:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        _, count = build_report.build(md, target, meta)
    except Exception as e:
        warnings.append(f"فشل بناء السجل التراكمي: {e}")
        return None
    html = site_chrome.inject(target.read_text(encoding="utf-8"), active="cumulative",
                              note="سجل تراكمي 28 فبراير – 11 أكتوبر 2026")
    target.write_text(html, encoding="utf-8")
    return {"size": target.stat().st_size, "sections": count}


def build_monthly(site_root: Path, dist: Path, warnings):
    ledger = site_root / "sources" / "ledger.json"
    if not ledger.exists():
        warnings.append("دفتر الأحداث غير متاح، تُجاوَز اللوحة الشهرية")
        return None
    target = dist / "reports" / "monthly-2026-10.html"
    try:
        info = monthly_dashboard.build(str(ledger), str(target), "لوحة المؤشرات الشهرية — أمن الملاحة 2026")
    except Exception as e:
        warnings.append(f"فشل بناء اللوحة الشهرية: {e}")
        return None
    html = site_chrome.inject(target.read_text(encoding="utf-8"), active="monthly",
                              note="لوحة مبنية من دفتر الأحداث التراكمي")
    target.write_text(html, encoding="utf-8")
    return info


def build_index(dist: Path, reports, notfound: bool = False):
    latest = reports[0] if reports else None
    ledger_total = ledger_count(dist)
    rows = "".join(
        f'<li class="ar-row"><a class="ar-link" href="/reports/{r["iso"]}.html">'
        f'<span class="ar-date">{esc(r["label"])}</span>'
        f'<span class="ar-risk rk-{esc(r["risk_kind"])}">{esc(r["risk"])}</span>'
        f'<span class="ar-note">{esc((r["headline"] or DAILY_TITLE)[:88])}</span>'
        f'</a></li>'
        for r in reports
    ) or '<li class="ar-empty">لا توجد تقارير منشورة بعد.</li>'

    if latest:
        hero_card = f"""<a class="hero-card" href="/reports/{latest['iso']}.html">
      <div class="hc-top"><span class="hc-tag">آخر إصدار</span>
        <span class="hc-risk rk-{esc(latest['risk_kind'])}">مستوى الخطر: {esc(latest['risk'])}</span></div>
      <h2>{esc(latest['label'])}</h2>
      <p class="hc-changed">{esc(latest['changed'] or latest['headline'] or '')}</p>
      <p class="hc-action"><b>المطلوب فورًا:</b> {esc(latest['action'] or '—')}</p>
      <span class="hc-open">افتح التقرير كاملًا ←</span>
    </a>"""
    else:
        hero_card = '<div class="hero-card"><h2>لا يوجد إصدار بعد</h2></div>'

    return f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="مركز الوعي بالمجال البحري: تقارير أمن الملاحة اليومية في مضيق هرمز والخليج العربي وبحر العرب والبحر الأحمر.">
<meta name="theme-color" content="#040810">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="تغذية الإصدارات اليومية" href="/feed.xml">
<title>مركز الوعي بالمجال البحري — تقارير أمن الملاحة</title>
<style>
{site_chrome.SITE_CSS}
:root{{--bg:#040810;--panel:#0b1524;--panel2:#0f1d33;--line:#1b2b45;--ink:#e9f0f9;--ink2:#b9c8dc;
--muted:#7f95ae;--accent:#22c3b6;--accent-ink:#04120f;--danger:#ff5d52;--warn:#ffb02e;--ok:#33d07a;--info:#4d9dff}}
body.daylight{{--bg:#eef3f9;--panel:#ffffff;--panel2:#f5f8fc;--line:#d3dded;--ink:#0d1a2b;--ink2:#33475e;
--muted:#5d738c;--accent:#0f8f86;--accent-ink:#ffffff;--danger:#c2352c;--warn:#a86b00;--ok:#1d7a4c;--info:#1d5fa8}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);line-height:1.95;
font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:34px 20px 10px}}
h1{{font-size:30px;margin:0 0 8px;line-height:1.4}}
.lede{{color:var(--muted);margin:0 0 24px;font-size:14.5px;max-width:70ch}}
.hero-card{{display:block;background:linear-gradient(150deg,var(--panel2),var(--panel));border:1px solid var(--line);
border-radius:14px;padding:22px;text-decoration:none;color:inherit;margin:0 0 22px;transition:border-color .2s}}
.hero-card:hover{{border-color:var(--accent)}}
.hc-top{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}}
.hc-tag{{font-size:12px;background:var(--accent);color:var(--accent-ink);padding:3px 10px;border-radius:99px;font-weight:700}}
.hc-risk{{font-size:12.5px;border:1px solid var(--line);padding:3px 10px;border-radius:99px}}
.hero-card h2{{margin:0 0 8px;font-size:20px}}
.hc-changed{{color:var(--ink2);font-size:14.5px;margin:0 0 10px}}
.hc-action{{color:var(--muted);font-size:14px;margin:0 0 14px}}
.hc-action b{{color:var(--ink2)}}
.hc-open{{color:var(--accent);font-size:13.5px;font-weight:600}}
.grid{{display:grid;grid-template-columns:1.15fr .85fr;gap:22px;align-items:start}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}}
.card h3{{margin:0 0 6px;font-size:17px}}
.card p.hint{{color:var(--muted);font-size:13px;margin:0 0 14px}}
.pref-row{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 0;border-bottom:1px solid var(--line);flex-wrap:wrap}}
.pref-row:last-child{{border-bottom:0}}
.pref-row span{{font-size:14px;color:var(--ink2)}}
.seg{{display:flex;border:1px solid var(--line);border-radius:10px;overflow:hidden}}
.seg button{{background:transparent;border:0;color:var(--ink2);padding:7px 13px;cursor:pointer;font:inherit;font-size:13.5px}}
.seg button.on{{background:var(--accent);color:var(--accent-ink);font-weight:700}}
.cont{{display:none;background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:14px;margin:0 0 22px}}
.cont.on{{display:block}}
.cont a{{color:var(--accent);text-decoration:none;font-weight:600}}
.cont .ct{{color:var(--muted);font-size:12.5px;display:block;margin-top:4px}}
ul.ar{{list-style:none;margin:0;padding:0}}
.ar-row{{border-bottom:1px solid var(--line)}}
.ar-row:last-child{{border-bottom:0}}
.ar-link{{display:grid;grid-template-columns:1fr auto;gap:6px 12px;padding:13px 2px;text-decoration:none;color:inherit}}
.ar-link:hover .ar-date{{color:var(--accent)}}
.ar-date{{font-weight:600;font-size:15px}}
.ar-risk{{font-size:12px;border:1px solid var(--line);border-radius:99px;padding:2px 10px;align-self:start}}
.ar-note{{grid-column:1/-1;color:var(--muted);font-size:13px}}
.rk-high{{color:var(--danger);border-color:var(--danger)}}
.rk-med{{color:var(--warn);border-color:var(--warn)}}
.rk-low{{color:var(--ok);border-color:var(--ok)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:0 0 22px}}
.tile{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}}
.tile b{{display:block;font-size:22px;font-family:"IBM Plex Mono",monospace}}
.tile span{{color:var(--muted);font-size:12.5px}}
.foot-note{{color:var(--muted);font-size:12.5px;margin:26px 0 0;border-top:1px solid var(--line);padding-top:14px}}
</style>
</head>NF_CSS_PLACEHOLDER<body>
PREFS_EARLY_PLACEHOLDER
NAV_PLACEHOLDER
<div class="wrap">
  <h1>مركز الوعي بالمجال البحري</h1>
  <p class="lede">منصة دائمة لتقارير أمن الملاحة: إصدار يومي بمؤشراته وخرائطه، ولوحة شهرية مبنية من دفتر أحداث تراكمي، وسجل تاريخي للمقارنة. كل إصدار يفصل الحقيقة عن التقدير ويربط الرقم بجهة قادرة على حسمه.</p>

  <div class="cont" id="cont">
    <a id="cont-link" href="/">تابع من حيث توقفت ←</a>
    <span class="ct" id="cont-meta"></span>
  </div>

  {hero_card}

  <div class="tiles">
    <div class="tile"><b>{len(reports)}</b><span>إصدار يومي منشور</span></div>
    <div class="tile"><b>{ledger_total or "—"}</b><span>سجل في الدفتر التراكمي</span></div>
    <div class="tile"><b>{approved_source_count()}</b><span>مصدرًا مفحوصًا في كل تشغيل</span></div>
    <div class="tile"><b>07:00</b><span>توقيت الإصدار اليومي (البحرين)</span></div>
  </div>

  <div class="grid">
    <section class="card" id="archive">
      <h3>أرشيف الإصدارات</h3>
      <p class="hint">كل إصدار يبقى متاحًا بالرابط الخاص به، ومفتاح اللون يبيّن مستوى الخطر المسجل في بطاقة القرار.</p>
      <ul class="ar">{rows}</ul>
    </section>
    <div>
      <section class="card" style="margin-bottom:22px">
        <h3>تفضيلات القراءة</h3>
        <p class="hint">تُحفظ في متصفحك وتُطبَّق تلقائيًا في الزيارة القادمة، بلا حساب ولا تسجيل.</p>
        <div class="pref-row"><span>مظهر الصفحة</span>
          <div class="seg" id="p-theme">
            <button type="button" data-theme="dark">ليلي</button>
            <button type="button" data-theme="light">نهاري</button>
          </div>
        </div>
        <div class="pref-row"><span>حجم الخط</span>
          <div class="seg">
            <button type="button" data-scale="1">أ</button>
            <button type="button" data-scale="1.12">أ+</button>
            <button type="button" data-scale="1.25">أ++</button>
          </div>
        </div>
        <div class="pref-row"><span>تذكّر آخر تقرير فتحته</span>
          <div class="seg"><button type="button" id="p-clear">مسح التفضيلات</button></div>
        </div>
      </section>
      <section class="card">
        <h3>صفحات مرجعية</h3>
        <p class="hint">مبنية من دفتر الأحداث نفسه، لا من تقديرات منفصلة.</p>
        <ul class="ar">
          <li class="ar-row"><a class="ar-link" href="/reports/monthly-2026-10.html">
            <span class="ar-date">اللوحة الشهرية</span><span class="ar-risk">مؤشرات</span>
            <span class="ar-note">سجلات بحسب الشهر والتوزيع الجغرافي والتصنيف ودرجة الثقة</span></a></li>
          <li class="ar-row"><a class="ar-link" href="/reports/cumulative-2026.html">
            <span class="ar-date">السجل التراكمي</span><span class="ar-risk">مرجع</span>
            <span class="ar-note">28 فبراير – 11 أكتوبر 2026 بحسب أقسام التقرير اليومي</span></a></li>
        </ul>
      </section>
    </div>
  </div>

  <p class="foot-note">تصنيف الإصدار: عام · لا تُنشر الإصدارات المقيّدة أو الحساسة على هذا الموقع · المصادر الرسمية: UKMTO وIMO والنشرات الاستشارية.</p>
</div>
FOOT_PLACEHOLDER
PREFS_LATE_PLACEHOLDER
<script>
(function(){{
var LS=window.localStorage;
function get(k,d){{try{{return LS.getItem(k)||d;}}catch(e){{return d;}}}}
function set(k,v){{try{{LS.setItem(k,v);}}catch(e){{}}}}
function paintTheme(){{
  var light=document.body.classList.contains('daylight');
  document.querySelectorAll('#p-theme button').forEach(function(b){{
    b.classList.toggle('on', (b.getAttribute('data-theme')==='light')===light);
  }});
  var sb=document.getElementById('sn-theme'); if(sb) sb.textContent = light?'المظهر: نهاري':'المظهر: ليلي';
}}
function paintScale(){{
  var s=parseFloat(get('mn-scale','1'));
  document.querySelectorAll('[data-scale]').forEach(function(b){{
    b.classList.toggle('on', parseFloat(b.getAttribute('data-scale'))===s);
  }});
}}
document.querySelectorAll('#p-theme button').forEach(function(b){{
  b.addEventListener('click',function(){{
    var light=b.getAttribute('data-theme')==='light';
    document.body.classList.toggle('daylight',light); set('mn-theme',light?'light':'dark'); paintTheme();
  }});
}});
document.querySelectorAll('[data-scale]').forEach(function(b){{
  b.addEventListener('click',function(){{
    var s=parseFloat(b.getAttribute('data-scale')); set('mn-scale',s);
    document.body.style.zoom=(s===1?'':s); paintScale();
  }});
}});
var clear=document.getElementById('p-clear');
if(clear) clear.addEventListener('click',function(){{
  try{{LS.removeItem('mn-theme');LS.removeItem('mn-scale');LS.removeItem('mn-last');}}catch(e){{}}
  document.body.classList.remove('daylight'); document.body.style.zoom='';
  paintTheme(); paintScale(); document.getElementById('cont').classList.remove('on');
}});
paintTheme(); paintScale();
var last=get('mn-last','');
if(last){{
  try{{
    var o=JSON.parse(last);
    if(o&&o.path){{
      document.getElementById('cont-link').setAttribute('href',o.path);
      document.getElementById('cont-meta').textContent=(o.title||'')+' · آخر فتح '+(o.at||'').slice(0,10);
      document.getElementById('cont').classList.add('on');
    }}
  }}catch(e){{}}
}}
}})();
</script>
NOTFOUND_PLACEHOLDER
</body></html>""".replace("PREFS_EARLY_PLACEHOLDER", site_chrome.PREFS_EARLY) \
   .replace("NF_CSS_PLACEHOLDER", NF_STYLE) \
   .replace("NOTFOUND_PLACEHOLDER", notfound_panel(reports, notfound)) \
   .replace("NAV_PLACEHOLDER", site_chrome.nav_html("home")) \
   .replace("FOOT_PLACEHOLDER", site_chrome.foot_html("الرئيسية")) \
   .replace("PREFS_LATE_PLACEHOLDER", site_chrome.PREFS_LATE)


def site_base(dist: Path) -> str:
    """نطاق الموقع المنشور. غيابه أو فساده يوقف البناء: لا نطاق احتياطي وهمي."""
    cfg_p = dist.parent / "sources" / "site.json"
    site = ""
    if cfg_p.exists():
        try:
            site = str(json.loads(cfg_p.read_text(encoding="utf-8")).get("base_url") or "").strip().rstrip("/")
        except json.JSONDecodeError as e:
            raise SystemExit(f"توقف البناء: ملف sources/site.json غير صالح ({e})")
    if not site:
        raise SystemExit("توقف البناء: base_url مفقود في sources/site.json؛ لا يُبنى الموقع بنطاق احتياطي وهمي.")
    if not site.startswith("https://") or "example" in site:
        raise SystemExit(f"توقف البناء: base_url غير صالح ({site})؛ يجب رابطًا عامًا يبدأ بـ https://")
    return site


def ledger_count(dist: Path) -> int:
    """عدد سجلات الدفتر التراكمي — يُقرأ ولا يُكتب يدويًا في الصفحة."""
    f = dist.parent / "sources" / "ledger.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        ev = d.get("events") if isinstance(d, dict) else d
        return len(ev) if isinstance(ev, list) else 0
    except Exception:
        return 0


def build_feed(dist: Path, reports):
    """تغذية RSS للإصدارات اليومية، لمتابعة الموقع دون زيارة يدوية."""
    from xml.sax.saxutils import escape as xesc
    site = site_base(dist)
    items = []
    for r in reports:
        link = f"{site}/reports/{r['iso']}.html"
        desc = r["changed"] or r["headline"] or ""
        items.append(
            "  <item>\n"
            f"    <title>{xesc(r['label'])} — مستوى الخطر: {xesc(r['risk'])}</title>\n"
            f"    <link>{link}</link>\n"
            f"    <guid isPermaLink=\"false\">mn-{r['iso']}</guid>\n"
            f"    <description>{xesc(desc)}</description>\n"
            "  </item>"
        )
    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
           "<rss version=\"2.0\"><channel>\n"
           "  <title>مركز الوعي بالمجال البحري — تقارير أمن الملاحة</title>\n"
           f"  <link>{site}/</link>\n"
           "  <description>إصدار يومي لأمن الملاحة في مضيق هرمز والخليج العربي وبحر العرب والبحر الأحمر</description>\n"
           "  <language>ar</language>\n"
           + ("\n".join(items) if items else "") + "\n</channel></rss>\n")
    (dist / "feed.xml").write_text(xml, encoding="utf-8")
    return len(items)


def build_routes(dist: Path, reports):
    routes = [{"path": "/", "title": "الرئيسية والأرشيف"}]
    for r in reports:
        routes.append({"path": f"/reports/{r['iso']}.html", "title": f"تقرير {r['label']}"})
    routes.append({"path": "/reports/:date", "title": "تقرير يومي"})
    routes.append({"path": "/reports/monthly-2026-10.html", "title": "اللوحة الشهرية"})
    routes.append({"path": "/reports/cumulative-2026.html", "title": "السجل التراكمي"})
    (dist / "manus-routes.json").write_text(
        json.dumps({"routes": routes}, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(routes)


def known_paths(reports):
    """المسارات المنشورة فعليًا: تُستخدم في صفحة «غير موجودة» وفي خريطة الموقع."""
    ks = ["/", "/reports/cumulative-2026.html", "/reports/monthly-2026-10.html"]
    ks += [f"/reports/{r['iso']}.html" for r in reports]
    return ks


def notfound_panel(reports, visible: bool = False) -> str:
    """لوحة «الصفحة غير موجودة» + فاحص مسار في المتصفح.

    الاستضافة تعيد صفحة الرئيسية لأي مسار غير معروف (soft-404)، فيعرض هذا الفاحص
    اللوحة الصحيحة للزائر. رمز الاستجابة يبقى 200 لأن التوصيل ثابت بلا خادم.
    """
    ks = known_paths(reports)
    items = "".join(f'<li><a href="{k}">{k}</a></li>' for k in ks)
    keys = ",".join(f'"{k}":1' for k in ks)
    hid = "" if visible else " hidden"
    script = ""
    if not visible:
        script = (
            "<script>(function(){var K={" + keys + "};"
            r"var p=location.pathname.replace(/\/index\.html$/,'/');"
            "if(!K[p]){var nf=document.getElementById('nf404');"
            "var w=document.querySelector('.wrap');"
            "if(nf){if(w){w.setAttribute('hidden','');}nf.removeAttribute('hidden');"
            "document.title='الصفحة غير موجودة — مركز الوعي بالمجال البحري';}}})();</script>"
        )
    return (
        f'<section class="card nf" id="nf404"{hid}>'
        "<h1>الصفحة غير موجودة</h1>"
        "<p>الرابط المطلوب لا يقابل صفحة منشورة على هذا الموقع. هذه الروابط المتاحة الآن:</p>"
        f'<ul class="nf-list">{items}</ul>'
        '<p><a class="nf-back" href="/">العودة إلى الرئيسية والأرشيف</a></p></section>' + script
    )


NF_STYLE = """<style>
.nf{max-width:760px;margin:26px auto}
.nf h1{font-size:30px;margin:6px 0 10px}
.nf-list{list-style:none;padding:0;margin:14px 0;display:grid;gap:8px}
.nf-list a{display:block;padding:10px 12px;border:1px solid var(--line,#2b3b4e);border-radius:8px;
  text-decoration:none;color:inherit;font-family:"IBM Plex Mono",monospace;direction:ltr;
  unicode-bidi:isolate;overflow-wrap:anywhere}
.nf-list a:hover{border-color:var(--accent,#2fd6c3)}
.nf-back{display:inline-block;margin-top:6px;font-weight:700;text-decoration:none;color:var(--accent,#2fd6c3)}
</style>"""


def build_sitemap(dist: Path, reports) -> int:
    site = site_base(dist)
    urls = known_paths(reports)
    last = reports[0]["iso"] if reports else ""
    body = "".join(
        f"  <url><loc>{site}{u}</loc>" + (f"<lastmod>{last}</lastmod>" if last else "") + "</url>\n"
        for u in urls
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")
    (dist / "sitemap.xml").write_text(xml, encoding="utf-8")
    return len(urls)


def build_robots(dist: Path) -> None:
    site = site_base(dist)
    (dist / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site}/sitemap.xml\n", encoding="utf-8")


def build_notfound(dist: Path, reports) -> None:
    html = build_index(dist, reports, notfound=True).replace(
        "<title>مركز الوعي بالمجال البحري — تقارير أمن الملاحة</title>",
        "<title>الصفحة غير موجودة — مركز الوعي بالمجال البحري</title>")
    (dist / "404.html").write_text(html, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-root", default=str(HERE.parent))
    ap.add_argument("--check", action="store_true", help="فحص المخرجات بعد البناء")
    ap.add_argument("--allow-restricted", action="store_true",
                    help="يسمح بنشر إصدار مقيّد أو حساس على الموقع العام (ممنوع افتراضيًا)")
    a = ap.parse_args()

    site_root = Path(a.site_root).resolve()
    dist = site_root / "dist"
    (dist / "reports").mkdir(parents=True, exist_ok=True)

    warnings = []
    reports, w = discover(site_root)
    warnings += w
    if not a.allow_restricted:
        kept, blocked = [], []
        for r in reports:
            (blocked if is_restricted(r["meta"]) else kept).append(r)
        for r in blocked:
            warnings.append(f"لم يُنشر إصدار مقيّد أو حساس: {r['iso']} — يبقى داخل المحادثة فقط")
        if blocked and not kept:
            raise SystemExit("توقف البناء: كل الإصدارات مقيّدة أو حساسة، ولا يُنشر منها شيء على الموقع العام.")
        reports = kept
    built = build_reports(site_root, dist, reports, warnings)
    cum = build_cumulative(site_root, dist, warnings)
    mon = build_monthly(site_root, dist, warnings)

    (dist / "index.html").write_text(build_index(dist, built), encoding="utf-8")
    (dist / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    n_feed = build_feed(dist, built)
    n_routes = build_routes(dist, built)
    n_sitemap = build_sitemap(dist, built)
    build_robots(dist)
    build_notfound(dist, built)

    # قسم «التقارير الخاصة» — يُبنى آليًا من sources/special
    n_sp_items = 0
    try:
        import build_special
        _, n_sp_items = build_special.build_all(dist)
    except Exception as e:  # لا يُسقط بناء الموقع بسبب قسم فرعي
        warnings.append(f"تعذّر بناء صفحة التقارير الخاصة: {e}")

    print(f"الرئيسية: {len(built)} إصدار · السجل التراكمي: {'نعم' if cum else 'لا'} · "
          f"اللوحة الشهرية: {'نعم' if mon else 'لا'} · المسارات: {n_routes} · التغذية: {n_feed} · "
          f"خريطة الموقع: {n_sitemap} · robots: نعم · 404: نعم · التقارير الخاصة: {n_sp_items}")
    for w_ in warnings:
        print(f"تنبيه: {w_}")

    if a.check:
        pages = sorted(p for p in dist.rglob("*.html"))
        missing = []
        escaped = []
        for p in pages:
            t = p.read_text(encoding="utf-8")
            if "site-nav" not in t:
                missing.append(p.name)
            if len(t) < 3000:
                missing.append(p.name + " (صغير)")
            if "&lt;" in t:
                escaped.append(f"{p.name} ({t.count('&lt;')})")
        print(f"فحص: {len(pages)} صفحة، بلا ترويسة أو غير مكتملة: {missing or 'لا شيء'}")
        print(f"فحص الوسوم المهرَّبة (تظهر للقارئ نصًّا): {escaped or 'لا شيء'}")
        # فحص سياسة عرض رموز الأحداث (2+5): الرمز الكامل في قسم الوقائع فقط
        try:
            import subprocess as _sp
            _r = _sp.run([sys.executable, "/home/ubuntu/brain-marine-news/validators/check_code_policy.py",
                          str(dist)], capture_output=True, text=True)
            _line = [l for l in _r.stdout.splitlines() if "النتيجة" in l]
            print(f"فحص سياسة الرموز: {(_line[-1].strip() if _line else _r.stdout.strip()[-80:])}")
        except Exception as _e:
            print(f"تنبيه: تعذر فحص سياسة الرموز ({_e})")
        bad = [p.name for p in pages if not (dist / "manus-routes.json").exists()]
        if bad:
            print("تنبيه: بيان المسارات مفقود")
        return 0 if not (missing or escaped) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
