# جولة إصلاح عيوب إصدار 2026-11-11 — حالة مقيسة

## المادة الخام المرجعية
- ملف الواجهة اليومية: brain/web/meta/<date>.json
- دفتر الوقائع: brain/cumulative-*/daily/<date>.json
- المتنان: brain/reports/<date>-sectioned.md · sources/i18n/en/<date>-sectioned.en.md
- البطاقات الرسمية: brain/appendices/imo-incidents.json (source.as_at = 3 November 2026 · list_updated = 2026-10-30)
- المعجم الحاكم: sources/i18n/en/glossary.json (بنية جذرية: entries)
- المخرج المبني: dist/** · الحيّ: seawatch-live.pages.dev · seawatch-xp4qirmr.manus.space

## ما أُغلق بقياس
- ثنائية اللغة: 18 مدخلًا معجميًا + 3 قواعد أنماط ديناميكية (اختصار/الرمز الكامل · وقت الواقعة غير متاح · موثوقية المصدر برمزها). القائمة الكاملة المقيسة: brain/notes/missing-units-2026-11-11.json (21 وحدة فريدة).
- أسماء الأشهر في التذييل · سطر IMO · بطاقة الإضافات (ثلاثة حقول) · فصل موثوقية المصدر عن درجة الثقة · مرساة الدليل · عزل النسبة · وسم المقتطف · الرمز الكامل · رابط العودة.
- المهارة: multi-agent-audit-ops موسّعة ومعتمدة (D-0650) + مرآة المشروع.

## العائق الجاري
- 15 ملف واجهة (10-29 إلى 11-02) بلا layers.updated.value → أُضيف سقوط موثق إلى source.as_at بصيغة ISO في build_report.py:174-196.
- الوكيلان المصلحان لبناء الموقع والتقرير ختمَا عملهما: 2 + 9 اختبارات خضراء + 5 للوكيل الثالث.

## خطوات المحرّك
python3 tools/runbook.py run --date 2026-11-11 --redo B010,D005,D010,D020
