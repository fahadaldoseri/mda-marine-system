---
name: approved-output-change-ops
description: ضبط أي تغيير يمس مخرجًا مقفلًا أو معتمدًا عبر قياس حي قبل/بعد، بوابات PDF والأسطح، اعتماد بصمة موثّق، وحلقة تعلم تمنع التكرار. استخدمها عند تغيير print CSS أو سياسة الأقسام أو قاموس حاكم أو مخطط علامة أو قالب PDF، أو عند نقل أقسام، إصلاح فراغ/تخطيط، إضافة سطح قارئ، أو رفض إصدار بسبب اختلاف بصمة.
---

# Approved Output Change Ops

## الغرض وقاعدة الأمان

حوّل التغيير في المخرج المقفل إلى أثر قابل للتكرار: **قياس قبل → إصلاح محدود → قياس بعد → بوابات → بصمة → قرار مالك → سجل → تشديد**. لا تعتبر رمز خروج صفريًا وحده دليل نجاح؛ احفظ الأمر ومخرجه والبصمات والملفات المقاسة.

لا تعدّل `/home/ubuntu/brain-marine-news` أو `/home/ubuntu/seawatch` أثناء الاختبار. انسخ الملفات المعنية إلى `/tmp/<run>`، وشغّل الأدوات على النسخة. لا تعتمد بصمة جديدة ولا تخفف حدًا إلا بقرار مالك صريح.

## بوابة القرار

- **ينفّذ تلقائيًا:** قراءة الحالة، النسخ المؤقت، القياس، إصلاح عطل داخلي محدود لا يغير حدًا أو معنى، إعادة تشغيل البوابات، جمع الأدلة، وتوثيق الأثر.
- **يحتاج قرار المالك:** تغيير أي حد أو نطاق صفحات، تعديل سياسة أقسام، نقل سطح قارئ، اعتماد CSS جديد، تخفيف/تعطيل بوابة، أو تغيير قاموس/مخطط حاكم.
- **ممنوع:** تجاوز `allow_css_change` لإخفاء اختلاف، إعلان نجاح بلا مخرج حي، أو كتابة «مُغلق» بلا مانع آلي.

## التسلسل التنفيذي

1. **عرّف القفل والسطوح.** حدّد `brain` وملف `--frozen` و`--profile`، PDF الفعلي، صفحة HTML إن وجدت، وسجل المفردات/السياسة المتأثر.
2. **خذ خط أساس حي.** احفظ `sha256`/`sha16` للـ CSS وprofile وPDF. شغّل البوابات قبل الإصلاح، وسجّل عدد الصفحات، تعبئة الصفحات، أكبر فجوة، قياس الخريطة، تصفير المتن، وحالة كل سطح.
3. **أصلح السبب لا الحد.** أصلح قاعدة CSS متعارضة، مسارًا أو مصدرًا ميتًا، أو ازدواجًا داخليًا. لا تغيّر `avg_fill_min` أو `max_internal_void_mm` أو نطاق الصفحات لتعويض عطل.
4. **أعد البناء والقياس.** قِس PDF النهائي نفسه، لا HTML وحده. أعد تشغيل `check_pdf_format.py` و`check_print_quality.py` و`audit_style_coverage.py`. احتفظ بمخرج كل أمر.
5. **افحص التعارضات.** شغّل `check_registry_conflicts.py` قبل اعتماد قاموسين؛ بند ممنوع ومطلوب معًا مانع.
6. **اعتمد البصمة فقط بعد القرار.** مرّر هوية المعتمد والسبب والدليل والتاريخ إلى `freeze_adopt.py`. سيحفظ النسخة السابقة باسم `SUPERSEDED-<sha>.css`، ويحدّث `print_css_sha16`، ويضيف سجل `from/to/reason/approved_by/evidence/date`.
7. **ابنِ حزمة الدليل.** استخدم `gate_evidence.py`؛ سلّم `evidence.json` وجدول `evidence.txt`. راجع المخرج لا رمز الخروج فقط.
8. **أغلق العطل بالتعلم الإلزامي.** في نهاية الجولة، سجّل العطل وأثره في `audit/سجل-الأعطال-والثغرات.md`، أضف درسًا إلى `memory/learning-log.jsonl`، أعد بناء `audit/faults-index.jsonl`، ثم أضف بوابة أو اختبار تراجع يمنع التكرار. لا تُعلن الإغلاق قبل إثبات التشديد.

## الأوامر الأساسية

استخدم المسارات المطلقة في التشغيل الفعلي أو مرّرها صراحةً:

```bash
SKILL=/home/ubuntu/skills/approved-output-change-ops
BRAIN=/tmp/approved-output-change-ops-run/brain
FROZEN="$BRAIN/templates/approved-pdf/print-css-frozen.css"
PROFILE="$BRAIN/templates/approved-pdf/print-profile.json"

python3 "$SKILL/scripts/gate_evidence.py" \
  --brain "$BRAIN" --frozen "$FROZEN" --profile "$PROFILE" \
  --date YYYY-MM-DD --pdf /path/to/final.pdf --page /path/to/report.html

python3 "$SKILL/scripts/freeze_adopt.py" \
  --brain "$BRAIN" --frozen "$FROZEN" --profile "$PROFILE" \
  --approved-by "اسم المالك" --reason "سبب قابل للقياس" \
  --evidence "logs/.../evidence.json" --date YYYY-MM-DD

python3 "$SKILL/scripts/check_registry_conflicts.py" \
  --brain "$BRAIN" --frozen "$FROZEN" --profile "$PROFILE"
```

للمصدر غير المكتشف مرّر `freeze_adopt.py --current path/to/build_report.py`. وللقوائم غير القياسية مرّر `check_registry_conflicts.py --forbidden ... --required ...`، ويمكن تكرار كل خيار.

## مثال موثّق: فراغ الطباعة وبصمة القفل

في الحالة المرجعية، سببت قاعدتان متعارضتان للمحدِّد نفسه (`break-inside:auto` ثم `avoid`) فراغًا **206 مم** في ورقة. كان الإصلاح حذف القاعدة المكررة، ثم صار الناتج **9 صفحات**، بتعبئة **96.6%**، ولا فجوة داخلية `≥45 مم`. تحسّن الناتج، لكن بصمة القفل تغيّرت؛ لذلك مُنع الإصدار حتى اعتمد المالك البصمة الجديدة، حُدّث profile، وسُجل السبب والدليل والمعتمد، وحُفظت البصمة السابقة باسم `SUPERSEDED-<البصمة>.css`.

حالة أخرى لا تُفسَّر كنجاح: ملخص الاختبارات قال «0 فشل» بينما فحصًا كان خارج العدّاد وبوابتان بعد `exit 0` كانتا كودًا ميتًا. عالج ذلك بضمّ الأمر إلى العدّاد، وباختبار سلوك البوابات ورمزها ومخرجها.

## الأدلة واللغة العربية

اقرأ [references/change-control.md](references/change-control.md) عند تحديد ما يحتاج قرارًا، و[references/evidence.md](references/evidence.md) عند بناء الدليل الحي. لا تجعل `pdftotext` وحده حكمًا على العربية: قد يقلب الحروف أو يضيف مسافات ومحارف اتجاه؛ استخدم قياسات PDF الهندسية، الرموز اللاتينية، البصمات، ومعاينة بصرية.

## حلقة التعلم ومنع التكرار

اقرأ [references/self-learning.md](references/self-learning.md) في كل جولة. الحد الأدنى الفعلي داخل مشروع يوفّر الأدوات هو:

```bash
SKILL=/home/ubuntu/skills/approved-output-change-ops
python3 memory/record_learning.py --lesson "..." --category operational \
  --origin validator --evidence "logs/.../evidence.json" --status confirmed
python3 "$SKILL/scripts/rebuild_fault_index.py" --brain "$BRAIN"
python3 tools/reports_index.py --today YYYY-MM-DD
python3 tools/self_improve.py --date YYYY-MM-DD
```
`rebuild_fault_index.py` يقرأ سجل الأعطال ويُخرج `audit/faults-index.jsonl` و`audit/فهرس-الأعطال.json`؛ ولا يُمنع بغياب ملف القفل، بل يطبع تنبيهًا ويكمل الإخراج.

`reports_index.py` يعيد فهرس التقارير؛ أما فهرس الأعطال فيُعاد بناؤه من سجل الأعطال إلى `audit/faults-index.jsonl` بأمر الفهرسة المعتمد في المشروع. إن لم يوجد أمر مخصص، لا تُخفِ ذلك: نفّذ سكربت فهرسة موثّقًا من نفس النسخة، احفظ مخرجه، وأضف اختبارًا يمنع عودة العطل قبل قول «مُغلق».

## معيار التسليم

سلّم مسار `SKILL.md`، مخرج `quick_validate.py`، جدولًا لكل سكربت (الأمر · المخرج · الحالة)، قائمة الملفات الناتجة، ومسارات `evidence.json`/`evidence.txt`. اذكر صراحة أي جزء لم يُختبر. لا تستخدم كلمة «نجح» بلا مخرج حي محفوظ.


## حدود المهارة
هذه المهارة لا تدير تشغيل الجولة الكامل؛ المهارة الجارة `crossing-gate-ops` تضبط عبور المرحلة بدليل قبل/بعد.
