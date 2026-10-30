---
name: print-freeze-verify-ops
description: "استخدم هذه المهارة عند الحفاظ على الهيئة المقفلة للطباعة أو فحص PDF قبل التسليم أو قياس الصفحات والخريطة وتصفير المتن أو مراجعة القص والانقسام بصريًا أو اعتماد تغيير CSS للطباعة بقرار صريح"
---

# تشغيل الهيئة المقفلة للطباعة

حافظ على مظهر الطباعة المعتمد، وقِس مخرجات PDF نفسها، ولا تعتبر نجاح HTML أو الشاشة دليلًا كافيًا. استخدم هذه المهارة للتقارير العربية أو أي تقرير يتطلب ثبات الصفحات والخريطة والمفتاح والتذييل قبل التسليم.

## القاعدة الحاكمة

للعقد العام الوحيد لقياس قبل/بعد والبصمة وقرار المالك، اقرأ [approved-output-change-ops/references/print-fingerprint-contract.md](../approved-output-change-ops/references/print-fingerprint-contract.md)؛ وتبقى هنا خصوصية `B030`: اقرأ `references/frozen-print-profile.md` و`references/frozen-css.md` عند الحاجة، وطبّق ميزانية الصفحات **7–12** دون تخفيف العتبات.

## سير العمل الإلزامي

1. حدّد المخرجات الموجودة بالفعل، وحدد `--brain` و`--site` وملف PDF وصفحة HTML المقابلة. لا تعِد تصدير PDF أثناء التحقق إلا إذا صدر طلب مستقل وصريح للتصدير.
2. قبل أي تغيير، سجّل عدد صفحات PDF من `pdfinfo`، وبصمة CSS المقفل، وحجم الملف، وتاريخ PDF وHTML.
3. بعد كل تغيير، حتى التغيير الصغير، أعد قياس عدد الصفحات وشغّل البوابتين التاليتين. لا تسجل «تم» قبل رؤية رموز الخروج.

```bash
python3 /home/ubuntu/skills/print-freeze-verify-ops/scripts/validators/check_pdf_format.py \
  --pdf /path/to/report.pdf --date YYYY-MM-DD --brain /path/to/brain --site /path/to/site
python3 /home/ubuntu/skills/print-freeze-verify-ops/scripts/validators/check_print_quality.py \
  --pdf /path/to/report.pdf --page /path/to/report.html --brain /path/to/brain
```

4. افحص أن `check_pdf_format.py` يثبت نطاق 7–12، تعبئة الصفحات، الفجوات، التذييل، الأقسام، مفتاح الخريطة، وبصمة CSS. افحص أن `check_print_quality.py` يقيس هندسيًا كتلة الخريطة وتجمّع الحافة اليسرى للنص من PDF نفسه.
5. عاين بصريًا بنسبة **100%** الغلاف، وصفحة الخريطة، والصفحة الأخيرة. راجع قص النص أو الدليل عند العرض المحدود، الحدود، التذييل، الخرائط، والمفتاح. اعتبر قص الطرف أو اختفاء عنصر عيبًا مانعًا.
6. امنع انقسام أي عنصر صغير ذي معنى، وبخاصة مفتاح الخريطة، بين صفحتين. لا تقبل أن يبقى عنوان بلا مضمونه، ولا أن تُدفع كتلة كبيرة فتترك فراغًا يخرق profile.
7. إذا تغيّرت البصمة، أوقف التسليم وطبّق [عقد البصمة وقرار المالك](../approved-output-change-ops/references/print-fingerprint-contract.md)؛ ثم أعد تشغيل عدّ الصفحات والبوابتين والمعاينة الثلاثية. لا تعالج المخالفة بتصغير الخط أو الضغط أو تخفيف profile.

## الأداة المنسوخة والمصدّر

حافظ على منطق الأدوات المنسوخة في `scripts/validators/` و`scripts/tools/`. مرّر `--brain` و`--site` بدل مسارات صلبة. استخدم المصدّر للمعاينة الجافة عند اختبار الحزمة دون كتابة مخرجات

```bash
python3 /home/ubuntu/skills/print-freeze-verify-ops/scripts/tools/export_report_assets.py \
  --date YYYY-MM-DD --brain /path/to/brain --site /path/to/site --dry-run
```

لا تستخدم المصدّر العادي على مشروع حقيقي أثناء مهمة تحقق لا تطلب إعادة التصدير؛ فهو قد يكتب PDF وصورة الخريطة. لا تتجاوز البوابات بمتغيرات البيئة أو خيارات المعايرة في إصدار التسليم.

## حلقة التحسين الذاتي

للعقد العام للتسجيل والتشديد، أحِل إلى [approved-output-change-ops/references/self-learning.md](../approved-output-change-ops/references/self-learning.md)؛ وتبقى أداة التشديد الخاصة بهذه المهارة كما هي:

عند ظهور أي ثغرة، شغّل `scripts/propose_tightening.py` على سجل JSON أو JSONL أو Markdown، وارفق مخرجه مع الجولة، ثم نفّذ جولة تحقق ثانية بالبوابتين والمعاينة نفسها.

```bash
python3 /home/ubuntu/skills/print-freeze-verify-ops/scripts/propose_tightening.py \
  --root /path/to/brain --log /path/to/brain/audit/faults-raw.jsonl \
  --out /path/to/tightening-proposals.md
```

## مخرجات التسليم

سلّم تقريرًا يذكر نطاق PDF، عدد الصفحات، بصمة CSS، رمز كل بوابة، نتيجة المعاينة 100% للغلاف والخريطة والصفحة الأخيرة، وأي قرار صريح أعاد تجميد الهيئة. اذكر بوضوح أي فحص بصري أو تشغيلي لم يُنفّذ.
