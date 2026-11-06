# حالات مقيسة — جولة 2026-11-05

استخدم هذه الأرقام كصيغة دليل لا كبديل عن إعادة القياس. كل رقم هنا من مخرج أمر فعلي في الجولة.

## الحالة 1 — تعارض سجل `no_material` مع الدفتر (توقف S071)

**السياق:** بعد إتمام W010 (التقرير العربي) وW020 (ملف الواجهة) وW030 (دفتر اليوم) وS070 (دمج الذاكرة التراكمية)، خرج الكتيب بـ`RUNBOOK_RC=2` عند `S071 — حارس استمرارية دفتر الوقائع`.

**المخرج الحرفي للحارس** (`logs/runbook/2026-11-05/S071.log`):
```
✘ فشل مغلق: يوم موسوم no_material وله مادة أيضًا: 2026-04-14, 2026-06-13, 2026-07-26,
2026-08-01, 2026-08-05, 2026-08-18, 2026-08-27, 2026-09-13
```

**السبب الجذري:** `cumulative-2026/no-material.json` كان يعلن ثمانية أيام «بلا مادة»، بينما ملفاتها اليومية في `cumulative-2026/daily/` صار لها وقائع فعلية بعد دفعة الملء الرجعي من أرشيف UKMTO الرسمي (1 إلى 3 صفوف لكل يوم). والحارس يقارن `material & exempt` ويفشل مغلقًا عند أي تقاطع.

**الإصلاح المطبَّق:** حذف الأيام الثمانية من قائمة `no_material` مع إبقاء الوقائع الرسمية كما هي.
```
قائمة no_material: 99 ← 91 | المحذوفة: 8
```
**إعادة القياس:**
```
✔ استمرارية الدفتر مكتملة: 251 يومًا · مادة 141 · no_incident موثق 110
```

## الحالة 2 — نقص في أرضية الأصول الحاكمة (توقف G000)

**المخرج الحرفي** (`logs/runbook/2026-11-05/G000.log`):
```
الملفات في النطاق: 2986 · مدخلات الأرضية: 2987 · نموّ مسجَّل: 25
✘ أصل حاكم مفقود أو خارج النطاق: /home/ubuntu/skills/map-section-upgrade-ops/scripts/measure_map_layers.py
✘ أصل حاكم مفقود أو خارج النطاق: /home/ubuntu/skills/map-section-upgrade-ops/scripts/measure_map_layers_live.py
✘ نقص في أصل معتمد: runbook/runbook.json — أسطر 5214→5401 · بايت 166665→152654
✘ نقص في أصل معتمد: tests/test_map_points_nonspatial.py — 5761→5760
✘ نقص في أصل معتمد: skills/bilingual-master-direction-ops/scripts/verify_master_direction.py — 5948→5944
✘ نقص في أصل معتمد: skills/map-section-upgrade-ops/SKILL.md — 10929→5990
✘ نقص في أصل معتمد: skills/map-section-upgrade-ops/scripts/check_surface_extraction.py — 2552→2444
✘ نقص في أصل معتمد: skills/source-coverage-route-ops/scripts/probe_source_routes.py — 4769→4608
النتيجة: منع — نقص في أصل معتمد
```

**التصنيف والعلاج:**
- **مفقود فعليًا (استُعيد من المرآة، ولم يُدرج في قرار القبول):** `map-section-upgrade-ops/SKILL.md` (10929) · `measure_map_layers.py` (4154) · `measure_map_layers_live.py` (2055) · `check_surface_extraction.py` (2552) · `tests/test_map_points_nonspatial.py` (5761).
- **نقص مقصود موثّق (قرار بالسبب ثم `--update`):** `runbook/runbook.json` (إعادة تنسيق بترميز عربي مقروء: الأسطر زادت والبايت نقصت) · `verify_master_direction.py` (إصلاح السكربت في جولة 2026-11-04، المزامنة `21135d7f`) · `probe_source_routes.py` (مزامنة الشيفرة المصحّحة `ed3a7507 ← 21135d7f`).

**الأمر الذي نجح:**
```bash
printf '%s\n' 'runbook/runbook.json' \
  '/home/ubuntu/skills/bilingual-master-direction-ops/scripts/verify_master_direction.py' \
  '/home/ubuntu/skills/source-coverage-route-ops/scripts/probe_source_routes.py' > /tmp/asset-decisions.txt
python3 validators/check_asset_floor.py --decisions /tmp/asset-decisions.txt --reason "<سبب صريح + دليل>"
python3 validators/check_asset_floor.py --update
```
**المخرج:** `الملفات في النطاق: 2988 · مدخلات الأرضية: 2987 · نموّ مسجَّل: 25 · قرارات: 3 (حذف 0 · نقص مقبول 3)` ثم `النتيجة: سليم`، وبعد `--update`: `نموّ مسجَّل: 0 · النتيجة: سليم`.

**درس الأداة:** مسارات المهارات في ملف القرارات تُكتب **مطلقة**، ومسارات الجذر **نسبية**؛ الخطأ في ذلك يعطي «قرار على مسار غير معروف في الأرضية» = فشل مغلق.

## ملاحظة على التمييز بين الرمزين

- `رمز 2`: منع مقصود من حارس (تعارض بيانات، أرضية أصول، اتساق، تماثل). العلاج: إصلاح المصدر ثم إعادة القياس.
- `رمز 1`: فشل اختبار أو أمر عادي. العلاج: تشخيص الشيفرة أو الاختبار، ثم إضافة اختبار انحدار قبل الاستئناف.

في الحالتين: الخطوات المكتملة لا تُعاد، والاستئناف يكون من الخطوة الفاشلة نفسها عبر `python3 tools/runbook.py run --date <DATE>`.