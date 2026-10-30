---
name: skill-coverage-audit-ops
description: Use when auditing a runbook against its installed skills, mapping steps and tools to owners, or proving coverage gaps with reproducible read-only evidence.
---

# جرد تغطية المهارات والعمليات

## متى تُستدعى
استدعِ هذه المهارة عند تدقيق مانيفست تشغيل، أو مطابقة كل خطوة/أداة/بوابة بمهارة مالكة، أو تحويل فجوة متكررة إلى مهارة قابلة لإعادة الاستخدام. لا تستعملها لتشغيل الجولة أو تعديل المانيفست.

## المسار الإلزامي
1. اقرأ `INDEX.md` ثم `runbook/runbook.json` بوصفه مصدر الحقيقة الوحيد.
2. اجرد أرقام الخطوات ذات البادئات `S/W/G/B/D/Q`، ثم اجرد الملفات الفعلية تحت `tools/` و`validators/` مع فصل `_oneoff` والملفات المولّدة.
3. افحص وصف ومتن كل مهارة مرشحة؛ لا تعتبر تشابه الاسم دليل ملكية.
4. لكل صف سجّل: العملية، المالك، الأمر الحرفي، رمز الخروج، ومقتطف المخرج. شغّل القراءة فقط؛ استخدم `--date YYYY-MM-DD` عند الحاجة.
5. صنّف الفجوة: لا مالك، مالك جزئي لا يذكر العملية، أو تكرار يدمج في مهارة قائمة. أنشئ مهارة جديدة فقط لفجوة متكررة مستقلة.
6. شغّل `scripts/inventory_skill_coverage.py` ثم `quick_validate.py` لكل مهارة جديدة. لا تعدّل المشروع أو المانيفست أو سجل الأعطال.

## أوامر التحقق
```bash
python3 scripts/inventory_skill_coverage.py --brain /home/ubuntu/brain-marine-news --skills /home/ubuntu/skills
python3 /home/ubuntu/skills/skill-creator/scripts/quick_validate.py --path /home/ubuntu/skills/skill-coverage-audit-ops
```

## أخطاء حقيقية يجب إيقافها
- عدّ `__pycache__` أو ملفات JSON المولّدة كأدوات تنفيذية.
- تشغيل `runbook.py run` أو أمر كتابة أثناء الجرد.
- اعتبار `--help` دليل تشغيل حي؛ بعض السكربتات لا تستخدم argparse وتنفّذ أثرًا جانبيًا.
- إطلاق حكم «مغطى» من تشابه الاسم دون ذكر الأداة أو العملية في المهارة.
- إعلان الإغلاق مع وجود رمز خروج غير صفري أو مخرج مبتور.

## التعلم الذاتي والإغلاق
عند ظهور عطل أو درس، سجّله لاحقًا في `audit/سجل-الأعطال-والثغرات.md` بصف الأعمدة الاثني عشر المعتمد، ثم شغّل حارس الإغلاق في `validators/check_closure.py` أو مالكه الفعلي. عند تكرار الصنف، حدّث هذه المهارة أو أضف اختبارًا يمنع عودته؛ لا تُسقط الفشل من المصفوفة.
