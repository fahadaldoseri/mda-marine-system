# إغلاق ب-03 وG064 — توحيد سياق المتصفح

## السبب المثبت
مشغّل G064 يستدعي `/home/ubuntu/brain-marine-news/tools/browser_measure.py` فعلًا وبوسائط `runbook/regression-items.json`، لا نسخة المرآة. النسخة الجارية تفتح الصفحة المصدر داخل `context` ذي User-Agent Firefox، لكنها تفتح الهدف الخارجي بـ`browser.new_page()` خارج السياق؛ لذلك يفقد الهدف البصمة ويعود DOM غير مكتمل/403، بينما اختبار ب-03 الصناعي لا يميّز User-Agent.

## التغيير الأدنى
- إضافة اختبار محلي يرفض الهدف إذا لم يحمل User-Agent سياق Firefox، ليثبت أن السياق ينتقل إلى الصفحة الخارجية.
- تغيير فتح الهدف من `browser.new_page()` إلى `context.new_page()` في `tools/browser_measure.py` فقط.
- مزامنة نسخة المرآة `mda-marine-system/brain/tools/browser_measure.py` إلى نفس المحتوى والبصمة، دون منطق ثانٍ.
- إبقاء انتظار DOM والفشل المغلق كما هما: غياب الهدف أو الاستثناء يبقي `targets[key] = False` ويعيد الحكم رمز `2`.

## القبول القابل للقياس
- الاختبار المحلي الجديد يفشل قبل التغيير ويمر بعده.
- `python3 -m pytest tests/test_regression_b03_dynamic_anchor.py -q` يمر.
- اختبار سلبي لمرساة مفقودة يبقى رمز `2`.
- أمر G064 المستخرج حرفيًا من المانيفست، عبر `bash -lc` مع `export D=$(date -u +%F)`, يخرج `0`، وعدد الناجح يساوي كل البنود وعدد الساقط `0`.
- `sha256sum` للنسختين متطابق، و`duplicate_scan.py` يخرج `0` لكل نسخة.
- يضاف درس JSONL واحد وقياس مختصر في `audit/measurements/`.

## القيود
لا تعطيل للبند، لا تخفيف للحكم، لا تعديل يومي للمخرج، لا نشر أو Telegram أو backup أو Git push.
