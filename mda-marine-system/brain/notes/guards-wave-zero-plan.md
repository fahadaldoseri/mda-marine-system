# خطة موجة الصفر — حراس واختبارات الدفتر

## المطلوب

1. إضافة حارس أسماء المصادر `validators/check_source_naming.py` وقائمة بياناته `appendices/source-label-blacklist.json`.
2. إضافة حارس تغطية الأيام `validators/check_day_coverage.py` للمدى `2026-02-28` إلى آخر ملف يومي.
3. تشديد `validators/check_area_vocabulary.py` على ألفاظ «غير مكاني/غير مكانية» وعلى غياب `area` المشروط بـ`area_basis`.
4. تشديد `validators/check_daily_events_schema.py` وتحديث `schemas/daily-events.schema.json` بحيث تكون `area` اختيارية للمادة فقط مع `area_basis`، مع إبقاء حقول المصدر والدليل والزمن الإلزامية حسب نوع الصف.
5. إضافة اختبارات موجبة وسالبة بملفات مؤقتة، وربط الحراس والاختبارات بخطوات G حرة في `runbook/runbook.json`، ثم توليد `docs/runbook.md` بالمحرّك.

## الملفات المتأثرة المتوقعة

- جديد: `appendices/source-label-blacklist.json`، `validators/check_source_naming.py`، `validators/check_day_coverage.py`، `tests/test_source_naming_gate.py`، `tests/test_day_coverage_gate.py`، `tests/test_area_absence.py`، واختبار لفظ «غير مكانية».
- قائم بعد أخذ نسخة `/tmp/pre-guards-<اسم الملف>`: `validators/check_area_vocabulary.py`، `validators/check_daily_events_schema.py`، `schemas/daily-events.schema.json`، `runbook/runbook.json`، `docs/runbook.md`.
- لا تعديل: `cumulative-2026/**`، `tools/backfill_ukmto_archive.py`، `tools/ledger_totals.py`، `seawatch/**`.

## معايير قبول قابلة للقياس

- كل حارس جديد يعيد `0` لمدخل نظيف و`2` لمخالفته، مع بقاء الانهيار غير المتوقع عبر `_guard` بالرمز `70`.
- حارس تسمية المصدر يقرأ القائمة من JSON، ويفحص `source` في الدفتر والواجهة والتقرير، ولا يسمح بالوصف العام حتى في صف «لا واقعة».
- حارس الأيام يرفض أي ملف ناقص أو دليل ناقص، ويرفض «المصدر المحجوب» إذا كان العنصر الوحيد، ويقبل مادة مكتملة أو «لا واقعة» مكتملة.
- حارس المساحة يرفض اللفظين «غير مكاني» و«غير مكانية» ويقبل `area` الفارغة فقط مع `area_basis` غير الفارغ.
- حارس المخطط لا يسقط أي قيمة `event_kind` قائمة، ويُبقي إلزام `source` و`evidence_ref` و`retrieved_at` للمادة وإلزام `sources_checked` لعدم الواقعة.
- `python3 tools/runbook.py handbook` يولد `docs/runbook.md`، ثم `python3 tools/runbook.py verify` يُشغّل حديثًا وتُسجّل نتيجة الخروج والمخرج الخام دون ادعاء غير مثبت.

## أثر الرجوع

يمكن استعادة كل ملف قائم من نسخته المقفلة في `/tmp/pre-guards-<اسم الملف>`، وحذف الملفات الجديدة فقط؛ لا تُلمس بيانات الدفتر أو أصول `seawatch`.