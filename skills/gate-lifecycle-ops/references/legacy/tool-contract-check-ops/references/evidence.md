# دليل تشغيل حي — tool-contract-check-ops

التاريخ: 2026-10-28

## 1) `cli_contract.py` على بوابة PDF الحقيقية

الأمر:

```bash
python3 scripts/cli_contract.py --tool /home/ubuntu/brain-marine-news/validators/check_pdf_format.py
```

المخرج الحرفي:

```text
عقد الأداة: /home/ubuntu/brain-marine-news/validators/check_pdf_format.py
مصدر العقد: ast:add_argument
الخيارات المقبولة: --allow-css-change, --date, --help, --pdf, -h
الوسائط الموضعية: (لا يوجد/لم تُستخرج)
الوسائط الإلزامية: --pdf
أكواد الخروج المعلنة: 0, 2, 4
تحقق الوسائط: لا توجد وسائط غير معروفة
```

رمز تشغيل السكربت: `0`.

## 2) `cli_contract.py` على بوابة أسطح الإضافات الحقيقية

الأمر:

```bash
python3 scripts/cli_contract.py --tool /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py -- --brain /home/ubuntu/brain-marine-news --site /home/ubuntu/brain-marine-news/site --date 2026-10-28 --strict-print
```

المخرج الحرفي:

```text
عقد الأداة: /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py
مصدر العقد: ast:add_argument
الخيارات المقبولة: --brain, --date, --help, --pdf, --site, --strict-print, -h
الوسائط الموضعية: (لا يوجد/لم تُستخرج)
الوسائط الإلزامية: (لم تُعلن)
أكواد الخروج المعلنة: 0, 2
تحقق الوسائط: لا توجد وسائط غير معروفة
```

رمز تشغيل السكربت: `0`.

## 3) مسار `--help` الآمن القصير

الأمر:

```bash
python3 scripts/cli_contract.py --tool /home/ubuntu/brain-marine-news/validators/check_pdf_format.py --probe-help
```

المخرج الحرفي:

```text
عقد الأداة: /home/ubuntu/brain-marine-news/validators/check_pdf_format.py
مصدر العقد: ast:add_argument
الخيارات المقبولة: --allow-css-change, --date, --help, --pdf, -h
الوسائط الموضعية: (لا يوجد/لم تُستخرج)
الوسائط الإلزامية: --pdf
أكواد الخروج المعلنة: 0, 2, 4
فحص --help الآمن: {'attempted': True, 'returncode': 0, 'timeout_seconds': 2.0}
تحقق الوسائط: لا توجد وسائط غير معروفة
```

رمز تشغيل السكربت: `0`.

## 4) تحذير وسيط مجهول قبل التشغيل

الأمر:

```bash
python3 scripts/cli_contract.py --tool /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py -- --brain /home/ubuntu/brain-marine-news --strict-print --not-a-real-option
```

المخرج الحرفي:

```text
عقد الأداة: /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py
مصدر العقد: ast:add_argument
الخيارات المقبولة: --brain, --date, --help, --pdf, --site, --strict-print, -h
الوسائط الموضعية: (لا يوجد/لم تُستخرج)
الوسائط الإلزامية: (لم تُعلن)
أكواد الخروج المعلنة: 0, 2
تحذير: وسائط لا يعرفها العقد: --not-a-real-option
```

رمز تشغيل السكربت: `0`؛ التحذير متوقع لأن السكربت نفسه لم يشغّل البوابة.

## 5) `duplicate_scan.py` على بوابة أسطح الإضافات الحقيقية

الأمر:

```bash
python3 scripts/duplicate_scan.py /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py
```

المخرج الحرفي:

```text
فحص التكرار البنيوي: /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py
تعريفات دوال/أصناف مكررة: لا يوجد
استيرادات مكررة: لا يوجد
كتل مكررة بنيويًا: لا يوجد
فحص norm قبل splitlines: لا تحذير
duplicate_scan_exit=0
```

## 6) `duplicate_scan.py` على بوابة PDF الحقيقية

الأمر:

```bash
python3 scripts/duplicate_scan.py /home/ubuntu/brain-marine-news/validators/check_pdf_format.py
```

المخرج الحرفي:

```text
فحص التكرار البنيوي: /home/ubuntu/brain-marine-news/validators/check_pdf_format.py
تعريفات دوال/أصناف مكررة: لا يوجد
استيرادات مكررة: لا يوجد
كتل مكررة بنيويًا: لا يوجد
فحص norm قبل splitlines: لا تحذير
duplicate_scan_pdf_exit=0
```

## 7) `exit_code_read.py` على بوابة PDF وملف PDF موجود

الأمر:

```bash
python3 scripts/exit_code_read.py --contract-tool /home/ubuntu/brain-marine-news/validators/check_pdf_format.py --timeout 120 -- python3 /home/ubuntu/brain-marine-news/validators/check_pdf_format.py --pdf '/home/ubuntu/brain-marine-news/reports/docx/التقرير-اليومي-2026-10-18.pdf' --date 2026-10-18
```

المخرج الحرفي:

```text
العقد قبل التشغيل:
  المصدر: ast:add_argument · الأداة: /home/ubuntu/brain-marine-news/validators/check_pdf_format.py
  الخيارات المقبولة: --allow-css-change, --date, --help, --pdf, -h
كود الخروج: 4
آخر 30 سطرًا من المخرج الحرفي:
فحص شكل PDF: التقرير-اليومي-2026-10-18.pdf
  ✓ مفتاح الخريطة حاضر (16 رمزًا)
  ✓ تذييل الترقيم على 10 صفحة
  ✓ متوسط التعبئة 99.5%
  ✓ لا عنوان قسم أو بطاقة يتيم آخر ورقة
  ✓ لا فجوة داخلية ≥ 45 مم في متن التقرير
  ✓ الغلاف والصفحة الأخيرة فوق حدّ التعبئة الأدنى
  ✗ ظهر ما يجب حجبه: «المصادر والمراجع»
  ✗ ظهر ما يجب حجبه: «محجوبمننسخةالطباعة»
  ✗ أقسام ناقصة في PDF: ['الاحتمالات ونسبة الحادث إلى جهاته']
النتيجة: مخالف للشكل المعتمد (3 مخالفة)
التصنيف المقترح: 4 عطل
قاعدة الفشل المغلق: توقّف واقرأ المخرج والعقد قبل أي متابعة
```

كود خروج الأمر المقروء: `4`؛ كود غلاف الاختبار الذي سمح باستمرار جمع الأدلة: `4`.

## 8) `exit_code_read.py` على بوابة أسطح الإضافات بمدخلات موجودة

الأمر:

```bash
python3 scripts/exit_code_read.py --contract-tool /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py --timeout 120 -- python3 /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py --brain /home/ubuntu/brain-marine-news --site /home/ubuntu/brain-marine-news --date 2026-10-28 --strict-print
```

المخرج الحرفي:

```text
العقد قبل التشغيل:
  المصدر: ast:add_argument · الأداة: /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py
  الخيارات المقبولة: --brain, --date, --help, --pdf, --site, --strict-print, -h
كود الخروج: 2
آخر 30 سطرًا من المخرج الحرفي:
سطح إضافات: 0 عنوانًا · المطلوب نقلُه: 11
  × صفحة الإضافات غير مبنية: /home/ubuntu/brain-marine-news/dist/additions.html
  × عنوان منقول غائب عن الإضافات: «ما تغيّر»
  × عنوان منقول غائب عن الإضافات: «الخلاصة»
  × عنوان منقول غائب عن الإضافات: «التوزيع الجغرافي للوقائع»
  × عنوان منقول غائب عن الإضافات: «التوجيهات التشغيلية»
  × عنوان منقول غائب عن الإضافات: «الوقائع الجديدة»
  × عنوان منقول غائب عن الإضافات: «التحذيرات والنشرات الرسمية»
  × عنوان منقول غائب عن الإضافات: «سجل IMO»
  × عنوان منقول غائب عن الإضافات: «قراءة الموقف وتحليل المؤشرات»
  × عنوان منقول غائب عن الإضافات: «الحركة الملاحية والتكدس»
  × عنوان منقول غائب عن الإضافات: «ما لم يُحسم»
  × عنوان منقول غائب عن الإضافات: «الخلفية»
  × صفحة التقرير غير مبنية: /home/ubuntu/brain-marine-news/dist/reports/2026-10-28.html
  × PDF غير موجود للفحص: /home/ubuntu/brain-marine-news/dist/reports/pdf/2026-10-28.pdf
النتيجة: مخالف — البوابة مغلقة
التصنيف المقترح: 2 منع/استخدام خاطئ
قاعدة الفشل المغلق: توقّف واقرأ المخرج والعقد قبل أي متابعة
```

كود خروج الأمر المقروء: `2`؛ هذا التشغيل استخدم عقدًا صحيحًا، لذا الرمز هنا منع فعلي بسبب مخرجات/مدخلات البناء، لا خطأ وسيط.

## 9) `exit_code_read.py` مع وسيط مجهول

الأمر:

```bash
python3 scripts/exit_code_read.py --contract-tool /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py --timeout 30 -- python3 /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py --brain /home/ubuntu/brain-marine-news --not-a-real-option
```

المخرج الحرفي:

```text
العقد قبل التشغيل:
  المصدر: ast:add_argument · الأداة: /home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py
  الخيارات المقبولة: --brain, --date, --help, --pdf, --site, --strict-print, -h
  تنبيه العقد: الاستخدام يتضمن وسائط لا يعرفها العقد: --not-a-real-option
كود الخروج: 2
آخر 30 سطرًا من المخرج الحرفي:
usage: check_additions_surface.py [-h] [--date DATE] [--brain BRAIN]
                                  [--site SITE] [--pdf PDF] [--strict-print]
check_additions_surface.py: error: unrecognized arguments: --not-a-real-option
التصنيف المقترح: 2 منع/استخدام خاطئ
قاعدة الفشل المغلق: توقّف واقرأ المخرج والعقد قبل أي متابعة
```

هذا يثبت أن الرمز `2` قد يكون استخدامًا خاطئًا؛ فحص العقد سبق التشغيل ونبّه إلى الوسيط.

## 10) عيوب اكتُشفت ولم تُصلح

- `/home/ubuntu/brain-marine-news/reports/docx/التقرير-اليومي-2026-10-18.pdf` — ملف PDF ثنائي، لذلك لا ينطبق رقم سطر. التشغيل الحي أعاد `4` وأثبت ظهور ما يجب حجبه ونقص العنوان `الاحتمالات ونسبة الحادث إلى جهاته`. قاعدة الكشف في `/home/ubuntu/brain-marine-news/validators/check_pdf_format.py:156-177`. مصدر التقرير يضع العنوان الناقص في `/home/ubuntu/brain-marine-news/reports/2026-10-18-sectioned.md:160` والقسم المصدر الذي يجب أن يبقى خارج PDF في السطر `213`.
- `/home/ubuntu/brain-marine-news/dist/` — شجرة البناء غير موجودة في القراءة الحالية؛ لذلك أعادت بوابة الأسطح `2` مع `dist/additions.html` و`dist/reports/2026-10-28.html` وPDF مفقودة. قاعدة الكشف في `/home/ubuntu/skills/report-surface-policy-ops/scripts/check_additions_surface.py:144-177`. لم أعد البناء ولم أعدّل المشروع.
- لم يكشف `duplicate_scan.py` أي تعريفات دوال/أصناف أو استيرادات أو كتل مكررة أو تطبيع قبل `splitlines` في البوابتين المفحوصتين.

## 11) ما لم أختبره

لم أختبر تشغيلًا ناجحًا لبوابة أسطح الإضافات بعد بناء `dist/`؛ البناء غير موجود، ولم أختبر إصلاح PDF أو إعادة بناء الموقع لأن النطاق يمنع تعديل ملفات المشروع. لم أختبر حالة `10` الحية؛ وثّقتها من عقد المشروع والمرجع فقط.
