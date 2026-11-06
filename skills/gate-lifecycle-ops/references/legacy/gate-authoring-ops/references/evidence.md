# أدلة التشغيل

هذه النتائج التُقطت في 2026-10-28 داخل `/tmp`، ولم تُكتب أي تجربة في المشاريع المقيدة.

## 1) التهيئة والتحقق الأولي

الأمر:

```text
python3 -m py_compile /home/ubuntu/skills/gate-authoring-ops/scripts/scaffold_gate.py /home/ubuntu/skills/gate-authoring-ops/scripts/wire_into_runner.py /home/ubuntu/skills/gate-authoring-ops/templates/gate_template.py /home/ubuntu/skills/gate-authoring-ops/templates/test_template.py
```

المخرج:

```text
py_compile: 0
```

## 2) توليد البوابة والاختبار في `/tmp`

الأمر الفعلي:

```text
python3 /home/ubuntu/skills/gate-authoring-ops/scripts/scaffold_gate.py --name sample_gate --description 'يمنع اعتماد مخرج بلا أثر قابل للقياس' --scope 'مخرج التقرير اليومي' --output-dir /tmp/gate-authoring-ops-demo
```

المخرج:

```text
أُنشئت البوابة: /tmp/gate-authoring-ops-demo/validators/check_sample_gate.py
أُنشئ الاختبار: /tmp/gate-authoring-ops-demo/tests/test_sample_gate.py
الخطوات التالية:
  1) خصّص violations() لقاعدة المجال، مع إبقاء الفشل المغلق وأسباب المنع الحرفية.
  2) اربط البوابة في tests/run_checks.sh: python3 scripts/wire_into_runner.py --runner <runner> --gate /tmp/gate-authoring-ops-demo/validators/check_sample_gate.py --label "يمنع اعتماد مخرج بلا أثر قابل للقياس"
  3) شغّل القياس الحقيقي على --date و--brain و--site و--pdf، وسجّل الأمر ورمز الخروج.
```

## 3) تشغيل الاختبار المولّد

الأمر:

```text
python3 /tmp/gate-authoring-ops-demo/tests/test_sample_gate.py
```

المخرج ورمز الخروج:

```text
اختبار البوابة: sample_gate
  ✔ مدخل سليم يجتاز
  ✔ مدخل مخالف يُمنع
  ✔ مدخل مفقود يُمنع فشلًا مغلقًا
  ✔ مدخل غير قابل للقياس يُمنع فشلًا مغلقًا
نجح 4 · فشل 0
exit 0
```

## 4) تشغيل البوابة المولّدة

عند مدخل سليم:

```text
python3 /tmp/gate-authoring-ops-demo/validators/check_sample_gate.py --date 2026-10-28 --brain /tmp/gate-authoring-ops-demo/fixture/brain --site /tmp/gate-authoring-ops-demo/fixture/site --pdf /tmp/gate-authoring-ops-demo/fixture/report.pdf
```

```text
مطابق: sample_gate — يمنع اعتماد مخرج بلا أثر قابل للقياس
exit 0
```

وعند إزالة وسم النطاق من الموقع:

```text
منع: sample_gate
  ✗ --site: تعذّر القياس — وسم النطاق «gate-scope:مخرج التقرير اليومي» غير موجود
exit 2
```

وعند حذف PDF:

```text
منع: sample_gate
  ✗ --pdf: المدخل مفقود؛ تعذّر القياس
exit 2
```

## 5) ربط نسخة مؤقتة من المشغّل الحقيقي

الأمر شُغّل على `/tmp/gate-authoring-ops-runner-demo/project/tests/run_checks.sh` بعد نسخه من `/home/ubuntu/brain-marine-news/tests/run_checks.sh`.

dry-run:

```text
python3 /home/ubuntu/skills/gate-authoring-ops/scripts/wire_into_runner.py --runner /tmp/gate-authoring-ops-runner-demo/project/tests/run_checks.sh --gate /tmp/gate-authoring-ops-runner-demo/project/validators/check_sample_gate.py --label 'بوابة تجريبية'
```

المخرج المختصر الحرفي:

```text
--- /tmp/gate-authoring-ops-runner-demo/project/tests/run_checks.sh
+++ /tmp/gate-authoring-ops-runner-demo/project/tests/run_checks.sh (مقترح)
@@ -224,6 +224,9 @@
 t "أهم الأخبار المتعلقة بالأمن البحري: كل صف نصًّا ورابطًا صالحًا على السطحين" python3 validators/check_decision_card.py --date "$(date -u +%F)"
+# gate-authoring-ops: check_sample_gate.py — بوابة تجريبية
+t "بوابة تجريبية" python3 "$B/validators/check_sample_gate.py" --date "$(date -u +%F)" --brain "$B" --site "${SITE_DIR:-$B/../seawatch}" --pdf "${PDF_PATH:-$B/../seawatch/dist/reports/pdf/$(date -u +%F).pdf}"
وضع dry-run: لم يُعدّل الملف؛ أعد الأمر مع --apply للتطبيق
exit 0
```

التطبيق والتحقق:

```text
طُبّق الربط بلا تكرار: /tmp/gate-authoring-ops-runner-demo/project/tests/run_checks.sh
runner bash -n rc=0
لا تغيير: البوابة موجودة مسبقًا بلا تكرار: check_sample_gate.py
second dry-run rc=0
```

## 6) القياس على مخرج حقيقي و`quick_validate.py`

الأمر الفعلي استخدم ملف Brain، صفحة الموقع، وPDF بتاريخ 2026-10-28:

```text
python3 /tmp/gate-authoring-ops-demo/validators/check_sample_gate.py --date 2026-10-28 --brain /home/ubuntu/brain-marine-news/reports/raw-notes-2026-10-15.md --site /home/ubuntu/seawatch/dist/reports/special.html --pdf /home/ubuntu/seawatch/dist/reports/pdf/2026-10-28.pdf
```

المخرج الحرفي:

```text
منع: sample_gate
  ✗ --pdf: تعذّرت قراءة الملف: /home/ubuntu/seawatch/dist/reports/pdf/2026-10-28.pdf ('utf-8' codec can't decode byte 0xd3 in position 10: invalid continuation byte)
real-output rc=2
```

هذا منع فشل مغلق متوقع من القالب العام: PDF الثنائي ليس نص UTF-8 قابلًا للقياس بواسطة قاعدة الوسم التجريبية، لذلك لم يتحول تعذّر القياس إلى نجاح.

الأمر:

```text
python3 /home/ubuntu/skills/skill-creator/scripts/quick_validate.py gate-authoring-ops
```

المخرج:

```text
🔍 Validating skill at: /home/ubuntu/skills/gate-authoring-ops
Skill is valid!
quick_validate rc=0
```

## 7) حدود الاختبار

لم أعدّل أو أشغّل `tests/run_checks.sh` الأصلي، ولم أختبر قاعدة مجال حقيقية خاصة ببوابة جديدة داخل Brain؛ اختبرت الربط على نسخة مؤقتة منه، وقياس القالب العام على مخرجات حقيقية انتهى بمنع PDF غير النصي كما هو موثق أعلاه. لم أختبر إرسالًا أو نشرًا أو Git أو Telegram، ولم أختبر `--force` في المولّد.
