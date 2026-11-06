# أدلة تشغيل فعلية

هذه المخرجات أُنشئت في 2026-10-28 على مجلدات `/tmp` فقط؛ لم تُعدّل مستودعات المشروع.

## `plan_diff.py` — خارج النطاق وتجاوز السقف يمنعان التنفيذ

إعداد التجربة: مصدر يحوي `new.txt` و`shared.txt`، هدف يحوي نسخة قديمة من `shared.txt`، ملفًا محذوفًا داخل `managed/obsolete.txt`، وملفًا خارج النطاق `keep.txt`.
خطة الفرق (تجربة جافة؛ لم تُعدّل الملفات)
المصدر: /tmp/destructive-op-guard-ops-test/plan/source
الهدف: /tmp/destructive-op-guard-ops-test/plan/target
نطاق الهدف: managed
جديد: 1
  - managed/new.txt
محدّث: 1
  - managed/shared.txt
محذوف ضمن النطاق: 1
  - managed/obsolete.txt
خارج نطاق المصدر: 1
  - keep.txt
سقف الحذف: 0
السبب: تجاوز عدد الحذف سقف الحماية.
السبب: توجد ملفات في الهدف خارج النطاق المعلن للمصدر.
القرار: غير آمن (خرج 2)
اقتراح الحاجز: أوقف التنفيذ، صحّح جذر الهدف أو --scope-prefix، وراجع الخطة قبل أي حذف.
رمز الخروج الفعلي: 2

## `plan_diff.py` — خطة آمنة مباشرة
خطة الفرق (تجربة جافة؛ لم تُعدّل الملفات)
المصدر: /tmp/destructive-op-guard-ops-test/plan/source
الهدف: /tmp/destructive-op-guard-ops-test/plan/target
نطاق الهدف: managed
جديد: 1
  - managed/new.txt
محدّث: 1
  - managed/shared.txt
محذوف ضمن النطاق: 1
  - managed/obsolete.txt
خارج نطاق المصدر: 0
سقف الحذف: 1
القرار: آمن مبدئيًا (خرج 0؛ ما زالت المراجعة البشرية مطلوبة).
رمز الخروج الفعلي: 0

## `safe_restore.py` — تجربة جافة ثم استعادة
$ python3 scripts/safe_restore.py --repo /tmp/.../repo --sha HEAD~1
المستودع: /tmp/destructive-op-guard-ops-test/restore/repo
المصدر: b797f54f5148b74ea99c9d0f9faddf80df6ca846
عدد الملفات المحذوفة المرشحة للاستعادة: 2
عدد الملفات الغائبة الآن التي ستُستعاد: 2
المسارات المرشحة:
  - quote name.txt
  - ملف عربي.txt
الوضع: تجربة جافة؛ لم تُنفذ الاستعادة.
التحقق قبل/بعد (لم يُنفذ): 2/2 ملفًا غائبًا.
اقتراح الحاجز: راجع القائمة ثم استخدم --apply فقط بعد التأكد من SHA والمسارات.
رمز الخروج الفعلي: 0
$ python3 scripts/safe_restore.py --repo /tmp/.../repo --sha HEAD~1 --apply
المستودع: /tmp/destructive-op-guard-ops-test/restore/repo
المصدر: b797f54f5148b74ea99c9d0f9faddf80df6ca846
عدد الملفات المحذوفة المرشحة للاستعادة: 2
عدد الملفات الغائبة الآن التي ستُستعاد: 2
المسارات المرشحة:
  - quote name.txt
  - ملف عربي.txt
الوضع: طُبّقت الاستعادة الآمنة على 2 ملفًا.
التحقق بعد/قبل: قبل=2 · بعد=0 ملفًا غائبًا.
ملاحظة: لم يُنفذ reset أو force-push أو commit تلقائي.
اقتراح الحاجز: راجع git diff وgit status، ثم سجّل الدرس والحاجز قبل أي commit لاحق.
القرار: تمت الاستعادة والتحقق (خرج 0).
رمز الخروج الفعلي: 0
التحقق الإضافي:
[32mA[m  "quote name.txt"
[32mA[m  "\331\205\331\204\331\201 \330\271\330\261\330\250\331\212.txt"
ملف عربي موجود: نعم
quote name موجود: نعم

## `preflight_guard.py` — حالة آمنة
فحص ما قبل العملية المدمرة (فشل مغلق)
الهدف: /tmp/destructive-op-guard-ops-test/preflight/repo/managed
تصنيف الهدف: مجلد فرعي
جذر Git: /tmp/destructive-op-guard-ops-test/preflight/repo
المصدر: /tmp/destructive-op-guard-ops-test/preflight/source
المسارات الحساسة/المستثناة داخل النطاق: لا توجد
التتبع: الفرع=main · upstream=origin/main · المتوقع=main/origin/main
شجرة العمل: نظيفة
النتيجة: آمن مبدئيًا (خرج 0؛ لا يغني عن خطة جافة ومراجعة بشرية).
اقتراح الحاجز: شغّل plan_diff.py مع سقف حذف وتجربة جافة، وسجّل قياس قبل/بعد.
رمز الخروج الفعلي: 0

## `preflight_guard.py` — مسار state داخل الهدف مرفوض
فحص ما قبل العملية المدمرة (فشل مغلق)
الهدف: /tmp/destructive-op-guard-ops-test/preflight/repo/managed
تصنيف الهدف: مجلد فرعي
جذر Git: /tmp/destructive-op-guard-ops-test/preflight/repo
المصدر: /tmp/destructive-op-guard-ops-test/preflight/source
المسارات الحساسة/المستثناة داخل النطاق: state
التتبع: الفرع=main · upstream=origin/main · المتوقع=main/origin/main
شجرة العمل: غير نظيفة
النتيجة: غير آمن (خرج 2)
الأسباب:
  - توجد مسارات حساسة/مستثناة داخل نطاق الهدف: state
  - شجرة العمل غير نظيفة؛ احفظ أو راجع التغييرات قبل العملية المدمرة.
اقتراح الحاجز: استخدم مجلدًا فرعيًا محددًا، افصل الأسرار و.git/state، صحّح upstream، ثم أعد الفحص قبل التنفيذ.
رمز الخروج الفعلي: 2

## `preflight_guard.py` — جذر مرفوض فشلًا مغلقًا
فحص ما قبل العملية المدمرة (فشل مغلق)
الهدف: /tmp/destructive-op-guard-ops-test/preflight/repo
تصنيف الهدف: جذر مستودع
جذر Git: /tmp/destructive-op-guard-ops-test/preflight/repo
المصدر: /tmp/destructive-op-guard-ops-test/preflight/repo
المسارات الحساسة/المستثناة داخل النطاق: .git, managed/state
التتبع: الفرع=main · upstream=origin/main · المتوقع=main/origin/main
شجرة العمل: غير نظيفة
النتيجة: غير آمن (خرج 2)
الأسباب:
  - الهدف هو جذر المستودع؛ الحارس يرفض النطاق الواسع افتراضيًا.
  - المصدر والهدف متطابقان؛ لا تسمح بعملية استبدال ذاتية النطاق.
  - توجد مسارات حساسة/مستثناة داخل نطاق المصدر: .git, managed/state
  - توجد مسارات حساسة/مستثناة داخل نطاق الهدف: .git, managed/state
  - مسارات مستثناة معلنة داخل نطاق العملية: *.key, *.pem, .env, .env.*, .git, secrets, state
  - شجرة العمل غير نظيفة؛ احفظ أو راجع التغييرات قبل العملية المدمرة.
اقتراح الحاجز: استخدم مجلدًا فرعيًا محددًا، افصل الأسرار و.git/state، صحّح upstream، ثم أعد الفحص قبل التنفيذ.
رمز الخروج الفعلي: 2
