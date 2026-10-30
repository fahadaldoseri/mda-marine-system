---
name: source-ingest-ops
description: Use when collecting daily source feeds, normalizing source data, preserving official originals, or reconciling feed and source counters before report writing.
---

# إدخال المصادر وحفظ الأصل

## متى تُستدعى
استدعِ هذه المهارة عند تنفيذ S020 أو S030 أو S040 أو S050 أو S060 أو عند اختلاف عدادات المصادر أو الحاجة إلى أصل رسمي قابل للتتبع. لا تستعملها لبناء التقرير أو لتغيير سجل المصادر المعتمد.

## المسار الإلزامي
1. ثبّت `DATE=YYYY-MM-DD` واقرأ `INDEX.md` وطرق الوصول في `sections/10-sources.md`.
2. افحص حالة `feeds/feeds-$DATE.status.json` ومخرج الخلاصة قبل أي تحويل.
3. شغّل `scripts/ingest_preflight.py` قراءة فقط؛ سجّل `complete/degraded/failed` ولا تحوّل التحذير إلى نجاح.
4. نفّذ الفحص الفعلي بأمر المانيفست مع `--date $DATE`، ثم افصل التطبيع عن حفظ الأصل الرسمي.
5. ولّد أهداف OFAC وافحصها فقط عندما توجد أهداف؛ اربط النتيجة بالتقرير ولا تخمّن غياب السفن.
6. طابق `source_counts.py --check` و`check_sources_count.py` و`check_source_route_coverage.py` قبل الكتابة.

## أوامر التحقق
```bash
python3 scripts/ingest_preflight.py --brain /home/ubuntu/brain-marine-news --date 2026-10-30
python3 tools/source_counts.py --date 2026-10-30 --check
python3 validators/check_source_route_coverage.py --date 2026-10-30
```

## أخطاء حقيقية
- تشغيل فحص التغذية دون التاريخ أو استخدام `D` فارغًا.
- اعتبار `degraded` فشلًا صامتًا أو نجاحًا كاملًا؛ يجب الإفصاح عنه.
- تشغيل `--write` أو `archive_originals.py` بلا قائمة أصول مؤرخة.
- خلط رقم المصدر المعتمد بالناجح آليًا أو المرجعي اليدوي.
- تشغيل فحص OFAC على ملف أهداف غير موجود بدل إعلان «لا أهداف».

## التعلم الذاتي والإغلاق
عند ظهور عطل أو درس، سجّله لاحقًا في `audit/سجل-الأعطال-والثغرات.md` بصف الأعمدة الاثني عشر المعتمد، ثم شغّل حارس الإغلاق المالك. عند تكرار الخطأ حدّث هذه المهارة أو أضف اختبارًا يمنع عودته؛ احتفظ بحالة التغذية كما ظهرت ولا تستبدلها يدويًا.
