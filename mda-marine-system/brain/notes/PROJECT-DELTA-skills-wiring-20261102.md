# خطة جولة ربط المهارات — 2026-11-02

## المطلوب
1. قياس كل مهارات `/home/ubuntu/skills`، وتحديد مجموعة المشروع من نسخة `brain/skills`.
2. فحص ربط مهارات المشروع بالمانيفست والبوابات.
3. إصلاح الانحراف المثبت في `source-coverage-route-ops/scripts/probe_source_routes.py` من النسخة الأطول في `brain-marine-news/skills` إلى السطحين الناقصين، مع عدم حذف ملفات.
4. إضافة مدقق مشروع واحد وربطه بخطوة مانيفست جديدة بعد `G018` ليتحقق يوميًا من المهارات السبع عبر الأسطح الأربعة، مع إضافة مسارات المهارات إلى روابط الخطوة.
5. ربط `tools/derive_event_links.py` بموضع حاكم قائم لأن `runbook.py verify` قبل التعديل يمنعه كملف غير متصل.
6. إعادة توليد الكتيب والتحقق، ثم تشغيل مدققات المهارات ذات الصلة قبل/بعد.

## الملفات المتأثرة المتوقعة
- `runbook/runbook.json` — إضافة روابط/خطوة فقط.
- `docs/runbook.md` — ناتج مولّد من المانيفست.
- `validators/check_project_skills.py` — مدقق جديد.
- `/home/ubuntu/skills/source-coverage-route-ops/scripts/probe_source_routes.py` — استعادة من النسخة الأطول.
- `/home/ubuntu/mda-marine-system/skills/source-coverage-route-ops/scripts/probe_source_routes.py` — استعادة من النسخة الأطول.

## معايير قبول قابلة للقياس
- يبقى عدد خطوات المانيفست 95 أو يزيد، ولا ينقص أي `id` قائم.
- `runbook.py handbook` ثم `runbook.py verify` يخرجان برمز 0، ويختفي عطل `tools/derive_event_links.py`.
- مدقق المشروع يطبع 7 مهارات مشروعية، ويمرّ برمز 0، ويثبت تطابق ملفات المصدر غير المترجمة بين الأسطح.
- `check_skills_integrity.py` يمرّ برمز 0 قبل وبعد.
- لا يكون هناك اختلاف محتوى في أي ملف مصدر لمهارة مشروعية بين الأسطح الأربعة؛ تُهمل ملفات `__pycache__/*.pyc` لأنها مشتقات غير حاكمة.
- لا تشغيل لـ `runbook.py run`، ولا نشر، ولا دفع Git، ولا لمس `/home/ubuntu/seawatch`.

## الرجوع
استعادة `runbook.json` و`docs/runbook.md` وملفات `probe_source_routes.py` من:
`/home/ubuntu/audit-2026-10-30/backups-20261102/`، ثم إعادة `runbook.py handbook`/`verify` وقياس سلامة المهارات.
