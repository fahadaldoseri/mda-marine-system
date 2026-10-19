#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
وحدة ترويسة الموقع الدائم وتفضيلات القراءة.

تُستخدم من build_site.py لحقن:
- شريط تنقّل موحّد في كل صفحة.
- تفضيلات محفوظة في المتصفح (المظهر، حجم الخط، آخر تقرير فُتح).
- أنماط الموقع المشتركة.
"""

BRAND = "مركز الوعي بالمجال البحري"
BRAND_SUB = "تقارير أمن الملاحة — مملكة البحرين"

MARK_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    '<path d="M12 3l7 3v6c0 4.4-2.9 7.6-7 9-4.1-1.4-7-4.6-7-9V6z"/>'
    '<path d="M12 11.5v4"/><path d="M9.6 13.2h4.8"/></svg>'
)

SITE_CSS = """
:root{--sn-bg:#040810;--sn-panel:#0b1524;--sn-line:#1b2b45;--sn-ink:#e9f0f9;--sn-ink2:#b9c8dc;
--sn-muted:#7f95ae;--sn-accent:#22c3b6;--sn-accent-ink:#04120f}
html{scroll-behavior:smooth}
body.daylight{--sn-bg:#eef3f9;--sn-panel:#ffffff;--sn-line:#d3dded;--sn-ink:#0d1a2b;--sn-ink2:#33475e;
--sn-muted:#5d738c;--sn-accent:#0f8f86;--sn-accent-ink:#ffffff}
.site-nav{position:sticky;top:0;z-index:60;background:var(--sn-bg);border-bottom:1px solid var(--sn-line);
font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif}
.site-nav .sn-inner{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:18px;padding:9px 20px;flex-wrap:wrap}
.site-nav a{color:var(--sn-ink2);text-decoration:none}
.sn-brand{display:flex;align-items:center;gap:10px;color:var(--sn-ink)!important;font-weight:700}
.sn-mark{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;flex:0 0 auto;
background:linear-gradient(150deg,var(--sn-accent),#0c8b83);color:#04120f}
.sn-mark svg{width:17px;height:17px}
.sn-name{display:flex;flex-direction:column;line-height:1.25}
.sn-name em{font-style:normal;font-size:11.5px;font-weight:500;color:var(--sn-muted)}
.sn-links{display:flex;gap:4px;margin-inline-start:auto;flex-wrap:wrap}
.sn-links a{padding:6px 11px;border-radius:8px;font-size:13.5px;border:1px solid transparent}
.sn-links a:hover{background:var(--sn-panel);border-color:var(--sn-line);color:var(--sn-ink)}
.sn-links a[aria-current="page"]{background:var(--sn-panel);border-color:var(--sn-line);color:var(--sn-ink);font-weight:600}
.sn-tools{display:flex;align-items:center;gap:8px}
.sn-scale{display:flex;border:1px solid var(--sn-line);border-radius:9px;overflow:hidden}
.sn-scale button{background:transparent;border:0;color:var(--sn-ink2);padding:5px 10px;cursor:pointer;font:inherit;font-size:13px}
.sn-scale button.on{background:var(--sn-accent);color:var(--sn-accent-ink);font-weight:700}
.sn-theme{background:var(--sn-panel);border:1px solid var(--sn-line);color:var(--sn-ink2);
border-radius:9px;padding:6px 11px;cursor:pointer;font:inherit;font-size:13px}
.sn-theme:hover{color:var(--sn-ink)}
.sn-foot{margin-top:44px;border-top:1px solid var(--sn-line);background:var(--sn-bg);
font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif}
.sn-foot .sf-inner{max-width:1180px;margin:0 auto;padding:20px;color:var(--sn-muted);font-size:12.5px;
display:flex;gap:16px;flex-wrap:wrap;justify-content:space-between}
.sn-foot a{color:var(--sn-ink2)}
body.daylight .topbar{background:#ffffff!important;border-bottom-color:#d3dded!important}
body.daylight .brand-title,body.daylight .brand-sub{color:#0d1a2b}
@media print{.site-nav,.sn-foot{display:none!important}}
"""

# سكربت يُنفَّذ فور فتح الجسم لمنع وميض المظهر المحفوظ
PREFS_EARLY = """<script>
(function(){try{
var b=document.body;if(!b)return;
var t=localStorage.getItem('mn-theme');if(t==='light')b.classList.add('daylight');
var s=parseFloat(localStorage.getItem('mn-scale')||'1');if(s&&s!==1)b.style.zoom=s;
}catch(e){}})();
</script>"""

# سكربت نهاية الصفحة: يربط الأدوات ويحفظ التفضيلات ويتذكر آخر تقرير
PREFS_LATE = """<script>
(function(){
var LS=window.localStorage, body=document.body;
function save(k,v){try{LS.setItem(k,v);}catch(e){}}
var reportBtn=document.getElementById('btn-theme'), siteBtn=document.getElementById('sn-theme');
// إزالة مستمع الزر الأصلي داخل التقرير بمضاعفة العقدة لمنع الازدواج
if(reportBtn){var clone=reportBtn.cloneNode(true);reportBtn.parentNode.replaceChild(clone,reportBtn);reportBtn=clone;}
function isLight(){return body.classList.contains('daylight');}
function paint(){
  if(reportBtn) reportBtn.textContent = isLight() ? 'النمط الليلي' : 'النمط النهاري';
  if(siteBtn) siteBtn.textContent = isLight() ? 'المظهر: نهاري' : 'المظهر: ليلي';
  document.querySelectorAll('[data-scale]').forEach(function(b){
    b.classList.toggle('on', parseFloat(b.getAttribute('data-scale'))===currentScale());
  });
}
function currentScale(){var s=parseFloat(LS.getItem('mn-scale')||'1');return (s&&s>0)?s:1;}
function toggleTheme(){var on=body.classList.toggle('daylight');save('mn-theme',on?'light':'dark');paint();}
if(reportBtn) reportBtn.addEventListener('click',function(e){e.preventDefault();toggleTheme();});
if(siteBtn) siteBtn.addEventListener('click',function(e){e.preventDefault();toggleTheme();});
document.querySelectorAll('[data-scale]').forEach(function(b){
  b.addEventListener('click',function(e){e.preventDefault();
    var s=parseFloat(b.getAttribute('data-scale'));save('mn-scale',s);
    body.style.zoom=(s===1?'':s);paint();});
});
paint();
// تذكّر آخر تقرير فُتح
var p=location.pathname;
if(p.indexOf('/reports/')===0){
  var t=(document.title||'').split(/[|·]/)[0].trim();
  save('mn-last',JSON.stringify({path:p,title:t,at:new Date().toISOString()}));
}
})();
</script>"""


def nav_html(active: str = "") -> str:
    """شريط التنقّل الموحّد. active: home | monthly | cumulative | report"""
    def link(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    return f"""<nav class="site-nav no-print" aria-label="تنقل الموقع">
  <div class="sn-inner">
    <a class="sn-brand" href="/">
      <span class="sn-mark">{MARK_SVG}</span>
      <span class="sn-name">{BRAND}<em>{BRAND_SUB}</em></span>
    </a>
    <div class="sn-links">
      {link('/', 'الرئيسية', 'home')}
      {link('/reports/special.html', 'التقارير الخاصة', 'special')}
      {link('/#archive', 'الأرشيف', 'archive')}
      {link('/reports/monthly-2026-10.html', 'اللوحة الشهرية', 'monthly')}
      {link('/reports/cumulative-2026.html', 'السجل التراكمي', 'cumulative')}
    </div>
    <div class="sn-tools">
      <div class="sn-scale" role="group" aria-label="حجم الخط">
        <button type="button" data-scale="1" title="حجم عادي">أ</button>
        <button type="button" data-scale="1.12" title="حجم أكبر">أ+</button>
        <button type="button" data-scale="1.25" title="أكبر حجم">أ++</button>
      </div>
      <button type="button" class="sn-theme" id="sn-theme">المظهر</button>
    </div>
  </div>
</nav>"""


def foot_html(note: str = "") -> str:
    extra = f" · {note}" if note else ""
    return f"""<footer class="sn-foot no-print">
  <div class="sf-inner">
    <span>{BRAND} — {BRAND_SUB}{extra}</span>
    <span>تُحدَّث الصفحات آليًا مع كل إصدار · <a href="/#archive">الأرشيف الكامل</a> · <a href="/feed.xml">تغذية الإصدارات</a></span>
  </div>
</footer>"""


def inject(html: str, active: str, note: str = "") -> str:
    """حقن الترويسة والتفضيلات في صفحة مُولَّدة."""
    if "</head>" not in html:
        return html
    style = f"<style>{SITE_CSS}</style>"
    html = html.replace("</head>", style + "</head>", 1)

    # سكربت المظهر المبكر بعد فتح الجسم مباشرة
    marker = ">"
    idx = html.find("<body")
    if idx >= 0:
        close = html.find(">", idx)
        if close >= 0:
            html = html[: close + 1] + PREFS_EARLY + html[close + 1 :]

    # شريط التنقل بعد عنصر الشريط العلوي للصفحة إن وُجد، وإلا بعد الجسم
    nav = nav_html(active)
    topbar_end = html.find("</div>\n</div>\n<div class=\"wrap\"")
    if topbar_end > 0:
        # إدراج الشريط قبل الحاوية الرئيسية
        pos = html.find('<div class="wrap">')
        html = html[:pos] + nav + html[pos:]
    else:
        close = html.find(">", html.find("<body"))
        html = html[: close + 1] + nav + html[close + 1 :]

    if "</body>" in html:
        html = html.replace("</body>", foot_html(note) + PREFS_LATE + "</body>", 1)
    return html
