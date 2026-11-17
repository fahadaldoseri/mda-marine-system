# سجل التغييرات

كل بند يذكر ما أُثبت بالتشغيل. ما لم يُختبر يُذكر صراحةً.

## 17 نوفمبر 2026 (2) — التشغيل اليومي عبر Claude

- **قرار المالك:** التشغيل اليومي مهمة مجدولة عند Claude بدل خادم Manus، والبدء من نسخة بيانات 12 نوفمبر، والنشر والإرسال يبقيان موقوفين.
- أُضيفت `docs/التشغيل-اليومي-عبر-Claude.md` (تعليمات الجلسة المجدولة)، وربطت من `docs/الاستقلال-عن-مانوس.md`.
- **ما أُثبت بالتشغيل:** `runbook.py verify` متسق. حارس الاستمرارية `check_ledger_continuity.py --date 2026-11-18` خرج 2 على الأيام 13 إلى 18 نوفمبر. البيئة السحابية الافتراضية رفضت الاتصال بـ ukmto.org وmsi.nga.mil وsanctionssearch.ofac.treas.gov.
- **فجوة النقل 13 إلى 17 نوفمبر (قرار المالك):** `cumulative-2026/migration-gaps.json` ومحمّله المشترك `validators/_migration_gaps.py`، يقرؤه `check_ledger_continuity.py` و`check_day_coverage.py`. الفجوة تُعدّ يومًا لم يُفحص بعدّ مستقل، وتفشل إن تداخلت مع سجل يومي أو نقص سببها.
- **اختبار يفشل أولًا:** خمس حالات جديدة في `test_ledger_continuity.py` و`test_day_coverage_gate.py` فشلت كلها قبل التنفيذ، ثم نجحت الحالات العشر بعده (`gap-tests.txt`). الحارس على البيانات الفعلية حتى 2026-11-17 خرج 0 بفجوة نقل 5 أيام (`ledger-continuity-after-gap.txt`).
- **المجموعة الكاملة `tests/run_checks.sh`** (بـ`SITE` يشير إلى مجلد فيه `dist`): نجح 84 وفشل 7 قبل الفجوة وبعدها، والإخفاقات السبعة نفسها حرفيًا (`run_checks-branch.txt` و`run_checks-branch-gap.txt`).
- **سجل 2026-11-12 (قرار المالك: الاشتقاق من ملف الحالة):** كان `check_day_coverage.py` يفشل على main بـ13 مخالفة (`day-coverage.txt`). الأداة الجديدة `tools/derive_http_status.py` (أداة يدوية مسجلة في `manual_tools`) اشتقت 12 قيمة من `feeds/feeds-2026-11-12.status.json`: سبعة مصادر بـ200، وثلاثة بـ401، وواحد بـ403، وواحد بـ0 لانتهاء المهلة. وكل قيمة موسومة `http_status_derived` مع أساسها (`derive-http-status-apply.txt`). بعدها خرج الحارس 0 (`day-coverage-after.txt`). اختبار الأداة `tests/test_derive_http_status.py`: فشلت ثلاث حالات قبل الأداة، ثم نجحت الحالات الأربع بعدها. وأُضيف إلى `runbook/prompts/write-ledger.md` قسم لسجل «لا واقعة» يُلزم بنقل `http_status` من الجلب.
- **أثر جانبي للاختبارات أُرجع:** المجموعة الكاملة تكتب في `logs/telegram-sends.jsonl` (سجلات رفض فقط، بلا أي إرسال) وفي سجلين و`reports/2026-11-12-sectioned.md`. أُرجعت هذه الملفات ولم تُرفع.
- **ما لم يُختبر:** لم يُشغَّل الخط اليومي كاملًا في بيئة Claude، ولم تُنشأ المهمة المجدولة بعد.

## 17 نوفمبر 2026 — تطبيق قرارات المالك: إيقاف النشر والإرسال، موعد 06:40، نطاق pages.dev

- **إيقاف النشر والإرسال التلقائيين:** عُطّلت في `runbook/runbook.json` الخطوات D010 وD016 وD020 وD021 وD030 وD031 وD033 (`"disabled": true` مع السبب)، حتى يحدد المالك الوضع المعتمد بقرار مكتوب. لم يُغيَّر `runbook/delivery-policy.json`، فتغيير الوضع «أ» قرار المالك وحده. أُعيد توليد `docs/runbook.md`.
- **موعد الجدولة 06:40 بتوقيت البحرين (03:40 UTC):** في `sections/90-automation.md` و`sections/70-delivery.md` و`appendices/telegram-delivery.md` ورسائل `tools/telegram_bot.py` و`README.md`. لم يُغيَّر وقت القطع `0400Z` في ترويسة التقارير، ولم تُغيَّر التقارير السابقة.
- **نطاق النشر pages.dev:** استُبدل `seawatch-xp4qirmr.manus.space` بـ`seawatch-live.pages.dev` في `appendices/web-delivery.md` و`schedule/detail-v7.txt` و`tools/telegram_bot.py` وقيم `--base` الافتراضية في أدوات التدقيق البصري. بقيت قناة Manus المرآة (D016 و`tools/manus_channel_attempt.py`) والأوامر القديمة v4 وv6 كما هي.
- **وقت القطع 0340Z (06:40 بتوقيت البحرين)** بقرار المالك في 2026-11-17، ليطابق موعد التشغيل الجديد: في `appendices/telegram-delivery.md` (صيغة الفترة ومثال سطر الوقت) و`appendices/terminology.md` و`appendices/glossary-standard.json` و`appendices/style-blacklist.json` و`sections/20-lexicon.md` و`sections/20-examples.md`. لم تُغيَّر التقارير والبيانات السابقة، ولم يُعثر في الأدوات على ساعة قطع ثابتة في الشيفرة.
- **ما أُثبت بالتشغيل:** `runbook.py verify` متسق، و`check_delivery_policy.py` خرج 0، و`test_runbook_disabled_steps` وtest_delivery_policy وtest_gate_verdict وtest_site_guards وtest_no_publish_without_runbook وtest_runbook_engine نجحت. فشلان موجودان في main قبل التعديل بالنتيجة نفسها: `test_d020_uses_live_urls_not_file_urls` و«الملخص يمرّ فحص سياسة الإرسال» في test_delivery_scripts.
- **المجموعة الكاملة `tests/run_checks.sh`:** نجح 82 وفشل 9 على main وعلى الفرع، وكذلك بعد تعديل وقت القطع (`run_checks-branch-cutoff.txt`)، والإخفاقات التسعة نفسها، وهي سابقة للتعديل وتتعلق ببيئة السحابة والمعجم والأسرار. المخرجات الخام وبصماتها في `audit/measurements/owner-decisions-2026-11-17/`.
- **ما لم يُختبر:** لم يُشغَّل الخط على الخادم، ولم تُطبَّق التعديلات عليه، ولم تُغيَّر المهمة المجدولة الخارجية ولا الأسرار.

## 12 نوفمبر 2026 — اعتماد مهارة إصلاح قابلية النقل

- سُجل اعتماد `portable-paths-repair-ops` بقرار `D-0652`، مع مستهلك G026 وحارس ربط يُشغّل فعليًا من G001.
- اختبار الاعتماد: RED فشل 1؛ GREEN نجحت 3 حالات. نجحت حالات النقل الثلاث، وبقي الكاشف الأصلي دون تعديل؛ فحص المهارات 45 مهارة و302 ملف مصدر و0 عوائق.
- الأدلة: `audit/measurements/portable-paths-skill-2026-11-12.txt`. لم تُشغّل الجولة الكاملة أو البناء أو النشر أو تلغرام، ولم تُعدّل الأصول العالمية المالية أو أرضيتها.

## 31 أكتوبر 2026 — قابلية النقل وتماثل الأدلة

- اشتُقت جذور اختبارات وعدّاء hermetic ونافذة السببية من موقع الملف أو `BRAIN_DIR`/`SITE_DIR`/`SKILLS_DIR`؛ `python3 validators/check_portable_paths.py` = 0، واختبارات العداء 7/7 واختبار مطابقة المعرّف = 0.
- صُنّفت `brain/evidence/**` بيانات دليل مولّدة في `appendices/code-paths.json` بعد أن منع الحارس 53 مسارًا غير مصنّف؛ `python3 tools/code_paths.py check --root .` = 0 بعد الإصلاح، و`python3 tools/runbook.py verify --root brain` = 0.

## 24 أكتوبر 2026 (2) — بعد أول تثبيت على الخادم

مراجعة `bootstrap-result.md` من مانوس كشفت:
- التطبيق الأول فشل في `verify` (17 خللًا) وتراجع تلقائيًا كما صُمّم: 17 ملف `tests/sections/*.sh` القديمة باقية على الخادم وملغاة عمدًا في GitHub. أعاد مانوس إضافتها في PR #2؛ الصواب إلغاؤها لا إحياؤها (تقرأ `/home/ubuntu/seawatch` وتفحص جملة ثابتة).
  - الإصلاح: `appendices/retired-paths.json` و`apply_from_github.py` يؤرشف المسارات المُلغاة ويحذفها من الخادم (هي وحدها، ولا يحذف غيرها). اختُبر في `tests/test_apply_from_github.py` (11 ✔).
- `run_checks.sh` فشل مرتين على تخطيط الخادم (`brain-marine-news` بلا مستودع أب): تصنيف المسارات يُتخطى صراحةً خارج نسخة المستودع، واختبار الأسرار لا يعتمد التخطيط. جُرّب على تخطيط خادم محاكى: المتبقي فشل واحد سببه غياب مجلد المهارات في المحاكاة وحدها (على الخادم `/home/ubuntu/skills` موجود).
- حقائق الأرشيف من PR #2 أُخذت (`reports-archive.json`): النظام Windows بدليل بيانات المنصة لا تصريحًا من المالك؛ المسار «لا أعرف».
- لم يُختبر: `github_backup.sh` على الخادم (أوقفه مانوس لأنه يدفع بيانات إلى `main`، وهو سلوكه المصمَّم).

## 24 أكتوبر 2026 — GitHub مصدر الشيفرة وتقوية المحرّك (فرع claude/inspiring-davinci-otevea)

### أُثبت بالتشغيل
| الادعاء | الأمر | النتيجة |
|---|---|---|
| كل الاختبارات تنجح | `bash tests/run_checks.sh` | نجح 42 · فشل 0 (أيضًا على نسخة مستنسخة جديدة من الفرع) |
| المانيفست متسق على الشجرة الحقيقية | `python3 tools/runbook.py verify` | 0 خلل (كان 29 خللًا قبل الإصلاح) |
| 71 استدعاء سكربت في المانيفست موجود وخياراته معرَّفة | `python3 tests/test_manifest_commands.py` | سليم |
| البيئة تبني الموقع وPDF وWord وتجتاز البوابتين | `bash tools/verify_codespace.sh` (مع `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`) | نجح 22 · تحذير 3 · فشل مانع 0 |
| بصمة كتلة الطباعة = المعتمدة | `python3 -c` على `build_report.py` | `ac05b43f996ae9f0` |
| كل مسار في المستودع مصنَّف | `python3 tools/code_paths.py check --root ..` | 1412 مسارًا مصنَّفًا (من نسخة مستنسخة جديدة) |

### ما تغيّر
- **محرّك الكتيب** (`tools/runbook.py`): مسارات محمولة (`BRAIN_DIR` و`SITE_DIR`)، متغيرات `{date} {site} {brain}`، تضمين `{{include}}` و`{{sections}}` في البرومت، فحص ربط بالوصول من المانيفست (الملف غير المتصل خطأ)، ترتيب المراحل، رفض شرط الإتمام التافه، `gates-status` يغطي `gate_phases`، والأمر الجديد `gate-json` (يكتب `logs/gate-D/gate.json` من سجل المحرّك).
- **المانيفست**: ترتيب الختام G042 ثم G043 ثم G038 ثم G039؛ إضافة B035 (خط الأساس) وQ015 (تدقيق المكتبات الأسبوعي) وD045 (فهرس التقارير)؛ B040 يستعمل `build_report_docx_exact.py` ولا يُترك اختياريًا؛ شروط إتمام حقيقية لـ D010 وD020 وD030 وD040 وD060 وQ020؛ إصلاح D060 (كان يمرّر `--check` إلى أداة لا تعرفه)؛ سبب مكتوب لكل استثناء.
- **عناوين الأقسام**: استبدال 17 اختبار `tests/sections/test_*.sh` (كانت تفحص جملة ثابتة من مسار `/home/ubuntu`) باختبار واحد `tests/test_sections_registry_vs_report.py` يقرأ السجل وسياسة الأقسام.
- **برومت الكتابة**: يضمّن المختصر والمعجم والأمثلة وأقسام السجل نصًّا (كان يحيل إلى «المعجم أدناه» وهو غير مضمّن)، ولا يقرأ الكاتب `editor-prompt.md`.
- **التسليم**: `publish_site.sh` و`check_live.sh` محمولان بحالة حقيقية (`status` و`rc`) و`pipefail`؛ `check_live.sh --compare` يقارن بصمة PDF المنشور بالمحلي؛ مولّد ملخص تلغرام الجديد `tools/make_tg_digest.py` (سقف 900 حرف، يمرّ فحص السياسة). لم يُرسل شيء ولم يُنشر شيء.
- **الطباعة**: إعادة سطرين انجرفا عن الشكل المعتمد (`.sec-lede` و`section.doc`)؛ `heading_present` في `check_pdf_format.py` يعالج قلب لام-ألف في استخراج النص؛ تدقيق المحاذاة يتجاهل العناصر المحجوبة في الطباعة (طبقة الشاشة بصنف `no-print`).
- **أدوات اللغة**: `preserve_check.py` (لا إنذار كاذب على «Z.»، يمنع تغيير نص العنوان، ويقبل حذف مصطلح مسجَّل في `appendices/removable-latin.json`)؛ `check_orthography.py` (حذف «قبل» من قائمة حروف الجر)؛ `edit_pass.py` (كان يُسقط ما قبل أول `##` عند `--apply`، يفحص التقرير كاملًا قبل الكتابة، عميل النموذج قابل للضبط).
- **GitHub مصدر الشيفرة**: `AGENTS.md` بجذر المستودع · `appendices/code-paths.json` و`tools/code_paths.py` · `tools/apply_from_github.sh/.py` (تعارض يمنع، أرشفة قبل الاستبدال، استعادة عند فشل verify) · `github_backup.py/.sh` لا يكتبان الشيفرة فوق المستودع ويعلنان الانحراف · `.github/workflows/verify.yml` · `appendices/reports-archive.json` و`tools/reports_index.py` و`docs/reports-index.md`.
- **المهارات**: مسارها محمول (`SKILLS_DIR` ← مسار الخادم ← `skills/` في المستودع) في `check_skills_integrity.py` و`check_libraries_skills.py` و`check_backup_parity.py` و`restore_skills.sh` و`publish_changes.sh`.
- **الوثائق**: `INDEX.md` («فترتا» بدل «نافذتا»، وإزالة إحالات لملفات غير موجودة).

### لم يُختبر أو بقي مفتوحًا
- **تشغيل `runbook.py run` كاملًا** على نسخة إنتاج لم يُجرَّ: خطواته تجلب مصادر وتفحص عقوبات عبر الشبكة. اختُبرت أجزاؤه: `verify` والخطوات المنفردة بالاختبارات أعلاه.
- **`apply_from_github.sh` على الخادم الفعلي** لم يُشغَّل (لا وصول إليه). اختُبر على مستودع مؤقت فقط (`tests/test_apply_from_github.py`). أول تطبيق على الخادم يحتاج `--accept-repo` لأن الخادم فيه فروق عن المستودع.
- **النشر وتلغرام**: لم يُنفَّذا بقرار المالك. `publish_site.sh` و`make_tg_digest.py` اختُبرا بلا إرسال.
- **اختبارات تكتب في الشجرة الحية**: `tests/test_language_tools.py` و`tests/test_review2.sh` وأقسام من `run_checks.sh` تعدّل ملفات في `logs/` و`reports/` للتاريخ الحالي (إدخال سطر فارغ في تقرير اليوم، وإعادة كتابة سجلات). لم تُعالَج في هذه الجولة؛ في CI بلا أثر لأن الشجرة مؤقتة.
- **الأرشيف الخاص على جهاز المالك**: مدة الاحتفاظ 30 يومًا اعتمدها المالك. المسار ونظام التشغيل وطريقة وصول التقارير غير معروفة لدى المالك وتُستخرج من سجلات مانوس (`appendices/reports-archive.json` فيها `null` حتى ذلك).
- **الأسرار**: بقرار المالك تُحفظ نصًّا صريحًا في `brain/secrets/secrets.env` بالمستودع الخاص (توثيق وحدود في `brain/secrets/README.md`). لم يُدخَل أي سر فعلي في هذا الفرع؛ يضعها مانوس من الخادم. المستودع خاص وبلا forks (تحقق منه عبر واجهة GitHub).
