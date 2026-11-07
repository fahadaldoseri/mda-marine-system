# B006 Arabic Counter Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven development and verification-before-completion; execute each checkbox in order and retain command output.

**Goal:** توحيد عقد تصريف عدّاد «روايات لم تتأكد» بين العقد الحاكم والمولّد والحارس، وإغلاق B006 دون تخفيف الفشل المغلق.

**Architecture:** يعرّف `appendices/card_registry.json` صيغة بطاقة الروايات في طبقات الصفر/1/2/3–10/11–99/100+، ويستعمل المولّد والحارس دالة تصريف واحدة مشتقة من هذا العقد. تبقى قاعدة العرض رقمًا ظاهرًا مع الاسم المناسب: 0 روايات، 1 رواية، 2 روايتان، 3 روايات، 11 رواية، 100 رواية.

**Tech Stack:** Python 3، `unittest`، JSON، runbook engine.

**Spec:** `logs/runbook/2026-11-07/B006.log` و`appendices/card_registry.json` و`runbook/runbook.json`.

## Global Constraints

- لا تُخفّف الحارس ولا تُعدّل المخرجات المشتقة يدويًا؛ أصلح العقد/الدالة وأعد التوليد.
- يلزم RED ثم GREEN، مع اختبار موجب وسالب، وربط التنفيذ بـ`runbook.py verify`.
- لا تشغيل `tools/github_backup.sh` ولا D040/D070؛ فحص parity النهائي قراءة فقط.
- لا force push ولا كتابة مباشرة على `main`؛ الموقع على فرع `fix/g001-content-fidelity-2026-11-07`.

---

### Task 1: تثبيت الاختبار الحاكم قبل الإصلاح

**Files:**
- Modify: `tests/test_card_counters.py`

- [ ] أضف اختبارًا يستدعي دالة التصريف الحاكمة من `validators.check_card_counters` للقيم `0, 1, 2, 3, 11, 100` ويتوقع `روايات، رواية، روايتان، روايات، رواية، رواية`.
- [ ] أضف حالة سلبية تثبت أن `1 روايات` لا يطابق العقد.
- [ ] شغّل الاختبار منفردًا وسجّل RED قبل أي تغيير إنتاجي.

### Task 2: توحيد العقد والمولّد والحارس

**Files:**
- Modify: `appendices/card_registry.json`
- Modify: `validators/check_card_counters.py`
- Modify: `tools/build_hero_kpis.py`

- [ ] أضف إلى عقد بطاقة `unconfirmed-narratives` تعريفًا صريحًا لصيغ العدد الست.
- [ ] عرّف دالة تصريف واحدة في الحارس، ثم اجعل `_hero_detail` يستخدمها.
- [ ] اجعل المولّد يستورد/يستخدم نفس القاعدة أو يشتقها مباشرة من العقد بلا نسخة ثانية.
- [ ] أعد توليد `web/meta/2026-11-07.json` من المصدر، ولا تصلح الملف المشتق يدويًا.
- [ ] شغّل اختبار التصريف ثم حزمة `tests/test_card_counters.py` وسجّل GREEN.

### Task 3: إغلاق العطل وتحقق المانيفست

**Files:**
- Modify: `audit/سجل-الأعطال-والثغرات.md`
- Modify: `memory/learning-log.jsonl`
- Modify: `runbook/runbook.json` only if linkage is missing
- Regenerate: `docs/runbook.md` if manifest changes

- [ ] سجل عطلًا جديدًا بمعرّف وحاجز وأدلة RED/GREEN.
- [ ] أضف درسًا JSONL بمفتاح منع تكرار ثابت.
- [ ] نفّذ `python3 tools/runbook.py verify` وتأكد من رمز الخروج الفعلي.
- [ ] أعد تشغيل `B006` عبر محرك الكتيب.

### Task 4: الاستئناف والتسليم المنضبط

- [ ] افحص `pgrep -af 'runbook.py run'` ثم شغّل الأمر الحرفي المطلوب في الخلفية مع مراقبة السجل.
- [ ] عند `rc=10` نفّذ البرومت وحده ثم `complete`؛ عند `rc=2` أصلح العطل الجذري ولا تتجاوز.
- [ ] لا تنفذ D010 إذا كانت أداة Webdev غير متاحة؛ اطبع اسم الخطوة والأمر الحرفي وتوقف عندها.
- [ ] نفّذ parity strict قراءة فقط، وأبلغ أعداد الشجرة والمستودع والروابط والانحرافات والفروق.
