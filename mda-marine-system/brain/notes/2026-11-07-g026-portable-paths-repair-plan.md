# خطة إصلاح G026 — قابلية النقل — 2026-11-07

## المطلوب
إزالة literals التي تربط الشيفرة بجذري `brain-marine-news` و`seawatch` من المواضع التي أبلغ عنها `G026`، مع الحفاظ على اختبار السلوك السالب، وتمرير الجذور من البيئة أو اشتقاقها من موقع الملف.

## الملفات المتأثرة
- `brain/tests/test_gate_guard_contracts.py`
- `brain/skills/source-coverage-route-ops/scripts/probe_source_routes.py`
- `brain/skills/bilingual-master-direction-ops/scripts/verify_master_direction.py`
- `brain/tests/test_g026_portable_paths.py` (حاجز انحدار جديد)
- `brain/tests/test_surface_deferral_contract.py` (اختبار قائم كان غير متصل بالمانيفست)
- `brain/runbook/runbook.json` و`brain/docs/runbook.md` (ربط الاختبارين وتوليد الكتيب)
- `brain/notes/2026-11-07-g026-portable-paths-repair-plan.md`

## معايير القبول
1. اختبار العقد الجديد يفشل قبل الإصلاح (`RED`) بسبب literals الأربعة التي سجلها `G026`.
2. بعد الإصلاح ينجح الاختبار نفسه (`GREEN`) ويظل اختبار السلوك السالب في `test_gate_guard_contracts.py` يثبت أن المسار المطلق المصطنع يُمنع.
3. `python3 validators/check_portable_paths.py` يخرج `0` ويطبع «لا مسار مطلق في أي ملف تنفيذي».
4. `python3 tools/runbook.py verify` يخرج `0` بعد ربط اختبار الحاجز بالخطوة `G026` وإعادة توليد الكتيب عند الحاجة.
5. إعادة تشغيل `G026` من مشغل الكتيب تخرج `0`، ثم تستأنف الجولة من `G027` فقط.
6. `tests/test_surface_deferral_contract.py` مرتبط بـ`G045` وموجود في مرآة الحوكمة والتشغيل، و`runbook.py verify` يخرج `0` على المرآتين.

## أثر الرجوع
إذا فشل الاختبار أو المدقق بعد الإصلاح، يُعاد الفرع إلى الالتزام السابق لهذا الإصلاح وتُستعاد الملفات الأربعة فقط من النسخة السابقة؛ لا تُلمس تغييرات المهارات غير المرتبطة ولا مخرجات الموقع.
