# تسليم مطابق إلى Grok — تشغيل ونشر 28 نوفمبر 2026

أمر المالك (فهد الدوسري): للتنفيذ حرفيًا دون اجتهاد ودون تحسين. هذا الملف يصف ما نُفِّذ فعلًا في تشغيل 28 نوفمبر 2026 بيد Claude على النسخة الأصلية المعتمدة، ولا يضيف خطوة لم تُنفَّذ. كل ما لم أجده مكتوب فيه «غير موجود» مع موضع البحث.

- إيداع التشغيل والنشر: `ebdf7312fac835e7f7e350520bb45f833f78da24` (مستودع `mda-marine-system`، فرع `claude/project-thread-igt0ro`، دُمج في main عبر PR 677 بالإيداع `39a3ba0f634c6bee2f2dd03ef0ad75fbc57c31c5`).
- إيداع النشر في `seawatch-live`: `6c4530d8fdcfe63c15ca37d176e60ccf5c67d5cb`.
- الصفحة الحية: https://mda-bh.pages.dev/reports/2026-11-28
- الكاتب الفعلي لمتن التقرير: Claude (النموذج `claude-sonnet-5-5` كما أبلغت الجلسة `last_served_model`). لا نموذج مجاني كتب شيئًا في هذا التشغيل.

# 0. حكم التسليم

## 0.1 ما يُعدّ تشغيلًا ناجحًا
- رمز الحكم: **3** (منقوص مُفصح)، التسمية «منقوص مُفصح»، `publish_allowed: true`، `final_gate_exit_code: 1`، `mark_overall: degraded`، ويُقرأ من `brain/logs/gate-verdict-2026-11-28.json` ومن `verdict` داخل `brain/logs/deliver-2026-11-28.json`.
- حسب CLAUDE.md: 0 سليم، 3 منقوص يُفصح عنه، غير ذلك فاشل. الحكم 3 مقبول للنشر ولا يُوصف بأنه تشغيل بلا ملاحظات.
- فحوص المستودع: `cd brain && bash tests/run_checks.sh` أعطى «نجح: 108 · فشل: 0» ورمز الخروج 0 (المخرج حُفظ مؤقتًا في `/tmp/runchecks.log` ولم يُودَع؛ التفصيل في §12 البند 1).
- بصمة المتن المنشور: `2b4f78a403b191e9ed7846e5f442d5fd86ad460a83190786d5e2535a562509d5` (`brain/reports/2026-11-28-sectioned.md`، 23962 بايت)، وهي نفسها `report_sha256` في حكم النشر.
- النشر: `tools/cloud_deliver.py --push` فحص الحكم أولًا، ونسخ ملفات اليوم، ودفع إلى main في `seawatch-live` (الإيداع `6c4530d`)، وانتظر نشر Cloudflare Pages لذلك الإيداع، ثم فحص حيًّا (صفحة عربية 200 وبصمتها تساوي بصمة المبني).
- ما طُوبق صفحةً صفحة (من `brain/logs/deliver-2026-11-28.json`): `reports/2026-11-28.html` و`reports/en/2026-11-28.html` و`reports/index.html` و`reports/en/index.json` و`reports/en/additions.html` و`additions.html` و`index.html` و`feed.xml` و`sitemap.xml` و`sources.html` و`404.html` و`manus-routes.json`. التفصيل الرقمي لكل ملف داخل ملف deliver نفسه.
- تلغرام: رسالة واحدة (رقم الرسالة 86) بعد النشر والتحقق وبعد موافقة فهد المكتوبة (relay 10:32Z). علامة الإرسال: `brain/logs/publish-2026-11-28-telegram.json` (`status: ok`, `rc: 0`, `pdf: skipped-printing-disabled`).

## 0.2 ما لم يُفعَل عمدًا ومن أمر به
| ما لم يُفعل | من أمر |
|---|---|
| لا تقسيم لـ W010 ولا خفض ولا نموذج مجاني؛ التشغيل كاملًا بالنسخة الأصلية | فهد، 28 نوفمبر 06:51Z |
| لا إعادة cron ولا تشغيل مجدول ولا لمس `handover/grok-2026-11-28` | فهد (الجدولة أوقفها غروك بأمره بالإيداع `a214ac7`) |
| لم يُشغَّل D005 فعليًا (يتوقف دائمًا، خاص بـ Manus؛ الحكم من G069) | قاعدة المانيفست/المهارة seawatch-daily-run |
| لم تُشغَّل خطوات التسليم/الصيانة الـ20 المدرجة في §7.3 | لم يطلبها فهد؛ بعضها لـ Manus وبعضها أسبوعي/ربع سنوي |
| لم يُصلَح خلل 2-chain في `derive_event_links.py` ولا ثبات رابط UKMTO عبر عدة تشغيلات | لم يُطلب؛ مفصح في CHANGELOG |
| لم تُدوَّر أي مفاتيح | قرار فهد 20 نوفمبر (ذاكرة المشروع) |

## 0.3 الفرق عن تشغيلات Grok التي توقفت قبل النشر
المسجَّل أدناه هو ما أستطيع إثباته من سجل git. أسباب التوقف نفسها داخل جلسات Grok ومخرجاته **غير موجودة عندي**: موضع البحث `docs/handover/` على الفرع `handover/grok-2026-11-28` وسجل Actions للمستودع `fahadaldoseri/mda-marine-system` (سير العمل `daily.yml`). الإيداعات التالية سبقت دمجي على main ولم تكن في فرعي وقت التشغيل:

| ما يخص تشغيل Grok | ما طبّقتُه أنا في تشغيلي | أثر الإيداع (غير مطبّق عندي) |
|---|---|---|
| S070 يحتاج ملف اليوم السابق (دفتر 27) | كتبتُ دفترًا استعاديًا لـ27 أولًا (صفّان، `retrospective: true`) بقرار فهد، ثم مرّ S070 | الإيداعان `e9095df0` ثم `2433b0f7` وثّقا ثم ألغيا فجوة 27 في `migration-gaps.json` (الصافي صفر) |
| S065 (تصنيف القطاعات) توقف | انتهى `done` rc 0 في سجلي | الإيداع `6cabd099` (استثناء العمق السعودي من رسم الخريطة) و`78880bd4` (اسم منطقة مركّب فيه يابسة لا يوقف النشر) على `area-coordinates.json` و`derive_map_points.py`: انحراف عن طريقتي |
| عناوين إنجليزية | كتبتُ الأصل الإنجليزي B004 والمعجم يدويًا مع مفاتيح كاملة (§8.4) | `d878141e` (`classify_zones.py` +11 سطرًا) و`944b64ec` (`area-coordinates.json`): انحراف |
| مناطق بلا مرساة | لم تظهر عندي | `78880bd4` و`6cabd099` أعلاه |
| الاستئناف مسح فرع اليوم | لم أستعمل `resume`؛ أُودعت المخرجات كاملة | `188bd428` و`687f953d` (`daily.yml`): خطوة الاستئناف، انحراف |
| W010 EST الجديدة | سجّلتُ رموز EST بيدي في ملاحقها | `cc6a07d8` (`agent_write_llm.py`) وكذلك `c28087cc` (`agent_steps` الافتراضي 8): انحراف |

الحكم الصحيح كما طُبّق عندي: الحكم 3 مع G033 («إعلان بقرار المالك 2026-11-28 · صالح حتى 2026-12-05») ومع استثناء ب-03 المؤرخ (§8)، وليس «فشل» ولا «سليم».

# 1. طريقة العمل
1. اقرأ `CLAUDE.md` ثم `HANDOFF.md` قبل أي عمل. `HANDOFF.md`: غير موجود في المستودع (فحصتُ `brain/` والجذر)؛ موضع البحث: الخادم `brain-marine-news` وحزمة `docs/handover/` على فرع غروك.
2. الكتابة كلها بيد وكيل حقيقي، لا بنموذج مجاني، والخطوات الوكيلية الأربع (W010 التقرير، W030 الدفتر، W020 الواجهة/meta، B004 الأصل الإنجليزي) تُكتب ثم تُسجَّل بـ`python3 tools/runbook.py complete`.
3. لا قفز فوق بوابة. كل استثناء يحتاج قرارًا مكتوبًا من فهد (بطاقة قرار)؛ «واصل» ليست موافقة.
4. لا نشر ولا تلغرام إلا بأمر مكتوب من فهد في تلك المرة.
5. قبل ادعاء «تم»: `bash tests/run_checks.sh` وإرفاق الناتج.
6. ما لم يُختبر يُقال إنه لم يُختبر (CHANGELOG).

# 2. آلية العمل
- المحرّك: `brain/tools/runbook.py` بأوامر `run` و`complete` و`--redo` و`--only`، والمانيفست `brain/runbook/runbook.json` (132 خطوة؛ شُغّل منها 112 يوم 28 نوفمبر). المراحل: verify, ingest, write, gates, build, outputs, finalize, deliver, maintenance.
- الدفتر: `brain/logs/runbook/2026-11-28.jsonl` (1435 سطرًا؛ المفاتيح step/status/rc/outputs/log/attempt/elapsed_s/ts)، وسجل كل خطوة في `brain/logs/runbook/2026-11-28/<STEP>.log` (لم تُودَع، عدا `timings.md`).
- الحكم: بوابة G069 الواحدة (لا إعادة `final_gate.sh`)، تكتب `brain/logs/gate-verdict-2026-11-28.json` و`brain/logs/gate-2026-11-28/gate.json` ثم علامة `brain/logs/pipeline-2026-11-28.json`.
- التسليم: `tools/cloud_deliver.py --date D [--push]`. لا يحذف شيئًا، ولا ينسخ ما انحرف (`drift`)، ويعيد التحقق عند إعادته.
- المسار القانوني: `/home/ubuntu/mda-marine-system` (ورابط `/home/user/mda-marine-system`)، المتغيران `BRAIN_DIR=…/brain` و`SITE_DIR=…/site`.
- إعادة التشغيل التزايدية عبر `stale-snapshot.json`: تعديل المتن بعد B009 يُسقط G042، فالعلاج `--redo B009`.

# 3. خطوات العمل
جدول كل خطوات المانيفست لتاريخ 28 نوفمبر (112 خطوة شُغّلت). الأعمدة من المانيفست الحرفي ومن الدفتر، والحالة والتشغيلات والزمن من آخر سطر لكل خطوة.

| المعرّف | المرحلة | العنوان | النوع | الأمر الحرفي (أو المطالبة للوكيل) | شرط الإتمام (assert) | الكتابة (writes) | الرمز الفعلي | حالة السجل النهائية | التشغيلات | الزمن الأخير (ث) |
|---|---|---|---|---|---|---|---|---|---|---|
| S000 | verify | فحص المانيفست (verify) قبل أي خطوة | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/runbook.py verify; rc=$?; exit $rc'` | cmd: test -s docs/runbook.md |  | 0 | done | 1 | 4.918 |
| S010 | ingest | استعادة المهارات وفحص التماثل | script | `bash -lc 'B="$PWD"; export B SITE; bash tools/restore_skills.sh; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/S010.log |  | 0 | done | 1 | 3.951 |
| S015 | ingest | فحص مسبق مبكر لعطلي G000 وG049 (الدقيقة الأولى) | script | `bash -lc 'B="$PWD"; export B SITE; bash "$B/tools/early_preflight.sh" "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/S015.log |  | 0 | done | 1 | 1.391 |
| S020 | ingest | فحص التغذيات (كل المصادر المسجّلة) | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/check_feeds.py --date {date}; w=$?; if [ $w -gt 1 ]; then exit $w; fi; python3 "$B/tools/mark_components.py" --date "$D" --component feeds; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; exit ${w:-0}'` | cmd: test -s logs/runbook/{date}/S020.log |  | 1 | done_warn | 3 | 110.328 |
| S030 | ingest | ترقيم التغذيات (أرقام لاتينية) | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/normalize_digits.py; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/S030.log |  | 0 | done | 1 | 1.128 |
| S060 | ingest | حفظ الأصول الرسمية | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/refresh_imo_incidents.py --apply; ri=$?; if [ $ri -eq 2 ]; then echo "✘ سجل IMO: العدّاد المعلن يخالف الصفوف — لا يُكتب مالك مضلّل"; exit 2; fi; if [ $ri -ne 0 ]; then echo "⚠ تعذّر جلب سجل IMO (رمز $ri) — يبقى المالك السابق ويُفصح عنه"; fi; if [ ! -f watchlist/original-sources.txt ]; then echo "· لا ينطبق: لا قائمة أصول لليوم — لا توقف التسليم"; [ $ri -eq 0 ] \|\| exit 1; exit 0; fi; python3 tools/archive_originals.py {date} watchlist/original-sources.txt; rc=$?; if [ $rc -gt 1 ]; then exit $rc; fi; python3 "$B/tools/mark_components.py" --date "{date}" --component originals; rc2=$?; if [ $rc2 -gt $rc ]; then exit $rc2; fi; if [ $rc -eq 0 ] && [ $ri -ne 0 ]; then exit 1; fi; exit $rc'` | cmd: test -s logs/runbook/{date}/S060.log |  | 0 | done | 1 | 1.599 |
| S080 | ingest | فرز التغذيات بالنموذج (اختياري) | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/llm_triage.py --input feeds/feeds-{date}.md; rc=$?; exit $rc'` | cmd: test -e logs/runbook/{date}/S080.log |  | 1 | failed | 32 | 0.118 |
| S090 | ingest | مراجعة التقرير بالنموذج (اختياري) | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/llm_review.py --report reports/{date}-sectioned.md --limit 25; rc=$?; exit $rc'` | cmd: test -e logs/runbook/{date}/S090.log |  | 1 | failed | 32 | 0.118 |
| W010 | write | كتابة التقرير اليومي | agent | `prompt: runbook/prompts/write-report.md` | cmd: python3 tools/register_estimate.py --check --date {date}؛ {"type": "min_bytes", "path": "reports/{date}-sectioned.md", "n": 6000}؛ {"type": "contains", "path": "reports/{date}-sectioned.md", "text": "## "} | reports/{date}-sectioned.md, appendices/estimate-code-map.json | None | done | 2 | None |
| S040 | write | توليد أهداف العقوبات من التقرير | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/ofac_targets_from_report.py --date {date}; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/S040.log |  | 0 | done | 27 | 0.12 |
| S050 | write | فحص العقوبات (OFAC) | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/ofac_screen.py watchlist/ofac-targets.txt; w=$?; if [ $w -gt 1 ]; then exit $w; fi; python3 "$B/tools/mark_components.py" --date "$D" --component ofac; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; exit ${w:-0}'` | cmd: test -s logs/runbook/{date}/S050.log |  | 0 | done | 27 | 3.362 |
| W030 | write | بناء دفتر اليوم (وقائع ومقتطفات الأصل) | agent | `prompt: runbook/prompts/write-ledger.md` | {"type": "min_bytes", "path": "cumulative-2026/daily/{date}.json", "n": 400} | cumulative-2026/daily/{date}.json | None | done | 2 | None |
| S065 | write | تصنيف القطاعات ومستوى التهديد قبل ملف الواجهة | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/classify_zones.py" --date "$D" --write; rc=$?; exit $rc'` | cmd: test -s web/zones/{date}.json | web/zones/{date}.json | 0 | done | 26 | 0.161 |
| W020 | write | بناء ملف واجهة التقرير | agent | `prompt: runbook/prompts/write-meta.md` | {"type": "min_bytes", "path": "web/meta/{date}.json", "n": 1500} | web/meta/{date}.json | None | done | 2 | None |
| S070 | write | دمج الذاكرة التراكمية (دفتر اليوم) | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/merge_ledger_daily.py; r=$?; if [ $r -ne 0 ]; then exit $r; fi; python3 tools/ledger_link_fields.py --all; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 tools/resolve_source_links.py --date "$D" --brain "$B" --site "$SITE"; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/tools/mark_components.py" --date "$D" --component ledger_merge; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/tools/repair_ledger_prose.py" --check; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/tools/classify_zones.py" --date "$D" --write; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/tools/ledger_totals.py" --date "$D" --write; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; exit ${w:-0}'` | cmd: test -s logs/runbook/{date}/S070.log | web/zones/{date}.json, web/meta/{date}.json | 0 | done | 26 | 0.908 |
| S071 | write | حارس استمرارية دفتر الوقائع | script | `python3 validators/check_ledger_continuity.py --date {date}` | cmd: python3 validators/check_ledger_continuity.py --date {date} |  | 0 | done | 25 | 0.055 |
| S072 | write | اشتقاق روابط الوقائع وتسجيل المعرّفات الرسمية (فشل مغلق) | script | `python3 tools/derive_event_links.py --apply` | cmd: python3 tools/derive_event_links.py --apply | cumulative-2026/daily/ | 0 | done | 25 | 0.217 |
| S073 | write | رقم الحادث ورقم البلاغ (سجل ثابت لا يُعاد ترقيمه) | script | `python3 tools/assign_incident_ids.py --apply` | cmd: python3 tools/assign_incident_ids.py --check | appendices/incident-id-map.json | 0 | done | 25 | 0.069 |
| S074 | write | دمج مصادر الواقعة الواحدة وإعادة العدّ بعد الربط | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/merge_event_sources.py --ledger cumulative-2026/daily --apply; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/tools/classify_zones.py" --date "$D" --write; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/tools/ledger_totals.py" --date "$D" --write; exit $?'` | cmd: test -s logs/runbook/{date}/S074.log | cumulative-2026/daily/, web/zones/{date}.json, web/kpis-totals/{date}.json | 0 | done | 25 | 0.332 |
| W040 | write | علامة التشغيل اليومية (pipeline mark) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/write_mark.py" --date "$D" --stage pipeline; rc=$?; exit $rc'` | {"type": "min_bytes", "path": "logs/pipeline-{date}.json", "n": 80} |  | 0 | done | 25 | 0.07 |
| G000 | gates | لقطة الأصول الحاكمة وإلحاق السجل قبل البوابات | script | `bash -lc 'python3 validators/check_asset_floor.py --update && python3 tools/governing_assets_merkle.py --snapshot && snapshot="evidence/merkle/snapshot.json" && root="$(python3 -c '"'"'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["root"])'"'"' "$snapshot")" && files="$(python3 -c '"'"'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["file_count"])'"'"' "$snapshot")" && python3 tools/append_only_ledger.py --append --kind snapshot --root "$root" --files "$files"; rc=$?; exit "$rc"'` | {"type": "file_exists", "path": "evidence/merkle/ledger.jsonl"}؛ {"type": "min_bytes", "path": "evidence/merkle/ledger.jsonl", "n": 1} | evidence/merkle/snapshot.json, evidence/merkle/ledger.jsonl | 0 | done | 25 | 1.308 |
| G000A | gates | بوابة الأصول الحاكمة — ledger والمرآة (فشل مغلق) | script | `bash -lc 'python3 validators/check_skills_integrity.py && python3 validators/check_asset_floor.py && python3 validators/check_area_vocabulary.py && bash tools/restore_skills.sh && python3 validators/check_skills_integrity.py && python3 tools/append_only_ledger.py --verify && python3 tools/check_governing_assets.py --json; rc=$?; exit "$rc"'` | {"type": "file_exists", "path": "evidence/merkle/ledger.jsonl"}؛ {"type": "contains", "path": "tools/governing-assets.txt", "text": "GLOB /home/ubuntu/skills/*/SKILL.md"} |  | 0 | done | 25 | 7.081 |
| G000B | gates | مالك أدوات التشغيل المحكمة والمراقب | script | `bash -lc 'bash tools/hermetic_run.sh --help && bash -n tools/watch_governing_assets.sh && test -x tools/watch_governing_assets.sh; rc=$?; exit "$rc"'` | {"type": "file_exists", "path": "evidence/hermetic/HERMETIC-RUN.md"}؛ {"type": "file_exists", "path": "tools/watch_governing_assets.sh"} |  | 0 | done | 25 | 0.026 |
| G000C | gates | اختبارات التشغيل داخل الحاوية المحكمة | script | `bash -lc 'python3 -m pytest -p no:cacheprovider -q tests/test_hermetic_run.py && test -s evidence/hermetic/HERMETIC-RUN.md; rc=$?; exit "$rc"'` | {"type": "file_exists", "path": "evidence/hermetic/HERMETIC-RUN.md"} | evidence/hermetic/declaration-proof.json, evidence/hermetic/fingerprints/declaration-proof/project-after.json, evidence/hermetic/fingerprints/declaration-proof/project-before.json, evidence/hermetic/f | 0 | done | 25 | 15.249 |
| G000C2 | gates | توليد المعجم المشتق آليًا (إلزامي قبل التحقق) | script | `bash -lc 'B="$PWD"; export B SITE; if [ -f "feeds/feeds-$D.status.json" ]; then python3 "$B/tools/source_counts.py" --date "$D" --write \|\| exit $?; fi; python3 "$B/tools/build_lexicon_corpus.py" --apply; rc=$?; [ $rc -eq 0 ] \|\| exit $rc; python3 "$B/tools/build_lexicon_corpus.py" --check; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G000C2.log | appendices/lexicon-corpus.json | 0 | done | 25 | 0.425 |
| G000D | gates | اتساق المعجم المشتق (مصدر واحد) | script | `python3 tools/build_lexicon_corpus.py --check` | cmd: python3 tools/build_lexicon_corpus.py --check |  | 0 | done | 25 | 0.154 |
| G001 | gates | اختبارات البوابات (tests) | script | `bash -lc 'B="$PWD"; export B SITE; RUN_CHECKS_CACHE="${TMPDIR:-/tmp}/seawatch-g001-cache/$D.json" bash "$B/tests/run_checks.sh"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G001.log |  | 0 | done | 26 | 108.137 |
| G002 | gates | تنظيف المحتوى الداخلي | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/scrub_internal.py" --date "$D" --apply; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G002.log |  | 0 | done | 19 | 0.059 |
| G003 | gates | دمج بنك التعريفات | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/merge_glossary.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G003.log |  | 0 | done | 19 | 0.108 |
| G004 | gates | أرقام المصادر (معتمدة/مفحوصة/ناجحة) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/source_counts.py" --date "$D" --write; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G004.log |  | 0 | done | 19 | 0.132 |
| G006 | gates | إصلاح الصياغة الآلي (خطوة واحدة) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/repair_prose.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G006.log |  | 0 | done | 19 | 0.062 |
| G007 | gates | تحرير لغوي آلي (قبل/بعد لكل قسم) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/edit_pass.py" --report "$B/reports/$D-sectioned.md" --out-dir "$B/audit" $( [ "${EDIT_PASS_APPLY:-1}" = "1" ] && echo --apply ); rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G007.log |  | 1 | done_warn | 19 | 0.061 |
| G008 | gates | بوابات اللغة المتدرجة (إملاء ونحو وأسلوب) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/language_gates.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G008.log |  | 0 | done | 19 | 0.125 |
| G009 | gates | أصل نص كل واقعة (للفحص العكسي) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/ledger_source_excerpt.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G009.log |  | 0 | done | 19 | 0.065 |
| G010 | gates | بصمة النص قبل البناء | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/text_hash_guard.py" --date "$D" --stage record; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G010.log |  | 0 | done | 19 | 0.047 |
| G011 | gates | فحص ما قبل التشغيل | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/preflight_check.py" "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G011.log |  | 0 | done | 20 | 0.228 |
| G011H | gates | اشتقاق توزيع احتمالات الفرضيات والتحقق منه | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/hypothesis_distribution.py" --meta "$B/web/meta/$D.json" --write; rc=$?; [ $rc -eq 0 ] \|\| exit $rc; python3 "$B/tools/hypothesis_distribution.py" --meta "$B/web/meta/$D.json" --check; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G011H.log | web/meta/{date}.json | 0 | done | 19 | 0.092 |
| G012 | gates | مدقق التقرير (الواجهة) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/validate_report.py" "$B/web/meta/$D.json" --md "$B/reports/$D-sectioned.md"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G012.log |  | 0 | done | 19 | 0.096 |
| G013 | gates | بوابة الأسلوب | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_style.py" "$B/reports/$D-sectioned.md"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G013.log |  | 0 | done | 17 | 0.076 |
| G014 | gates | بوابة اللغة | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_language.py" "$B/reports/$D-sectioned.md"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G014.log |  | 0 | done | 17 | 0.04 |
| G015 | gates | بوابة إغلاق المكتبات | script | `bash -lc 'B="$PWD"; export B SITE; python3 validators/check_findings_closed.py --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G015.log |  | 0 | done | 17 | 0.386 |
| G016 | gates | ترابط المكتبات والمهارات | script | `bash -lc 'B="$PWD"; export B SITE; python3 validators/check_libraries_skills.py; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G016.log |  | 0 | done | 17 | 1.115 |
| G017 | gates | تماثل المهارات والمكتبات (مزامنة فورية) | script | `bash -lc 'B="$PWD"; export B SITE; bash tools/restore_skills.sh --check; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G017.log |  | 0 | done | 17 | 4.657 |
| G018 | gates | سلامة المهارات | script | `bash -lc 'B="$PWD"; export B SITE; python3 validators/check_skills_integrity.py; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G018.log |  | 0 | done | 17 | 0.038 |
| G018A | gates | سلامة مهارات المشروع عبر الأسطح | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_project_skills.py"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G018A.log |  | 0 | done | 17 | 0.119 |
| G019 | gates | بوابة الفهم (مرحلة $COMP_STAGE) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_comprehension.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G019.log |  | 0 | done | 17 | 0.052 |
| G020 | gates | بوابة قراءة الموقف وتحليل المؤشرات | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_intel.py" "$B/reports/$D-sectioned.md" "$B/web/meta/$D.json"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G020.log |  | 0 | done | 17 | 0.048 |
| G021 | gates | استخراج أهداف OFAC | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/ofac_targets_from_report.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G021.log |  | 0 | done | 17 | 0.046 |
| G022 | gates | فحص OFAC | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/ofac_screen.py" "$B/watchlist/ofac-targets.txt"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G022.log |  | 0 | done | 17 | 3.171 |
| G023 | gates | تغطية فحص العقوبات | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_ofac_coverage.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G023.log |  | 0 | done | 17 | 0.052 |
| G024 | gates | استعمال المكتبات (المعجم والبنك والفجوات) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_library_use.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G024.log |  | 1 | done_warn | 17 | 0.057 |
| G025 | gates | عدد المصادر (مصدر واحد) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_sources_count.py"; w=$?; if [ $w -gt 1 ]; then exit $w; fi; python3 "$B/validators/check_source_route_coverage.py" --date "$D"; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; exit ${w:-0}'` | cmd: test -s logs/runbook/{date}/G025.log |  | 0 | done | 17 | 1.153 |
| G026 | gates | قابلية النقل (مسارات) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_portable_paths.py"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G026.log |  | 0 | done | 17 | 0.161 |
| G028 | gates | حصاد الألفاظ الجديدة | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/harvest_terms.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G028.log |  | 0 | done | 17 | 1.328 |
| G030 | gates | فصل فضاءات الرموز MN-/EST- | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_code_spaces.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G030.log |  | 0 | done | 17 | 0.058 |
| G031 | gates | قاعدة النقاط في المصدر | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_points_rule.py" --md "$B/reports/$D-sectioned.md" --meta "$B/web/meta/$D.json"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G031.log |  | 1 | done_warn | 17 | 0.046 |
| G032 | gates | فاحص النقل بين الإصدارات | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_carryover.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G032.log |  | 0 | done | 17 | 0.067 |
| G033 | gates | اكتمال التشغيل (الأعطال المعروفة) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_run_completeness.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G033.log |  | 1 | done_warn | 17 | 0.071 |
| G034 | gates | عيوب الكتابة (الصياغة والترقيم) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_prose_defects.py" --md "$B/reports/$D-sectioned.md"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G034.log |  | 0 | done | 16 | 0.937 |
| G035 | gates | تسرّب المحتوى الداخلي إلى المتن | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_internal_leak.py" --md "$B/reports/$D-sectioned.md"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G035.log |  | 0 | done | 16 | 0.05 |
| G036 | gates | المفردات المبسطة (تنبيهي حتى الموافقة) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_vocabulary.py" --md "$B/reports/$D-sectioned.md"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G036.log |  | 0 | done | 16 | 0.112 |
| G044 | gates | السجل الحاكم للمفردات ومُولَّده | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/build_vocab_gate.py" --check && python3 "$B/tools/lexicon_wiring.py" --check && python3 "$B/validators/check_glossary_shape.py"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G044.log |  | 0 | done | 16 | 0.168 |
| G044B | gates | حارس سلسلة الاستبدال في المفردات (ك-479) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_vocab_chain.py"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G044B.log |  | 0 | done | 16 | 0.054 |
| G048 | gates | بوابة الإغلاق (الأعطال والاستثناءات) | script | `bash -lc 'B="$PWD"; export B; python3 "$B/validators/check_closure.py" --brain "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G048.log |  | 0 | done | 16 | 0.063 |
| G048A | gates | تغطية المصادر في دفتر الوقائع (اتحاد المصادر المسجّل) | script | `bash -lc 'B="$PWD"; export B; python3 "$B/validators/check_source_daily_coverage.py" --brain "$B" --date "$D" --days 30 --json-out "$B/logs/runbook/$D/G048A-coverage.json"; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/tests/test_source_coverage_transient.py"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G048A.log |  | 0 | done | 16 | 0.898 |
| G040 | gates | اختبارات المراجعة الثانية (أ · ب · ج · د · هـ · ز) | script | `bash -lc 'B="$PWD"; export B SITE; bash "$B/tests/test_review2.sh" "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G040.log |  | 0 | done | 16 | 2.67 |
| G041 | gates | اختبار انحدار المصلح (12→23) | script | `bash -lc 'B="$PWD"; export B SITE; bash "$B/tests/test_repair_regression.sh"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G041.log |  | 0 | done | 16 | 0.216 |
| G057 | gates | حارس اسم المصدر الحقيقي (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 -m pytest -p no:cacheprovider -q "$B/tests/test_source_naming_gate.py"; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/validators/check_source_naming.py" --root "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G057.log |  | 0 | done | 16 | 0.473 |
| G058 | gates | حارس تغطية الأيام والأدلة (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 -m pytest -p no:cacheprovider -q "$B/tests/test_day_coverage_gate.py"; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/validators/check_day_coverage.py" --root "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G058.log |  | 0 | done | 16 | 0.377 |
| G059 | gates | حارس مفردات الموقع وغياب area (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 -m pytest -p no:cacheprovider -q -k '"'"'not current_round'"'"' "$B/tests/test_area_absence.py" "$B/tests/test_non_spatial_term.py"; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/validators/check_area_vocabulary.py" --root "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G059.log |  | 0 | done | 16 | 0.778 |
| G060 | gates | حارس مخطط الدفتر وحقول الدليل (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_daily_events_schema.py" --all --brain "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G060.log |  | 0 | done | 16 | 0.098 |
| S085 | build | فحص جاهزية قنوات النشر قبل البناء | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/publish_channels.py preflight --date {date} --root "$B"; rc=$?; exit $rc'` | cmd: python3 -c import json,sys;d=json.load(open("logs/publish-channel-{date}.json"));c=d.get("channels",{});sys.exit(0 if set(c)=={"cloudflare-pages","raw-githack","raw.githubusercontent"} and any(v.get("state")=="ready" and v.get("presentation_eligible",True) for v in c.values()) else 1)؛ cmd: gre | logs/publish-channel-{date}.json | 0 | done | 16 | 0.359 |
| B004 | build | تحرير الأصل الإنجليزي اليومي من التقرير العربي (فشل مغلق) | agent | `prompt: runbook/prompts/write-en-master.md` | {"type": "file_exists", "path": "../site/sources/i18n/en/{date}-sectioned.en.md"}؛ cmd: python3 tools/validate_en_master.py --arabic reports/{date}-sectioned.md --english ../site/sources/i18n/en/{date}-sectioned.en.md | ../site/sources/i18n/en/{date}-sectioned.en.md | None | done | 2 | None |
| B004A | build | مزامنة الأصل الإنجليزي والمعجم إلى شجرة التشغيل (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/i18n_assets_sync.py" --sync --brain "$B" --site "$SITE" --date {date}'` | {"type": "file_exists", "path": "{site}/sources/i18n/en/{date}-sectioned.en.md"}؛ cmd: python3 tools/i18n_assets_sync.py --check --brain {brain} --site {site} --date {date} | {site}/sources/i18n/en/{date}-sectioned.en.md, {site}/sources/i18n/en/glossary.json | 0 | done | 15 | 0.075 |
| B005 | build | بوابة مُدخل الترجمة الإنجليزية قبل البناء (B004 المنتج · B009 المستهلك · فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; P="$SITE/sources/i18n/en/{date}-sectioned.en.md"; if [ ! -s "$P" ]; then printf '"'"'✘ مُدخل EN مفقود: %s\n'"'"' "$P"; exit 2; fi; python3 -c '"'"'from pathlib import Path; import sys; p=Path(sys.argv[1]); t=p.read_text(encoding="utf-8"); rows=sum(1 for l in t.splitlines() if l.strip().startswith("\|")); print(f"✔ مُدخل EN حاضر: {p}"); print(f"   lines={len(t.splitlines())} · table_rows={rows}"); raise SystemExit(0 if rows else 2)'"'"' "$P"; rc=$?; exit $rc'` | cmd: grep -q '✔ مُدخل EN حاضر:' logs/runbook/{date}/B005.log && grep -Eq 'table_rows=[1-9][0-9]*' logs/runbook/{date}/B005.log | logs/runbook/{date}/B005.log | 0 | done | 15 | 0.046 |
| B006 | build | بوابة عقد عدّادات بطاقة أهم الأخبار قبل البناء (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; (cd "$SITE" && python3 "$B/tools/sync_card_layers.py" --date "$D" && python3 "$B/tools/build_hero_kpis.py" --date "$D" --apply && python3 generator/sync_from_brain.py --date "$D") \|\| exit $?; printf '"'"'بوابة عقد عدّادات بطاقة أهم الأخبار — اختبار موجب وسالبان قبل البناء\n'"'"'; python3 -m unittest -v tests/test_card_counters.py tests/test_card_registry_pairs.py; rc=$?; printf '"'"'نتيجة بوابة العقد: rc=%s\n'"'"' "$rc"; exit $rc'` | cmd: grep -qE '^Ran [0-9]+ tests' logs/runbook/{date}/B006.log && grep -q '^OK$' logs/runbook/{date}/B006.log | logs/runbook/{date}/B006.log | 0 | done | 15 | 64.263 |
| B009 | build | اشتقاق الوحدات الإنجليزية من المتن الحاكم (النسخة الإنجليزية أصل) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$SITE/tests/test_b009_template_leak_guard.py" && bash "$B/tools/en_master_build.sh" {date} "$SITE" && python3 "$B/../skills/bilingual-master-direction-ops/scripts/verify_master_direction.py" --brain "$B" --site "$SITE" --date {date}'` | {"type": "file_exists", "path": "{site}/dist/reports/{date}.html"} |  | 0 | done | 8 | 65.388 |
| B010 | build | بناء الموقع من البيانات | script | `bash -lc 'B="$PWD"; export B SITE; cd "$SITE" && python3 "$B/tools/sync_card_layers.py" --date "$D" && python3 "$B/tools/build_hero_kpis.py" --date "$D" --apply && python3 generator/sync_from_brain.py --date {date} && python3 generator/build_site.py && python3 "$B/validators/check_card_counters.py" --date "$D" --dist-root "$SITE/dist" && python3 "$B/validators/check_kpi_layers.py" --date "$D" --dist-root "$SITE/dist" --brain "$B" && python3 "$B/validators/check_map_note_counts.py" --date "$D" --site "$SITE" && python3 "$B/tests/test_map_location_term.py" --date "$D" && python3 "$B/tests/test_map_cluster.py"; rc=$?; exit $rc'` | {"type": "file_exists", "path": "{site}/dist/reports/{date}.html"}؛ cmd: grep -q '✔ بطاقة الفروع الثلاثة: العناوين والعدادات والمراسي متطابقة عربيًا وإنجليزيًا' logs/runbook/{date}/B010.log |  | 0 | done | 8 | 129.568 |
| G049 | build | شريط نسب القطاعات بعد البناء (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_zone_strip.py" --date "$D" --brain "$B" --site "$SITE"; rc=$?; exit $rc'` | cmd: B="$PWD"; export B SITE; python3 "$B/validators/check_zone_strip.py" --date "$D" --brain "$B" --site "$SITE"; rc=$?; exit $rc | logs/runbook/{date}/G049.log | 0 | done | 8 | 0.063 |
| G052 | build | وضوح سطح الحاسوب: أحجام الخط والقص والفيض والتمرير | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_desktop_readability.py" --date "$D" --site "$SITE"; rc=$?; exit $rc'` | cmd: B="$PWD"; export B SITE; python3 "$B/validators/check_desktop_readability.py" --date "$D" --site "$SITE"; rc=$?; exit $rc | logs/runbook/{date}/G049.log | 0 | done | 8 | 6.425 |
| G050 | build | سطح سجل الأحداث ومخطط الدفتر وعقد البطاقة بعد البناء (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_daily_event_surface.py" --date "$D" --brain "$B" --site "$SITE" \|\| exit $?; python3 "$B/validators/check_daily_events_schema.py" --date "$D" --brain "$B" --site "$SITE" \|\| exit $?; python3 "$B/validators/check_event_card_contract.py" --date "$D" --brain "$B" --site "$SITE"; rc=$?; exit $rc'` | cmd: B="$PWD"; export B SITE; python3 "$B/validators/check_daily_event_surface.py" --date "$D" --brain "$B" --site "$SITE" // exit $?; python3 "$B/validators/check_daily_events_schema.py" --date "$D" --brain "$B" --site "$SITE" // exit $?; python3 "$B/validators/check_event_card_contract.py" --date  | logs/runbook/{date}/G050.log | 0 | done | 8 | 0.195 |
| G051 | build | بوابة روابط الوقائع — سند الربط ومعرّفه الموجود (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_event_links.py" --date "$D"'` | cmd: B="$PWD"; export B SITE; python3 "$B/validators/check_event_links.py" --date "$D" |  | 0 | done | 8 | 0.062 |
| G053 | build | بوابة حقول علاقة دفتر الوقائع والأسطح المبنية (فشل مغلق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_ledger_links.py" --date "$D" --brain "$B" --site "$SITE"'` | cmd: B="$PWD"; export B SITE; python3 "$B/validators/check_ledger_links.py" --date "$D" --brain "$B" --site "$SITE" |  | 0 | done | 8 | 0.183 |
| B020 | build | تصدير PDF المعتمد | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/export_report_assets.py --date {date} --only pdf; rc=$?; exit $rc'` | {"type": "min_bytes", "path": "{site}/dist/reports/pdf/{date}.pdf", "n": 100000} |  | 0 | skipped | 1 | None |
| B030 | build | بوابتا جودة الطباعة على PDF نفسه | script | `bash -lc 'B="$PWD"; export B SITE; python3 validators/check_pdf_format.py --pdf {site}/dist/reports/pdf/{date}.pdf && python3 validators/check_print_quality.py --pdf {site}/dist/reports/pdf/{date}.pdf --date {date}; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/B030.log |  | 0 | skipped | 1 | None |
| G047 | build | بطاقة القرار (لا إفراغ ولا رابط ميت) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_decision_card.py" --date "$D" --dist-root "$SITE/dist" && python3 "$B/validators/check_threat_consistency.py" --date "$D" --brain "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G047.log |  | 0 | done | 4 | 4.036 |
| G046 | build | سطح الإضافات (نقل الأقسام مرة واحدة) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_additions_surface.py" --date "$D" --site "$SITE"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G046.log |  | 0 | done | 4 | 0.051 |
| G045 | build | تغطية بوابة الأسلوب لكل سطح يقرأه القارئ | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/make_tg_digest.py" --date "$D" >/dev/null 2>&1 \|\| true; python3 "$B/validators/check_forbidden_surface_terms.py" --date "$D" --brain "$B" --site "$SITE"; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; python3 "$B/tools/audit_style_coverage.py" --date "$D" && python3 "$B/validators/check_surface_hygiene.py"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G045.log |  | 0 | done | 4 | 6.876 |
| B035 | build | خط الأساس الرسمي (virgin) — تنبيهي | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/check_baseline.py; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/B035.log |  | 1 | done_warn | 4 | 0.047 |
| B040 | build | نسخة Word طبق الأصل (بوابة المخرج 9 تمنع التسليم بدونها) | script | `bash -lc 'B="$PWD"; export B SITE; python3 tools/build_report_docx_exact.py --date {date}; rc=$?; exit $rc'` | cmd: ls reports/docx/*{date}*.docx >/dev/null 2>&1 |  | 0 | done | 4 | 5.148 |
| G005 | outputs | تطابق أرقام المصادر في كل المواضع | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/source_counts.py" --date "$D" --check; rc=$?; [ $rc -eq 0 ] \|\| exit $rc; python3 -m pytest -q tests/test_source_totals_governed.py tests/test_source_counts_idempotent.py tests/test_en_translator_deterministic.py; exit $?'` | cmd: test -s logs/runbook/{date}/G005.log |  | 1 | done_warn | 4 | 1.609 |
| G027 | outputs | الأرقام (0-9 لاتينية) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_numerals.py"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G027.log |  | 0 | done | 4 | 1.322 |
| G029 | outputs | سياسة الرموز في المخرجات | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_code_policy.py" "$SITE/dist"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G029.log |  | 1 | done_warn | 4 | 0.144 |
| G037 | outputs | بوابات المخرج العشر | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/qa_gates.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G037.log |  | 0 | done | 4 | 1.891 |
| G056 | finalize | بوابة ترجمة الشيفرة (صياغة بايثون) | script | `bash -lc 'B="$PWD"; export B; python3 "$B/validators/check_python_syntax.py"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G056.log |  | 0 | done | 3 | 0.932 |
| G055 | finalize | بوابة تغطية الربط الشامل | script | `bash -lc 'B="$PWD"; export B; python3 "$B/tools/binding_coverage.py" --json "logs/gate-$D/binding-coverage.json"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G055.log |  | 1 | done_warn | 3 | 0.236 |
| G054 | finalize | بوابة ربط الأرقام بمصادرها | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_number_bindings.py" --date "$D"; rc=$?; python3 "$B/validators/check_published_counters.py" --brain "$B" --date "$D"; rc2=$?; if [ $rc -eq 0 ] && [ $rc2 -ne 0 ]; then exit $rc2; fi; exit $rc'` | cmd: test -s logs/runbook/{date}/G054.log |  | 0 | done | 3 | 0.18 |
| G042 | finalize | تطابق النص المبني مع النص النهائي | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/text_hash_guard.py" --date "$D" --stage verify; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G042.log |  | 0 | done | 2 | 0.067 |
| G043 | finalize | سجل البوابات gate.json من سجل المحرّك | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/runbook.py" gate-json --date "$D" --through G042 --root "$B"; rc=$?; exit $rc'` | cmd: grep -q 'runbook-ledger' logs/gate-{date}/gate.json |  | 0 | done | 2 | 0.078 |
| G038 | finalize | كتابة العلامة بعد البوابة | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/write_mark.py" --date "$D" --stage final; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G038.log؛ {"type": "file_exists", "path": "logs/pipeline-{date}.json"}؛ cmd: grep -q 'العلامة (final)' logs/runbook/{date}/G038.log | logs/pipeline-{date}.json | 0 | done | 2 | 0.05 |
| G039 | finalize | مخطط العلامة الثابت | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_mark_schema.py" --date "$D"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G039.log |  | 0 | done | 2 | 0.049 |
| G061 | finalize | سياسة التسليم المتصل (قرار المالك: أ) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_delivery_policy.py" --root "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G061.log؛ cmd: grep -q '✔ سياسة التسليم المتصل:' logs/runbook/{date}/G061.log |  | 0 | done | 2 | 0.049 |
| G062 | finalize | دفتر القرارات (حالة كل قرار ودليله) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_decisions_registry.py" --root "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G062.log؛ cmd: grep -q '✔ دفتر القرارات:' logs/runbook/{date}/G062.log |  | 0 | done | 2 | 0.053 |
| G062R | finalize | توليد مرجع آلية العمل من المانيفست | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/build_workflow_reference.py" build --root "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G062R.log؛ cmd: grep -q 'مرجع-آلية-العمل.md' logs/runbook/{date}/G062R.log |  | 0 | done | 2 | 0.051 |
| G063 | finalize | مرجع آلية العمل المولَّد (بنود مرقّمة وسقف جهد مشتق) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/validators/check_reference_generated.py" --root "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G063.log؛ cmd: grep -q '✔ مرجع آلية العمل:' logs/runbook/{date}/G063.log |  | 0 | done | 2 | 0.069 |
| G064 | finalize | الانحدار التراكمي وأدوات البوابة المانعة | script | `bash -lc 'B="$PWD"; export B SITE; mkdir -p "$B/logs/runbook/{date}"; python3 "$B/tools/regression_gate.py" --root "$B" --until الكل --out "$B/logs/runbook/{date}/G064-regression.json" --share-dir "$B/logs/runbook/{date}"; rc=$?; [ $rc -eq 0 ] \|\| exit $rc; python3 - <<'"'"'PY'"'"' import pathlib ok = all("CMD_SHAPE_V1" in pathlib.Path(f).read_text(encoding="utf-8") for f in ("tools/runbook.py",)) print("CMD_SHAPE_V1: " + ("مرتبط" if ok else "غائب")) raise SystemExit(0 if ok else 2) PY'` | cmd: test -s logs/runbook/{date}/G064.log؛ cmd: grep -q '✔ الانحدار:' logs/runbook/{date}/G064.log |  | 0 | done | 4 | 79.11 |
| G065 | finalize | القياس البصري الحي (قصّ · توافق · مراسٍ · بطاقة القرار) | script | `bash -lc 'B="$PWD"; SITE="${SITE:-/home/ubuntu/seawatch}"; export B SITE; mkdir -p "$B/logs/runbook/{date}"; python3 "$B/tools/browser_measure.py" --root "$B" --site-root "$SITE/dist" --check overflow --check console --check anchor --check decision --check readiness --soft readiness --out "$B/logs/runbook/{date}/G065-measure.json" --reuse "$B/logs/runbook/{date}/shared-measure-ar.json"'` | cmd: test -s logs/runbook/{date}/G065.log؛ cmd: grep -q '✔ القياس البصري' logs/runbook/{date}/G065.log |  | 0 | done | 1 | 0.056 |
| G066 | finalize | تدقيق صلابة البوابات (استشاري مع حفظ JSON وبصمة) | script | `bash -lc 'B="$PWD"; mkdir -p "$B/audit/measurements"; OUT="$B/audit/measurements/gate-audit-{date}.json"; python3 "skills/gate-lifecycle-ops/references/legacy/gate-strictness-hardening-ops/scripts/gate_audit.py" --root . --json > "$OUT"; rc=$?; sha256sum "$OUT" > "$OUT.sha256"; echo "gate_audit rc=$rc"; cat "$OUT.sha256"; cat "$OUT"; exit $rc'` | cmd: test -s audit/measurements/gate-audit-{date}.json؛ cmd: test -s audit/measurements/gate-audit-{date}.json.sha256 | audit/measurements/gate-audit-{date}.json, audit/measurements/gate-audit-{date}.json.sha256 | 1 | done_warn | 1 | 1.095 |
| G068 | finalize | عقد مهارة القياس الحي وميزانية الاستثناءات | script | `bash -lc 'B="$PWD"; export B; python3 "$B/tests/test_live_parity_skill_contract.py" \|\| exit 2; python3 "$B/tools/triage_closure_exceptions.py" --root "$B" --write \|\| exit 2; python3 "$B/validators/check_exceptions_burndown.py" --root "$B"; rc=$?; exit $rc'` | cmd: test -s logs/runbook/{date}/G068.log |  | 0 | done | 1 | 0.451 |
| G067 | finalize | ميزانية أداء البوابات (قياس صريح وفشل مغلق) | script | `bash -lc 'B="$PWD"; mkdir -p "$B/audit/measurements"; OUT="$B/audit/measurements/perf-budget-{date}.json"; python3 "$B/tools/perf_budget.py" --root "$B" --date "$D" --budget "$B/runbook/perf-budget.json" --out "$OUT"; rc=$?; sha256sum "$OUT" > "$OUT.sha256"; cat "$OUT.sha256"; exit $rc'` | cmd: test -s audit/measurements/perf-budget-{date}.json؛ cmd: test -s audit/measurements/perf-budget-{date}.json.sha256؛ cmd: grep -q '"status": "pass"' audit/measurements/perf-budget-{date}.json | audit/measurements/perf-budget-{date}.json, audit/measurements/perf-budget-{date}.json.sha256 | 0 | done | 1 | 0.069 |
| G069 | finalize | الحكم النهائي من سجل المحرّك (بوابة واحدة بلا إعادة final_gate.sh) | script | `bash -lc 'B="$PWD"; export B SITE; python3 "$B/tools/runbook.py" gate-json --date "$D" --through G067 --final --root "$B" \|\| exit 2; python3 "$B/tools/write_mark.py" --date "$D" --stage final \|\| exit 2; python3 "$B/validators/check_mark_schema.py" --date "$D" \|\| exit 2; python3 "$B/tools/publish_verdict.py" --date "$D" --brain "$B"; v=$?; case $v in 0) exit 0;; 3) exit 1;; *) exit 2;; esac'` | cmd: grep -q '"stage": "final"' logs/gate-{date}/gate.json | logs/gate-{date}/gate.json, logs/pipeline-{date}.json | 1 | done_warn | 1 | 0.216 |
| D005 | deliver | تحديث النسخة الاحتياطية قبل النشر (شرط بوابة ما قبل التشغيل) | script | `bash -lc 'B="${B:-$PWD}"; REPO="$(git -C "$B" rev-parse --show-toplevel 2>/dev/null)"; export B SITE REPO BACKUP_REPO_DIR="$REPO"; B="$PWD"; export B SITE; bash tools/github_backup.sh && python3 validators/check_backup_parity.py --mode strict; rc=$?; exit $rc'` | cmd: test -s "$B/logs/runbook/{date}/D005.log" && grep -q 'parity' "$B/logs/runbook/{date}/D005.log" // true |  | 2 | failed | 1 | 0.931 |


## 3.1 الحالة النهائية للدفتر (من jsonl)
- done: 96 · done_warn: 11 · failed: 3 · skipped: 2.
- done_warn: S020 (3 تشغيلات، تعذر كونا)، G007، G024، G031، G033، B035، G005، G029، G055، G066، G069.
- failed: S080 وS090 (اختياريان بالنموذج، المانيفست يسمح بالمتابعة، سبب الفشل من سجلهما: «Built-in LLM runtime is not ready. Run the script with manus-node» أي بيئة Manus غير متصلة)، وD005 (rc 2، خاص بـManus).
- skipped: B020 وB030.

## 3.2 الإعادات الآلية
- `brain/logs/auto-heal/2026-11-28.jsonl` (3 أسطر) و`.json` و`.md`: سجل الإصلاح الذاتي لذلك اليوم. القاعدة المطبقة والتفاصيل داخل الملفات نفسها؛ لا أضيف عليها شيئًا من الذاكرة.
- الإعادات اليدوية بـ`--redo` مثبتة في عدد التشغيلات بالجدول (مثل G001 26 مرة، S080/S090 32 مرة).

# 4. شرح المشروع
مركز الوعي بالمجال البحري (Seawatch/MDA) لفهد الدوسري، البحرية الملكية البحرينية. «العقل» `brain-marine-news` على الخادم (غير موجود في هذا المستودع) فيه الأقسام والملاحق والدفتر التراكمي. هذا المستودع فيه `brain/` (الخط والأدوات والمدققات) و`site/` (المولّد والموقع). ينتج تقريرًا يوميًا عربيًا مع أصل إنجليزي، ويُنشر على `mda-bh.pages.dev` (مشروع Cloudflare Pages على فرع main في `seawatch-live`). الموقع الدائم في `sources/site.json` على الخادم (غير موجود هنا).

# 5. كيفية التشغيل
- كاتب التقرير: Claude، النموذج `claude-sonnet-5-5` (من `get_session`: `session_context.model` و`external_metadata.last_served_model` كلاهما `claude-sonnet-5-5`)، داخل جلسة Claude Code السحابية.
- لم يكتب أي نموذج مجاني. خطوة G007 (التحرير اللغوي الآلي) سجلها يقول «النموذج: gpt-5-mini» لكنه «عميل النموذج غير مثبّت … لم يُجرَ التحرير الآلي»، أي لم يعمل.
- الخطوات الاختيارية بالنموذج S080 وS090 فشلتا (Built-in LLM runtime is not ready؛ يتطلب manus-node)، ومضى التشغيل.
- البيئة: `env_01YDjG6GKwqnAzqv31hH3rsu` (شبكة Full)، ومفتاح Cloudflare (Pages:Edit) يحقنه الوكيل للمضيف `api.cloudflare.com`.

# 6. الخطوات للتشغيل
هذه خطوات ما نُفِّذ فعلًا بالترتيب، وليس إرشادًا عامًا:
1. تجهيز البيئة (`cloud_env_prep.sh` عبر خطوات المحرّك)، وتحقق أن `/home/ubuntu/mda-marine-system` موجود.
2. قبل `browser_fetch.py`: `rm -f /tmp/.X11-unix/X99 /tmp/.X99-lock` (فخ Xvfb قديم).
3. جمع التغذيات وفحصها (S020): المصدر 27 (كونا) تعذّر بثلاثة مسارات؛ المقيس `feeds: checked 60, ok 59, failed 1` في `brain/logs/pipeline-2026-11-28.json`.
4. كتابة دفتر 27 الاستعادي (`brain/cumulative-2026/daily/2026-11-27.json`) قبل S070.
5. كتابة المتن (W010) والدفتر (W030) والواجهة (W020) والأصل الإنجليزي (B004) ثم `runbook.py complete` لكل منها.
6. معالجة B006 بإضافة مفتاح IMO إلى `site/sources/i18n/en/glossary.json`، وقيمتها حرفية للرموز اللاتينية والأرقام بلا عربي.
7. مواجهة G064 ب-03: رابط UKMTO تذبذب بحسب عرض الشاشة (نجح بإعادة عادية)، ورابط Mehr أخذ استثناءً مؤرخًا (§8.3).
8. بعد G069: `cd brain && bash tests/run_checks.sh` (108 / 0).
9. `python3 tools/cloud_deliver.py --date 2026-11-28 --push`.
10. تلغرام بعد النشر وبموافقة مكتوبة: `ensure_devserver.sh 3000` ثم `python3 tools/runbook.py run --only G011 --redo G011` ثم `bash tools/publish_site.sh --telegram 2026-11-28`.
11. قبل الإيداع: `git restore --staged` لما يخص `logs/runbook/D/` (أكثر من 1400 ملف سجل محاولات) مع إبقاء `timings.md`.

# 7. البوابات

## 7.1 نتيجة بوابات اليوم (من `brain/logs/gate-verdict-2026-11-28.json`)
| المعرّف | العنوان | الحالة | rc | الوقت |
|---|---|---|---|---|
| G000 | لقطة الأصول الحاكمة وإلحاق السجل قبل البوابات | سليم | 0 | 2026-11-28T10:29:51Z |
| G000A | بوابة الأصول الحاكمة — ledger والمرآة (فشل مغلق) | سليم | 0 | 2026-11-28T10:29:58Z |
| G000B | مالك أدوات التشغيل المحكمة والمراقب | سليم | 0 | 2026-11-28T10:29:58Z |
| G000C | اختبارات التشغيل داخل الحاوية المحكمة | سليم | 0 | 2026-11-28T10:30:13Z |
| G000C2 | توليد المعجم المشتق آليًا (إلزامي قبل التحقق) | سليم | 0 | 2026-11-28T10:30:14Z |
| G000D | اتساق المعجم المشتق (مصدر واحد) | سليم | 0 | 2026-11-28T10:30:14Z |
| G001 | اختبارات البوابات (tests) | سليم | 0 | 2026-11-28T10:32:02Z |
| G002 | تنظيف المحتوى الداخلي | سليم | 0 | 2026-11-28T10:32:02Z |
| G003 | دمج بنك التعريفات | سليم | 0 | 2026-11-28T10:32:03Z |
| G004 | أرقام المصادر (معتمدة/مفحوصة/ناجحة) | سليم | 0 | 2026-11-28T10:32:03Z |
| G005 | تطابق أرقام المصادر في كل المواضع | تحذير | 1 | 2026-11-28T10:37:17Z |
| G006 | إصلاح الصياغة الآلي (خطوة واحدة) | سليم | 0 | 2026-11-28T10:32:03Z |
| G007 | تحرير لغوي آلي (قبل/بعد لكل قسم) | تحذير | 1 | 2026-11-28T10:32:03Z |
| G008 | بوابات اللغة المتدرجة (إملاء ونحو وأسلوب) | سليم | 0 | 2026-11-28T10:32:03Z |
| G009 | أصل نص كل واقعة (للفحص العكسي) | سليم | 0 | 2026-11-28T10:32:03Z |
| G010 | بصمة النص قبل البناء | سليم | 0 | 2026-11-28T10:32:03Z |
| G011 | فحص ما قبل التشغيل | سليم | 0 | 2026-11-28T10:45:03Z |
| G011H | اشتقاق توزيع احتمالات الفرضيات والتحقق منه | سليم | 0 | 2026-11-28T10:32:04Z |
| G012 | مدقق التقرير (الواجهة) | سليم | 0 | 2026-11-28T10:32:04Z |
| G013 | بوابة الأسلوب | سليم | 0 | 2026-11-28T10:32:04Z |
| G014 | بوابة اللغة | سليم | 0 | 2026-11-28T10:32:04Z |
| G015 | بوابة إغلاق المكتبات | سليم | 0 | 2026-11-28T10:32:04Z |
| G016 | ترابط المكتبات والمهارات | سليم | 0 | 2026-11-28T10:32:06Z |
| G017 | تماثل المهارات والمكتبات (مزامنة فورية) | سليم | 0 | 2026-11-28T10:32:10Z |
| G018 | سلامة المهارات | سليم | 0 | 2026-11-28T10:32:10Z |
| G018A | سلامة مهارات المشروع عبر الأسطح | سليم | 0 | 2026-11-28T10:32:11Z |
| G019 | بوابة الفهم (مرحلة $COMP_STAGE) | سليم | 0 | 2026-11-28T10:32:11Z |
| G020 | بوابة قراءة الموقف وتحليل المؤشرات | سليم | 0 | 2026-11-28T10:32:11Z |
| G021 | استخراج أهداف OFAC | سليم | 0 | 2026-11-28T10:32:11Z |
| G022 | فحص OFAC | سليم | 0 | 2026-11-28T10:32:14Z |
| G023 | تغطية فحص العقوبات | سليم | 0 | 2026-11-28T10:32:14Z |
| G024 | استعمال المكتبات (المعجم والبنك والفجوات) | تحذير | 1 | 2026-11-28T10:32:14Z |
| G025 | عدد المصادر (مصدر واحد) | سليم | 0 | 2026-11-28T10:32:15Z |
| G026 | قابلية النقل (مسارات) | سليم | 0 | 2026-11-28T10:32:16Z |
| G027 | الأرقام (0-9 لاتينية) | سليم | 0 | 2026-11-28T10:37:18Z |
| G028 | حصاد الألفاظ الجديدة | سليم | 0 | 2026-11-28T10:32:17Z |
| G029 | سياسة الرموز في المخرجات | تحذير | 1 | 2026-11-28T10:37:18Z |
| G030 | فصل فضاءات الرموز MN-/EST- | سليم | 0 | 2026-11-28T10:32:17Z |
| G031 | قاعدة النقاط في المصدر | تحذير | 1 | 2026-11-28T10:32:17Z |
| G032 | فاحص النقل بين الإصدارات | سليم | 0 | 2026-11-28T10:32:17Z |
| G033 | اكتمال التشغيل (الأعطال المعروفة) | تحذير | 1 | 2026-11-28T10:32:17Z |
| G034 | عيوب الكتابة (الصياغة والترقيم) | سليم | 0 | 2026-11-28T10:32:18Z |
| G035 | تسرّب المحتوى الداخلي إلى المتن | سليم | 0 | 2026-11-28T10:32:18Z |
| G036 | المفردات المبسطة (تنبيهي حتى الموافقة) | سليم | 0 | 2026-11-28T10:32:19Z |
| G037 | بوابات المخرج العشر | سليم | 0 | 2026-11-28T10:37:20Z |
| G038 | كتابة العلامة بعد البوابة | سليم | 0 | 2026-11-28T10:37:22Z |
| G039 | مخطط العلامة الثابت | سليم | 0 | 2026-11-28T10:37:22Z |
| G040 | اختبارات المراجعة الثانية (أ · ب · ج · د · هـ · ز) | سليم | 0 | 2026-11-28T10:32:23Z |
| G041 | اختبار انحدار المصلح (12→23) | سليم | 0 | 2026-11-28T10:32:23Z |
| G042 | تطابق النص المبني مع النص النهائي | سليم | 0 | 2026-11-28T10:37:22Z |
| G043 | سجل البوابات gate.json من سجل المحرّك | سليم | 0 | 2026-11-28T10:37:22Z |
| G044 | السجل الحاكم للمفردات ومُولَّده | سليم | 0 | 2026-11-28T10:32:19Z |
| G044B | حارس سلسلة الاستبدال في المفردات (ك-479) | سليم | 0 | 2026-11-28T10:32:19Z |
| G045 | تغطية بوابة الأسلوب لكل سطح يقرأه القارئ | سليم | 0 | 2026-11-28T10:37:10Z |
| G046 | سطح الإضافات (نقل الأقسام مرة واحدة) | سليم | 0 | 2026-11-28T10:37:03Z |
| G047 | بطاقة القرار (لا إفراغ ولا رابط ميت) | سليم | 0 | 2026-11-28T10:37:03Z |
| G048 | بوابة الإغلاق (الأعطال والاستثناءات) | سليم | 0 | 2026-11-28T10:32:19Z |
| G048A | تغطية المصادر في دفتر الوقائع (اتحاد المصادر المسجّل) | سليم | 0 | 2026-11-28T10:32:20Z |
| G049 | شريط نسب القطاعات بعد البناء (فشل مغلق) | سليم | 0 | 2026-11-28T10:36:45Z |
| G050 | سطح سجل الأحداث ومخطط الدفتر وعقد البطاقة بعد البناء (فشل مغلق) | سليم | 0 | 2026-11-28T10:36:58Z |
| G051 | بوابة روابط الوقائع — سند الربط ومعرّفه الموجود (فشل مغلق) | سليم | 0 | 2026-11-28T10:36:59Z |
| G052 | وضوح سطح الحاسوب: أحجام الخط والقص والفيض والتمرير | سليم | 0 | 2026-11-28T10:36:58Z |
| G053 | بوابة حقول علاقة دفتر الوقائع والأسطح المبنية (فشل مغلق) | سليم | 0 | 2026-11-28T10:36:59Z |
| G054 | بوابة ربط الأرقام بمصادرها | سليم | 0 | 2026-11-28T10:37:22Z |
| G055 | بوابة تغطية الربط الشامل | تحذير | 1 | 2026-11-28T10:37:22Z |
| G056 | بوابة ترجمة الشيفرة (صياغة بايثون) | سليم | 0 | 2026-11-28T10:37:21Z |
| G057 | حارس اسم المصدر الحقيقي (فشل مغلق) | سليم | 0 | 2026-11-28T10:32:23Z |
| G058 | حارس تغطية الأيام والأدلة (فشل مغلق) | سليم | 0 | 2026-11-28T10:32:24Z |
| G059 | حارس مفردات الموقع وغياب area (فشل مغلق) | سليم | 0 | 2026-11-28T10:32:25Z |
| G060 | حارس مخطط الدفتر وحقول الدليل (فشل مغلق) | سليم | 0 | 2026-11-28T10:32:25Z |
| G061 | سياسة التسليم المتصل (قرار المالك: أ) | سليم | 0 | 2026-11-28T10:37:22Z |
| G062 | دفتر القرارات (حالة كل قرار ودليله) | سليم | 0 | 2026-11-28T10:37:23Z |
| G062R | توليد مرجع آلية العمل من المانيفست | سليم | 0 | 2026-11-28T10:37:23Z |
| G063 | مرجع آلية العمل المولَّد (بنود مرقّمة وسقف جهد مشتق) | سليم | 0 | 2026-11-28T10:37:23Z |
| G064 | الانحدار التراكمي وأدوات البوابة المانعة | سليم | 0 | 2026-11-28T10:42:04Z |
| G065 | القياس البصري الحي (قصّ · توافق · مراسٍ · بطاقة القرار) | سليم | 0 | 2026-11-28T10:42:04Z |
| G066 | تدقيق صلابة البوابات (استشاري مع حفظ JSON وبصمة) | تحذير | 1 | 2026-11-28T10:42:06Z |
| G067 | ميزانية أداء البوابات (قياس صريح وفشل مغلق) | سليم | 0 | 2026-11-28T10:42:06Z |
| G068 | عقد مهارة القياس الحي وميزانية الاستثناءات | سليم | 0 | 2026-11-28T10:42:06Z |
| G069 | الحكم النهائي من سجل المحرّك (بوابة واحدة بلا إعادة final_gate.sh) | تحذير | 1 | 2026-11-28T10:42:06Z |


## 7.2 نص gate.json وgate-verdict (مرجع)
- `brain/logs/gate-2026-11-28/gate.json`: `status: warn`, `exit_code: 1`, `stage: final`, `finished_utc: 2026-11-28T10:42:06Z`، المصدر `runbook-ledger`، SHA-256 عند الإيداع: `b1f4f527111dc1ea5fc90272c9a19a790a76288a478336c20737f3b3cd769acf` (15497 بايت).
- `brain/logs/gate-verdict-2026-11-28.json`: SHA-256 `98dbb5dda95363b2dbda46507e550154269392ec81a99602e34b59d0c94eb2e7` (10205 بايت)، 80 بوابة؛ التحذيرات التسع: G005 وG007 وG024 وG029 وG031 وG033 وG055 وG066 وG069 (rc 1 = done_warn، لا مانعة).
- أسباب التحذيرات من آخر أسطر سجلاتها: G005 «3 failed, 6 passed» في `tests/test_source_counts_idempotent.py`؛ G007 عميل النموذج غير مثبّت؛ G024 «4 بندًا (لا يمنع النشر)»؛ G029 «39 صفحة مخالفة» (صفحات قديمة)؛ G031 «5 تحذير» (تعدادات في فقرات)؛ G033 كونا بإعلان المالك؛ G055 «15 يتيمًا»؛ G066 تدقيق الصلابة؛ G069 «حكم النشر: منقوص مُفصح (رمز 3) · النشر مسموح».
- عدد المصادر في G069: 62/60/59 (يُقرأ من بيانات الإصدار لا من رقم مكتوب).

## 7.3 بوابات/خطوات لم تُستدعَ ولماذا
| الخطوة | سبب عدم التشغيل |
|---|---|
| D010, D020, D021, D016 (نشر قناتين/تحقق/Manus) | مسار Manus؛ النشر تم عبر `cloud_deliver.py` |
| D030, D031, D032, D033 (تلغرام عبر المحرّك) | الإرسال تم بالمسار الصريح `publish_site.sh --telegram` بموافقة فهد؛ D030 يتوقف دائمًا في السحابة |
| D035, D036, D040, D045, D050, D060, D070, D071 | صيانة/نسخ احتياطي خاصة بخادم Manus أو لاحقة للتسليم |
| Q010, Q012, Q015, Q020 | أسبوعية/ربع سنوية، ليست جزءًا من اليوم |
| D005 | جرى وفشل rc 2 (Manus فقط)، والحكم لـG069 |

# 8. الحراس
الاستثناءات كما نُفِّذت يوم 28 نوفمبر، كلها بقرار من فهد على بطاقة قرار:

## 8.1 دفتر 27 الاستعادي
- القرار: «كتابة تقرير 27 أولًا» (بطاقة، 07:16Z).
- الملف: `brain/cumulative-2026/daily/2026-11-27.json` (SHA-256 `c251cb933467c67e0758f69a6caa3824d8f8bedc171dd4a3b8b7e59a39f97106`، 5152 بايت)، صفّان `MN-2026-11-27-01` (سنتكوم، Pacific Archer) و`MN-2026-11-27-02` (UKMTO-224-26)، `retrospective: true`.
- السبب: غيابه يمنع S070 (دمج دفتر اليوم).

## 8.2 استثناء كونا
- القرار: «استثناء حتى 5 ديسمبر» (بطاقة، 08:02Z).
- الملف: `brain/appendices/known-faults.json`، المعرّف `owner-declared-2026-11-28-kuna`، `since: 2026-11-28`، `expires: 2026-12-05`، `max_items: 1`، `fault_ref: قرار المالك 2026-11-28`.
- العلاج الجذري المطلوب: مستخرج لصفحة كونا (لم يُنفَّذ).

## 8.3 تنازل مهر عن رابط الدليل (يوم واحد)
- القرار: «استثناء مهر اليوم» (بطاقة، 10:28Z).
- الملف: `brain/appendices/anchor-waivers.json` (SHA-256 `ca2772c572d215ee7be7cd91bff8a6dbe26b68e0a4352493757a87cab6194c23`، 409 بايت). الرابط: `https://en.mehrnews.com/news/249728/Oil-tanker-strikes-mine-in-south-of-Strait-of-Hormuz`، التاريخ 2026-11-28، `approved_by: فهد الدوسري، بطاقة قرار 2026-11-28`.
- التنفيذ: `owner_waiver()` في `brain/tools/browser_measure.py` (يمرّر فقط إن طابق الرابط بلا الجزء والتاريخ)، والاختبار `brain/tests/test_owner_anchor_waiver.py` (3 حالات).

## 8.4 المعجم الإنجليزي الرئيسي
- الملف: `site/sources/i18n/en/glossary.json` (نحو 70 مفتاحًا جديدًا أضيفت لهذا اليوم). القاعدة: المفتاح هو النص العربي الكامل، والقيمة الإنجليزية تحمل الرموز اللاتينية والأرقام حرفيًا بلا عربي، ومفاتيح `additions.html` من `en_missing_report.collect(date, Path(dist/additions.html))` لا من سطر الأوامر.
- الأصل الإنجليزي: `site/sources/i18n/en/2026-11-28-sectioned.en.md` (163 سطرًا).

## 8.5 حراس المانيفست التي مرّت
G000A (الأصول الحاكمة، فشل مغلق)، G044B (سلسلة الاستبدال في المفردات)، G054 (ربط الأرقام بمصادرها)، G057 (اسم المصدر الحقيقي)، G058 (تغطية الأيام والأدلة)، G059 (مفردات الموقع وغياب area)، G060 (مخطط الدفتر وحقول الدليل)، G061 (سياسة التسليم المتصل)، S071 (استمرارية الدفتر)، وكلها rc 0 في الدفتر.

## 8.6 فخاخ مثبتة يوم التشغيل
- G053: سلسلة من حلقتين بالمرجع الرسمي نفسه يعطيها `derive_event_links.py` الحقلين `parent_id` و`update_of` معًا فيرفضها G053؛ المعالجة المطبقة: عناوين متمايزة وبلا رقم التنبيه، والنتيجة أن حادثتين (UKMTO-224-26 وإعلان سنتكوم) تُحسبان في دفتري 27 و28 معًا (مفصح في CHANGELOG).
- G054: العدد التاريخي لـIMO (138) لا يظهر في المتن ولا في meta؛ الصياغة المطبقة «ارتفع العدد 8 عن تقرير 26/11» (`brain/web/meta/2026-11-28.json` السطر 165).
- D005: يتوقف دائمًا، والحكم من G069.

# 9. الربط
- مستودع الشيفرة: `fahadaldoseri/mda-marine-system` (فرع main بعد PR 677)، والنشر: `fahadaldoseri/seawatch-live` فرع main ← Cloudflare Pages ← `mda-bh.pages.dev`.
- مستودعات أخرى في النطاق: `seawatch-site` و`seawatch-web` و`seawatch-brain` و`seawatch-replica-build` و`mda-marine-system-independent` (لم تُلمس في هذا التشغيل).
- Telegram: البوت `@MDA_BH_bot`، محادثة فهد الخاصة. الأسرار بأسمائها في §SECRETS من الرد، لا هنا.
- Cloudflare: مفتاح Pages:Edit مضاف كسر شبكي لبيئة SeaWatch (Bearer للمضيف `api.cloudflare.com`).
- سير العمل: `.github/workflows/daily.yml` (على main: مداخل date وpublish وagent_steps (الافتراضي 8) وresume؛ مجموعة concurrency `daily`، المهلة 140 دقيقة؛ بلا cron). وقت الإيداع `ebdf7312` كانت نسخته غير هذه (SHA في §13).

# 10. الأوامر والتعليمات

## 10.1 أوامر نُفِّذت (من السجل/الذاكرة؛ ما لم أجد نصه الحرفي ذكرتُه كذلك)
1. `rm -f /tmp/.X11-unix/X99 /tmp/.X99-lock` — قبل المتصفح الآلي.
2. `python3 tools/runbook.py run` (من `brain/`)، ثم `python3 tools/runbook.py complete --step <ID>` بعد كتابة كل خطوة وكيلية: النص الحرفي لكل استدعاء غير موثق خارج `brain/logs/runbook/2026-11-28.jsonl` (حقل `outputs`)؛ ملفات `<STEP>.log` غير موجودة في الإيداع.
3. `python3 tools/runbook.py run --only <ID> --redo <ID>` — لإعادة خطوات منفردة (G001 وG011 وB006 وG064 ونحوها).
4. `bash tests/run_checks.sh` — «نجح: 108 · فشل: 0».
5. `python3 tools/cloud_deliver.py --date 2026-11-28 --push`.
6. `bash tools/ensure_devserver.sh 3000` ثم `python3 tools/runbook.py run --only G011 --redo G011` ثم `bash tools/publish_site.sh --telegram 2026-11-28`.
7. دمج PR 677 بعد موافقة فهد المكتوبة «أوافق على دمج PR 677».

## 10.2 أوامر فهد الدائمة
- لا نشر ولا تلغرام إلا بأمر مكتوب صريح في تلك المرة.
- استمرارية النشر اليومي إلزامية؛ كل تعديل يُقيَّم بأثره عليها.
- أسلوب الغائب في «الإجراء المطلوب»: «رفع التأهب عند عبور مضيق هرمز» لا «ارفعوا التأهب».
- أي سؤال لفهد ببطاقة قرار بخيارات جاهزة.
- لا تُطبع الأسرار.

## 10.3 ما أُلغي وما حلّ محله
- أُلغي الإرسال اليومي الآلي لتلغرام (الخطوة D030) في هذا التشغيل؛ حلّ محله إرسال واحد يدوي بعد النشر والتحقق وبموافقة مكتوبة (الخطوة 10.1 البند 6).
- أُلغي cron 04:40 على main بالإيداع `a214ac7` (أمر فهد)، ولا يُعاد.

## 10.4 ما يُمنع على المستلم
- إعادة cron أو تشغيل daily أو لمس main إلا بأمر فهد.
- النشر أو إرسال تلغرام بلا أمر مكتوب.
- الاستثناء من أي بوابة أو تعديلها أو تعديل حارس بلا موافقة مكتوبة.
- إضافة خطوة أو «تحسين» غير موثق هنا.
- نقل أي سر إلى مخرج أو مستودع.
- تعديل `handover/grok-2026-11-28` أو إعادة كتابة تاريخ main.

# 11. كل شيء لازم للسيطرة
- القراءة الأولى: `CLAUDE.md` (الجذر `brain/` أو المستودع) و`brain/runbook/runbook.json` و`brain/docs/runbook.md`.
- الحكم: `brain/logs/gate-verdict-2026-11-28.json` ثم `brain/logs/pipeline-2026-11-28.json` ثم `brain/logs/deliver-2026-11-28.json`.
- الدفتر: `brain/logs/runbook/2026-11-28.jsonl` و`timings.md` (32 سطرًا).
- الدفتر التراكمي: `brain/cumulative-2026/event-ledger-master.json` وملفات `daily/`.
- الملاحق: `brain/appendices/known-faults.json` و`anchor-waivers.json` و`incident-id-map.json` و`event-code-map.json` و`estimate-code-map.json` و`zone-registry.json` و`area-coordinates.json`.
- `migration-gaps.json`: موجود في `brain/cumulative-2026/migration-gaps.json` (لم يكن فيه شيء متعلق بـ27 عند إيداعي).
- الذاكرة: ملفات `team/silo` (مثال: `seawatch-run-2026-11-28-gotchas.md`).
- المهارات الثلاث: `seawatch-daily-run` و`seawatch-geo-style-guide` و`seawatch-blocked-sources-registry`.

الوقائع الأربع لهذا اليوم (من `brain/cumulative-2026/daily/2026-11-28.json`، SHA-256 `57b382cd88d7fd02d3d9815a2bf5b808be7b6a7b60937504b550faf62b8fca6b`، 7625 بايت):
| الرمز | الصنف | المنطقة | المصدر | المرجع الرسمي | درجة الإثبات |
|---|---|---|---|---|---|
| `MN-2026-11-28-01` | بيان رسمي | خليج عُمان | القيادة المركزية الأمريكية (DVIDS 580348) | لا يوجد | نص رسمي كامل |
| `MN-2026-11-28-02` | تنبيه رسمي | خليج عُمان | UKMTO — التحذيرات 2026 | UKMTO-224-26 | بلاغ رسمي غير مفصَّل |
| `MN-2026-11-28-03` | نقل إعلامي رسمي إيراني | مضيق هرمز | Mehr — العربي | لا يوجد | غير مؤكد من طرف واحد |
| `MN-2026-11-28-04` | نقل مهني | المنطقة كاملة | TradeWinds | لا يوجد | غير مؤكد بانتظار بيان رسمي |

# 12. تسليم السيطرة
عشرون بندًا، لكل بند أمر فحص ونتيجة متوقعة (من جذر المستودع ما لم يُذكر `brain/`):

| # | البند | أمر الفحص | المتوقع |
|---|---|---|---|
| 1 | فحوص المستودع | `cd brain && bash tests/run_checks.sh` | «نجح: 108 · فشل: 0» وrc=0 (قد يتغير العدد بتغير الاختبارات) |
| 2 | حكم النشر | `python3 -c "import json;print(json.load(open('brain/logs/deliver-2026-11-28.json'))['verdict']['verdict'])"` | `3` |
| 3 | بصمة المتن | `sha256sum brain/reports/2026-11-28-sectioned.md` | `2b4f78a4…509d5` |
| 4 | الدفتر لا يزال 1435 سطرًا | `wc -l brain/logs/runbook/2026-11-28.jsonl` | `1435` |
| 5 | G069 | `grep -c G069 brain/logs/runbook/2026-11-28.jsonl` | أكبر من 0 والحالة done_warn |
| 6 | الصفحة العربية حية | `curl -s -o /dev/null -w '%{http_code}' https://mda-bh.pages.dev/reports/2026-11-28` | `200` |
| 7 | الصفحة الإنجليزية حية | `curl -s -o /dev/null -w '%{http_code}' https://mda-bh.pages.dev/reports/en/2026-11-28` | `200` |
| 8 | إيداع النشر | `git ls-remote https://github.com/fahadaldoseri/seawatch-live refs/heads/main` | يحتوي `6c4530d` أو إيداعًا لاحقًا بأمر فهد |
| 9 | main يحتوي دمجي | `git merge-base --is-ancestor ebdf7312 origin/main && echo yes` | `yes` |
| 10 | بلا cron | `grep -n "cron" .github/workflows/daily.yml` | لا مطابقة |
| 11 | بلا أسرار في المستودع | `cd brain && python3 validators/check_repo_secrets.py` | «لا قيم غير منقّحة في N ملفًا» (بعد `git add`) |
| 12 | تنازل مهر ما زال محصورًا | `cat brain/appendices/anchor-waivers.json` | مدخل واحد، تاريخ 2026-11-28 |
| 13 | انتهاء استثناء كونا | `grep -n '"expires": "2026-12-05"' brain/appendices/known-faults.json` | مطابقة واحدة |
| 14 | اختبار التنازل | `cd brain && python3 -m unittest tests.test_owner_anchor_waiver` | `Ran 3 tests … OK` |
| 15 | أصول اليوم محفوظة | `cat brain/archive/originals/2026-11-28/manifest.json` | مداخل المصادر بـsha256 |
| 16 | الدفتر يحوي 4 وقائع | `python3 -c "import json;print(len(json.load(open('brain/cumulative-2026/daily/2026-11-28.json'))))"` | `4` |
| 17 | دفتر 27 استعادي | `python3 -c "import json;print(len(json.load(open('brain/cumulative-2026/daily/2026-11-27.json'))))"` | `2` |
| 18 | تلغرام أُرسل مرة واحدة | `cat brain/logs/publish-2026-11-28-telegram.json` | `status: ok` |
| 19 | غروك لم يلمس فرعه | `git log --oneline origin/handover/grok-2026-11-28 -1` | `71ebf62` أو لاحق بأمر فهد |
| 20 | ملف التسليم هذا | `sha256sum docs/handover/GROK-EXACT-2026-11-28.md` | مطابق للإيداع على فرع `handover/grok-exact-2026-11-28` |

نقطة الرجوع: صفحة `seawatch-live` عند `6c4530d8fdcfe63c15ca37d176e60ccf5c67d5cb` ، وشيفرة `mda-marine-system` عند `ebdf7312fac835e7f7e350520bb45f833f78da24`. الرجوع إلى أحدهما قرار فهد، لا يُنفَّذ تلقائيًا.

# 13. مطابق بلا تغيير

## 13.1 الملفات التي غيّرها إيداع النشر `ebdf7312` (80 ملفًا)
| الملف | SHA-256 عند الإيداع | الحجم (بايت) | الوظيفة |
|---|---|---|---|
| `brain/CHANGELOG.md` | 49bf0463fd7d960dd701d8df6601644d69410647f250f9a88d0f7cd825f085c5 | 140047 | سجل التغييرات |
| `brain/appendices/anchor-waivers.json` | ca2772c572d215ee7be7cd91bff8a6dbe26b68e0a4352493757a87cab6194c23 | 409 | ملحق/سجل مرجعي |
| `brain/appendices/estimate-code-map.json` | cc0f06475731cea964e825715e8ed51979c66a2021050f6d84a3c3dbd6221e88 | 55708 | ملحق/سجل مرجعي |
| `brain/appendices/event-code-map.json` | 48403cc22a2bd6a235e6da38e566c815e3f6f4194a3365e15704f5deb80ef3c2 | 114068 | ملحق/سجل مرجعي |
| `brain/appendices/imo-incidents.json` | 61e3f2be3ead7e7fb9412ae9b021633cde4ed11ad8fa928646913ad23e4b67f7 | 36014 | ملحق/سجل مرجعي |
| `brain/appendices/incident-id-map.json` | f2910bb0ade01b321eb04f0c0ebaf8e6cd9e0edf0470c8eba8a21b40abfd70ae | 41460 | ملحق/سجل مرجعي |
| `brain/appendices/known-faults.json` | e74943825f7d3029db8455436fbe008ee25e2a3367f302bfbd5ac7a8175d62a7 | 11949 | ملحق/سجل مرجعي |
| `brain/appendices/lexicon-corpus.json` | f3a8d54b28d9641eaf5b09e9296a12d425d7dd66f38f1805f07e7bfd2d20dd75 | 148741 | ملحق/سجل مرجعي |
| `brain/appendices/libraries/new-terms-register.json` | 6b467feade8c8a17972ecfc2941258e784948e76bd76bb9d3a60ad939f7843e8 | 28727 | ملحق/سجل مرجعي |
| `brain/appendices/libraries/new-terms-register.md` | 8b1a62b753c6ee47ab8910acad3e2cf93b8480da20c32dac5bfe29a1676dcc43 | 12540 | ملحق/سجل مرجعي |
| `brain/archive/ofac-screen-latest.json` | 988e2df7411fb85d9c56b17e06f60390d3cc772e3fdc9645b6d166a99a244aeb | 3140 | أرشيف |
| `brain/archive/originals/2026-11-28/1cd70443f1a4.html` | db0892d5106d62337edfdf9af7d52054b8a6092a7e99415aa084d18b5113ee20 | 158590 | أصول المصادر المحفوظة وقت الجمع |
| `brain/archive/originals/2026-11-28/dvids-centcom-580348.md` | a4bed4af7161fbb6ec68c081b22e04fc91c8be1163137152eb9a84d499668e7e | 1132 | أصول المصادر المحفوظة وقت الجمع |
| `brain/archive/originals/2026-11-28/imo-middle-east-incidents.md` | aad97f188355f99bec46b098d6a94499caad91dbbb7e3c8156fb70217b36bc11 | 4236 | أصول المصادر المحفوظة وقت الجمع |
| `brain/archive/originals/2026-11-28/manifest.json` | 3cc356bfacb3421acc947e9deed9393eeab118f1419b4e73daa836360bfa2494 | 861 | أصول المصادر المحفوظة وقت الجمع |
| `brain/archive/originals/2026-11-28/status.json` | 7bc0e60d9b66791d5d3f1fad6cd2943dd56f0a4ffa291eb01bb8687bbcaf50bc | 296 | أصول المصادر المحفوظة وقت الجمع |
| `brain/archive/originals/2026-11-28/ukmto-recent-incidents.md` | d6fe4fcf6fba2261c63323940c3e945b827321faeadf34fff7de6b333d84ba5b | 9770 | أصول المصادر المحفوظة وقت الجمع |
| `brain/archive/source-text/2026-11-28/MN-2026-11-28-01.txt` | 531f71687e2f1b6e09dd5ee4f56334461b44a3420b894b4c465108722d841996 | 691 | نص مقتطف الأصل لكل واقعة |
| `brain/archive/source-text/2026-11-28/MN-2026-11-28-02.txt` | f64363d9c1e7885b317fd5226db5b46bf4a0f6a6c1e3f788bc9d3acfda3cd853 | 567 | نص مقتطف الأصل لكل واقعة |
| `brain/archive/source-text/2026-11-28/MN-2026-11-28-03.txt` | 41bf85a025a4fb6a6b9e9caa14a4be18e15949bd9352478a686ae966b9425c87 | 472 | نص مقتطف الأصل لكل واقعة |
| `brain/archive/source-text/2026-11-28/MN-2026-11-28-04.txt` | d1045a2b8901d3ffa9f286e5253918f7e87c80f9dc33bc2ac6ba179c8c710b5c | 458 | نص مقتطف الأصل لكل واقعة |
| `brain/audit/asset-floor.json` | 0d4ec5aba2f99ae11fc9134735ad06970ba423d38c16263702039a9de23cb447 | 1262565 | قياسات وتدقيق |
| `brain/audit/measurements/exceptions-triage-2026-11-28.json` | f59065080b0a0c27a090ec5f74a2dcba764b25cea7347da5cc3afcc7b8fd17ff | 13810 | قياسات وتدقيق |
| `brain/audit/measurements/gate-audit-2026-11-28.json` | 1f4c12e5baaa72a21a713d9744e0d611655acff59f60428de1de211472ad1546 | 3424 | قياسات وتدقيق |
| `brain/audit/measurements/gate-audit-2026-11-28.json.sha256` | 937f4a0775e6036cc5a6d929da61bc006bebc11afafa01fc049489d14ceae523 | 149 | قياسات وتدقيق |
| `brain/audit/measurements/perf-budget-2026-11-28.json` | f9e7f6468b68215885d36d1bb36850ca5f261fbaf767301c2db2000a945d3e87 | 2048 | قياسات وتدقيق |
| `brain/audit/measurements/perf-budget-2026-11-28.json.sha256` | c47b793c8f4dd2e57276c5ea66d70f76c1def35f7c728daab9a91267dff84c6d | 150 | قياسات وتدقيق |
| `brain/audit/measurements/regression-b-01.json` | f8ac3356354b6a23af184f628c2910cb4d94d4a6cde031207bf3051e100c4ed3 | 21343 | قياسات وتدقيق |
| `brain/audit/measurements/regression-b-02.json` | 6a723c87d33587ab588f2af0db0358343403d9c243845221347c18d714f746c2 | 20606 | قياسات وتدقيق |
| `brain/audit/measurements/regression-b-03.json` | 5356b00dc3566449e2faadc0f4641b15003007f09b0e92a7c18c74d2a31bb5e9 | 21341 | قياسات وتدقيق |
| `brain/audit/measurements/regression-b-04.json` | 84496f164c4931aadb94de770cce8d8e377c26801c28498a9e6624bffe51bb5d | 21342 | قياسات وتدقيق |
| `brain/audit/measurements/regression-b-13.json` | a5bfe50ff729312af930b08ffeead0594c8e634e218893d957e4d2cdc205a367 | 21583 | قياسات وتدقيق |
| `brain/audit/measurements/regression-b-14.json` | e6f66b7370ec2f9b66a9843bb83200d24dc05cb290ede9a02d3b1faaf4911a14 | 21363 | قياسات وتدقيق |
| `brain/cumulative-2026/daily/2026-11-27.json` | c251cb933467c67e0758f69a6caa3824d8f8bedc171dd4a3b8b7e59a39f97106 | 5152 | دفتر الوقائع التراكمي |
| `brain/cumulative-2026/daily/2026-11-28.json` | 57b382cd88d7fd02d3d9815a2bf5b808be7b6a7b60937504b550faf62b8fca6b | 7625 | دفتر الوقائع التراكمي |
| `brain/cumulative-2026/event-ledger-master.json` | 3cf24185fa977f192044a309cb45aeec1fc307f6734dcb86e6907f3d6d3e9664 | 1004535 | دفتر الوقائع التراكمي |
| `brain/evidence/merkle/ledger.jsonl` | 1eeb97aa6689c29fc792f701e31b16903f1e78827d5a14e3bcf0eb6af47d5c91 | 22483 | سجل الأدلة (merkle) |
| `brain/evidence/merkle/snapshot.json` | 02348c58980da3ffc632576a5d0bd4c982feba73424587c86e95ba2fb2bd3555 | 926692 | سجل الأدلة (merkle) |
| `brain/feeds/feeds-2026-11-28.json` | f8dc94b703f1f9ceb18d17d4ed613d2665f74cbb9e23fcd30fcca6b70f62127a | 494822 | نتائج جمع التغذيات |
| `brain/feeds/feeds-2026-11-28.md` | 86a2ab1779a72b457b2b51f94f138df67c29a988b49c11935ad8692eff3655f9 | 49275 | نتائج جمع التغذيات |
| `brain/feeds/feeds-2026-11-28.status.json` | bcfd96b3ca0d9b9e34531745418b9130987419d3f248216afaa4ba6a7bcdb4b0 | 32008 | نتائج جمع التغذيات |
| `brain/logs/alerts/waw-2026-11-28.md` | 20281ab1b2a2e1aeacfb4f23d526de9fb14eaed36c937fef486e5f6b2fa26697 | 276 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/auto-heal/2026-11-28.json` | c965db170a07e686ed2c7ce9178076024b6ebd936c66851045447bd0a672e3ef | 57 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/auto-heal/2026-11-28.jsonl` | 7c2a68186a5cad180a66eae3c11c35185098137a8279d86bc0bca230ac9d8c51 | 553 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/auto-heal/2026-11-28.md` | 8060ecc1489fce9609a56912bca1eac0b88c5bd58d2d70dc0d8e77db5b775f75 | 393 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/deliver-2026-11-28.json` | 6cb7fb840833fb5c89ec4e2d212a9820709eaf2dc74b3cdd3d03c9574f044fb1 | 3589 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/gate-2026-11-28/.text-hash-2026-11-28.json` | 5eccacbdceab9a73dc0c601767082b3ad4fb5edce33876f7584ed48a8b0df819 | 536 | نتائج البوابات |
| `brain/logs/gate-2026-11-28/binding-coverage.json` | 2405aa44edf5ef7925b3f2befac7b2a6016b4da0ece7ad18522822105eb16d37 | 2794 | نتائج البوابات |
| `brain/logs/gate-2026-11-28/gate.json` | b1f4f527111dc1ea5fc90272c9a19a790a76288a478336c20737f3b3cd769acf | 15497 | نتائج البوابات |
| `brain/logs/gate-verdict-2026-11-28.json` | 98dbb5dda95363b2dbda46507e550154269392ec81a99602e34b59d0c94eb2e7 | 10205 | نتائج البوابات |
| `brain/logs/github-backup-2026-11-28.log` | 0c8d2bafd35157050c0347dcc805e65e5d734b02094bf3b20598950a34cdf5fd | 252460 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/orthography-2026-11-28.json` | 86a7be41f27fe0d09ffdb6a595258eb8243ee9b4ded8512a2951294bfa56f5da | 108 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/pipeline-2026-11-28.json` | 89b77628fa28bda1945be78fac07e0d663d0f219eabd7fc620e04b276af796c2 | 3085 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/publish-2026-11-28-telegram.json` | 05acd030d953eb41f34689e74bb44354f3a21828db95fe51a6bd6eafcc80ce1e | 160 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/publish-channel-2026-11-28.json` | 2139c22bb0ff396a74d2977b0477e9548dc629f120c590a9fc03015f9c483eb8 | 1775 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/qa-2026-11-28.json` | 3653794544eae0d912f74deb2cc8d2451a31d3bfb7c9a444063c1afaeba6db26 | 171 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/runbook/2026-11-28.jsonl` | 1ea5f379a6fb2627b8a10c36dee50588cd9c546875b54dffbed188740e70cf9d | 351324 | سجل المحرّك (دفتر الخطوات) وأزمنتها |
| `brain/logs/runbook/2026-11-28/timings.md` | 4eb169781ecf9f92a33d7de0c0e38fc912f7aea3beb5901020b45b541716b157 | 1517 | سجل المحرّك (دفتر الخطوات) وأزمنتها |
| `brain/logs/scrub-2026-11-28.json` | 028f732797ea3194f70e118ce75b46adfe260497543d9dc92de66f33b611eebe | 78 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/style-metrics-2026-11-28.json` | 66cdda843754f8bfa753251176e1e89ad46fd290c9c3958ce44e5b668540ab27 | 253 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/telegram-2026-11-28.out` | 84ae7cd0019545068c70d8f1c7922aed6966a31ba6c8e4aa5837bee08c644053 | 231 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/telegram-archive/2026-11-28-2026-11-28T104504Z.html` | 853e3193f7f4a96b96e10389e53ef4857849e14a28f778d450d854549d4f8925 | 1481 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/logs/tg-digest-2026-11-28.html` | 853e3193f7f4a96b96e10389e53ef4857849e14a28f778d450d854549d4f8925 | 1481 | سجل/علامة تشغيل ونشر وإرسال اليوم |
| `brain/reports/2026-11-28-sectioned.md` | 2b4f78a403b191e9ed7846e5f442d5fd86ad460a83190786d5e2535a562509d5 | 23962 | متن التقرير العربي |
| `"brain/reports/docx/\330\247\331\204\330\252\331\202\330\261\331\212\330\261-\330\247\331\204\331\212\331\210\331\205\331\212-2026-11-28-\330\267\330\250\331\202-\330\247\331\204\330\243\330\265\331\204.docx"` | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | مخرج طباعة (نسخة DOCX/PDF من التقرير) |
| `"brain/reports/docx/\330\247\331\204\330\252\331\202\330\261\331\212\330\261-\330\247\331\204\331\212\331\210\331\205\331\212-2026-11-28-\330\267\330\250\331\202-\330\247\331\204\330\243\330\265\331\204.pdf"` | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 0 | مخرج طباعة (نسخة DOCX/PDF من التقرير) |
| `brain/tests/test_owner_anchor_waiver.py` | 90279a33756f5e1fc23c41c36d40454b841b6611ca2512608b1b893b66e89fcd | 1726 | اختبار |
| `brain/tools/browser_measure.py` | 28aa247987248348017a6511399e80b60b588306a28e335d245a37a66f7dba5f | 32472 | أداة |
| `brain/web/kpis-totals/2026-11-28.json` | 631d5c8a68e3cf22c176a3094f35be6d3a2349f1eb276f5d648e19322cc0e8e5 | 8966 | بيانات واجهة التقرير |
| `brain/web/meta/2026-11-28.json` | 220745837c54e2d4d2edb83af778fcac9c5bcd2ad2ae78928c525ae9cadd039d | 29561 | بيانات واجهة التقرير |
| `brain/web/zones/2026-11-28.json` | f009783238fb3707683d978a3a9d70c0b68deb986302721dc141226150ef5336 | 7534 | بيانات واجهة التقرير |
| `site/sources/daily-events/2026-11-28.json` | 57b382cd88d7fd02d3d9815a2bf5b808be7b6a7b60937504b550faf62b8fca6b | 7625 | مصدر الموقع (نسخة من brain) |
| `site/sources/feeds-status.json` | bcfd96b3ca0d9b9e34531745418b9130987419d3f248216afaa4ba6a7bcdb4b0 | 32008 | مصدر الموقع (نسخة من brain) |
| `site/sources/i18n/en/2026-11-28-sectioned.en.md` | f28ff5cdda1d32d5fe13ea202d618adfa13ae360ce16153db173265f00770bbd | 19262 | الأصل الإنجليزي والمعجم |
| `site/sources/i18n/en/glossary.json` | fbf68699c78f94f449cbe76c96761fab6f12834c9c09dcd546edb338db229dd2 | 698436 | الأصل الإنجليزي والمعجم |
| `site/sources/incident-id-map.json` | f2910bb0ade01b321eb04f0c0ebaf8e6cd9e0edf0470c8eba8a21b40abfd70ae | 41460 | مصدر الموقع (نسخة من brain) |
| `site/sources/ledger.json` | 3cf24185fa977f192044a309cb45aeec1fc307f6734dcb86e6907f3d6d3e9664 | 1004535 | مصدر الموقع (نسخة من brain) |
| `site/sources/meta/2026-11-28.json` | 95290663704e68ae4eaa80b0005e6bf9445a1e56b4bbe5323a9df53af8008df7 | 29562 | مصدر الموقع (نسخة من brain) |
| `site/sources/reports/2026-11-28-sectioned.md` | 2b4f78a403b191e9ed7846e5f442d5fd86ad460a83190786d5e2535a562509d5 | 23962 | مصدر الموقع (نسخة من brain) |
| `site/sources/zones/2026-11-28.json` | f009783238fb3707683d978a3a9d70c0b68deb986302721dc141226150ef5336 | 7534 | مصدر الموقع (نسخة من brain) |


## 13.2 ما غيّره غروك بعد نشري وقبل دمجي — انحراف يُترك خارج التشغيل القادم
هذه الإيداعات على main وليست من طريقتي ولم تكن في فرعي وقت التشغيل. لا تُعتمد في أي تشغيل «مطابق» ما لم يأمر فهد.

| الإيداع | الوصف | الملف | الأثر |
|---|---|---|---|
| `c28087cc` | W010: تشغيل كاملًا بلا تقسيم، `agent_steps` الافتراضي 8 | `.github/workflows/daily.yml` | انحراف |
| `cc6a07d8` | W010: تسجيل رموز EST الجديدة قبل فحص الإتمام | `brain/tools/agent_write_llm.py` | انحراف |
| `6cabd099` | استثناء العمق السعودي من رسم الخريطة | `brain/appendices/area-coordinates.json` | انحراف |
| `78880bd4` | اسم منطقة مركّب فيه يابسة لا يوقف النشر | `brain/tools/derive_map_points.py` | انحراف |
| `188bd428` | الاستئناف من مخرجات اليوم المحفوظة | `.github/workflows/daily.yml` | انحراف |
| `687f953d` | لا يُستبدل فرع اليوم إن غاب التقرير | `.github/workflows/daily.yml` | انحراف |
| `d878141e` | عنوان إنجليزي لواقعة سفينة رسمية يُحسب بنوعه | `brain/tools/classify_zones.py` | انحراف |
| `944b64ec` | سواحل اليمن مرساتها خليج عدن | `brain/appendices/area-coordinates.json` | انحراف |
| `e9095df0` ثم `2433b0f7` | توثيق ثم إلغاء فجوة 27 | `brain/cumulative-2026/migration-gaps.json` | الصافي صفر (SHA مطابق لحالة الإيداع `ebdf7312`) |

بصمات هذه الملفات: عند إيداعي (أول 16 حرفًا) وحاليًا على main:

| الملف | SHA-256 عند `ebdf7312` (16) | SHA-256 على main | الحجم الحالي |
|---|---|---|---|
| `.github/workflows/daily.yml` | 899191a8018afbaf | af216bf4971578b76bc4c69b14bf8f959078d1b0fdedfa03072897fb23312172 | 11698 |
| `brain/appendices/area-coordinates.json` | baf972752c59f9ff | f09e70bc9b3577fb282e4b362d64b97acebc578679a818d215c131acd03aab7d | 11652 |
| `brain/tools/agent_write_llm.py` | d03e18bcfd7ffa1c | 9e69a8a2f5c9633fe87fb76cd08af16f2605f14097ec96853aefc36654dd9213 | 20742 |
| `brain/tools/classify_zones.py` | 3ba5e0fee4573125 | 14ee02f7870c464388e8d88ed2d3441e57b4c709027de175a929d7afb249515a | 30130 |
| `brain/tools/derive_map_points.py` | cb8b7eef39c04e44 | be130cf97c5d692a103839fc1bfffab1888a13673eff1b918f796761ed0f3a78 | 17641 |
| `brain/cumulative-2026/migration-gaps.json` | 86cadd8a88f06165 | 86cadd8a88f06165f210a0738ea9666dd62abaf2886981b4961de7a3137d980f | 1628 |


ملاحظة صدق: أسماء مؤلفي هذه الإيداعات في git كلها «fahad aldoseri» (نفس هوية الدفع)، فنسبتها إلى Grok مبنية على أنها في فرع main الآتي من عمل Grok قبل دمج PR 677، لا على توقيع المؤلف. تأكيد الجهة صاحبة كل إيداع: غير موجود عندي؛ موضع البحث: سجل جلسات Grok أو سؤال فهد.

## 13.3 ما لم أختبره
- لم أختبر تشغيل daily.yml الحالي على main (يحوي انحرافات §13.2).
- لم أختبر إصلاح خلل 2-chain، ولا ثبات رابط UKMTO عبر عدة تشغيلات متتالية.
