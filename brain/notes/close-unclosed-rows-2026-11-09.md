# خطة إغلاق صفوف القياس غير المغلقة — 2026-11-09

## المطلوب
إعادة قياس كل صف غير مغلق في result-A.json وresult-B.json، وإغلاق الصفوف بإثبات rc=0 أو وسمها «معلّق بسلطة أخرى» عندما يتوقف الإغلاق على مسار البناء/الطباعة/النسخ أو قرار مالك خارج النطاق.

## الملفات المحتملة
- أدوات/اختبارات قابلة للإصلاح محليًا: `tools/audit_broad_excepts.py`, `validators/check_libraries_skills.py`, `tests/run_checks.sh`, `tests/test_sections_registry_vs_report.py`, `validators/check_exceptions_burndown.py`, `tests/test_sync_guard.py`, `tools/check_feeds.py`, `tools/check_lang_switch_live.py`, `validators/check_en_parity.py`, `tools/build_lexicon_corpus.py`, `tests/test_lexicon_gate.py`, `tools/binding_coverage.py`, `tests/test_surface_hygiene.py`, `tests/test_event_card_rows.py`, `tests/test_review2.sh`, `tools/publish_channels.py`, `tests/test_publish_channels.py`, `tools/telegram.py`/اختباراته، ومسارات الترجمة/المعجم.
- مصادر بيانات/تقارير عند الحاجة: ملفات التقرير الحالية وملفات الاختبار المؤقتة فقط.
- مخرجات القياس الجديدة: `audit/measurements/batches/result-A2.json` و`result-B3.json`.

## حدود القبول
1. لا تشغيل أو تعديل لمسارات البناء/التصدير/PDF المحجوزة: `generator/build_site.py`, `generator/build_report.py`, `tools/export_report_assets.py`, `validators/check_pdf_format.py`.
2. لا تعديل لسجل الأعطال أو الاستثناءات أو التتبع أو runbook أو `generator/build_report.py` و`generator/map_gulf.py`، ولا Git/نشر/تلغرام.
3. لكل إصلاح برمجي: اختبار موجب وسالب قبل/بعد، ثم إعادة تشغيل الأمر الأصلي حتى `rc=0` إن لم يكن محجوزًا.
4. لكل صف: الأمر، rc الفعلي، ذيل المخرج، بصمة SHA-256 للسجل، والحكم واسم الحاجز.
5. الصفوف المتوقفة على أثر محجوز تُوسم «معلّق بسلطة أخرى» بسبب صريح ومرجع الصف/الوكيل المسؤول، لا يُختلق لها rc=0.

## استراتيجية التنفيذ
- تصنيف كل صف: قابل للإصلاح محليًا، قابل لإعادة القياس دون بناء، أو محجوز/تابع لسلطة أخرى.
- قراءة شيفرة الأداة والاختبار كاملًا قبل تعديلها.
- إجراء RED/GREEN على الاختبارات أو fixtures المعزولة، ثم تشغيل الأمر الأصلي.
- توليد ملفات النتائج من السجلات الجديدة دون المساس بالملفات المرجعية الممنوعة.
