# خطة إصلاح القشرة المشتركة للجوال — 2026-10-28

## المطلوب
نقل قواعد أهداف اللمس وإلغاء القص من `screen_layer.py` إلى `site_chrome.py` حتى تُحقن عبر `CH.inject` في المصادر والتقارير والإضافات والرئيسية، مع إبقائها داخل `@media screen and (max-width:820px)` فقط.

## الملفات
- `generator/site_chrome.py`: إضافة كتلة CSS مشتركة لأهداف اللمس وروابط خلايا الجداول وإلغاء القص.
- `generator/screen_layer.py`: حذف الكتلة المشتركة المنقولة، والإبقاء على CSS طبقة الشاشة الخاص بالتقارير فقط.
- عدم تعديل `generator/build_report.py` أو `dist/` أو قواعد الطباعة.

## معايير القبول
1. المحددات المطلوبة موجودة داخل `site_chrome.MOBILE_NAV_CSS` في `@media screen and (max-width:820px)`.
2. المحددات غير موجودة ككتلة تنفيذية ثانية داخل `screen_layer.SCREEN_CSS`.
3. `.sc-kn` و`.sc-peek span` يفقدان `line-clamp` و`overflow:hidden` و`max-height` على الشاشة.
4. `python3 -m py_compile` ينجح لكل ملف مولد معدّل.
5. لا يُشغّل بناء الموقع أو تصدير الأصول أو نشر أو Git.

## الرجوع
إرجاع التعديلين في `site_chrome.py` و`screen_layer.py` فقط؛ ملفا الطباعة و`dist/` خارج النطاق.
