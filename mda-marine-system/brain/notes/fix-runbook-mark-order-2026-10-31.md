# خطة إصلاح تناقض ترتيب علامة التشغيل — 2026-10-31

## القرار
اختيار (ب): إبقاء ترتيب المانيفست كما هو، لأن `phase_order` يرفض وضع خطوة `write` (`W040`) قبل خطوة `ingest` (`S020`). العلامة مرحلة pipeline تلخّص الحالة الحالية التي ستُحدَّث لاحقًا بمكوّنات التغذية وغيرها؛ لذا يُنشئ `mark_components.py` العلامة عند غيابها عبر نفس مسار `write_mark.py --stage pipeline` ثم يضيف أثرًا صريحًا `created_by: mark_components`.

## الملفات المتأثرة
- `tools/mark_components.py`: bootstrap محدود للعلامة المفقودة فقط؛ لا إزالة لشروط الفشل المغلق الأخرى.
- `runbook/runbook.json`: لا تغيير في ترتيب الخطوات أو سلاسل أوامر argv؛ يبقى S020 قبل W040.
- `docs/runbook.md`: توليد من المانيفست.
- `tests/test_mark_components_bootstrap.py`: اختبار دائم يثبت حالة العلامة المفقودة وحالة JSON التالف.
- `audit/سجل-الأعطال-والثغرات.md` و`memory/learning-log.jsonl`: تسجيل العطل والدرس بعد الإثبات.

## معايير قبول قابلة للقياس
1. `bash tools/restore_skills.sh` ثم `python3 validators/check_skills_integrity.py` يخرجان 0.
2. النسخ الاحتياطية الثلاث في `/home/ubuntu/audit-2026-10-30/backups-20261031/` متطابقة بالبصمة.
3. `python3 tools/runbook.py handbook` يخرج 0، ثم `python3 tools/runbook.py verify` يخرج 0.
4. من يوم نظيف، تشغيل `python3 tools/runbook.py run --date 2026-10-31 --redo S020` يتجاوز S020 ولا يرجع بسبب غياب العلامة؛ يُسجّل رمز الخروج الحرفي.
5. اختبار دائم يثبت أن العلامة تُنشأ مع `created_by` وأن JSON التالف يبقى فشلًا مغلقًا برمز 2.
6. ملف شارد غير معلن يجعل `verify` يخرج 2، ثم إزالته يعيد `verify` إلى 0.
7. يضاف صف 12 عمودًا للعطل الجديد ودرس JSONL مطابق، ثم `closure_round.py --apply` و`check_closure.py` مرتان، كل مرة 0.
8. الاستئناف يسجل رمز كل خطوة ويتوقف فقط عند 10 أو 2 أو الإكمال؛ لا نشر/تلغرام/نسخ احتياطي خارج المانيفست.

## الرجوع
استعادة `tools/mark_components.py` من النسخة الاحتياطية، ثم توليد handbook وتشغيل verify؛ لا تغيير في شروط البوابات الأخرى ولا في ترتيب المانيفست.
