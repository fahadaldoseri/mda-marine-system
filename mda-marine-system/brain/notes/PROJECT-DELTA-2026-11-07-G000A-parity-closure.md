# خطة إصلاح G000A وتماثل المهارات — 2026-11-07

## المطلوب
1. تصحيح القيمة المركبة `مضيق هرمز ومداخل خليج عُمان` إلى قيمتي السجل القانونيتين `مضيق هرمز · خليج عُمان` في حقول الموقع، وتوحيد الصياغة النثرية إلى `مضيق هرمز وخليج عُمان`.
2. إثبات حارس موجب/سالب يمنع القيمة المركبة غير المسجلة ويقبل الفاصل القانوني `·`.
3. مزامنة ملفي المهارة من المصدر الحاكم `/home/ubuntu/skills` إلى مرآة التشغيل `/home/ubuntu/brain-marine-news/skills`، مع تأكيد أن `/home/ubuntu/mda-marine-system/brain/skills` هو النسخة الملتزمة الصحيحة.
4. إعادة تشغيل G000A والتماثل، ثم استئناف الكتيب حتى النشر والتحقق الحي، مع عدم تشغيل D005/D040/D070 لأنها تستدعي النسخة الاحتياطية المحظورة.

## الملفات المتأثرة المتوقعة
- `cumulative-2026/daily/2026-11-07.json`
- `web/meta/2026-11-07.json`
- `web/zones/2026-11-07.json`
- `cumulative-2026/event-ledger-master.json`
- `reports/2026-11-07-sectioned.md`
- `tests/test_area_absence.py`
- `skills/report-surface-and-print-ops/references/legacy/live-visual-audit-ops/{SKILL.md,scripts/verify_range_bidi.py}`
- `audit/سجل-الأعطال-والثغرات.md`
- `memory/learning-log.jsonl`

## معايير القبول
- قبل الإصلاح: `python3 validators/check_area_vocabulary.py --root .` يثبت RC=2 بسبب القيمة المركبة، واختبار السالب يفشل.
- بعد الإصلاح: `python3 validators/check_area_vocabulary.py --root .` يخرج RC=0، و`python3 -m pytest -p no:cacheprovider -q tests/test_area_absence.py` يخرج RC=0، والقيمة المركبة لا تظهر في الأسطح الحاكمة.
- تماثل المهارات: بصمتا الملفين في المصدر ومرآتي التشغيل وGit متطابقة، ومدقق `check_skills_parity.py` يخرج RC=0.
- كل خطوة لاحقة تُنفذ بمحرك الكتيب فقط، مع فحص `pgrep -af 'runbook.py run'` قبل كل تشغيل؛ أي RC=2 يُوقف الجولة.
- لا تشغيل للنسخة الاحتياطية أو الطباعة أو تلغرام، ولا دفع مباشر إلى `main`.

## أثر الرجوع
إعادة الملفات المتأثرة إلى بصماتها المسجلة قبل الإصلاح، ثم إعادة تشغيل الحراس نفسها؛ لا تعديل للحارس ولا تخفيف نطاقه.
