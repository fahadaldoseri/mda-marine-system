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
--sn-muted:#4f657c;--sn-accent:#0b7a72;--sn-accent-ink:#ffffff}
.site-nav{position:sticky;top:0;z-index:60;background:var(--sn-bg);border-bottom:1px solid var(--sn-line);
font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif}
.site-nav .sn-inner{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:12px;padding:9px 20px;flex-wrap:wrap}
.site-nav a{color:var(--sn-ink2);text-decoration:none}
.sn-brand{display:flex;align-items:center;gap:10px;color:var(--sn-ink)!important;font-weight:700}
.sn-mark{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;flex:0 0 auto;
background:linear-gradient(150deg,var(--sn-accent),#0c8b83);color:#04120f}
.sn-mark svg{width:17px;height:17px}
.sn-name{display:flex;flex-direction:column;line-height:1.25}
.sn-name em{font-style:normal;font-size:12.5px;font-weight:500;color:var(--sn-muted)}
.sn-links{display:flex;gap:4px;margin-inline-start:auto;flex-wrap:wrap}
.sn-links a{padding:6px 8px;min-height:32px;display:inline-flex;align-items:center;border-radius:8px;font-size:13.5px;border:1px solid transparent}
.sn-links a:hover{background:var(--sn-panel);border-color:var(--sn-line);color:var(--sn-ink)}
.sn-links a[aria-current="page"]{background:var(--sn-panel);border-color:var(--sn-line);color:var(--sn-ink);font-weight:600}
.sn-tools{display:flex;align-items:center;gap:8px}
.sn-scale{display:flex;border:1px solid var(--sn-line);border-radius:9px;overflow:hidden}
.sn-scale button{background:transparent;border:0;color:var(--sn-ink2);padding:5px 8px;min-width:34px;min-height:32px;cursor:pointer;font:inherit;font-size:13px}
.sn-scale button.on{background:var(--sn-accent);color:var(--sn-accent-ink);font-weight:700}
.sn-theme{background:var(--sn-panel);border:1px solid var(--sn-line);color:var(--sn-ink2);
border-radius:9px;padding:6px 11px;cursor:pointer;font:inherit;font-size:13px}
.sn-theme:hover{color:var(--sn-ink)}
.sn-skip{position:absolute;inset-inline-start:12px;top:-80px;z-index:70;background:var(--sn-accent);color:var(--sn-accent-ink)!important;
padding:9px 16px;border-radius:9px;font-weight:700;font-size:14px}
.sn-skip:focus{top:8px;outline:2px solid var(--sn-ink);outline-offset:2px}
.sn-print{background:var(--sn-accent);color:var(--sn-accent-ink);border-color:transparent;font-weight:700}
.sn-print:hover{color:var(--sn-accent-ink);filter:brightness(1.08)}
.sn-foot{margin-top:44px;border-top:1px solid var(--sn-line);background:var(--sn-bg);
font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif}
.sn-foot .sf-inner{max-width:1180px;margin:0 auto;padding:20px;color:var(--sn-muted);font-size:13px;
display:flex;gap:16px;flex-wrap:wrap;justify-content:space-between}
.sn-foot a{color:var(--sn-ink2);display:inline-block;padding:4px 2px;min-height:24px}
body.daylight .topbar{background:#ffffff!important;border-bottom-color:#d3dded!important}
body.daylight .brand-title,body.daylight .brand-sub{color:#0d1a2b}
@media print{.site-nav,.sn-foot{display:none!important}}
"""

# سكربت يُنفَّذ فور فتح الجسم لمنع وميض المظهر المحفوظ
PREFS_EARLY = """<script>
(function(){try{
var b=document.body;if(!b)return;
var t=localStorage.getItem('mn-theme');if(t==='light')b.classList.add('daylight');
var g=localStorage.getItem('mn-lang');if(g==='en'){document.documentElement.lang='en';document.documentElement.dir='ltr';b.classList.add('lang-en');}
var s=parseFloat(localStorage.getItem('mn-scale')||'1');if(s&&s!==1)b.style.zoom=s;
}catch(e){}})();
</script>"""

# سكربت نهاية الصفحة: يربط الأدوات ويحفظ التفضيلات ويتذكر آخر تقرير
PREFS_LATE = r"""<script>
(function(){
var LS=window.localStorage, body=document.body;
function save(k,v){try{LS.setItem(k,v);}catch(e){}}
var reportBtn=document.getElementById('btn-theme'), siteBtn=document.getElementById('sn-theme');
// إزالة مستمع الزر الأصلي داخل التقرير بمضاعفة العقدة لمنع الازدواج
if(reportBtn){var clone=reportBtn.cloneNode(true);reportBtn.parentNode.replaceChild(clone,reportBtn);reportBtn=clone;}
function isLight(){return body.classList.contains('daylight');}
function paint(){
  paintLang();
  document.querySelectorAll('[data-scale]').forEach(function(b){
    b.classList.toggle('on', parseFloat(b.getAttribute('data-scale'))===currentScale());
  });
}
function currentScale(){var s=parseFloat(LS.getItem('mn-scale')||'1');return (s&&s>0)?s:1;}
function toggleTheme(){var on=body.classList.toggle('daylight');save('mn-theme',on?'light':'dark');paint();}
if(reportBtn) reportBtn.addEventListener('click',function(e){e.preventDefault();toggleTheme();});
if(siteBtn) siteBtn.addEventListener('click',function(e){e.preventDefault();toggleTheme();});
var printBtn=document.getElementById('sn-print');
if(printBtn) printBtn.addEventListener('click',function(e){e.preventDefault();window.print();});
document.querySelectorAll('[data-scale]').forEach(function(b){
  b.addEventListener('click',function(e){e.preventDefault();
    var s=parseFloat(b.getAttribute('data-scale'));save('mn-scale',s);
    body.style.zoom=(s===1?'':s);paint();});
});
var I18N={ar:{"skip": "الانتقال إلى المحتوى", "menu": "القائمة", "home": "الرئيسية", "special": "التقارير الخاصة", "archive": "الأرشيف", "monthly": "اللوحة الشهرية", "cumulative": "السجل التراكمي", "sources": "المصادر والمراجع", "additions": "إضافات", "scale": "حجم الخط", "theme-dark": "المظهر: ليلي", "theme-light": "المظهر: نهاري", "print": "طباعة / PDF", "lang": "اللغة", "foot2-html": "تُحدَّث الصفحات آليًا مع كل إصدار · <a href=\"/#archive\">الأرشيف الكامل</a> · <a href=\"/feed.xml\">تغذية الإصدارات</a>", "no-en": "النسخة الإنجليزية لهذا الإصدار غير متاحة بعد."},en:{"skip": "Skip to content", "menu": "Menu", "home": "Home", "special": "Special reports", "archive": "Archive", "monthly": "Monthly dashboard", "cumulative": "Cumulative record", "sources": "Sources & references", "additions": "Additions", "scale": "Font size", "theme-dark": "Theme: night", "theme-light": "Theme: day", "print": "Print / PDF", "lang": "Language", "foot2-html": "Pages update automatically with every edition · <a href=\"/#archive\">Full archive</a> · <a href=\"/feed.xml\">Edition feed</a>", "no-en": "The English edition of this report is not available yet."}};
function currentLang(){var lock=document.documentElement.getAttribute('data-lang');if(lock)return lock;var l=LS.getItem('mn-lang');return (l==='en')?'en':'ar';}
function i18nTxt(key){var d=I18N[currentLang()];return (d&&d[key])||I18N.ar[key]||'';}
var _b=document.querySelector('.sn-name'), _s=document.querySelector('.sn-name em');
var BRAND_TXT=_b?(_b.childNodes[0].nodeValue||'').trim():'', BRAND_SUB_TXT=_s?_s.textContent.trim():'';
function paintLang(){
  var l=currentLang();
  document.querySelectorAll('[data-i18n]').forEach(function(el){var v=i18nTxt(el.getAttribute('data-i18n'));if(v)el.textContent=v;});
  document.querySelectorAll('[data-i18n-aria]').forEach(function(el){var v=i18nTxt(el.getAttribute('data-i18n-aria'));if(v)el.setAttribute('aria-label',v);});
  var f1=document.querySelector('[data-i18n-html="foot1"]'); if(f1) f1.textContent=BRAND_TXT+' — '+BRAND_SUB_TXT;
  var f2=document.querySelector('[data-i18n-html="foot2"]'); if(f2) f2.innerHTML=i18nTxt('foot2-html');
  document.querySelectorAll('[data-lang]').forEach(function(b){b.classList.toggle('on', b.getAttribute('data-lang')===l);});
  var rb=document.getElementById('btn-theme'), sb=document.getElementById('sn-theme');
  var L=(l==='en'), light=body.classList.contains('daylight');
  if(rb) rb.textContent = light ? (L?'Night mode':'النمط الليلي') : (L?'Day mode':'النمط النهاري');
  if(sb) sb.textContent = light ? i18nTxt('theme-light') : i18nTxt('theme-dark');
}
function note(msg){
  var n=document.getElementById('sn-lang-note');
  if(!n){n=document.createElement('div');n.id='sn-lang-note';n.className='sn-lang-note no-print';document.body.appendChild(n);}
  n.textContent=msg; n.style.display='block'; setTimeout(function(){n.style.display='none';},4600);
}
function routeLang(l){
  var m=location.pathname.match(/^\/reports\/(en\/)?(\d{4}-\d{2}-\d{2})\.html$/);
  if(!m) return;
  var isEn=!!m[1], date=m[2];
  if(l==='en'&&!isEn){
    fetch('/reports/en/index.json?ts='+Date.now(),{cache:'no-store'}).then(function(r){return r.ok?r.json():null;}).then(function(d){
      var list=(d&&d.dates)||[];
      if(list.indexOf(date)>=0){ location.href='/reports/en/'+date+'.html'; } else { note(i18nTxt('no-en')); }
    }).catch(function(){ note(i18nTxt('no-en')); });
  } else if(l==='ar'&&isEn){
    location.href='/reports/'+date+'.html';
  }
}
function applyLang(l,go){
  try{LS.setItem('mn-lang',l);}catch(e){}
  var lock=document.documentElement.getAttribute('data-lang');
  if(lock&&l!==lock){ if(go) routeLang(l); return; }
  var root=document.documentElement;
  root.lang=(l==='en')?'en':'ar'; root.dir=(l==='en')?'ltr':'rtl';
  body.classList.toggle('lang-en', l==='en');
  paintLang(); if(go) routeLang(l);
}
document.querySelectorAll('[data-lang]').forEach(function(b){
  b.addEventListener('click',function(e){e.preventDefault();applyLang(b.getAttribute('data-lang'),true);});
});
paintLang();
paint();
// رابط التخطي: أول عنوان ظاهر في الصفحة (أو المتن)، فلا يمرّ قارئ لوحة المفاتيح على الشريط كله في كل صفحة
var skip=document.getElementById('sn-skip');
if(skip){
  var hs=[].slice.call(document.querySelectorAll('h1')).filter(function(h){return h.offsetParent!==null;});
  var tg=hs[0]||document.querySelector('main,[role=main]');
  if(tg){ if(!tg.id) tg.id='sn-main'; tg.setAttribute('tabindex','-1'); skip.setAttribute('href','#'+tg.id); }
  else { skip.parentNode.removeChild(skip); }
}
// تذكّر آخر تقرير فُتح
var p=location.pathname;
if(p.indexOf('/reports/')===0){
  var t=(document.title||'').split(/[|·]/)[0].trim();
  save('mn-last',JSON.stringify({path:p,title:t,at:new Date().toISOString()}));
}
})();
</script>"""


LANG_CSS = """
.sn-lang{display:inline-flex;border:1px solid var(--sn-line);border-radius:9px;overflow:hidden}
.sn-lang button{background:transparent;border:0;color:var(--sn-ink2);padding:6px 11px;min-height:32px;min-width:42px;
cursor:pointer;font:inherit;font-size:12.5px;font-weight:700}
.sn-lang button.on{background:var(--sn-accent);color:var(--sn-accent-ink)}
.sn-lang button:hover{color:var(--sn-ink)}
.sn-lang-note{position:fixed;left:50%;transform:translateX(-50%);top:14px;z-index:60;background:var(--sn-panel);
border:1px solid var(--sn-line);color:var(--sn-ink);border-radius:10px;padding:10px 14px;font-size:13px;
box-shadow:0 10px 30px rgba(0,0,0,.35);max-width:90vw;text-align:center}
"""

LANG_JS = r"""
var I18N={ar:{"skip": "الانتقال إلى المحتوى", "menu": "القائمة", "home": "الرئيسية", "special": "التقارير الخاصة", "archive": "الأرشيف", "monthly": "اللوحة الشهرية", "cumulative": "السجل التراكمي", "sources": "المصادر والمراجع", "additions": "إضافات", "scale": "حجم الخط", "theme-dark": "المظهر: ليلي", "theme-light": "المظهر: نهاري", "print": "طباعة / PDF", "lang": "اللغة", "foot2-html": "تُحدَّث الصفحات آليًا مع كل إصدار · <a href=\"/#archive\">الأرشيف الكامل</a> · <a href=\"/feed.xml\">تغذية الإصدارات</a>", "no-en": "النسخة الإنجليزية لهذا الإصدار غير متاحة بعد."},en:{"skip": "Skip to content", "menu": "Menu", "home": "Home", "special": "Special reports", "archive": "Archive", "monthly": "Monthly dashboard", "cumulative": "Cumulative record", "sources": "Sources & references", "additions": "Additions", "scale": "Font size", "theme-dark": "Theme: night", "theme-light": "Theme: day", "print": "Print / PDF", "lang": "Language", "foot2-html": "Pages update automatically with every edition · <a href=\"/#archive\">Full archive</a> · <a href=\"/feed.xml\">Edition feed</a>", "no-en": "The English edition of this report is not available yet."}};
function currentLang(){var lock=document.documentElement.getAttribute('data-lang');if(lock)return lock;var l=LS.getItem('mn-lang');return (l==='en')?'en':'ar';}
function t(key){var d=I18N[currentLang()];return (d&&d[key])||I18N.ar[key]||'';}
var _b=document.querySelector('.sn-name'), _s=document.querySelector('.sn-name em');
var BRAND_TXT=_b?(_b.childNodes[0].nodeValue||'').trim():'', BRAND_SUB_TXT=_s?_s.textContent.trim():'';
function paintLang(){
  var l=currentLang();
  document.querySelectorAll('[data-i18n]').forEach(function(el){var v=t(el.getAttribute('data-i18n'));if(v)el.textContent=v;});
  document.querySelectorAll('[data-i18n-aria]').forEach(function(el){var v=t(el.getAttribute('data-i18n-aria'));if(v)el.setAttribute('aria-label',v);});
  var f1=document.querySelector('[data-i18n-html="foot1"]'); if(f1) f1.textContent=BRAND_TXT+' — '+BRAND_SUB_TXT;
  var f2=document.querySelector('[data-i18n-html="foot2"]'); if(f2) f2.innerHTML=t('foot2-html');
  document.querySelectorAll('[data-lang]').forEach(function(b){b.classList.toggle('on', b.getAttribute('data-lang')===l);});
  var rb=document.getElementById('btn-theme'), sb=document.getElementById('sn-theme');
  var L=(l==='en'), light=body.classList.contains('daylight');
  if(rb) rb.textContent = light ? (L?'Night mode':'النمط الليلي') : (L?'Day mode':'النمط النهاري');
  if(sb) sb.textContent = light ? t('theme-light') : t('theme-dark');
}
function note(msg){
  var n=document.getElementById('sn-lang-note');
  if(!n){n=document.createElement('div');n.id='sn-lang-note';n.className='sn-lang-note no-print';document.body.appendChild(n);}
  n.textContent=msg; n.style.display='block'; setTimeout(function(){n.style.display='none';},4600);
}
function routeLang(l){
  var m=location.pathname.match(/^\/reports\/(en\/)?(\d{4}-\d{2}-\d{2})\.html$/);
  if(!m) return;
  var isEn=!!m[1], date=m[2];
  if(l==='en'&&!isEn){
    fetch('/reports/en/index.json?ts='+Date.now(),{cache:'no-store'}).then(function(r){return r.ok?r.json():null;}).then(function(d){
      var list=(d&&d.dates)||[];
      if(list.indexOf(date)>=0){ location.href='/reports/en/'+date+'.html'; } else { note(t('no-en')); }
    }).catch(function(){ note(t('no-en')); });
  } else if(l==='ar'&&isEn){
    location.href='/reports/'+date+'.html';
  }
}
function applyLang(l,go){
  try{LS.setItem('mn-lang',l);}catch(e){}
  var lock=document.documentElement.getAttribute('data-lang');
  if(lock&&l!==lock){ if(go) routeLang(l); return; }
  var root=document.documentElement;
  root.lang=(l==='en')?'en':'ar'; root.dir=(l==='en')?'ltr':'rtl';
  body.classList.toggle('lang-en', l==='en');
  paintLang(); if(go) routeLang(l);
}
"""


def nav_html(active: str = "") -> str:
    """شريط التنقّل الموحّد. active: home | monthly | cumulative | report"""
    def link(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{href}"{cur} data-i18n="{key}">{label}</a>'
    # زر الطباعة في الشريط الواحد لصفحات الإصدار فقط (يحلّ محل زر الشريط العلوي المخفي على الشاشة)
    print_btn = '<button type="button" class="sn-theme sn-print" id="sn-print" data-i18n="print">طباعة / PDF</button>' if active == "report" else ""
    return f"""<nav class="site-nav no-print" aria-label="تنقل الموقع">
  <a class="sn-skip" href="#" id="sn-skip" data-i18n="skip">الانتقال إلى المحتوى</a>
  <div class="sn-inner">
    <a class="sn-brand" href="/">
      <span class="sn-mark">{MARK_SVG}</span>
      <span class="sn-name">{BRAND}<em>{BRAND_SUB}</em></span>
    </a>
    <button type="button" class="sn-menu no-print" aria-expanded="false" aria-controls="sn-panel">
      <span class="sn-menu-icon" aria-hidden="true"></span><span data-i18n="menu">القائمة</span>
    </button>
    <div class="sn-panel" id="sn-panel">
    <div class="sn-links">
      {link('/', 'الرئيسية', 'home')}
      {link('/reports/special.html', 'التقارير الخاصة', 'special')}
      {link('/#archive', 'الأرشيف', 'archive')}
      {link('/reports/monthly-2026-10.html', 'اللوحة الشهرية', 'monthly')}
      {link('/reports/cumulative-2026.html', 'السجل التراكمي', 'cumulative')}
      {link('/sources.html', 'المصادر والمراجع', 'sources')}
      {link('/additions.html', 'إضافات', 'additions')}
    </div>
    <div class="sn-tools">
      <div class="sn-lang" role="group" aria-label="اللغة / Language">
        <button type="button" data-lang="ar" title="العربية" lang="ar">ع</button>
        <button type="button" data-lang="en" title="English" lang="en">EN</button>
      </div>
      <div class="sn-scale" role="group" aria-label="حجم الخط" data-i18n-aria="scale">
        <button type="button" data-scale="1" title="حجم عادي">أ</button>
        <button type="button" data-scale="1.12" title="حجم أكبر">أ+</button>
        <button type="button" data-scale="1.25" title="أكبر حجم">أ++</button>
      </div>
      <button type="button" class="sn-theme" id="sn-theme">المظهر</button>
      {print_btn}
    </div>
    </div>
  </div>
</nav>"""


def foot_html(note: str = "") -> str:
    extra = f" · {note}" if note else ""
    return f"""<footer class="sn-foot no-print">
  <div class="sf-inner">
    <span><span data-i18n-html="foot1">{BRAND} — {BRAND_SUB}</span>{extra}</span>
    <span data-i18n-html="foot2">تُحدَّث الصفحات آليًا مع كل إصدار · <a href="/#archive">الأرشيف الكامل</a> · <a href="/feed.xml">تغذية الإصدارات</a></span>
  </div>
</footer>"""


def inject(html: str, active: str, note: str = "") -> str:
    """حقن الترويسة والتفضيلات في صفحة مُولَّدة."""
    if "</head>" not in html:
        return html
    style = f"<style>{SITE_CSS}{MOBILE_NAV_CSS}{LANG_CSS}</style>"
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
        html = html.replace("</body>", foot_html(note) + PREFS_LATE + MOBILE_NAV_JS + "</body>", 1)
    return html

MOBILE_NAV_CSS = """
/* قائمة الجوال — تضغط شريطي الموقع والصفحة إلى ارتفاع صغير */
.sn-menu{display:none}
/* سطح المكتب: الروابط والأدوات في صف واحد بجانب الشعار (كانت تتراصّ صفين داخل اللوحة) */
@media (min-width:1041px){
  .sn-panel{display:flex;align-items:center;gap:12px;flex:1 1 auto;min-width:0}
  .sn-panel .sn-links{margin-inline-start:0}
  .sn-panel .sn-tools{margin-inline-start:auto}
}
/* عرض متوسط (لوحي): يبقى الشريط صفًّا واحدًا حتى مع زر الطباعة */
@media (min-width:1041px) and (max-width:1180px){
  .sn-name em{display:none}
  .site-nav .sn-inner{gap:8px;padding-inline:14px}
  .sn-links{gap:0}
  .sn-links a{padding:6px 5px;font-size:13px}
  .sn-panel{gap:6px}
  .sn-tools{gap:6px}
  .sn-theme{padding:6px 8px}
}
@media (max-width:1040px){
  .site-nav .sn-inner{flex-wrap:nowrap;padding:8px 14px;gap:10px;position:relative}
  .sn-name em{display:none}
  .sn-menu{
    display:inline-flex;align-items:center;gap:8px;margin-inline-start:auto;
    min-height:44px;padding:0 14px;border-radius:10px;cursor:pointer;
    background:var(--sn-panel);border:1px solid var(--sn-line);color:var(--sn-ink);font:inherit;font-size:14px
  }
  .sn-menu-icon,.sn-menu-icon::before,.sn-menu-icon::after{
    display:block;width:16px;height:2px;background:currentColor;border-radius:2px;position:relative;
    transition:transform .2s ease,background-color .2s ease
  }
  .sn-menu-icon::before,.sn-menu-icon::after{content:"";position:absolute;inset-inline:0}
  .sn-menu-icon::before{top:-5px}
  .sn-menu-icon::after{top:5px}
  .site-nav.open .sn-menu-icon{background:transparent}
  .site-nav.open .sn-menu-icon::before{top:0;transform:rotate(45deg)}
  .site-nav.open .sn-menu-icon::after{top:0;transform:rotate(-45deg)}
  .sn-panel{
    display:none;position:absolute;inset-inline:0;top:100%;
    background:var(--sn-bg);border-bottom:1px solid var(--sn-line);padding:10px 14px 16px;
    flex-direction:column;gap:12px;box-shadow:0 0 0 100vh rgba(0,0,0,.45);z-index:5
  }
  .site-nav.open .sn-panel{display:flex}
  .site-nav .sn-links{flex-direction:column;margin:0;gap:2px}
  .site-nav .sn-links a{min-height:44px;display:flex;align-items:center}
  .topbar-inner{flex-wrap:nowrap !important;padding:6px 14px !important;gap:8px !important}
  .topbar .brand-sub,.topbar .tb-meta .chip,.topbar .brand-mark{display:none}
  .topbar .brand-title{font-size:13.5px;line-height:1.4;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
  .topbar .tb-meta{display:flex;gap:6px;flex:0 0 auto}
  .topbar .btn{min-height:40px;padding:6px 10px}
}
  .topbar .btn{min-width:44px;display:inline-flex;align-items:center;justify-content:center}
}
/* أهداف لمس على سطح المكتب — الشاشة فقط (قياس 2026-10-29: 34×35.3 و93.9×39.3) */
@media screen{
  .topbar a, .topbar button, .topbar .btn, .sn-brand, .sn-links a,
  .sc-toggle, .sc-jump a, .chip, .chip a, .tb-meta .btn,
  .sn-tools button, .sn-tools a, .sn-scale button, .sc-more a,
  .sc-all button, details.sc-basis summary, .sf-inner a{
    min-height:44px; min-width:44px; display:inline-flex; align-items:center;
    justify-content:center; box-sizing:border-box;
  }
}
/* أهداف لمس وقص النص على الجوال — الشاشة فقط */
@media screen and (max-width:820px){
  a, button, [role="button"], summary {
    min-height:44px !important;
    min-width:44px !important;
    display:inline-flex;
    align-items:center;
    box-sizing:border-box;
  }
  nav a, .sn-link, .sn-brand, .p-btn, .chip a, .sc-jump a,
  button, summary, .sc-toggle {
    min-height:44px !important;
    min-width:44px !important;
    padding-block:8px;
  }
  .sc-toggle, .sc-toggle.no-print {
    width:44px;
    height:44px;
    min-width:44px;
  }
  td a, th a, table a, .src a, .st a {
    min-height:44px !important;
    min-width:44px !important;
    display:inline-flex;
    align-items:center;
    box-sizing:border-box;
    padding-block:8px;
    vertical-align:middle;
  }
  .sc-peek, .sc-peek span, .sc-kn, .sc-gist, .sc-sum,
  [class*="clamp"], [class*="gist"] {
    -webkit-line-clamp:unset !important;
    display:block !important;
    max-height:none !important;
    overflow:visible !important;
    white-space:normal !important;
    text-overflow:clip !important;
  }
  nav.sc-jump { -webkit-mask-image:linear-gradient(90deg, transparent 0, #000 18px, #000 calc(100% - 26px), transparent 100%);
    mask-image:linear-gradient(90deg, transparent 0, #000 18px, #000 calc(100% - 26px), transparent 100%); }
}
html{scroll-padding-top:calc(var(--nav-h, 60px) + var(--bar-h, 0px) + 12px);scroll-padding-bottom:80px}
section.doc{scroll-margin-top:0 !important}
"""

MOBILE_NAV_JS = """
<script>
(function(){
  var nav = document.querySelector('.site-nav'); if (!nav) return;
  var btn = nav.querySelector('.sn-menu'), panel = nav.querySelector('.sn-panel');
  var root = document.documentElement;
  function measure(){
    root.style.setProperty('--nav-h', nav.offsetHeight + 'px');
    var b = document.querySelector('.topbar');
    root.style.setProperty('--bar-h', (b && getComputedStyle(b).display !== 'none' ? b.offsetHeight : 0) + 'px');
  }
  if (btn && panel){
    btn.addEventListener('click', function(){
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape' && nav.classList.contains('open')){
        nav.classList.remove('open'); btn.setAttribute('aria-expanded','false'); btn.focus();
      }
    });
    nav.addEventListener('focusout', function(e){
      if (nav.classList.contains('open') && !nav.contains(e.relatedTarget)){
        nav.classList.remove('open'); btn.setAttribute('aria-expanded','false');
      }
    });
  }
  if ('ResizeObserver' in window) new ResizeObserver(measure).observe(nav);
  addEventListener('resize', measure); measure();
})();
</script>
"""


def mobile_nav_css() -> str:
    return MOBILE_NAV_CSS


def mobile_nav_js() -> str:
    return MOBILE_NAV_JS
