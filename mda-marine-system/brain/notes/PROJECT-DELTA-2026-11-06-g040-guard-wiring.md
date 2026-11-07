# خطة إصلاح G040 — ربط الحراس وتضييق JSON

## المطلوب
إغلاق فشل G040 بنيويًا: ربط المدققين الأربعة التي كشفها تحليل AST بالحارس الموحّد `validators/_guard.py` وفق نمط `from _guard import run` ثم `run(main)`، واستبدال الاستثناءات العامة في مدققي JSON وأدوات G040 باستثناءات القراءة/التشغيل المتوقعة دون تغيير منطق الفحص أو رسائل النجاح/المنع.

## الملفات المتأثرة
- `validators/check_decisions_registry.py`
- `validators/check_delivery_policy.py`
- `validators/check_gate_readiness.py`
- `validators/check_reference_generated.py`
- `tools/browser_measure.py`
- `tools/gate_coverage.py`
- `tools/impact_matrix.py`
- `tools/regression_gate.py`
- `memory/learning-log.jsonl` (درس واحد فقط)

## معايير القبول
1. تحليل AST في `tests/test_review2.sh` لا يسجل أي مدقق غير موصول، مع بقاء عدد المدققات الموصول فعليًا مساويًا أو أكبر من خط الأساس.
2. لا يظهر موقع جديد غير مصنّف في فحص الاستثناءات العامة، ولا يُضاف إلى خط الأساس.
3. اختبارات `tests.test_decisions_registry` و`tests.test_delivery_policy` تخرجان 0، والمدققان يخرجان 0 على الجذر السليم و2 على نسخة `/tmp` مخالفة.
4. إعادة تشغيل G040 كاملة تخرج `نجح 11 · فشل 0` (أو ما يعادلها) ورمز 0.
5. لا تعديل في `reports/2026-11-06-sectioned.md` أو المانيفست أو النشر أو Git.

## الرجوع
إعادة الملفين إلى محتواهما السابق وإزالة سطر الدرس وسجل الخطة إذا لزم؛ لا توجد عملية حذف أو دفع أو تعديل بيانات التقرير.
