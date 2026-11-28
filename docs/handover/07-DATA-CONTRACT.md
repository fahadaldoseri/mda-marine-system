# 07 — عقد البيانات

> تاريخ الكتابة: 2026-11-28 (البحرين)
> الفرع: handover/grok-2026-11-28
> الالتزام الأب: 66f16c9364e744db4697c622dec508ac16248e67
> المشغّل المنتهية مهمته: Claude


كسر أي بند هنا يُسقط بوابة مانعة أو يفسد النشر.

## رموز الوقائع `MN-YYYY-MM-DD-NN`

| البند | الحقيقة | السند |
|---|---|---|
| الصيغة | `MN-` ثم تاريخ الإصدار ثم رقم من خانتين، مثل `MN-2026-11-21-03` | `brain/cumulative-2026/event-ledger-master.json` الحقل `display_code` |
| لماذا لا يتغير معناها | الرمز يُمنح مرة واحدة ويربط التقرير بمعرّف الدفتر `EV-...`؛ تغيير المعنى يقطع الإسناد إلى الوقائع السابقة | `brain/tools/merge_ledger_daily.py` رأس الملف |
| المنع | لا إعادة إسناد: تعارض في `code_conflicts` أو ارتباط رمز بمعنيين مخالفة مانعة | `brain/validators/check_code_spaces.py` القاعدة 4 |
| كل `MN-` في النص | موجود في `appendices/event-code-map.json` أو في `event_keys` بواجهة الإصدار | القاعدة 2 |
| رقم الحادث ورقم البلاغ (قرار المالك 21 نوفمبر 2026، الصيغة أ) | `YY-NNNN` للحادث و`YY-NNNN/k` للبلاغ، مثل `26-0417` و`26-0417/1`؛ الرمز `MN-` باقٍ بلا تغيير | `brain/appendices/incident-id-map.json` والخطوة S073 و`brain/CHANGELOG.md` |

## فضاء `EST-`

| البند | الحقيقة |
|---|---|
| الصيغة | `EST-YYYY-MM-DD-NN` |
| ما يدخل فيه | التقديرات التحليلية فقط (قراءة الموقف، الاحتمالات) |
| السجل | `brain/appendices/estimate-code-map.json` (5 مفاتيح: `generated_utc` و`rule` و`spaces` و`codes` و`notes`) |
| التسجيل | `python3 brain/tools/register_estimate.py --date D --seq N --section ... --statement ... --confidence ... --reliability ... --support ...`، ورفض عند التعارض (رمز 2) |
| المنع | `EST-` داخل «الوقائع الجديدة» مخالفة مانعة (التقدير ليس واقعة)؛ `EST-` غير مسجل مخالفة مانعة |
| فحص يوم الكتابة | `python3 brain/tools/register_estimate.py --check --date D` (شرط إتمام W010) |

## دفتر الأحداث

| البند | القيمة |
|---|---|
| المسار | `brain/cumulative-2026/event-ledger-master.json` (599 سجلًا عند الالتزام `66f16c9`) |
| القائمة | حقل `events` وحده؛ توحيد البنية المزدوجة `records` و`events` عيب ث-04 مغلق |
| مفتاح السجل | `event_id` بصيغة `EV-YYYY-MM-DD-NNN-hash8`، ويحمل `display_code` (`MN-...`) |
| ملفات اليوم | `brain/cumulative-2026/daily/DATE.json` (يكتبها W030) |
| الدمج اليومي | `python3 brain/tools/merge_ledger_daily.py` من جذر `brain` (الخطوة S070)، مخرجاته الدفتر وخريطة الرموز `appendices/event-code-map.json` |
| حارس الاستمرارية | `python3 brain/validators/check_ledger_continuity.py --date D` (S071) |
| دمج مصادر الواقعة الواحدة | `tools/merge_event_sources.py` (S074) بقاعدة 6 من `brain/sections/10-sources.md` |

## مستويات التهديد والقطاعات كما تُكتب في الواجهة

المصدر: `brain/appendices/threat-scale.json` و`brain/appendices/zone-registry.json`.

| الرتبة | العربية | الإنجليزية | الرمز البرمجي |
|---|---|---|---|
| 5 | حرج | CRITICAL | `critical` |
| 4 | مرتفع جدًا | SEVERE | `severe` |
| 3 | مرتفع | SUBSTANTIAL | (في الملف) |
| 2 | متوسط | MODERATE | (في الملف) |
| 1 | منخفض | LOW | (في الملف) |

القيم المسموحة في الواجهة: «حرج» و«مرتفع جدًا» و«مرتفع» و«متوسط» و«منخفض» (`allowed_values`).

| القطاع | الاسم العربي |
|---|---|
| Z1 | مضيق هرمز وخليج عُمان والخليج العربي |
| Z2 | باب المندب والبحر الأحمر |
| Z3 | بحر العرب |
| Z4 | القرن الأفريقي |
| Z5 | المحيط الهندي |

التصنيف في ملف الواجهة `classification`: «عام» أو «مقيّد» أو «حساس». مخطط ملف الواجهة `report_schema_version` = 2.1.

## عدد المصادر

| البند | الحقيقة |
|---|---|
| المصدر الوحيد | `brain/appendices/sources-manifest.json` |
| الرقم الحالي | `approved_source_count` = 62 (آخر تحديث 2026-10-22) |
| الحقول الأخرى | `rss_feeds_checked` = 57 و`official_originals_archived` = 3 (قيم تاريخية في الملف) |
| القائمة المرجعية | `appendices/source-reliability-40.json` (الاسم تاريخي) |
| الفحص اليومي الفعلي | 60 تغذية في 21 نوفمبر 2026 (`brain/logs/pipeline-2026-11-21.json` حقل `feeds.checked`) |
| الحارس | `brain/validators/check_sources_count.py` (G025) ويخالف أي رقم مثبت في ملف آخر |
| الأرقام الممنوع تثبيتها | «40 مصدرًا» في `README.md` وفي `brain/docs/` (قديمة)، وأي رقم في الشيفرة |

## قاعدة النقاط وقائمة الأسلوب السوداء

| البند | المسار |
|---|---|
| قاعدة النقاط | `brain/validators/check_points_rule.py` (G031): حقول «أهم الأخبار» قوائم لا نصًّا، و«ما يُراقب خلال 24 ساعة» بين 3 و4 نقاط، والتعداد بثلاث فواصل فأكثر يُنقَّط |
| القائمة السوداء | `brain/appendices/style-blacklist.json` (الحقول: `term` و`reason` و`replacement` و`blocking` و`source`) |
| أداة التعلم | `brain/tools/style_learn.py` |
| المعجم المشتق | `brain/appendices/lexicon-corpus.json` يولّده G000C2 ويفحصه G000D |

## بصمة كتلة الطباعة

الملفان اللذان يجب أن يتطابقا (`AGENTS.md` القاعدة 7 وفحص `brain/validators/check_pdf_format.py`):

1. `brain/templates/approved-pdf/print-css-frozen.css` (المقفل)
2. كتلة `@media print` في `site/generator/build_report.py` (الحالي)

القيمة الحالية لـ`print_css_sha16` في `brain/templates/approved-pdf/print-profile.json`: **`25f8825e360acc30`** (بلا تعديل).

القياس على `main`: هذه القيمة تساوي بصمة الملف المقفل. بصمة الكتلة الحالية في `build_report.py` تساوي `5c9fa94cff0558cf`. **لا تطابق.** انظر `05-GATES.md` الحاشية.

أمر القراءة الذي يُظهر الاختلاف بلا كتابة:

```bash
BRAIN_DIR=$PWD/brain SITE_DIR=$PWD/site python3 - <<'PY'
import importlib.util
sp=importlib.util.spec_from_file_location('cpf','brain/validators/check_pdf_format.py')
m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
cur=m.current_print_css(); fr=m.FROZEN_CSS.read_text(encoding='utf-8')
print(m.css_fingerprint_failure(fr,cur) or 'مطابق')
PY
```

**تحذير:** `brain/tools/sync_profile_hash.py` ليس أداة قراءة. لا يقبل `--help`، وأي تشغيل له يعيد كتابة `print_css_sha16` في `print-profile.json` فورًا. انظر `16-DO-NOT.md`.
