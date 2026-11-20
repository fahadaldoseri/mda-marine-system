#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import html as _html
import re
import pathlib
"""
وحدة ترويسة الموقع الدائم وتفضيلات القراءة.

تُستخدم من build_site.py لحقن:
- شريط تنقّل موحّد في كل صفحة.
- تفضيلات محفوظة في المتصفح (المظهر، حجم الخط، آخر تقرير فُتح).
- أنماط الموقع المشتركة.
"""

BRAND = "مركز الوعي بالمجال البحري"
BRAND_SUB = "تقارير أمن الملاحة — مملكة البحرين"
# سياسة مالكية مؤقتة: لا تعرض الواجهة زرًا تفاعليًا للطباعة ولا رابط تنزيل PDF.
# لا تُغيّر إلى True إلا بأمر المالك الصريح وبالتزامن مع runbook/runbook.json.
PRINT_ENABLED = False
ROOT = pathlib.Path(__file__).resolve().parents[1]

# ── هوية بصرية (م-28): ذهبي للهوية · تركوازي للبيانات · ألوان التهديد دلالية ──
SITE_ORIGIN = "https://mda-bh.pages.dev"
LOGO_HEADER = "/assets/logo-header.png"
LOGO_ALT = "شعار مركز الوعي بالمجال البحري — مملكة البحرين"
LOGO_ALT_EN = "Maritime Domain Awareness Center logo — Kingdom of Bahrain"
ICON_32 = "/assets/icon-32.png"
ICON_180 = "/assets/icon-180.png"
ICON_512 = "/assets/icon-512.png"
OG_IMAGE = "/assets/og-1200x630.png"


def icon_links() -> str:
    """أيقونات المتصفح: اقتصاص من الشعار الرسمي بلا تعديل تصميم (م-28 · 1.2)."""
    return (
        f'<link rel="icon" href="{ICON_32}" sizes="32x32" type="image/png">'
        f'<link rel="icon" href="{ICON_512}" sizes="512x512" type="image/png">'
        f'<link rel="apple-touch-icon" href="{ICON_180}">'
    )


def social_meta(title: str, description: str, path: str = "/", image: str = OG_IMAGE) -> str:
    """وسوم المشاركة (م-28 · 1.3): صورة 1200×630 وعنوان ووصف عربيان."""
    t = _html.escape((title or BRAND).strip(), quote=True)
    d = _html.escape((description or BRAND_SUB).strip(), quote=True)
    u = _html.escape(SITE_ORIGIN + path, quote=True)
    img = _html.escape(SITE_ORIGIN + image, quote=True)
    return (
        '<meta property="og:type" content="website">'
        f'<meta property="og:site_name" content="{_html.escape(BRAND, quote=True)}">'
        '<meta property="og:locale" content="ar_BH">'
        f'<meta property="og:title" content="{t}">'
        f'<meta property="og:description" content="{d}">'
        f'<meta property="og:url" content="{u}">'
        f'<meta property="og:image" content="{img}">'
        '<meta property="og:image:width" content="1200">'
        '<meta property="og:image:height" content="630">'
        '<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{t}">'
        f'<meta name="twitter:description" content="{d}">'
        f'<meta name="twitter:image" content="{img}">'
    )


def head_assets(html: str, path: str = "/") -> str:
    """أيقونات ووسوم مشاركة تُشتق من رأس الصفحة نفسه — تُحقن مرة واحدة فقط."""
    if 'rel="icon"' in html:
        return ""
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = m.group(1).strip() if m else BRAND
    m2 = re.search(r'<meta name="description" content="(.*?)"', html, re.S)
    desc = m2.group(1).strip() if m2 else BRAND_SUB
    return icon_links() + social_meta(title, desc, path)


def print_brand_html() -> str:
    """ترويسة الطباعة: الشعار والاسم، تظهر في الطباعة فقط (م-28 · 1.4)."""
    return (
        '<div class="print-brand" aria-hidden="true">'
        f'<img src="{LOGO_HEADER}" width="34" height="34" alt="{LOGO_ALT}">'
        f'<span>{BRAND} — {BRAND_SUB}</span></div>'
    )
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
/* ── هوية (م-28): ذهبي للهوية · تركوازي للبيانات ── */
:root{--sn-gold:#e8be60}
body.daylight{--sn-gold:#8a6410}
.sn-logo{width:40px;height:40px;flex:0 0 auto;display:block;border-radius:50%;
filter:drop-shadow(0 1px 2px rgba(0,0,0,.35))}
body.daylight .sn-logo{box-shadow:0 0 0 1px rgba(10,41,59,.28)}
.site-nav.is-compact .sn-logo{width:26px;height:26px}
.sn-name{color:var(--sn-gold)}
.sn-links a:hover{color:var(--sn-gold)}
.sn-links a[aria-current="page"]{color:var(--sn-gold);border-color:var(--sn-gold)}
.print-brand{display:none}
@media print{.print-brand{display:flex!important;align-items:center;gap:10px;padding:0 0 8px;
border-bottom:1px solid #999;margin:0 0 12px;font-size:13px;color:#111}
.print-brand img{width:34px;height:34px}}

body.daylight{--sn-bg:#eef3f9;--sn-panel:#ffffff;--sn-line:#d3dded;--sn-ink:#0d1a2b;--sn-ink2:#33475e;
--sn-muted:#4f657c;--sn-accent:#0b7a72;--sn-accent-ink:#ffffff}
.site-nav{position:sticky;top:0;z-index:60;background:var(--sn-bg);border-bottom:1px solid var(--sn-line);
font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif}
.site-nav .sn-inner{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:12px;padding:9px 20px;flex-wrap:wrap}
.site-nav.is-compact .sn-inner{padding:3px 20px;gap:8px}
.site-nav.is-compact .sn-name em{display:none}
.site-nav.is-compact .sn-mark{width:22px;height:22px}
.site-nav.is-compact .sn-mark svg{width:13px;height:13px}
.site-nav.is-compact .sn-links{flex-wrap:nowrap;overflow-x:auto}
.site-nav.is-compact .sn-links a{padding:4px 7px;min-height:26px;font-size:13px}
.site-nav.is-compact{box-shadow:0 6px 18px rgba(0,0,0,.35)}
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
.sn-tools{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end;min-width:0}
/* أدوات أيقونية بأربع أدوات (م-06 · م-23 · م-24) */
.sn-tools button,.sn-tools a,.sn-tools span.sn-tool{min-height:44px;min-width:44px}
.sn-tool{display:inline-flex;align-items:center;justify-content:center;background:var(--sn-panel);
border:1px solid var(--sn-line);color:var(--sn-ink2);border-radius:9px;padding:0;cursor:pointer;font:inherit}
.sn-tool:hover{color:var(--sn-ink);border-color:var(--sn-accent)}
.sn-tool:focus-visible{outline:2px solid var(--sn-accent);outline-offset:2px}
.sn-ico{width:19px;height:19px;display:inline-block}
.sn-ico-a{font-size:15px;font-weight:700;line-height:1;width:auto;height:auto}
.sn-ico-sun{display:none}
body.daylight .sn-ico-sun{display:inline-block}
body.daylight .sn-ico-moon{display:none}
.sn-vh{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
.sn-lang{display:flex;flex:0 0 auto;border:1px solid var(--sn-line);border-radius:9px;overflow:hidden;background:var(--sn-panel)}
.sn-lang a,.sn-lang span{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;
color:var(--sn-ink2);text-decoration:none;font-size:13px;background:transparent}
.sn-lang a:hover{color:var(--sn-ink);background:var(--sn-bg)}
.sn-lang .sn-cur{background:var(--sn-accent);color:var(--sn-accent-ink);font-weight:700}
.sn-lang .sn-off{color:var(--sn-muted);opacity:.6;cursor:not-allowed}
.sn-skip{position:absolute;inset-inline-start:12px;top:-80px;z-index:70;background:var(--sn-accent);color:var(--sn-accent-ink)!important;
padding:9px 16px;border-radius:9px;font-weight:700;font-size:14px}
.sn-skip:focus{top:8px;outline:2px solid var(--sn-ink);outline-offset:2px}
.sn-print{background:var(--sn-accent);color:var(--sn-accent-ink);border-color:transparent;font-weight:700}
.sn-print:hover{color:var(--sn-accent-ink);filter:brightness(1.08)}
.sn-print-disabled{background:var(--sn-panel);color:var(--sn-muted);border-color:var(--sn-line);cursor:not-allowed}
.sn-foot{margin-top:44px;border-top:1px solid var(--sn-line);background:var(--sn-bg);
font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif}
.sn-foot .sf-inner{max-width:1180px;margin:0 auto;padding:20px;color:var(--sn-muted);font-size:13px;
display:flex;gap:16px;flex-wrap:wrap;justify-content:space-between}
.sn-foot a{color:var(--sn-ink2);display:inline-block;padding:4px 2px;min-height:24px}
body.daylight .topbar{background:#ffffff!important;border-bottom-color:#d3dded!important}
body.daylight .brand-title,body.daylight .brand-sub{color:#0d1a2b}
@media print{.site-nav,.sn-foot{display:none!important}}
/* ── التنسيق الكتابي الموحّد (م-27): قصير وسط · فقرة مبرَّرة · قوائم إلى اليمين ── */
.prose{text-align:right}
.prose p{margin:0 0 9px;line-height:1.7;text-align:justify;text-justify:inter-word}
.tx-center{text-align:center}
.tx-just{text-align:justify;text-justify:inter-word}
.tx-start{text-align:right}
@media print{.prose p{orphans:3;widows:3}}
"""

# سكربت يُنفَّذ فور فتح الجسم لمنع وميض المظهر المحفوظ
PREFS_EARLY = """<script>
(function(){try{
var b=document.body;if(!b)return;
var t=localStorage.getItem('mn-theme');if(t==='light')b.classList.add('daylight');
/* لغة المستند تعلنها الصفحة نفسها (وسم lang + data-lang)؛ ولغة الشريط تتبع الصفحة أو تفضيل الزائر. */
var lockE=document.documentElement.getAttribute('data-lang');
if(lockE==='en'){b.classList.add('lang-en');}
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
var SCALES=[1,1.12,1.25], SCALE_NAMES=((document.documentElement.getAttribute('lang')||'').indexOf('en')===0)?['Font size: normal','Font size: larger','Font size: largest']:['حجم الخط: عادي','حجم الخط: أكبر','حجم الخط: أكبر حجم'];
function currentScale(){var s=parseFloat(LS.getItem('mn-scale')||'1');return (s&&s>0)?s:1;}
function scaleIdx(){var i=SCALES.indexOf(currentScale());return i<0?0:i;}
function paintScaleBtn(){
  var b=document.getElementById('sn-scale'); if(!b) return;
  var i=scaleIdx(); b.title=SCALE_NAMES[i];
  var t=document.getElementById('sn-scale-text'); if(t) t.textContent=SCALE_NAMES[i];
}
function paint(){
  paintLang();
  paintScaleBtn();
}
function toggleTheme(){var on=body.classList.toggle('daylight');save('mn-theme',on?'light':'dark');paint();}
if(reportBtn) reportBtn.addEventListener('click',function(e){e.preventDefault();toggleTheme();});
if(siteBtn) siteBtn.addEventListener('click',function(e){e.preventDefault();toggleTheme();});
var scaleBtn=document.getElementById('sn-scale');
if(scaleBtn) scaleBtn.addEventListener('click',function(e){e.preventDefault();
  var s=SCALES[(scaleIdx()+1)%SCALES.length]; save('mn-scale',s);
  body.style.zoom=(s===1?'':s); paintScaleBtn();});
paintScaleBtn();
var I18N={ar:{"chg_confirmation": "تأكيد", "chg_denial": "نفي", "row_one_sided_account": "رواية من طرف واحد", "row_account": "رواية", "row_declaration": "إعلان", "row_official_report": "بلاغ رسمي", "row_unconfirmed_report": "بلاغ غير مؤكد", "row_report": "بلاغ", "row_professional_report": "تقرير مهني", "area_iran": "إيران", "hist_aden_taiz": "عدن وتعز ومخزون الأدوية", "hist_latest_official": "أحدث بلاغ رسمي", "hist_three_incidents": "عن ثلاث وقائع في مضيق هرمز وخليج عُمان والخليج العربي مع استمرار تضارب روايات الألغام والناقلات", "hist_incidents_period": "عن وقائع في مضيق هرمز وخليج عُمان والخليج العربي داخل الفترة", "hist_quad_criticism": "عنوان إعلامي عن انتقاد مجموعة رباعية لقيود التصدير وإغلاق مضيق هرمز", "hist_media_reopening": "نقل إعلامي؛ لم يُثبت تنفيذ الفتح (01-02 و01-03؛ موثوقية متوسطة وتصديق متوسط)", "hist_leak_stopped": "نقل مهني يفيد توقف التسرب واستمرار أعمال التنظيف (01-06؛ موثوقية متوسطة وتصديق متوسط)", "hist_possible_attack_hormuz": "أبلغت عن هجوم محتمل على سفينة داخل مضيق هرمز", "hist_basis_assessment_1102": "أساس التقدير: يستند التقدير إلى صدور ثلاثة تحذيرات رسمية خلال الفترة، بينها بلاغ هجوم داخل مضيق هرمز، وإلى إدانة رسمية لهجوم على ناقلة غاز. ولا ترفع الروايات غير المؤكدة مستوى التهديد (02-01 إلى 02-05؛ موثوقية جيدة وتصديق جيد).", "hist_fifth_fleet": "أعلن الأسطول الخامس الأمريكي تقديم مساندة لبحّارة واجهوا عطلًا في المحرك في بحر العرب", "hist_coalition_intercept": "أعلن التحالف المشترك اعتراض وتدمير صاروخ باليستي وطائرة مسيّرة أُطلقا باتجاه المنطقة الجنوبية، وتدمير مصادر في الحديدة وذمار", "hist_bahrain_condemn": "أعلنت وزارة الخارجية البحرينية إدانتها لهجوم استهدف ناقلة غاز قطرية في الخليج العربي", "hist_three_warnings_1102": "ثلاثة تحذيرات رسمية خلال الفترة، وأظهرت قائمتها بلاغ هجوم داخل مضيق هرمز. وهذا أعلى تصعيد في قطاع مضيق هرمز وخليج عُمان والخليج العربي. ونقلت مصادر إيرانية ووسائل متابعة أن ناقلتي نفط انفجرتا بعد اصطدامهما المزعوم بألغام بحرية، من دون تأكيد رسمي مستقل (02-01 إلى 02-06).", "hist_one_sided_repeat": "رواية من طرف واحد، والتكرار لا يعادل تأكيدًا مستقلًا (02-06؛ موثوقية متوسطة وتصديق متوسط)", "hist_incident_warning_list": "عن واقعة داخل مضيق هرمز في قائمة تحذيرات", "hist_incident_hormuz_report_dated": "عن واقعة داخل مضيق هرمز، وبلاغ بتاريخ", "hist_incident_72nm_khafji": "عن واقعة على بعد 72 ميلًا بحريًا شرق رأس الخفجي في السعودية", "hist_incident_72nm_detail": "عن واقعة على بعد 72 ميلًا بحريًا شرق رأس الخفجي، بلا تفاصيل عن السفن أو الضرر في النص المتاح (02-05 و02-15؛ موثوقية جيدة وتصديق جيد)", "hist_projectiles_tug": "نقل إعلامي عن مقذوفين مجهولين باتجاه ناقلة، وتقرير عن إصابة قاطرة بحرية في المضيق، بلا نص رسمي مطابق (02-08 و02-16؛ موثوقية متوسطة وتصديق متوسط)", "hist_hijack_fishing_somalia": "اختطاف سفينة صيد إيرانية مع 23 فردًا على متنها قرب السواحل الشمالية الشرقية للصومال", "hist_total_125_24": "المجموع بقي 125 حادثة مؤكدة و24 وفاة (03-04؛ موثوقية عالية وتصديق مرتفع)", "hist_two_groups_one": "عند وجود مجموعتين مؤكَّدتين في القطاع الأول، واليوم ثبتت مجموعة مؤكدة واحدة فقط. تظل الروايات غير المؤكدة قابلة للرفع حال ثبوتها رسميًا (03-05 و03-08؛ موثوقية متوسطة وتصديق متوسط).", "hist_horn_medium": "مستوى التهديد في القرن الأفريقي: متوسط. وردت رواية عن اختطاف سفينة صيد مقابل الساحل الصومالي بلا تأكيد رسمي منشور (03-09؛ موثوقية متوسطة وتصديق متوسط).", "hist_bab_low": "مستوى التهديد في باب المندب والبحر الأحمر: منخفض. لم تُسجَّل واقعة بحرية مؤهلة جديدة؛ البند الوحيد في المصادر المستخدمة هو تقدم بري في اليمن (03-11؛ موثوقية متوسطة وتصديق متوسط).", "hist_128_24": "عند 128 حادثة مؤكدة و24 وفاة مؤكدة بتاريخ 3/11/2026.", "hist_change_factors_1104": "عوامل التغيير: تأكيد رسمي داخل المضيق يرفعه، وغياب بلاغ مؤهل يخفضه.", "hist_irgc_four_tankers": "أعلن الحرس الثوري الإيراني تدمير أربع ناقلات نفط بألغام بحرية داخل مضيق هرمز، وضبط سفينتين، وإسقاط مسيّرة أمريكية من نوع MQ-9؛ الإعلان طرفي بلا تأكيد مستقل.", "hist_reassess_routes": "أعيدوا تقييم مسارات الاقتراب من مضيق هرمز وحدّدوا نقاط انتظار خارج نطاق الإعلان.", "hist_change_factors_1105": "عوامل التغيير: تأكيد رسمي لخسائر داخل المضيق يرفعه، وظهور ما يثبت أن الإعلان غير دقيق يخفضه.", "hist_straits_live_five": "أفادت straits.live بتقارير إيرانية عن إصابة خمس ناقلات بألغام بحرية قرب مضيق هرمز؛ لم يؤكد", "hist_iranian_five_tankers": "رواية إيرانية عن إصابة خمس ناقلات بألغام بحرية قرب مضيق هرمز خلال 24 ساعة", "hist_incident_50nm_shamal": "عن واقعة على بعد 50 ميلًا بحريًا شمال مدينة الشمال ووصفها بأنها هجوم", "hist_change_factors_text": "عوامل التغيير: يرفعه نص", "hist_or_official_denial": "أو نفي رسمي موثق للروايات.", "hist_continuing_latest": "مستمر؛ آخرها 2026-11-03", "hist_stray_cargo_accounts": "عن سفينة بضائع سائبة وروايات عن ناقلتين وسفينة شحن قرب مضيق هرمز وخليج عُمان دون تأكيد مستقل", "hist_stray_military_accounts": "عن سفينة بضائع سائبة وقوات عسكرية، مع روايات عن ناقلتين وسفينة شحن", "hist_incident_uae_rescue": "عنوان عن حادث بحري قريبًا من ساحل الإمارات وبلاغ إنقاذ 22 شخصًا من حريق في بحر عُمان", "hist_two_headlines_material": "تجمع المادة بين عنواني", "listed_fragment": "أدرجت", "top_news_page": "أهم الأخبار — في صفحة", "two_headlines": "عنوانان: نشاط مشبوه وهجوم", "about_attack_khasab_hormuz": "عن هجوم ونشاط مشبوه قرب خصب وهرمز مع روايات أخرى عن حرائق وألغام بلا تأكيد مستقل", "about_stray_cargo_vessel": "عن واقعة تشمل سفينة بضائع سائبة وقوات عسكرية", "about_late_attack_hormuz": "عن واقعة متأخرة الإبلاغ مصنفة هجومًا في مضيق هرمز", "media_tanker_mines_hormuz": "عناوين إعلامية عن ناقلة أو ناقلات احترقت أو أصيبت بألغام في مضيق هرمز", "headline_attack_hormuz": "عنوانًا عن واقعة مصنفة هجومًا في مضيق هرمز؛ لا اسم سفينة أو نتيجة.", "early_warning_signs": "علامات الإنذار المبكر", "skip": "الانتقال إلى المحتوى", "menu": "القائمة", "home": "الرئيسية", "special": "التقارير الخاصة", "archive": "الأرشيف", "monthly": "اللوحة الشهرية", "cumulative": "السجل التراكمي", "sources": "المصادر والمراجع", "additions": "الإضافات", "scale": "حجم الخط", "theme": "المظهر", "print-off": "الطباعة غير مفعّلة حاليًا", "no-en-note": "النسخة الإنجليزية متاحة ابتداءً من 29 أكتوبر 2026", "en-open": "English edition", "theme-dark": "المظهر: ليلي", "theme-light": "المظهر: نهاري", "print": "طباعة / PDF", "lang": "اللغة", "no-en": "النسخة الإنجليزية لهذا الإصدار غير متاحة بعد."},en:{"chg_confirmation": "confirmation", "chg_denial": "denial", "row_one_sided_account": "one-sided account", "row_account": "account", "row_declaration": "declaration", "row_official_report": "official report", "row_unconfirmed_report": "unconfirmed report", "row_report": "report", "row_professional_report": "professional report", "area_iran": "Iran", "hist_aden_taiz": "Aden, Taiz, and the medicine stock", "hist_latest_official": "the latest official report", "hist_three_incidents": "about three incidents in the Strait of Hormuz, the Gulf of Oman, and the Arabian Gulf, while conflicting accounts of mines and tankers continue", "hist_incidents_period": "about incidents in the Strait of Hormuz, the Gulf of Oman, and the Arabian Gulf within the period", "hist_quad_criticism": "a media headline about a quad group's criticism of export restrictions and the closure of the Strait of Hormuz", "hist_media_reopening": "media reporting; the reopening was not proven to have been carried out (01-02 and 01-03; medium reliability, medium corroboration)", "hist_leak_stopped": "professional reporting indicating the leak has stopped and cleanup work continues (01-06; medium reliability, medium corroboration)", "hist_possible_attack_hormuz": "reported a possible attack on a vessel inside the Strait of Hormuz", "hist_basis_assessment_1102": "Basis of the assessment: it rests on three official warnings issued during the period, including a report of an attack inside the Strait of Hormuz, and on an official condemnation of an attack on a gas tanker. Unconfirmed accounts do not raise the threat level (02-01 to 02-05; good reliability, good corroboration).", "hist_fifth_fleet": "the United States Fifth Fleet announced assistance to sailors who faced an engine failure in the Arabian Sea", "hist_coalition_intercept": "the joint coalition announced the interception and destruction of a ballistic missile and an unmanned aerial vehicle launched towards the southern region, and the destruction of sources in Al Hudaydah and Dhamar", "hist_bahrain_condemn": "the Bahraini Ministry of Foreign Affairs announced its condemnation of an attack targeting a Qatari gas tanker in the Arabian Gulf", "hist_three_warnings_1102": "three official warnings during the period, and their list showed a report of an attack inside the Strait of Hormuz. This is the highest escalation in the Strait of Hormuz, the Gulf of Oman, and the Arabian Gulf sector. Iranian sources and monitoring outlets reported that two oil tankers exploded after their alleged collision with naval mines, without independent official confirmation (02-01 to 02-06).", "hist_one_sided_repeat": "a one-sided account, and repetition does not amount to independent confirmation (02-06; medium reliability, medium corroboration)", "hist_incident_warning_list": "about an incident inside the Strait of Hormuz on a warnings list", "hist_incident_hormuz_report_dated": "about an incident inside the Strait of Hormuz, and a report dated", "hist_incident_72nm_khafji": "about an incident 72 nautical miles east of Ras Al Khafji in Saudi Arabia", "hist_incident_72nm_detail": "about an incident 72 nautical miles east of Ras Al Khafji, with no details on the vessels or the damage in the available text (02-05 and 02-15; good reliability, good corroboration)", "hist_projectiles_tug": "media reporting of two unidentified projectiles towards a tanker, and a report of a marine tug being hit in the strait, with no matching official text (02-08 and 02-16; medium reliability, medium corroboration)", "hist_hijack_fishing_somalia": "the hijacking of an Iranian fishing vessel with 23 people aboard near the north-eastern coast of Somalia", "hist_total_125_24": "the total remained 125 confirmed incidents and 24 deaths (03-04; high reliability, high corroboration)", "hist_two_groups_one": "while the first sector had two confirmed groups, only one confirmed group was established today. Unconfirmed accounts remain capable of raising the level once officially established (03-05 and 03-08; medium reliability, medium corroboration).", "hist_horn_medium": "Threat level in the Horn of Africa: medium. An account was reported of a fishing vessel hijacked off the Somali coast without published official confirmation (03-09; medium reliability, medium corroboration).", "hist_bab_low": "Threat level in Bab al-Mandab and the Red Sea: low. No new qualifying maritime incident was recorded; the only item in the sources used is a ground advance in Yemen (03-11; medium reliability, medium corroboration).", "hist_128_24": "at 128 confirmed incidents and 24 confirmed deaths as of 3/11/2026.", "hist_change_factors_1104": "Change factors: official confirmation inside the strait raises it, and the absence of a qualifying report lowers it.", "hist_irgc_four_tankers": "Iran's Revolutionary Guard announced the destruction of four oil tankers by naval mines inside the Strait of Hormuz, the seizure of two vessels, and the downing of a United States MQ-9 drone; the announcement is one-sided with no independent confirmation.", "hist_reassess_routes": "Reassess approach routes to the Strait of Hormuz and set waiting points outside the declared area.", "hist_change_factors_1105": "Change factors: official confirmation of losses inside the strait raises it, and evidence that the announcement is inaccurate lowers it.", "hist_straits_live_five": "straits.live noted Iranian reports of five tankers being hit by naval mines near the Strait of Hormuz; it did not confirm", "hist_iranian_five_tankers": "an Iranian account of five tankers being hit by naval mines near the Strait of Hormuz within 24 hours", "hist_incident_50nm_shamal": "about an incident 50 nautical miles north of the town of Ash Shamal, described as an attack", "hist_change_factors_text": "Change factors: it is raised by a text", "hist_or_official_denial": "or a documented official denial of the accounts.", "hist_continuing_latest": "continuing; the latest on 2026-11-03", "hist_stray_cargo_accounts": "about a stray cargo vessel and accounts of two tankers and a cargo ship near the Strait of Hormuz and the Gulf of Oman without independent confirmation", "hist_stray_military_accounts": "about a stray cargo vessel and military forces, with accounts of two tankers and a cargo ship", "hist_incident_uae_rescue": "a headline about a maritime incident near the coast of the United Arab Emirates and a report of 22 people rescued from a fire in the Gulf of Oman", "hist_two_headlines_material": "the material combines two headlines", "listed_fragment": "listed", "top_news_page": "Top news — on page", "two_headlines": "Two headlines: suspicious activity and an attack", "about_attack_khasab_hormuz": "about an attack and suspicious activity near Khasab and Hormuz, with further accounts of fires and mines without independent confirmation", "about_stray_cargo_vessel": "about an incident involving a stray cargo vessel and military forces", "about_late_attack_hormuz": "about a late-reported incident classified as an attack in the Strait of Hormuz", "media_tanker_mines_hormuz": "media headlines about one or more tankers that burned or were struck by mines in the Strait of Hormuz", "headline_attack_hormuz": "a headline about an incident classified as an attack in the Strait of Hormuz; no vessel name or outcome.", "early_warning_signs": "Early warning signs", "skip": "Skip to content", "menu": "Menu", "home": "Home", "special": "Special reports", "archive": "Archive", "monthly": "Monthly dashboard", "cumulative": "Cumulative record", "sources": "Sources & references", "additions": "Additions", "scale": "Font size", "theme": "Theme", "print-off": "Printing is currently disabled", "no-en-note": "The English edition is available from 29 October 2026", "en-open": "English edition", "theme-dark": "Theme: night", "theme-light": "Theme: day", "print": "Print / PDF", "lang": "Language", "no-en": "The English edition of this report is not available yet."}};
function pageLang(){var lock=document.documentElement.getAttribute('data-lang');if(lock)return lock;var p=location.pathname;if(p.indexOf('/reports/en/')===0)return 'en';if(p.indexOf('/reports/')===0&&/^\d{4}-\d{2}-\d{2}\.html$/.test(p.slice(9)))return 'ar';return '';}
function currentLang(){var pl=pageLang();if(pl)return pl;var l=LS.getItem('mn-lang');return (l==='en')?'en':'ar';}
function i18nTxt(key){var d=I18N[currentLang()];return (d&&d[key])||I18N.ar[key]||'';}
var _b=document.querySelector('.sn-name'), _s=document.querySelector('.sn-name em');
var BRAND_TXT=_b?(_b.childNodes[0].nodeValue||'').trim():'', BRAND_SUB_TXT=_s?_s.textContent.trim():'';
function paintLang(){
  var l=currentLang();
  document.querySelectorAll('[data-i18n]').forEach(function(el){var v=i18nTxt(el.getAttribute('data-i18n'));if(v)el.textContent=v;});
  document.querySelectorAll('[data-i18n-aria]').forEach(function(el){var v=i18nTxt(el.getAttribute('data-i18n-aria'));if(v)el.setAttribute('aria-label',v);});
  var f1=document.querySelector('[data-i18n-html="foot1"]'); if(f1) f1.textContent=BRAND_TXT+' — '+BRAND_SUB_TXT;
  document.querySelectorAll('[data-lang]').forEach(function(b){b.classList.toggle('on', b.getAttribute('data-lang')===l);});
  var rb=document.getElementById('btn-theme'), sb=document.getElementById('sn-theme');
  var L=(l==='en'), light=body.classList.contains('daylight');
  if(rb) rb.textContent = light ? (L?'Night mode':'النمط الليلي') : (L?'Day mode':'النمط النهاري');
  var st=document.getElementById('sn-theme-text');
  if(st) st.textContent = light ? i18nTxt('theme-light') : i18nTxt('theme-dark');
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
  var pl=pageLang();
  if(pl&&l!==pl){ if(go) routeLang(l); return; }
  var root=document.documentElement;
  root.lang=(l==='en')?'en':'ar'; root.dir=(l==='en')?'ltr':'rtl';
  body.classList.toggle('lang-en', l==='en');
  paintLang(); if(go) routeLang(l);
}
document.querySelectorAll('[data-lang]').forEach(function(b){
  b.addEventListener('click',function(e){e.preventDefault();applyLang(b.getAttribute('data-lang'),true);});
});
// ك-228 (2026-11-11): زر «EN» كان يحمل data-go بلا مستمع نقر، فلم ينقل القارئ إلى
// النسخة الإنجليزية. الربط هنا يسري على كل الصفحات لأن الشريط مشترك.
document.querySelectorAll('[data-go]').forEach(function(b){
  b.addEventListener('click',function(e){var u=b.getAttribute('data-go');if(u){e.preventDefault();location.href=u;}});
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
.sn-lang{display:inline-flex;flex:0 0 auto;border:1px solid var(--sn-line);border-radius:9px;overflow:hidden}
.sn-lang button{background:transparent;border:0;color:var(--sn-ink2);padding:6px 11px;min-height:44px;min-width:44px;
cursor:pointer;font:inherit;font-size:12.5px;font-weight:700}
.sn-lang button.on{background:var(--sn-accent);color:var(--sn-accent-ink)}
.sn-lang button:hover{color:var(--sn-ink)}
.sn-lang-note{position:fixed;left:50%;transform:translateX(-50%);top:14px;z-index:60;background:var(--sn-panel);
border:1px solid var(--sn-line);color:var(--sn-ink);border-radius:10px;padding:10px 14px;font-size:13px;
box-shadow:0 10px 30px rgba(0,0,0,.35);max-width:90vw;text-align:center}
"""

LANG_JS = r"""
var I18N={ar:{"skip": "الانتقال إلى المحتوى", "menu": "القائمة", "home": "الرئيسية", "special": "التقارير الخاصة", "archive": "الأرشيف", "monthly": "اللوحة الشهرية", "cumulative": "السجل التراكمي", "sources": "المصادر والمراجع", "additions": "إضافات", "scale": "حجم الخط", "theme-dark": "المظهر: ليلي", "theme-light": "المظهر: نهاري", "print": "طباعة / PDF", "lang": "اللغة", "no-en": "النسخة الإنجليزية لهذا الإصدار غير متاحة بعد."},en:{"skip": "Skip to content", "menu": "Menu", "home": "Home", "special": "Special reports", "archive": "Archive", "monthly": "Monthly dashboard", "cumulative": "Cumulative record", "sources": "Sources & references", "additions": "Additions", "scale": "Font size", "theme-dark": "Theme: night", "theme-light": "Theme: day", "print": "Print / PDF", "lang": "Language", "no-en": "The English edition of this report is not available yet."}};
function pageLang(){var lock=document.documentElement.getAttribute('data-lang');if(lock)return lock;var p=location.pathname;if(p.indexOf('/reports/en/')===0)return 'en';if(p.indexOf('/reports/')===0&&/^\d{4}-\d{2}-\d{2}\.html$/.test(p.slice(9)))return 'ar';return '';}
function currentLang(){var pl=pageLang();if(pl)return pl;var l=LS.getItem('mn-lang');return (l==='en')?'en':'ar';}
function t(key){var d=I18N[currentLang()];return (d&&d[key])||I18N.ar[key]||'';}
var _b=document.querySelector('.sn-name'), _s=document.querySelector('.sn-name em');
var BRAND_TXT=_b?(_b.childNodes[0].nodeValue||'').trim():'', BRAND_SUB_TXT=_s?_s.textContent.trim():'';
function paintLang(){
  var l=currentLang();
  document.querySelectorAll('[data-i18n]').forEach(function(el){var v=t(el.getAttribute('data-i18n'));if(v)el.textContent=v;});
  document.querySelectorAll('[data-i18n-aria]').forEach(function(el){var v=t(el.getAttribute('data-i18n-aria'));if(v)el.setAttribute('aria-label',v);});\n  document.addEventListener('click',function(e){var b=e.target.closest('[data-go]');if(b){var h=b.getAttribute('data-go');if(h)location.href=h;}});
  var f1=document.querySelector('[data-i18n-html="foot1"]'); if(f1) f1.textContent=BRAND_TXT+' — '+BRAND_SUB_TXT;
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
  var pl=pageLang();
  if(pl&&l!==pl){ if(go) routeLang(l); return; }
  var root=document.documentElement;
  root.lang=(l==='en')?'en':'ar'; root.dir=(l==='en')?'ltr':'rtl';
  body.classList.toggle('lang-en', l==='en');
  paintLang(); if(go) routeLang(l);
}
"""


def lang_group(active_lang: str = "ar", en_href: str = "", ar_href: str = "") -> str:
    """أداة اللغة: «ع» و«EN» — و«EN» ينقل إلى نسخة التاريخ نفسه عند توفرها (م-25 ب)."""
    # ك-629: مفتاح اللغة عنصر إجراء لا رابط، ومسمّاه لاتيني في النسخة الإنجليزية
    # كي لا يبقى حرف عربي ولا سمة عربية في الصفحة الإنجليزية (حارس تماثل الترجمة)،
    # ويكون عدد عناصر اللغة متساويًا في النسختين (زرّ في كلٍّ منهما) فلا يختل تماثل البنية.
    AR_LABEL, EN_LABEL = "AR", "EN"
    if active_lang == "en":
        ar = (f'<button type="button" class="sn-tool sn-lang-btn" data-go="{ar_href}" '
              f'lang="ar" title="Arabic edition" aria-label="Arabic edition">{AR_LABEL}</button>'
              if ar_href else
              f'<span class="sn-off" aria-disabled="true" lang="ar" title="Arabic edition">{AR_LABEL}</span>')
        en = f'<span class="sn-cur" aria-current="true" lang="en" title="English edition">{EN_LABEL}</span>'
        # لا يُطبَّق مفتاح الترجمة العربية على النسخة الإنجليزية، وإلا أعاد النصَّ العربي
        group_aria, group_i18n = "Language", ""
    else:
        ar = f'<span class="sn-cur" aria-current="true" lang="ar" title="العربية">{AR_LABEL}</span>'
        if en_href:
            en = (f'<button type="button" class="sn-tool sn-lang-btn" data-go="{en_href}" '
                  f'lang="en" title="English edition" aria-label="English edition">{EN_LABEL}</button>')
        else:
            en = ('<span class="sn-off" aria-disabled="true" lang="en" '
                  'title="النسخة الإنجليزية متاحة ابتداءً من 29 أكتوبر 2026" '
                  'data-i18n-aria="no-en-note">EN</span>')
        group_aria, group_i18n = "اللغة / Language", "lang"
    i18n_attr = f' data-i18n-aria="{group_i18n}"' if group_i18n else ''
    return (f'<div class="sn-lang" role="group" aria-label="{group_aria}"{i18n_attr}>'
            f'{ar}{en}</div>')


def _page_report_date(html: str) -> str:
    """اشتقاق تاريخ الإصدار من ترويسة الصفحة فقط، لا من تواريخ المتن."""
    import re as _re
    head = (html or "")[:4000]
    m = _re.search(r"(\d{2})/(\d{2})/(\d{4})", head)
    AR_MONTHS = {"يناير": "01", "فبراير": "02", "مارس": "03", "أبريل": "04", "مايو": "05",
                 "يونيو": "06", "يوليو": "07", "أغسطس": "08", "سبتمبر": "09", "أكتوبر": "10",
                 "نوفمبر": "11", "ديسمبر": "12"}
    ma = _re.search(r"(\d{1,2})\s+(يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+(\d{4})", head)
    if ma:
        date = f"{ma.group(3)}-{AR_MONTHS[ma.group(2)]}-{int(ma.group(1)):02d}"
    elif m:
        date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    else:
        m2 = _re.search(r"(\d{4}-\d{2}-\d{2})", head)
        if not m2:
            return ""
        date = m2.group(1)
    return date


def en_edition_href(html: str) -> str:
    """مسار النسخة الإنجليزية للتاريخ نفسه إن كانت منشورة، وإلا فراغ (م-25)."""
    date = _page_report_date(html)
    if not date:
        return ""
    # ك-630: الاشتقاق من مخرج البناء وحده كان يُخفق في صفحات تُبنى قبل صفحاتها
    # الإنجليزية، فيُعرض مفتاح اللغة معطّلًا (span) في العربية وزرًّا في الإنجليزية
    # فيختل تماثل البنية. المرجع الصحيح: مخرج البناء أو الماستر الإنجليزي، وكلاهما
    # يثبت أن النسخة الإنجليزية ستُنشر للتاريخ نفسه.
    if (ROOT / "dist" / "reports" / "en" / f"{date}.html").is_file() or \
       (ROOT / "sources" / "i18n" / "en" / f"{date}-sectioned.en.md").is_file():
        return f"/reports/en/{date}.html"
    return ""


def nav_html(active: str = "", en_href: str = "", report_date: str = "") -> str:
    """شريط التنقّل الموحّد. active: home | monthly | cumulative | report | additions | sources"""
    def link(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{href}"{cur} data-i18n="{key}">{label}</a>'
    # قرار المالك: لا رابط/زر تنزيل مكسور؛ يظهر وسم غير تفاعلي يوضح التعطيل.
    print_btn = ('<span class="sn-tool sn-print-disabled" role="status" aria-disabled="true" '
                 'title="الطباعة غير مفعّلة حاليًا" aria-label="الطباعة غير مفعّلة حاليًا" data-i18n-aria="print-off">'
                 '<svg class="sn-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                 'stroke-linecap="round" aria-hidden="true" focusable="false">'
                 '<path d="M7 8V3h10v5M7 18H5a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
                 '<path d="M7 14h10v7H7z"/></svg>'
                 '<span class="sn-vh">الطباعة غير مفعّلة حاليًا</span></span>') \
        if not PRINT_ENABLED else ""
    lang_group_html = lang_group("en" if active == "report-en" else "ar", en_href=en_href)
    report_return_links = ""
    if active == "additions":
        import re as _re
        en_match = _re.fullmatch(r"/reports/en/(\d{4}-\d{2}-\d{2})\.html", en_href or "")
        date = report_date or (en_match.group(1) if en_match else "")
        if _re.fullmatch(r"\d{4}-\d{2}-\d{2}", date or ""):
            report_return_links = (
                f'<a href="/reports/{date}.html" lang="ar" hreflang="ar" '
                'data-report-return="ar">التقرير العربي الموافق</a>'
            )
            if en_match and en_match.group(1) == date:
                report_return_links += (
                    f'<a href="{en_href}" lang="en" hreflang="en" '
                    'data-report-return="en">Matching English report</a>'
                )
    return f"""<nav class="site-nav no-print" aria-label="تنقل الموقع">
  <a class="sn-skip" href="#main" id="sn-skip" data-i18n="skip">الانتقال إلى المحتوى</a>
  {print_brand_html()}
  <div class="sn-inner">
    <a class="sn-brand" href="/">
      <img class="sn-logo" src="/assets/logo-header.png" width="40" height="40" alt="{LOGO_ALT}" decoding="async">
      <span class="sn-name">{BRAND} <em>{BRAND_SUB}</em></span>
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
      {link('/additions.html', 'الإضافات', 'additions')}
      {report_return_links}
    </div>
    <div class="sn-tools">
      {lang_group_html}
      <button type="button" class="sn-tool" id="sn-theme" title="المظهر" aria-label="المظهر" data-i18n-aria="theme">
        <svg class="sn-ico sn-ico-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true" focusable="false"><path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z"/></svg>
        <svg class="sn-ico sn-ico-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"/></svg>
        <span class="sn-vh" id="sn-theme-text">المظهر: ليلي</span>
      </button>
      <button type="button" class="sn-tool" id="sn-scale" title="حجم الخط: عادي" aria-label="حجم الخط" data-i18n-aria="scale">
        <span class="sn-ico sn-ico-a" aria-hidden="true">أ</span>
        <span class="sn-vh" id="sn-scale-text">حجم الخط: عادي</span>
      </button>
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
  </div>
</footer>"""


def inject(html: str, active: str, note: str = "") -> str:
    """حقن الترويسة والتفضيلات في صفحة مُولَّدة."""
    if "</head>" not in html:
        return html
    style = f"<style>{SITE_CSS}{MOBILE_NAV_CSS}{LANG_CSS}</style>"
    html = html.replace("</head>", head_assets(html) + "</head>", 1)
    html = html.replace("</head>", style + "</head>", 1)

    # سكربت المظهر المبكر بعد فتح الجسم مباشرة
    marker = ">"
    idx = html.find("<body")
    if idx >= 0:
        close = html.find(">", idx)
        if close >= 0:
            html = html[: close + 1] + PREFS_EARLY + html[close + 1 :]

    # م-33: مرساة حقيقية لرابط التخطّي — معرّف ثابت على حاوية المحتوى الرئيسية
    for _c in ('<div class="wrap" role="main">', '<div class="wrap">'):
        if _c in html:
            html = html.replace(_c, _c[:-1] + ' id="main" tabindex="-1">', 1)
            break
    # شريط التنقل بعد عنصر الشريط العلوي للصفحة إن وُجد، وإلا بعد الجسم
    nav = nav_html(active, en_edition_href(html), report_date=_page_report_date(html))
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
  /* كان هنا قوس زائد يغلق الاستعلام مبكرًا فيسري السطر التالي على سطح المكتب (seawatch-web #9) */
  .topbar .btn{min-width:44px;display:inline-flex;align-items:center;justify-content:center}
}
/* أهداف لمس على سطح المكتب — الشاشة فقط (قياس 2026-10-29: 34×35.3 و93.9×39.3) */
@media screen{
  .topbar a, .topbar button, .topbar .btn, .sn-brand, .sn-links a,
  .sc-toggle, .sc-jump a, .chip, .chip a, .tb-meta .btn,
  .sn-tools button, .sn-tools a, .sn-scale button, .sc-more a,
  .sc-all button, details.sc-basis summary, .sf-inner a,
  .sx-card a, .sx-name a, .sx-links a, .sx-row a, .sx-src a,
  .sx-ref a, .sx-refs a, .src-ref a, .open-report a, a.btn-link, .sup-banner a{
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
LOGO_ALT = "Maritime Domain Awareness Center logo — Kingdom of Bahrain"
LOGO_ALT_EN = "Maritime Domain Awareness Center logo — Kingdom of Bahrain"
