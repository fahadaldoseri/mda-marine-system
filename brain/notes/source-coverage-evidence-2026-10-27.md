# دليل تغطية المصادر — 2026-10-27

## المسارات الخمسة بعد الفحص الحقيقي

| المصدر | المسار | دليل الاستخراج |
|---:|---|---|
| 2 UKMTO — التحذيرات 2026 | `https://r.jina.ai/https://www.ukmto.org/ukmto-products/warnings/2026` | 12 عنصرًا؛ أول عنوان: `23/10/2026 Attack:UKMTO has received a verified time-late report of an incident in the Strait of...` |
| 3 UKMTO — النشرات الاستشارية 2026 | `https://r.jina.ai/https://www.ukmto.org/ukmto-products/advisories/2026` | 2 عنصران؛ أول عنوان: `23/10/2026 Attack:UKMTO has received a verified time-late report of an incident in the Strait of...` |
| 4 UKMTO — التقارير الأسبوعية 2026 | `https://r.jina.ai/https://www.ukmto.org/ukmto-products/weekly-reports/2026` | 2 عنصران؛ أول عنوان: `23/10/2026 Attack:UKMTO has received a verified time-late report of an incident in the Strait of...` |
| 43 The Maritime Executive | `https://maritime-executive.com/` | 31 عنصرًا؛ أول عنوان: `Democratic Senators Warn Seaports Not to Handle Russian Diesel` |
| 58 المركز الإعلامي للقوات المسلحة اليمنية | `https://yafm.net/` | 50 عنصرًا؛ أول عنوان: `مجلس الوزراء يستمع إلى إحاطة من وزير...` |

المصدر الخام: `feeds/feeds-2026-10-27.json`، والحالة: `feeds/feeds-2026-10-27.status.json`.

## الحالة الحية الأخيرة

أمر التشغيل: `python3 tools/check_feeds.py --date 2026-10-27`.

المخرج الخام الأخير: `logs/check-feeds-2026-10-27-rerun.log`، رمز الأمر `1` (degraded، لا يتجاوز حد الفشل).

من ملف الحالة الأخير: `checked=40`, `ok=38`, `failed=2`, `manual_reference` هو `[1,5,13,15,18,19,21,23,27,34,39,40,44,48,52,56,57,59,60,61,62]` (21 رقمًا مميزًا في القائمة المعطاة)، `items=1602`, `fail_ratio=0.05`, `fail_ratio_limit=0.20`، والفاشلان 17 و41.

بصمة الحالة الأخيرة: `96144b56a4d558417b2426fad108afd0b6d912a0d09d4c6164c746b1e08ff5dc`.

إعادة إنتاج 41 أعادت 403/Just a moment في محاولتين؛ إعادة إنتاج 42 أعادت نجاحًا في ثلاث محاولات، ثم أعاد التشغيل الكامل 42 ناجحًا. لا تغيير للحدود ولا تجاوز للحجب.

مفارقة الطلب: النص يقول 22 مرجعية لكنه يسرد 21 رقمًا، كما أن الهدف النصي 40/34/1/22 لا يطابق الحساب المقيس بعد إضافة خمسة مسارات؛ لم تُختلق أرقام أو مصادر.
