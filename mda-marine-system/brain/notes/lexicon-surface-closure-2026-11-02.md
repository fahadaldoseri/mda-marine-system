# خطة إغلاق فشل تغطية الأسطح والمعجم المشتق — 2026-11-02

## الهدف
إغلاق فشلي حزمة `SITE=/home/ubuntu/seawatch bash tests/run_checks.sh` دون إخفاء سطح قائم، ودون تشغيل `runbook.py run` أو النشر أو إعادة بناء الموقع أو تفعيل الطباعة/PDF/Word.

## الواقع المثبت قبل التعديل
- الحزمة الفعلية انتهت بـ `نجح: 59 · فشل: 2`.
- `tools/audit_style_coverage.py --date 2026-11-02 --json` خرج 2، وسجل 7 أسطح: 5 مغطاة و2 مانعة؛ المانعان المتن وصفحة التقرير، وكلاهما `ألفاظ مصطنعة ممنوعة` بسبب النص الفرعي `سند` داخل `يُسند`.
- المصدر هو `appendices/forbidden-coinages.json`، والقراءة المانعة في `validators/check_prose_defects.py:228-247`، حيث تُستخدم `re.finditer(re.escape(term), line)` بلا حدود كلمة.
- PDF ليس سطحًا مسقطًا: `tools/audit_style_coverage.py:164-167` يستثنيه فقط لأن B020/B030 معطّلتان، والقرار المعلن في `runbook/runbook.json:3608-3613, 3644-3649`، مع دليل `logs/owner-print-disable-20261031/site-surface-final.stdout`.
- `tools/build_lexicon_corpus.py --check` خرج 1: المخزّن `732538cd98d69959`/7507 مقابل المحسوب `381903ee61e4f553`/7512. مصدر الاشتقاق في `tools/build_lexicon_corpus.py:51-56,79-103`، والبصمة في السطر 100، والقراءة في السطرين 122-129.

## الملفات المتأثرة
1. `tests/test_forbidden_surface_terms.py`: إضافة حالة موجبة تمنع اللفظ الكامل `سند` وحالة سالبة لا تمنع `يُسند`.
2. `validators/check_prose_defects.py`: مطابقة المصطلح الممنوع بحدود الحروف العربية، مع بقاء الكلمات المركبة/علامات الترقيم مدعومة.
3. `appendices/lexicon-corpus.json`: إعادة توليد فقط من `tools/build_lexicon_corpus.py --apply`؛ لا تحرير يدوي.
4. `audit/سجل-الأعطال-والثغرات.md` و`memory/learning-log.jsonl`: صفا العطل/الدرس بعد إثبات الإصلاح.

## معايير القبول
- اختبار المطابقة الجديد يفشل قبل تعديل الحارس بسبب التقاط `سند` داخل `يُسند`، ثم ينجح بعد التعديل، مع بقاء إدخال `سند` الكامل مرفوضًا.
- `python3 validators/check_prose_defects.py --md reports/2026-11-02-sectioned.md` يخرج 0، وفحص النص المستخرج من صفحة التقرير يخرج 0، دون تعديل `seawatch/dist`.
- `python3 tools/audit_style_coverage.py --date 2026-11-02` يخرج 0 ويطبع 7/7 مغطاة، مع إبقاء استثناء PDF معلنًا من B020/B030 وعدم تغيير `runbook/runbook.json`.
- `python3 tools/build_lexicon_corpus.py --check` يخرج 0، وتثبت القراءة أن البصمة/العدد المخزنين يساويان المحسوبين.
- أي تغيير مستقبلي في مصدر المعجم يجعل `--check` غير صفري؛ يثبت ذلك باختبار مؤقت على نسخة معزولة لا يلوث المصدر.
- `SITE=/home/ubuntu/seawatch bash tests/run_checks.sh` يخرج `فشل: 0`، و`python3 tools/runbook.py verify` يخرج 0، ثم `python3 tools/closure_round.py --apply` و`python3 validators/check_closure.py` يخرجان أرقام الحالة الفعلية.

## الرجوع
استعادة الملفات المعدلة من النسخ التي تُحفظ قبل التعديل؛ لا Git ولا حذف جماعي ولا تشغيل كتيب أو نشر أو إعادة بناء.