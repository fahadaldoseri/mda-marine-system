#!/usr/bin/env python3
"""فحص شامل لسلسلة التشغيل الصباحي — يكشف كل ما تعطّل لا لوحة المعاينة فقط.

المنهج: فحص كل حلقة في السلسلة — المخرجات، الروابط بينها، الصفحة المنشورة، الأتمتة.
الاستخدام: python3 tools/full_chain_audit.py [DATE]  → يكتب audit/full-chain-<DATE>.json
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")
import json, re, subprocess, sys, time
from pathlib import Path

B = Path(f'{BRAIN}')
S = Path(f'{SITE}')
D = sys.argv[1] if len(sys.argv) > 1 else subprocess.run(['date', '-u', '+%F'], capture_output=True, text=True).stdout.strip()
BASE = 'https://seawatch-xp4qirmr.manus.space'
MORNING_END = f'{D}T05:30:00Z'          # فترة التشغيل الصباحي (07:00–08:30 بتوقيت البحرين)
R = {'date': D, 'sections': {}}

def sec(name, items):
    R['sections'][name] = items
    print(f'\n===== {name} =====')
    for it in items:
        mark = {'ok': '✔', 'warn': '!', 'fail': '✘', 'info': '·'}.get(it['level'], '·')
        print(f"  {mark} {it['text']}")

def mtime(p):
    return subprocess.run(['date', '-u', '-r', str(p), '+%Y-%m-%dT%H:%M:%SZ'], capture_output=True, text=True).stdout.strip()

# ---------------------------------------------------------------- 1) المخرجات وأوقاتها
art = []
for rel in [f'reports/{D}-sectioned.md', f'web/meta/{D}.json', f'feeds/feeds-{D}.md',
            'archive/ofac-screen-latest.json', f'archive/originals/{D}/manifest.json',
            f'logs/pipeline-{D}.json', f'reports/raw-notes-{D}.md',
            'appendices/source-reliability-40.md', 'memory/learning-log.jsonl']:
    p = B / rel
    if not p.exists():
        art.append({'level': 'fail', 'text': f'مفقود: {rel}'})
        continue
    t = mtime(p)
    late = t > MORNING_END and not rel.startswith('logs/')
    art.append({'level': 'warn' if late else 'ok',
                'text': f"{rel} — {t} — {p.stat().st_size} بايت" + ('  ← أُنشئ بعد فترة التشغيل الصباحي' if late else '')})
sec('1) مخرجات التشغيل وأوقات إنشائها', art)

# ---------------------------------------------------------------- 2) تقرير اليوم: الأقسام والكتل
sec_items = []
rep = B / 'reports' / f'{D}-sectioned.md'
meta = {}
if (B / 'web' / 'meta' / f'{D}.json').exists():
    meta = json.loads((B / 'web' / 'meta' / f'{D}.json').read_text(encoding='utf-8'))
titles = re.findall(r'^##\s+(.+?)\s*$', rep.read_text(encoding='utf-8'), re.M) if rep.exists() else []
sec_items.append({'level': 'ok' if len(titles) >= 12 else 'fail', 'text': f'أقسام التقرير: {len(titles)}'})
bmap = meta.get('blocks') or {}
unmatched = [t for t in titles if not any(k in t for k in bmap)]
sec_items.append({'level': 'warn' if unmatched else 'ok',
                  'text': f'أقسام بلا كتلة عرض: {unmatched}' if unmatched else 'كل الأقسام مرتبطة بكتل عرض'})

# كتل HTML الفعلية: تُستخرج من دوال المولّد ثم تُفحص في الصفحة
html = (S / 'dist' / 'reports' / f'{D}.html')
if html.exists():
    h = html.read_text(encoding='utf-8')
    # فحص منطقة كل قسم في الصفحة: القسم الذي يعلن كتلة يجب أن يحوي جدولًا أو مخططًا أو قائمة
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S)
    heads = [(m.start(), re.sub(r'<[^>]+>', '', m.group(1)).strip())
             for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', body, re.S)]
    for i, (pos, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(body)
        region = body[pos:end]
        text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', region)).strip()
        rich = (region.count('<table') + region.count('<svg') + region.count('<li') + region.count('<tr'))
        has_block = any(k in title for k in bmap)
        if has_block and (rich == 0 or len(text) < 200):
            sec_items.append({'level': 'fail', 'text': f'قسم بكتلة معلنة لكن منطقه فارغ/ناقص: «{title}» (نص {len(text)} · عناصر {rich})'})
        elif not has_block and len(text) < 150:
            sec_items.append({'level': 'warn', 'text': f'قسم نصّي قصير جدًا: «{title}» (نص {len(text)})'})
    sec_items.append({'level': 'info', 'text': f'أقسام الصفحة المفحوصة: {len(heads)}'})
    sec_items.append({'level': 'ok' if 'map-svg' in h else 'fail', 'text': 'الخريطة التشغيلية: ' + ('موجودة' if 'map-svg' in h else 'مفقودة')})
    sec_items.append({'level': 'ok' if 'kpi' in h else 'fail', 'text': 'بطاقات القيادة (KPI): ' + ('موجودة' if 'kpi' in h else 'مفقودة')})
    sec_items.append({'level': 'ok' if 'threat' in h else 'warn', 'text': 'بطاقة مستوى التهديد: ' + ('موجودة' if 'threat' in h else 'مفقودة')})
else:
    sec_items.append({'level': 'fail', 'text': f'صفحة اليوم غير مبنية: {html}'})
sec('2) تقرير اليوم وكتل الصفحة', sec_items)

# ---------------------------------------------------------------- 3) الروابط بين المخرجات
lk = []
man = B / 'archive' / 'originals' / D / 'manifest.json'
if man.exists():
    mm = json.loads(man.read_text(encoding='utf-8'))
    if isinstance(mm, list):
        n = len(mm)
    elif isinstance(mm, dict):
        v = mm.get('originals', mm.get('items', mm.get('files', [])))
        n = len(v) if isinstance(v, list) else len(mm)
    else:
        n = 0
    lk.append({'level': 'ok' if n else 'warn', 'text': f'أصول رسمية محفوظة: {n}'})
else:
    lk.append({'level': 'fail', 'text': f'لا بيان أصول رسمية لليوم: archive/originals/{D}/manifest.json'})
ofac = B / 'archive' / 'ofac-screen-latest.json'
lk.append({'level': 'ok' if ofac.exists() else 'fail',
           'text': 'نتيجة فحص OFAC: ' + ('موجودة' if ofac.exists() else 'مفقودة')})
if ofac.exists():
    try:
        o = json.loads(ofac.read_text(encoding='utf-8'))
        rows = o.get('results', o if isinstance(o, list) else [])
        lk.append({'level': 'ok', 'text': f'مستهدفون مفخورصون: {len(rows) if isinstance(rows, list) else "غير معروف"}'})
    except Exception as e:
        lk.append({'level': 'fail', 'text': f'نتيجة OFAC غير صالحة: {e}'})
if rep.exists():
    rt = rep.read_text(encoding='utf-8')
    lk.append({'level': 'ok' if re.search(r'OFAC|العقوبات', rt) else 'warn',
               'text': 'التقرير يذكر فحص العقوبات: ' + ('نعم' if re.search(r'OFAC|العقوبات', rt) else 'لا')})
    lk.append({'level': 'ok' if re.search(r'archive/originals|أصل رسمي', rt) else 'warn',
               'text': 'التقرير يذكر الأصول الرسمية: ' + ('نعم' if re.search(r'archive/originals|أصل رسمي', rt) else 'لا')})
    codes = sorted(set(re.findall(r'MN-\d{4}-\d{2}-\d{2}-\d{2}', rt)))
    lk.append({'level': 'info', 'text': f'رموز أحداث التقرير: {len(codes)}'})
    led = list((B / 'cumulative-2026').glob('event-ledger*.json'))
    if led and codes:
        lt = led[-1].read_text(encoding='utf-8')
        missing = [c for c in codes if c not in lt]
        lk.append({'level': 'fail' if missing else 'ok',
                   'text': f'رموز غير مسجلة في الدفتر التراكمي: {missing}' if missing else 'كل رموز التقرير مسجلة في الدفتر التراكمي'})
    elif not led:
        lk.append({'level': 'warn', 'text': 'لا دفتر أحداث تراكمي'})
sec('3) سلامة الربط بين المخرجات', lk)

# ---------------------------------------------------------------- 4) الموقع: بناء ومسارات وروابط
st = []
r = subprocess.run(['python3', str(S / 'generator' / 'build_site.py'), '--check'], capture_output=True, text=True)
st.append({'level': 'ok' if r.returncode == 0 else 'fail', 'text': f'فحص بناء الموقع: {r.stdout.strip().splitlines()[-1][:90] if r.stdout.strip() else r.stderr.strip()[:90]}'})
routes = ['/', f'/reports/{D}.html', '/reports/2026-10-12.html', '/reports/monthly-2026-10.html',
          '/reports/cumulative-2026.html', '/feed.xml', '/sitemap.xml', '/robots.txt', '/manus-routes.json', '/no-such-page']
live = {}
for p in routes:
    code = subprocess.run(['curl', '-sL', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '25',
                           '-A', 'Mozilla/5.0', BASE + p], capture_output=True, text=True).stdout.strip()
    live[p] = code
    bad = code not in ('200', '404')
    st.append({'level': 'fail' if bad else ('warn' if (p == '/no-such-page' and code != '404') else 'ok'),
               'text': f'{p} → {code}'})
# مطابقة المنشور بالمحلي
try:
    import hashlib
    loc = (S / 'dist' / 'reports' / f'{D}.html').read_text(encoding='utf-8')
    pub = subprocess.run(['curl', '-sL', '--max-time', '30', '-A', 'Mozilla/5.0', f'{BASE}/reports/{D}.html'],
                         capture_output=True, text=True).stdout
    same = hashlib.sha256(loc.encode()).hexdigest() == hashlib.sha256(pub.encode()).hexdigest()
    st.append({'level': 'ok' if same else 'warn',
               'text': 'الصفحة المنشورة مطابقة للمبنية محليًا' if same else 'الصفحة المنشورة تختلف عن المبنية محليًا (قد يكون إعادة تنسيق أو إصدار أقدم)'})
    # روابط داخلية في الصفحة
    hrefs = sorted(set(re.findall(r'href="(/[^"#?]*)"', pub)))
    bad_links = []
    for h in hrefs:
        if h.startswith('/manus-storage'): continue
        c = subprocess.run(['curl', '-sL', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '20',
                            '-A', 'Mozilla/5.0', BASE + h], capture_output=True, text=True).stdout.strip()
        if c not in ('200',):
            bad_links.append(f'{h}({c})')
    st.append({'level': 'fail' if bad_links else 'ok',
               'text': f'روابط داخلية مكسورة في صفحة اليوم: {bad_links}' if bad_links else f'كل الروابط الداخلية في صفحة اليوم تعمل ({len(hrefs)} رابطًا)'})
except Exception as e:
    st.append({'level': 'warn', 'text': f'تعذّر فحص الروابط الداخلية: {e}'})
sec('4) الموقع الدائم والمسارات', st)

# ---------------------------------------------------------------- 5) الأتمتة
au = []
sch = subprocess.run(['manus-config', 'schedule', 'status', '--limit', '1000', '--offset', '0'], capture_output=True, text=True).stdout
try:
    sc = json.loads(sch)['schedules'][0]
    au.append({'level': 'ok' if sc['status'] == 'active' else 'fail', 'text': f"الجدولة: {sc['status']} · {sc['timezone']} · {sc['cronExpression']} · آخر تنفيذ {sc.get('lastExecutedAt')}"})
except Exception as e:
    au.append({'level': 'fail', 'text': f'تعذّر قراءة الجدولة: {e}'})
code = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '6', 'http://127.0.0.1:3000/'], capture_output=True, text=True).stdout.strip()
au.append({'level': 'ok' if code == '200' else 'fail', 'text': f'خادم المعاينة (3000): {code}'})
helper = subprocess.run(['git', '-C', str(S), 'config', '--get', 'credential.helper'], capture_output=True, text=True).stdout.strip()
mh = re.search(r'"([^"]+\.mjs)"', helper)
au.append({'level': 'ok' if mh and Path(mh.group(1)).exists() else 'fail',
           'text': 'مساعد اعتماد الدفع: ' + ('سليم' if mh and Path(mh.group(1)).exists() else 'قديم/مفقود')})
r = subprocess.run(['git', '-C', str(S), 'status', '-sb'], capture_output=True, text=True).stdout.strip().splitlines()
au.append({'level': 'ok' if 'origin/main' in (r[0] if r else '') else 'warn',
           'text': 'حالة المستودع: ' + (r[0] if r else 'غير معروفة')})
mark = B / 'logs' / f'pipeline-{D}.json'
if mark.exists():
    stt = json.loads(mark.read_text(encoding='utf-8'))
    au.append({'level': 'ok' if stt.get('overall') == 'ok' else 'fail', 'text': f"علامة الخط اليومي: {stt.get('overall')} · تغذيات {stt['feeds']['status']} · OFAC {stt['ofac']['status']} · أصول {stt['originals']['status']}"})
else:
    au.append({'level': 'fail', 'text': 'لا علامة نجاح للخط اليومي'})
sec('5) الأتمتة والبيئة', au)

out = B / 'audit' / f'full-chain-{D}.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding='utf-8')
counts = {lvl: sum(1 for s in R['sections'].values() for i in s if i['level'] == lvl) for lvl in ('ok', 'warn', 'fail', 'info')}
print(f"\n===== الخلاصة: نجح {counts['ok']} · تحذير {counts['warn']} · فشل {counts['fail']} =====")
print(f"التقرير الآلي: {out}")
sys.exit(1 if counts['fail'] else 0)
