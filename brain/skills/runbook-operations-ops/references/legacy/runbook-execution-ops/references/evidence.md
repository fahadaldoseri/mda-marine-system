# أدلة الاختبار الفعلي

تاريخ الاختبار: 2026-10-28. لم تُكتب أي ملفات في `/home/ubuntu/brain-marine-news` أثناء اختبار السكربتات؛ تشغيل السائق على التاريخ المكتمل قرأ السجل ولم ينفذ خطوة جديدة.

## فحص الصياغة

الأمر:

```bash
python3 -m py_compile scripts/runbook_driver.py scripts/record_lesson.py
```

المخرج الفعلي:

```text
py_compile_rc=0
```

## `record_lesson.py`: إضافة درس

الأمر استعمل سجلًا مؤقتًا داخل مسار المهارة (`.test-work/learning-log.jsonl`) حتى لا يُعدّل سجل المشروع:

```bash
python3 scripts/record_lesson.py --learning .test-work/learning-log.jsonl \
  --entry-kind runbook --cls process --status observed \
  --symptom 'تشغيلان متوازيان' --cause 'غياب قفل موحد' \
  --fix 'استخدام سائق بقفل ذري' \
  --barrier 'تحقق من العملية والقفل قبل run → خرج 2 عند التوازي'
```

المخرج الفعلي:

```text
record_first_rc=0
✔ سُجّل الدرس في /home/ubuntu/skills/runbook-execution-ops/.test-work/learning-log.jsonl (البصمة cf47f986063efab6).
اقتراح التشديد القابل للإدراج:
{
  "barrier_id": "runbook-barrier-cf47f986063e",
  "if_symptom": "تشغيلان متوازيان",
  "root_cause": "غياب قفل موحد",
  "require_before_close": "تحقق من العملية والقفل قبل run → خرج 2 عند التوازي",
  "rule_to_insert": "امنع إغلاق الحالة عند ظهور «تشغيلان متوازيان» ما لم يتحقق: تحقق من العملية والقفل قبل run → خرج 2 عند التوازي"
}
```

## منع تكرار الدرس

عند إعادة الأمر نفسه كان المخرج الفعلي:

```text
record_duplicate_rc=0
⏸ الدرس موجود؛ لم يُكرّر الإدخال (البصمة cf47f986063efab6).
اقتراح التشديد القابل للإدراج:
{
  "barrier_id": "runbook-barrier-cf47f986063e",
  "if_symptom": "تشغيلان متوازيان",
  "root_cause": "غياب قفل موحد",
  "require_before_close": "تحقق من العملية والقفل قبل run → خرج 2 عند التوازي",
  "rule_to_insert": "امنع إغلاق الحالة عند ظهور «تشغيلان متوازيان» ما لم يتحقق: تحقق من العملية والقفل قبل run → خرج 2 عند التوازي"
}
```

## الفشل المغلق لسجل غير صالح

أُنشئ سجل مؤقت يحوي `{"legacy":true}` فقط. المخرج الفعلي:

```text
record_malformed_rc=2
✘ منع مغلق: سجل التعلم غير صالح (السطر 1 يفتقد الحقول: ts, entry_kind, cls, status, symptom, cause, fix, barrier). لم يُكتب شيء.
```

## تشغيل المشروع الفعلي

قبل التشغيل لم تكن هناك عملية `tools/runbook.py` أو `runbook_driver.py` قائمة، ولم توجد مؤشرات قفل معروفة في المشروع. الأمر الفعلي:

```bash
python3 scripts/runbook_driver.py --brain /home/ubuntu/brain-marine-news --date 2026-10-28
```

المخرج الفعلي:

```text
driver_rc=0
✔ اكتملت كل الخطوات
الخطوة التالية: لا توجد؛ اكتمل التشغيل وفق السجل.
```

هذا تشغيل قراءة آمن لتاريخ مكتمل؛ لم تُنفّذ عملية نشر أو Telegram أو نسخة احتياطية من الاختبار.

## منع التشغيل المتوازي بالقفل

حُجز القفل الذري المؤقت داخل مسار المهارة، ثم شُغّل السائق الثاني للتاريخ نفسه. المخرج الفعلي:

```text
driver_lock_rc=2
lock-holder-ready
✘ منع مغلق: سائق آخر يمسك قفل التاريخ؛ لم يُشغّل runbook.
```

## فرع المنع `2` وقراءة آخر 40 سطرًا

اُستخدم fixture مؤقت داخل `.test-work/driver-fixture-block`، وليس المشروع الفعلي، لإجبار محرّك مصغّر على إعادة 2 وكتابة 45 سطرًا. المخرج الفعلي يتضمن بالضبط السطر 06 إلى 45:

```text
fixture_rc2=2
▶ S999 — خطوة اختبار المنع [script]
✘ توقف عند S999: رمز الخروج 2
الخطوة المانعة: S999.
آخر 40 سطرًا من logs/runbook/2026-10-28/S999.log:
fixture-line-06
fixture-line-07
fixture-line-08
fixture-line-09
fixture-line-10
fixture-line-11
fixture-line-12
fixture-line-13
fixture-line-14
fixture-line-15
fixture-line-16
fixture-line-17
fixture-line-18
fixture-line-19
fixture-line-20
fixture-line-21
fixture-line-22
fixture-line-23
fixture-line-24
fixture-line-25
fixture-line-26
fixture-line-27
fixture-line-28
fixture-line-29
fixture-line-30
fixture-line-31
fixture-line-32
fixture-line-33
fixture-line-34
fixture-line-35
fixture-line-36
fixture-line-37
fixture-line-38
fixture-line-39
fixture-line-40
fixture-line-41
fixture-line-42
fixture-line-43
fixture-line-44
fixture-line-45
فشل مغلق: توقف؛ لا نشر ولا Telegram ولا نسخة احتياطية.
```

## فرع الانتظار `10`

اُستخدم fixture مؤقت داخل `.test-work/driver-fixture-agent` لإجبار محرّك مصغّر على إعادة 10. المخرج الفعلي:

```text
fixture_rc10=10
▶ W999 — خطوة اختبار الوكيل [agent]
────────────────────
برومت اختباري لا يُنفَّذ في هذا الاختبار
────────────────────
الخطوة التالية المطلوبة: W999.
نفّذ الـ prompt المطبوع وحده، ثم complete للخطوة نفسها، ثم أعد run.
```

## التحقق الرسمي

الأمر:

```bash
python3 /home/ubuntu/skills/skill-creator/scripts/quick_validate.py runbook-execution-ops
```

المخرج الفعلي:

```text
🔍 Validating skill at: /home/ubuntu/skills/runbook-execution-ops
Skill is valid!
```

## حدود الاختبار

- **لم أختبره:** إعادة تشغيل `10` على المشروع الفعلي؛ التاريخ 2026-10-28 مكتمل، ولم أنفّذ أي prompt يدوي.
- **لم أختبره:** منع خطوة فعلية برمز `2` على المشروع الفعلي مع قراءة سجلها؛ اختُبر هذا المسار بfixture معزول كما هو موثق أعلاه.
- **لم أختبره:** تنفيذ `complete <STEP>` الفعلي أو أي نشر أو Telegram أو نسخة احتياطية.
- **لم أختبره:** تعديل المانيفست ثم `handbook` و`verify` بعد التعديل؛ لم يُعدّل المانيفست في هذه المهمة.
- **لم أختبره:** الكتابة إلى `memory/learning-log.jsonl` في المشروع الفعلي؛ ذلك ممنوع بنطاق المهمة، كما أن السجل الحالي يستخدم مخططًا تاريخيًا لا يطابق الحقول الثمانية، وكان سيُرفض فشلًا مغلقًا بدل تعديله.
