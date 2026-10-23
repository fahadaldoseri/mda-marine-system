# حالة عمل: كتيب الإجراءات التشغيلية (أمر 23 أكتوبر 2026)

## الهدف
محرّك `tools/runbook.py` + مانيفست `runbook/runbook.json` = المصدر الوحيد للخطوات والأقسام.
الكتيب `docs/runbook.md` مولَّد آليًا. لا اعتماد على ذاكرة الوكيل.

## ما أُنجز
- `tools/runbook.py` مركّب من المرجع + أُضيف: `gates` · `gates-status` · `step-add` · `step-remove`.
- `tools/_oneoff/build_runbook_manifest.py` يبني المانيفست من الواقع:
  - 17 قسمًا من `sections/30-structure.md` (block = /home/ubuntu/seawatch/generator/blocks.py · validator · prompt_snippet · tests).
  - برومتات الأقسام: `runbook/prompts/sections/<slug>.md` · اختباراتها: `tests/sections/test_<slug>.sh`.
  - برومتات خطوات الوكيل: `runbook/prompts/write-report.md` و`write-meta.md`.
  - خطوات الخط اليومي S010–S090 · خطوتا كتابة W010/W020 · كل بوابة في final_gate.sh → G001..G0NN (phase=gates) · بناء B010–B040 · تسليم D010–D060 · صيانة Q010/Q020 (weekly/quarterly).

## المتبقي
1. تشغيل المولّد ثم `runbook.py verify` ومعالجة الحلقات المفقودة (الملفات غير المربوطة).
2. سكربتات لازمة: `tools/publish_site.sh` (بوابة: يرفض بلا سجل بوابات مكتمل) · `tools/check_live.sh` · `tools/alert_monitor.sh` (مراقب مستقل يكتب logs/alerts/).
3. اختبارات القبول 11 (منها على نسخة مؤقتة) + `tests/test_runbook_engine.sh` · `tests/test_no_publish_without_runbook.sh`.
4. تقليص الأمر المجدول إلى: تشغيل المحرّك · قراءة برومت الخطوة عند رمز 10 · complete · إعادة run · توقف عند رمز 2.
5. `runbook-result.md` + دفعه إلى GitHub.

## قيود من صاحب القرار
- لا نشر ولا إرسال إلى تلغرام في هذه الجولة.
- لا يُحذف ملف يتيم قبل عرضه في تقرير الجولة.
- كل بند: سُلِّم كاملًا / تعذّر (الأمر والمخرج والعائق). وما لا يُعرف يُقال «لا أعرف».