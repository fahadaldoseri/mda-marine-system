#!/usr/bin/env python3
"""فحص ما قبل التشغيل (Preflight) — يُشغَّل قبل أي بناء أو تسليم.

الغرض: كشف الأعطال الصامتة التي لا تُنتج خطأً ظاهرًا لكنها تُفقد التقرير مكوّنًا كاملًا،
مثل: عنوان قسم لا يطابق أي كتلة عرض، أو اسم كتلة غير مدعوم في المولّد، أو حقل ناقص في
ملف الواجهة، أو خط يومي لم يُكمل خطواته.

آلية الربط الفعلية (المُفحوصة): ملف الواجهة يحمل `blocks` = {جزء من عنوان القسم → اسم الكتلة}،
والمولّد يرسم الكتلة عبر blocks.render_block(name) الذي يدعم أسماء محددة.

الاستخدام: python3 tools/preflight_check.py [REPORT_DATE]
رمز الخروج: 0 = كل الفحوص الحرجة نجحت · 1 = يوجد فشل حرج يمنع التسليم.
"""
import json, re, subprocess, sys
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
GEN = Path('/home/ubuntu/seawatch/generator')
DATE = sys.argv[1] if len(sys.argv) > 1 else subprocess.run(['date', '-u', '+%F'], capture_output=True, text=True).stdout.strip()

fails, warns, oks = [], [], []
def check(cond, ok_msg, fail_msg):
    (oks if cond else fails).append(ok_msg if cond else fail_msg)
def warn(cond, ok_msg, warn_msg):
    (oks if cond else warns).append(ok_msg if cond else warn_msg)

# أسماء الكتل المدعومة فعليًا في المولّد (تُقرأ من موزّع render_block)
supported = set()
bp = GEN / 'blocks.py'
if bp.exists():
    src = bp.read_text(encoding='utf-8')
    m = re.search(r'def render_block\(.*?\n(.*?)\n\ndef ', src, re.S)
    if m:
        supported = set(re.findall(r'name == "([^"]+)"', m.group(1)))
check(bool(supported), f"كتل العرض المدعومة: {len(supported)}", "تعذّر قراءة كتل العرض المدعومة من المولّد")

# ملف واجهة اليوم
meta_today = B / 'web' / 'meta' / f'{DATE}.json'
report = B / 'reports' / f'{DATE}-sectioned.md'
meta = None
if meta_today.exists():
    try:
        meta = json.loads(meta_today.read_text(encoding='utf-8'))
        check(True, "ملف الواجهة صالح (JSON)", "")
    except Exception as e:
        check(False, "", f"ملف الواجهة غير صالح: {e}")
else:
    warn(False, "", f"ملف الواجهة غير موجود بعد ({meta_today.name}) — طبيعي قبل الكتابة")

# 1) ربط الأقسام بالكتل: أسماء مدعومة · مفاتيح حيّة · أقسام بلا كتلة
if meta and isinstance(meta.get('blocks'), dict) and report.exists():
    bmap = meta['blocks']
    titles = re.findall(r'^##\s+(.+?)\s*$', report.read_text(encoding='utf-8'), re.M)
    names = {n.strip() for v in bmap.values() for n in str(v).split('+')}
    bad_names = sorted(names - supported)
    check(not bad_names, f"كل أسماء الكتل مدعومة ({len(names)})", f"أسماء كتل غير مدعومة (لن تُرسم): {bad_names}")
    dead = [k for k in bmap if not any(k in t for t in titles)]
    check(not dead, f"كل مفاتيح الكتل تطابق عنوانًا ({len(bmap)})", f"مفاتيح كتل لا تطابق أي عنوان (ربط ميت): {dead}")
    no_block = [t for t in titles if not any(k in t for k in bmap)]
    warn(not no_block, f"كل الأقسام مرتبطة بكتلة ({len(titles)} قسمًا)",
         f"أقسام بلا كتلة عرض (تحقّق أنها مقصودة): {no_block}")
    check(len(titles) >= 12, f"عدد أقسام التقرير {len(titles)}", f"أقسام ناقصة: {len(titles)} فقط")

# 2) حقول ملف الواجهة: مخطط بالمثال مقابل ملف أمس
metas = sorted((B / 'web' / 'meta').glob('*.json'))
if meta_today.exists() and len(metas) > 1:
    prev = [m for m in metas if m.name != meta_today.name][-1]
    a = set(json.loads(meta_today.read_text(encoding='utf-8')).keys())
    b = set(json.loads(prev.read_text(encoding='utf-8')).keys())
    check(not (b - a), "حقول ملف الواجهة مكتملة", f"حقول ناقصة في ملف الواجهة: {sorted(b - a)}")

# 3) مدخلات الخط اليومي (قوائم دائمة في المستودع لا /tmp)
for wl in ('watchlist/ofac-targets.txt', 'watchlist/original-sources.txt'):
    check((B / wl).exists(), f"{wl} موجود", f"مدخل مفقود: {wl}")

# 4) أدوات الخط
for tool in ('tools/check_feeds.py', 'tools/ofac_screen.py', 'tools/archive_originals.py',
             'tools/daily_pipeline.sh', 'tools/build_source_reliability.py', 'tools/ensure_devserver.sh',
             'validators/check_language.py', 'validators/validate_report.py'):
    check((B / tool).exists(), f"{tool} موجود", f"أداة مفقودة: {tool}")

# 5) المولّد بنسخة واحدة + السجلات المرجعية
for f in ('build_report.py', 'blocks.py', 'map_gulf.py', 'verify.py', 'build_site.py', 'sync_from_brain.py'):
    check((GEN / f).exists(), f"المولّد: {f}", f"ملف مولّد مفقود: {f}")
check((B / 'appendices' / 'source-reliability-40.md').exists(),
      "سجل موثوقية المصادر الأربعين موجود", "سجل موثوقية المصادر مفقود")
check((B / 'sources' / 'site.json').exists() or (GEN.parent / 'sources' / 'site.json').exists(),
      "sources/site.json موجود", "sources/site.json مفقود")
site = GEN.parent / 'sources' / 'site.json'
if site.exists():
    try:
        bu = json.loads(site.read_text(encoding='utf-8')).get('base_url', '')
        check(isinstance(bu, str) and bu.startswith('https://'), f"base_url مضبوط: {bu}", "base_url مفقود أو غير صالح")
    except Exception as e:
        fails.append(f"تعذّر قراءة sources/site.json: {e}")

# 6) علامة الخط اليومي: إن وُجد تقرير اليوم وجب أن يكون الخط قد نجح
mark = B / 'logs' / f'pipeline-{DATE}.json'
if report.exists():
    if mark.exists():
        try:
            st = json.loads(mark.read_text(encoding='utf-8'))
            check(st.get('overall') == 'ok',
                  f"الخط اليومي نجح ({st.get('overall')})",
                  f"الخط اليومي لم ينجح: {st.get('feeds')} · {st.get('ofac')} · {st.get('originals')}")
        except Exception as e:
            fails.append(f"علامة الخط غير صالحة: {e}")
    else:
        fails.append(f"لا علامة نجاح للخط اليومي ({mark.name}) — لم يُنفَّذ الخط أو فشل قبل الكتابة")
else:
    warn(False, "", f"لا تقرير لهذا اليوم بعد ({report.name}) — طبيعي قبل الكتابة")

# 7) خادم المعاينة (تحذير لا فشل: مسار التسليم المعتمد هو الموقع الدائم)
code = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '6',
                       'http://127.0.0.1:3000/'], capture_output=True, text=True).stdout.strip()
warn(code == '200', "خادم المعاينة يعمل (3000)",
     "خادم المعاينة متوقف (3000) — شغّل tools/ensure_devserver.sh")

# 6ب) مساعد اعتماد الدفع: مسار قديم بعد تحديث الإضافة = فشل دفع صامت = لا نقطة استعادة = نشر نسخة قديمة
try:
    helper = subprocess.run(['git', '-C', str(GEN.parent), 'config', '--get', 'credential.helper'],
                            capture_output=True, text=True).stdout.strip()
except Exception:
    helper = ''
if helper:
    mh = re.search(r'"([^"]+\.mjs)"', helper)
    check(bool(mh) and Path(mh.group(1)).exists(),
          "مساعد اعتماد الدفع سليم",
          f"مسار مساعد اعتماد الدفع قديم أو مفقود: {(mh.group(1) if mh else helper[:70])}")
else:
    warn(False, "", "لا مساعد اعتماد مضبوط لدفع نقطة الاستعادة")

print(f"===== فحص ما قبل التشغيل — {DATE} =====")
for m in oks:   print(f"  ✔ {m}")
for m in warns: print(f"  ! {m}")
for m in fails: print(f"  ✘ {m}")
print(f"----- النتيجة: نجح {len(oks)} · تحذير {len(warns)} · فشل {len(fails)} -----")
print("الحكم: " + ("ممنوع التسليم — أصلح الفشل أولًا" if fails else "جاهز للتشغيل"))
sys.exit(1 if fails else 0)
# 7) خادم المعاينة (تحذير لا فشل: مسار التسليم المعتمد هو الموقع الدائم)
