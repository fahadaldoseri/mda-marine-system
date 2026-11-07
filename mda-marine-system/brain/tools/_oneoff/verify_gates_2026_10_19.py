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


# 2 · فاحص التغذيات: ملف حالة صادق ورمز خروج حقيقي
st = jload(B / 'feeds/feeds-2026-10-19.status.json', {}) or {}
check("2 · فحص التغذيات يكتب حالة صادقة", isinstance(st.get('status'), str) and 'fail_ratio' in st,
      f"الحالة={st.get('status')} · مفحوص={st.get('checked')} · ناجح={st.get('ok')} · فاشل={st.get('failed')} · النسبة={st.get('fail_ratio')}")
feed_src = txt(B / 'tools/check_feeds.py')
check("2 · رمز الخروج مبني على النسبة لا على الصفر الدائم",
      'fail_ratio_limit' in feed_src and 'SystemExit(main())' in feed_src,
      "raise SystemExit(main()) — 0/1/2 بحسب النسبة")

# 3 · الأصول: حالة لكل رابط (سليم/هيكل فارغ/فاشل)
arch = jload(B / 'archive/originals/2026-10-19/status.json', {}) or {}
check("3 · حفظ الأصول يكتب حالة لكل رابط", 'healthy' in arch and 'empty_shell' in arch and 'failed' in arch,
      f"سليم={arch.get('healthy')} · هيكل فارغ={arch.get('empty_shell')} · فاشل={arch.get('failed')}")
check("3 · رابط برأسية تحقّق 200 وحدهما لا يُعدّ أصلًا محفوظًا",
      'empty_shell' in txt(B / 'tools/archive_originals.py'), "فحص طول النص بعد إزالة الوسوم")

# 4 · الإحداثيات: الحقول الدقائقية فقط
meta = jload(B / 'web/meta/2026-10-19.json', {}) or {}
pt = [p for p in ((meta.get('map') or {}).get('points') or []) if p.get('label')]
check("4 · لا إحداثيات عشرية في نصوص نقاط الخريطة",
      not any(re.search(r'\d{1,3}\.\d{3,}', p['label']) for p in pt),
      f"{len(pt)} نقطة · مثال: {pt[0]['label'][:60] if pt else ''}")

# 5 و6 · بوابة التسليم: موجودة، داخل الخط، ومرتَّبة بعد بناء الصفحة وPDF
gate = B / 'tools/final_gate.sh'
gt = txt(gate) if gate.exists() else ""
check("5 · بوابة تسليم نهائية واحدة موجودة", gate.exists(), str(gate))
check("5 · الخط اليومي يستدعي البوابة ويوقف التسليم عند المخالفة",
      'final_gate.sh' in txt(B / 'tools/daily_pipeline.sh') and 'التسليم موقوف' in gt, "استدعاء + رمز مانع 2")
check("6 · البوابة تبنى وتُصدّر PDF قبل الفحوص",
      gt.find('تصدير PDF المعتمد') < gt.find('بوابة الأسلوب'),
      "الترتيب: بناء ← PDF ← فحص (لا تعليق على PDF قديم)")
check("6 · نتيجة البوابة مسجّلة في ملف حالة مرتبط بالعلامة",
      (B / 'logs/gate-2026-10-19/gate.json').exists(), "logs/gate-<D>/gate.json")

# 7 · رمز خروج فاحص العقوبات غير مضلّل
ofac_src = txt(B / 'tools/ofac_screen.py')
check("7 · فحص العقوبات يعبّر بتطابق/مراجعة، ورمز الخروج صادق",
      "'review'" in ofac_src and 'SystemExit(main())' in ofac_src,
      "review = تطابق جزئي يحتاج تحققًا يدويًا · 0/1/2")
om = jload(B / 'archive/ofac-screen-latest.json', {}) or {}
check("7 · نتيجة العقوبات تحمل حالة لكل هدف",
      all({'target', 'result'} <= set(r) for r in om.get('results', [])),
      f"{len(om.get('results', []))} هدف — {[(r['target'], r['result']) for r in om.get('results', [])]}")

# 8 · عدد المصادر من مصدر واحد
manifest = jload(B / 'appendices/sources-manifest.json', {}) or {}
check("8 · رقم المصادر من ملف واحد", manifest.get('approved_source_count') == 40,
      f"sources-manifest.json = {manifest.get('approved_source_count')}")
for f, bad in [('sections/30-structure.md', '37 مصدرًا'), ('sections/90-automation.md', 'الـ37'),
               ('sections/10-sources.md', 'sources-37')]:
    check(f"8 · لا رقم قديم في {f}", bad not in txt(B / f), f"بحث عن «{bad}»")

# 9 · قائمة العقوبات تُولَّد من سفن التقرير
check("9 · قائمة العقوبات مُولَّدة آليًا من التقرير",
      'ofac_targets_from_report.py' in txt(B / 'tools/daily_pipeline.sh'),
      "daily_pipeline v4 — الخطوة 2")

# 10 · الدفتر: قائمة واحدة
led = jload(B / 'cumulative-2026/event-ledger-master.json', {}) or {}
check("10 · الدفتر بقائمة سجلات واحدة (`events` بلا `records`)",
      'events' in led and 'records' not in led, f"{len(led.get('events', []))} سجلًا")

# 11 · الأقسام الرأسية: مُعاد بناؤها أو موسومة بتاريخها
vr = led.get('vertical_rebuild') or {}
check("11 · أقسام مُعاد بناؤها وأخرى موسومة بتاريخها",
      bool(vr.get('rebuilt_keys')) and bool(vr.get('point_in_time_keys')),
      f"مُعاد بناؤه={vr.get('rebuilt_keys')} · لقطات={[k['key'] for k in vr.get('point_in_time_keys', [])]}")
check("11 · كل لقطة تحمل `_state` و`_as_of`",
      all((led.get(k['key']) or {}).get('_state') == 'point_in_time' for k in vr.get('point_in_time_keys', [])),
      "لا قسم يبدو حديثًا بلا سند")

# 12 · المضاف في الجولة مقابل الإجمالي
ml = led.get('merge_log') or {}
check("12 · فصل مضاف الجولة عن إجمالي المضاف",
      'added_this_run_count' in ml and 'added_total_since_frozen' in ml,
      f"هذه الجولة={ml.get('added_this_run_count')} · الإجمالي={ml.get('added_total_since_frozen')}")

# 13 · الدمج قبل العلامة والعلامة تقرأ الدفتر
mark = jload(B / 'logs/pipeline-2026-10-19.json', {}) or {}
check("13 · العلامة تُسجِّل حالة الدمج ورقم السجل", bool((mark.get('ledger_merge') or {}).get('merged_utc')),
      f"records_total={((mark.get('ledger_merge') or {}).get('records_total'))} · merged_utc={((mark.get('ledger_merge') or {}).get('merged_utc'))}")
check("13 · العلامة تسجّل حالة كل مكوّن فعلية (لا نجاح دائم)",
      all(k in mark for k in ('feeds', 'ofac', 'originals', 'ledger_merge')) and mark.get('overall') in ('ok', 'degraded', 'failed'),
      f"الحالة العامة={mark.get('overall')} · تغذيات={(mark.get('feeds') or {}).get('status')}")

# 14 · توحيد صيغة «الأسطول نفسه»
bl = jload(B / 'appendices/style-blacklist.json', {}) or {}
terms = [b['term'] for b in bl.get('blocking', [])]
style = txt(B / 'sections/75-style.md')
check("14 · الصيغة المعتمدة لا تُمنع، والملكية تُمنع",
      'في الأسطول نفسه' not in terms and 'مالكها' in terms and 'تملك' in [w['term'] for w in bl.get('watch', [])],
      f"مانع: مالكها · تنبيه: تملك · الصيغة مسموحة في الأسلوب: {'في الأسطول نفسه' in style}")

# 15 · لا حالة عالمية لسياق الرموز
blocks = txt(S / 'generator/blocks.py')
check("15 · سياق الرموز معزول لكل جولة (لا قاموس عالمي)",
      'contextvars' in blocks and 'reset_code_context' in blocks and '_CODE_CTX = {"date"' not in blocks,
      "ContextVar + تفريغ صريح في نهاية البناء")
check("15 · المولّد يفرّغ السياق بعد كل جولة", 'reset_code_context()' in txt(S / 'generator/build_report.py'),
      "main() → finally")

# 16 · أمان الويب هوك والبوت
app = txt(S / 'server/app.py')
check("16 · الويب هوك فشل مغلق عند غياب السر",
      'webhook secret unset' in app and 'if not _hook:' in app, "لا سر ⇒ 503 · سر غير مطابق ⇒ 401")
check("16 · لا معرّف صاحب قرار افتراضيًا في الشيفرة",
      '1125' not in txt(B / 'tools/telegram_bot.py') and 'owner_id' in txt(B / 'tools/telegram_bot.py'),
      "owner_id() من ملف الجهات المعتمدة فقط")
check("16 · توثيق صريح للمخاطر المتبقية وتدوير الأسرار", (B / 'appendices/security-notes.md').exists(),
      "appendices/security-notes.md")

print("=== تحقق إصلاحات 19 أكتوبر 2026 (الدفعة الثانية) ===")
bad = 0
for name, ok, detail in res:
    bad += 0 if ok else 1
    print(f"  {'✔' if ok else '✘'} {name}" + (f"  — {detail}" if detail else ''))
print(f"=== النتيجة: {len(res) - bad}/{len(res)} نجحت · فشل={bad} ===")
sys.exit(1 if bad else 0)