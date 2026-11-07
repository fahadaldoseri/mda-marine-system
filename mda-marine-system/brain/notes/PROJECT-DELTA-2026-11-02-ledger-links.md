# خطة ربط حقول علاقة دفتر الوقائع — 2026-11-02

## المطلوب
ربط `event_kind` وحقول العلاقة في بطاقة الواقعة، ترجمة الوسوم الجديدة، وإضافة بوابة فشل مغلق تتحقق من اتساق العلاقة وقدم الهدف والدليل وسلامة الأسطح المبنية.

## الملفات المتأثرة
- `/home/ubuntu/seawatch/generator/build_report.py`
- `/home/ubuntu/seawatch/sources/i18n/en/glossary.json`
- `/home/ubuntu/seawatch/generator/i18n_en.py`
- `/home/ubuntu/brain-marine-news/validators/check_ledger_links.py` (إضافة)
- `/home/ubuntu/brain-marine-news/tools/qa_gates.py`
- `/home/ubuntu/brain-marine-news/tools/final_gate.sh`
- `/home/ubuntu/brain-marine-news/runbook/runbook.json`

## حدود صريحة
لا تعديل في `tools/ledger_link_fields.py`، أو `appendices/event-link-contract.md`، أو أي ملف داخل `cumulative-2026/`. لا تشغيل `tools/runbook.py` أو `build_site.py` أو نشر أو Git.

## معايير القبول
1. لا يظهر نص غياب العلاقة في البطاقة؛ ويظهر سطر العلاقة فقط عند اكتمال نوع العلاقة ومرجعها، مع `link_basis` ووسم عدم الاحتساب عند `counts_as_new=false`، دون `link_status` أو `link_evidence`.
2. يمر مترجم 2026-11-02 بلا بقايا عربية للوسوم الجديدة بعد إضافة المعجم/الترجمة.
3. `check_ledger_links.py` يستخدم `_guard`، و`argparse(allow_abbrev=False)`، ويدعم `--date --brain --site`، ويعيد 2 للعلاقة غير المتسقة/المفقودة/الدائرية/غير الموثقة أو العبارة المحظورة، و0 للدفتر السليم.
4. تُضاف أداة اشتقاق العلاقة بعد `merge_ledger_daily.py` في S070 دون تعديل أداة الاشتقاق نفسها، وتُربط البوابة الجديدة في `qa_gates.py` و`final_gate.sh`.
5. تُشغّل فحوص الصياغة المطلوبة، `bash -n tools/final_gate.sh`، واختبار البوابة على نسخة مؤقتة فاسدة ثم سليمة، مع حفظ رموز الخروج والمخرجات.
