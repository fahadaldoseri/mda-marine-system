---
name: report-build-export-ops
description: Use when a marine report must be built from its daily data, exported to PDF or Word, or checked across site and print surfaces before delivery.
---

# بناء التقرير وتصديره

## متى تُستدعى
استدعِ هذه المهارة عند تنفيذ B010 أو B020 أو B030 أو B040، أو عند تشخيص اختلاف بين التقرير والواجهة وPDF وWord. لا تستعملها للنشر؛ تحقق من المخرج محليًا ثم أحِل النشر إلى `site-publish-live-verify-ops`.

## المسار الإلزامي
1. اقرأ `runbook/runbook.json` و`INDEX.md`، وثبّت `DATE=YYYY-MM-DD` و`SITE` الفعليين.
2. افحص وجود `reports/$DATE-sectioned.md` و`web/meta/$DATE.json` ومصدر البيانات قبل البناء.
3. شغّل فحصًا جافًا عبر `scripts/build_preflight.py`؛ لا تكتب مخرجات أثناء التشخيص.
4. ابنِ الموقع من داخل `$SITE` بأمر المانيفست، ثم صدّر PDF/Word بأوامرهما الحرفية.
5. افحص PDF نفسه بـ`check_pdf_format.py` و`check_print_quality.py`؛ افصل عيوب التخطيط عن عيوب المحتوى.
6. سجّل رمز الخروج والمخرج الحرفي لكل مرحلة. لا تعلن التسليم قبل تطابق النص والبصمة والأسطح.

## أوامر التحقق
```bash
python3 scripts/build_preflight.py --brain /home/ubuntu/brain-marine-news --site /home/ubuntu/seawatch --date 2026-10-30
python3 validators/check_pdf_format.py --pdf /path/to/DATE.pdf
python3 validators/check_print_quality.py --pdf /path/to/DATE.pdf --date 2026-10-30
```

## أخطاء حقيقية
- تشغيل مولّد الموقع من جذر خاطئ بدل `$SITE`.
- تصدير PDF ثم فحص ملف مختلف عن الملف الذي سيُسلّم.
- إصلاح فراغ أو قص بالتقدير دون قياس الصفحة والكتلة.
- اعتبار نجاح Word دليل نجاح PDF؛ لكل سطح بوابته.
- تشغيل `export_report_assets.py` أو `build_report_docx_exact.py` أثناء فحص جاف غير مأذون.

## التعلم الذاتي والإغلاق
عند ظهور عطل أو درس، سجّله لاحقًا في `audit/سجل-الأعطال-والثغرات.md` بصف الأعمدة الاثني عشر المعتمد، ثم شغّل حارس الإغلاق المالك. عند تكرار الخطأ حدّث هذه المهارة أو أضف اختبارًا يمنع عودته؛ لا تُخفِ اختلاف بصمة أو سطح.
