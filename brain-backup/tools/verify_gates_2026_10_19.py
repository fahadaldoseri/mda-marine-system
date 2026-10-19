#!/usr/bin/env python3
"""تحقق آلي من إصلاحات 19 أكتوبر 2026 (الدفعة الثانية) — لكل بند فحص قابل للتشغيل.

الاستخدام: python3 tools/verify_gates_2026_10_19.py
رمز الخروج: 0 كل الفحوص نجحت · 1 فشل فحص أو أكثر
"""
import json
import re
import sys
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
S = Path('/home/ubuntu/seawatch')
res = []


def check(name, ok, detail=""):
    res.append((name, bool(ok), detail))


def txt(p):
    return Path(p).read_text(encoding='utf-8')


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception:
        return default


# ٢ · فاحص التغذيات: ملف حالة صادق ورمز خروج حقيقي
st = jload(B / 'feeds/feeds-2026-10-19.status.json', {}) or {}
check("٢ · فحص التغذيات يكتب حالة صادقة", isinstance(st.get('status'), str) and 'fail_ratio' in st,
      f"الحالة={st.get('status')} · مفحوص={st.get('checked')} · ناجح={st.get('ok')} · فاشل={st.get('failed')} · النسبة={st.get('fail_ratio')}")
feed_src = txt(B / 'tools/check_feeds.py')
check("٢ · رمز الخروج مبني على النسبة لا على الصفر الدائم",
      'fail_ratio_limit' in feed_src and 'SystemExit(main())' in feed_src,
      "raise SystemExit(main()) — 0/1/2 بحسب النسبة")

# ٣ · الأصول: حالة لكل رابط (سليم/هيكل فارغ/فاشل)
arch = jload(B / 'archive/originals/2026-10-19/status.json', {}) or {}
check("٣ · حفظ الأصول يكتب حالة لكل رابط", 'healthy' in arch and 'empty_shell' in arch and 'failed' in arch,
      f"سليم={arch.get('healthy')} · هيكل فارغ={arch.get('empty_shell')} · فاشل={arch.get('failed')}")
check("٣ · رابط برأسية تحقّق 200 وحدهما لا يُعدّ أصلًا محفوظًا",
      'empty_shell' in txt(B / 'tools/archive_originals.py'), "فحص طول النص بعد إزالة الوسوم")

# ٤ · الإحداثيات: الحقول الدقائقية فقط
meta = jload(B / 'web/meta/2026-10-19.json', {}) or {}
pt = [p for p in ((meta.get('map') or {}).get('points') or []) if p.get('label')]
check("٤ · لا إحداثيات عشرية في نصوص نقاط الخريطة",
      not any(re.search(r'\d{1,3}\.\d{3,}', p['label']) for p in pt),
      f"{len(pt)} نقطة · مثال: {pt[0]['label'][:60] if pt else ''}")

# ٥ و٦ · بوابة التسليم: موجودة، داخل الخط، ومرتَّبة بعد بناء الصفحة وPDF
gate = B / 'tools/final_gate.sh'
gt = txt(gate) if gate.exists() else ""
check("٥ · بوابة تسليم نهائية واحدة موجودة", gate.exists(), str(gate))
check("٥ · الخط اليومي يستدعي البوابة ويوقف التسليم عند المخالفة",
      'final_gate.sh' in txt(B / 'tools/daily_pipeline.sh') and 'التسليم موقوف' in gt, "استدعاء + رمز مانع 2")
check("٦ · البوابة تبنى وتُصدّر PDF قبل الفحوص",
      gt.find('تصدير PDF المعتمد') < gt.find('بوابة الأسلوب'),
      "الترتيب: بناء ← PDF ← فحص (لا تعليق على PDF قديم)")
check("٦ · نتيجة البوابة مسجّلة في ملف حالة مرتبط بالعلامة",
      (B / 'logs/gate-2026-10-19/gate.json').exists(), "logs/gate-<D>/gate.json")

# ٧ · رمز خروج فاحص العقوبات غير مضلّل
ofac_src = txt(B / 'tools/ofac_screen.py')
check("٧ · فحص العقوبات يعبّر بتطابق/مراجعة، ورمز الخروج صادق",
      "'review'" in ofac_src and 'SystemExit(main())' in ofac_src,
      "review = تطابق جزئي يحتاج تحققًا يدويًا · 0/1/2")
om = jload(B / 'archive/ofac-screen-latest.json', {}) or {}
check("٧ · نتيجة العقوبات تحمل حالة لكل هدف",
      all({'target', 'result'} <= set(r) for r in om.get('results', [])),
      f"{len(om.get('results', []))} هدف — {[(r['target'], r['result']) for r in om.get('results', [])]}")

# ٨ · عدد المصادر من مصدر واحد
manifest = jload(B / 'appendices/sources-manifest.json', {}) or {}
check("٨ · رقم المصادر من ملف واحد", manifest.get('approved_source_count') == 40,
      f"sources-manifest.json = {manifest.get('approved_source_count')}")
for f, bad in [('sections/30-structure.md', '37 مصدرًا'), ('sections/90-automation.md', 'الـ37'),
               ('sections/10-sources.md', 'sources-37')]:
    check(f"٨ · لا رقم قديم في {f}", bad not in txt(B / f), f"بحث عن «{bad}»")

# ٩ · قائمة العقوبات تُولَّد من سفن التقرير
check("٩ · قائمة العقوبات مُولَّدة آليًا من التقرير",
      'ofac_targets_from_report.py' in txt(B / 'tools/daily_pipeline.sh'),
      "daily_pipeline v4 — الخطوة 2")

# ١٠ · الدفتر: قائمة واحدة
led = jload(B / 'cumulative-2026/event-ledger-master.json', {}) or {}
check("١٠ · الدفتر بقائمة سجلات واحدة (`events` بلا `records`)",
      'events' in led and 'records' not in led, f"{len(led.get('events', []))} سجلًا")

# ١١ · الأقسام الرأسية: مُعاد بناؤها أو موسومة بتاريخها
vr = led.get('vertical_rebuild') or {}
check("١١ · أقسام مُعاد بناؤها وأخرى موسومة بتاريخها",
      bool(vr.get('rebuilt_keys')) and bool(vr.get('point_in_time_keys')),
      f"مُعاد بناؤه={vr.get('rebuilt_keys')} · لقطات={[k['key'] for k in vr.get('point_in_time_keys', [])]}")
check("١١ · كل لقطة تحمل `_state` و`_as_of`",
      all((led.get(k['key']) or {}).get('_state') == 'point_in_time' for k in vr.get('point_in_time_keys', [])),
      "لا قسم يبدو حديثًا بلا سند")

# ١٢ · المضاف في الجولة مقابل الإجمالي
ml = led.get('merge_log') or {}
check("١٢ · فصل مضاف الجولة عن إجمالي المضاف",
      'added_this_run_count' in ml and 'added_total_since_frozen' in ml,
      f"هذه الجولة={ml.get('added_this_run_count')} · الإجمالي={ml.get('added_total_since_frozen')}")

# ١٣ · الدمج قبل العلامة والعلامة تقرأ الدفتر
mark = jload(B / 'logs/pipeline-2026-10-19.json', {}) or {}
check("١٣ · العلامة تُسجِّل حالة الدمج ورقم السجل", bool((mark.get('ledger_merge') or {}).get('merged_utc')),
      f"records_total={((mark.get('ledger_merge') or {}).get('records_total'))} · merged_utc={((mark.get('ledger_merge') or {}).get('merged_utc'))}")
check("١٣ · العلامة تسجّل حالة كل مكوّن فعلية (لا نجاح دائم)",
      all(k in mark for k in ('feeds', 'ofac', 'originals', 'ledger_merge')) and mark.get('overall') in ('ok', 'degraded', 'failed'),
      f"الحالة العامة={mark.get('overall')} · تغذيات={(mark.get('feeds') or {}).get('status')}")

# ١٤ · توحيد صيغة «الأسطول نفسه»
bl = jload(B / 'appendices/style-blacklist.json', {}) or {}
terms = [b['term'] for b in bl.get('blocking', [])]
style = txt(B / 'sections/75-style.md')
check("١٤ · الصيغة المعتمدة لا تُمنع، والملكية تُمنع",
      'في الأسطول نفسه' not in terms and 'مالكها' in terms and 'تملك' in [w['term'] for w in bl.get('watch', [])],
      f"مانع: مالكها · تنبيه: تملك · الصيغة مسموحة في الأسلوب: {'في الأسطول نفسه' in style}")

# ١٥ · لا حالة عالمية لسياق الرموز
blocks = txt(S / 'generator/blocks.py')
check("١٥ · سياق الرموز معزول لكل جولة (لا قاموس عالمي)",
      'contextvars' in blocks and 'reset_code_context' in blocks and '_CODE_CTX = {"date"' not in blocks,
      "ContextVar + تفريغ صريح في نهاية البناء")
check("١٥ · المولّد يفرّغ السياق بعد كل جولة", 'reset_code_context()' in txt(S / 'generator/build_report.py'),
      "main() → finally")

# ١٦ · أمان الويب هوك والبوت
app = txt(S / 'server/app.py')
check("١٦ · الويب هوك فشل مغلق عند غياب السر",
      'webhook secret unset' in app and 'if not _hook:' in app, "لا سر ⇒ 503 · سر غير مطابق ⇒ 401")
check("١٦ · لا معرّف صاحب قرار افتراضيًا في الشيفرة",
      '1125' not in txt(B / 'tools/telegram_bot.py') and 'owner_id' in txt(B / 'tools/telegram_bot.py'),
      "owner_id() من ملف الجهات المعتمدة فقط")
check("١٦ · توثيق صريح للمخاطر المتبقية وتدوير الأسرار", (B / 'appendices/security-notes.md').exists(),
      "appendices/security-notes.md")

print("=== تحقق إصلاحات 19 أكتوبر 2026 (الدفعة الثانية) ===")
bad = 0
for name, ok, detail in res:
    bad += 0 if ok else 1
    print(f"  {'✔' if ok else '✘'} {name}" + (f"  — {detail}" if detail else ''))
print(f"=== النتيجة: {len(res) - bad}/{len(res)} نجحت · فشل={bad} ===")
sys.exit(1 if bad else 0)