---
name: runbook-execution-ops
description: "استخدم هذه المهارة عند تشغيل كتيب يومي مُقفل بخطوات إلزامية في مركز الوعي بالمجال البحري، أو عند تفسير أكواد runbook، أو قراءة سجل خطوة، أو منع تشغيلين متوازيين، أو تسجيل درس وحاجز بعد التشغيل."
license: Complete terms in LICENSE.txt
---

# تشغيل الكتيب التشغيلي المُقفل

## قواعد لا تتجاوزها

1. اعتبر `runbook/runbook.json` **المانيفست الوحيد**، واعتبر `docs/runbook.md` الكتيب المولّد منه، واعتبر `tools/runbook.py` المحرّك الوحيد.
2. عقد القفل ومنع التوازي وقراءة سجل الخطوة ورموز الخروج موحّد في [references/step-exit-codes.md](references/step-exit-codes.md).
3. لا تتجاوز خطوة ولا تنفّذ خطوة لاحقة يدويًا. لا تستخدم `complete` إلا بعد أن يسلّم المحرّك برومت الخطوة نفسها، وبعد تنفيذ ذلك البرومت وحده والتحقق من شروطه.
4. لا تنفّذ نشرًا أو إرسالًا إلى Telegram أو نسخة احتياطية إلا إذا كانت خطوة صريحة في المانيفست وبلغها المحرّك بالترتيب. لا تستنتج صلاحية التنفيذ من وجود ملف قديم أو من الذاكرة.
5. عند تعديل المانيفست، أعد توليد الكتيب ثم تحقّق منه:
   ```bash
   python3 tools/runbook.py handbook
   python3 tools/runbook.py verify
   ```
6. هذه المهارة لا تنسخ منطق سجلات الأعطال ولا تغلق عطلًا. عند الحاجة إلى سجل عطل أو سبب جذري أو حاجز إغلاق، أحِل إلى [fault-closure-ops](../fault-closure-ops/SKILL.md). وعند تشغيل حلقة إغلاق أعطال كاملة، أحِل أيضًا إلى [self-learning-loop-ops](../self-learning-loop-ops/SKILL.md).

## التشغيل القياسي

نفّذ من جذر المشروع وبالتاريخ المطلوب، بعد فحص القفل والعملية:

```bash
python3 tools/runbook.py verify
python3 tools/runbook.py status --date <DATE>
python3 tools/runbook.py run --date <DATE>
```

الأفضل للتشغيل الآمن:

```bash
python3 scripts/runbook_driver.py --brain /home/ubuntu/brain-marine-news --date <DATE>
```

اقرأ فقط المانيفست والكتيب والسجل. تُقرأ سجلات الخطوات عند المنع وفق القراءة الواحدة المحددة في [references/step-exit-codes.md](references/step-exit-codes.md).

## عقد المانيفست والقفل والخروج

التفاصيل الجدولية، قراءة سجل الخطوة، والأمثلة الفعلية موجودة في [references/step-exit-codes.md](references/step-exit-codes.md). لا تُعاد تعريف الرموز هنا.
وسجل المخرجات الفعلية والتحقق النهائي موجود في [references/evidence.md](references/evidence.md).

## التعلم الذاتي بعد كل تشغيل

بعد كل تشغيل سجّل درسًا واحدًا على الأقل عندما يوجد عرض أو ملاحظة، واقترح حاجزًا آليًا يمنع التكرار، ثم تحقّق أن الحاجز قائم فعليًا ولا تسجّل النص نفسه مرتين. استخدم السكربت المحلي بلا شبكة:

```bash
python3 scripts/record_lesson.py \
  --brain /home/ubuntu/brain-marine-news \
  --entry-kind runbook \
  --cls process \
  --status observed \
  --symptom "..." --cause "..." --fix "..." --barrier "..."
```

يكتب السكربت الحقول `ts`, `entry_kind`, `cls`, `status`, `symptom`, `cause`, `fix`, `barrier` بصيغة JSONL، ويفشل مغلقًا عند سجل غير صالح، ويطبع اقتراح الحاجز بصيغة قابلة للإدراج. تفاصيل الحلقة في [references/self-learning.md](references/self-learning.md). لا يستبدل ذلك سجل الأعطال: سجّل العطل وإغلاقه عبر [fault-closure-ops](../fault-closure-ops/SKILL.md).

## حدود الصلاحية

صلاحية هذه المهارة هي **التنسيق والتحقق والتوقف الآمن** حول محرّك الكتيب فقط. لا تمنح صلاحية النشر أو الإرسال أو النسخ الاحتياطي، ولا تسمح بتوسيع المانيفست، ولا تبرر تجاوز خطوة أو اعتماد سجل قديم. أي فعل ذي أثر خارجي يجب أن يكون أمرًا صريحًا في خطوة المانيفست الحالية وبشرط نجاحها.
