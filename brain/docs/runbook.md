# كتيب الإجراءات التشغيلية

<!-- مولَّد آليًا من runbook/runbook.json (بصمة 3737d278eb69b635). لا تعدّله يدويًا: عدّل المانيفست ثم شغّل handbook. -->

لا يعتمد التشغيل على ذاكرة الوكيل: المحرّك ينفّذ الخطوات بالترتيب، ولا تبدأ خطوة قبل اكتمال ما قبلها بدليل.

## الخطوات

| # | الخطوة | المنفّذ | يقرأ | يكتب | شرط الإتمام | القواعد | الملفات والمجلدات المرتبطة | عند الفشل |
|---|---|---|---|---|---|---|---|---|
| S000 | فحص المانيفست (verify) قبل أي خطوة | script |  |  | cmd:bash -lc test -s docs/runbook.md | الأمر التنفيذي: كتيب الإجراءات | tools/runbook.py، runbook/runbook.json، docs/runbook.md، INDEX.md، CLAUDE.md، bootstrap.sh، validators/check_orthography.py، tools/reorder_sections.py، tools/visual_audit.py، tools/add_source.py، tools/ensure_devserver.sh، tools/full_chain_audit.py، tools/next_version.py، tools/measure_filter_savings.py، tools/check_api_keys.py، tools/install_macr_skill.sh، tools/llm.mjs، tools/llm.sh، tools/check_builtin_llm.sh، tools/claude_check.py، tools/read_user_docx.py، tools/fetch_primary.py، tools/shorten_sentences.py، tools/ach_v3_model.py، tools/_publish_v3.py، tools/map_docx_changes.py، tools/verify_codespace.sh، tools/fix_legacy_reports.py، tools/rebuild_report.sh، tools/page_budget.py، tools/diagnose_print_layout.py، tools/vessel_names.py، tools/diagnose_sources.py، tools/check_baseline.py، tools/make_baseline.py، tools/known_faults.py، tools/preserve_check.py، tools/meaning_compare.py، tools/extract_ui_strings.py، tools/alert_monitor.sh، backups/macr-system-old-2026-10-15/scripts/example.py | stop |
| S010 | استعادة المهارات وفحص التماثل | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/S010.log | أ1 — سلسلة التشغيل اليومي | tools/restore_skills.sh، sections/90-automation.md | stop |
| S020 | فحص التغذيات (40 مصدرًا) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/S020.log | أ1 — سلسلة التشغيل اليومي | tools/check_feeds.py، sections/90-automation.md | stop |
| S030 | ترقيم التغذيات (أرقام لاتينية) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/S030.log | أ1 — سلسلة التشغيل اليومي | tools/normalize_digits.py، sections/90-automation.md، tools/normalize_terms.py | stop |
| S040 | توليد أهداف العقوبات من التقرير | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/S040.log | أ1 — سلسلة التشغيل اليومي | tools/ofac_targets_from_report.py، sections/90-automation.md | stop |
| S050 | فحص العقوبات (OFAC) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/S050.log | أ1 — سلسلة التشغيل اليومي | tools/ofac_screen.py، sections/90-automation.md | stop |
| S060 | حفظ الأصول الرسمية | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/S060.log | أ1 — سلسلة التشغيل اليومي | tools/archive_originals.py، sections/90-automation.md | stop |
| S070 | دمج الذاكرة التراكمية (دفتر اليوم) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/S070.log | أ1 — سلسلة التشغيل اليومي | tools/merge_ledger_daily.py، sections/90-automation.md، tools/daily_pipeline.sh | stop |
| S080 | فرز التغذيات بالنموذج (اختياري) (اختيارية) | script |  |  | cmd:bash -lc test -e logs/runbook/{date}/S080.log | أ1 — سلسلة التشغيل اليومي | tools/llm_triage.py، sections/90-automation.md | continue |
| S090 | مراجعة التقرير بالنموذج (اختياري) (اختيارية) | script |  |  | cmd:bash -lc test -e logs/runbook/{date}/S090.log | أ1 — سلسلة التشغيل اليومي | tools/llm_review.py، sections/90-automation.md | continue |
| W010 | كتابة التقرير اليومي | agent | sections/20-writing-brief.md، sections/20-lexicon.md، sections/20-examples.md، cumulative-2026/daily/{date}.json، feeds/feeds-{date}.md | reports/{date}-sectioned.md | min_bytes:reports/{date}-sectioned.md؛ contains:reports/{date}-sectioned.md | أ2 — قواعد الكتابة، ل1 — أسلوب اللغة | sections/20-writing-brief.md، sections/20-lexicon.md، sections/20-examples.md، runbook/prompts/write-report.md | stop |
| W020 | بناء ملف واجهة التقرير | agent | reports/{date}-sectioned.md، templates/mark-schema.json | web/meta/{date}.json | min_bytes:web/meta/{date}.json | ب2 — ترتيب الأقسام | templates/mark-schema.json | stop |
| G001 | اختبارات البوابات (tests) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G001.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tests/run_checks.sh | stop |
| G002 | تنظيف المحتوى الداخلي | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G002.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/scrub_internal.py، tools/apply_audit_gfs_docx.py، tools/apply_jmic_ukmto_to_gfs.py | stop |
| G003 | دمج بنك التعريفات | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G003.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/merge_glossary.py | stop |
| G004 | أرقام المصادر (معتمدة/مفحوصة/ناجحة) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G004.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/source_counts.py | stop |
| G006 | إصلاح الصياغة الآلي (خطوة واحدة) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G006.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/repair_prose.py، tools/pro_audit.py | stop |
| G007 | تحرير لغوي آلي (قبل/بعد لكل قسم) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G007.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/edit_pass.py، tools/audit_corpus.py، tools/audit_pdf_layout.py، tools/audit_pagination.py، tools/audit_broad_excepts.py | stop |
| G008 | بوابات اللغة المتدرجة (إملاء ونحو وأسلوب) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G008.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/language_gates.py | stop |
| G009 | أصل نص كل واقعة (للفحص العكسي) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G009.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/ledger_source_excerpt.py | stop |
| G010 | بصمة النص قبل البناء | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G010.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/_guard.py، tools/text_hash_guard.py | stop |
| G011 | فحص ما قبل التشغيل | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G011.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/preflight_check.py | stop |
| G012 | مدقق التقرير (الواجهة) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G012.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G013 | بوابة الأسلوب | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G013.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/style_learn.py، tools/style_metrics.py | stop |
| G014 | بوابة اللغة | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G014.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G015 | بوابة إغلاق المكتبات | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G015.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_findings_closed.py | stop |
| G016 | ترابط المكتبات والمهارات | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G016.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G017 | تماثل المهارات والمكتبات (مزامنة فورية) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G017.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G018 | سلامة المهارات | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G018.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_skills_integrity.py | stop |
| G019 | بوابة الفهم (مرحلة $COMP_STAGE) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G019.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G020 | بوابة التحليل الاستخباري | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G020.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/intel_self_review.py | stop |
| G021 | استخراج أهداف OFAC | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G021.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G022 | فحص OFAC | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G022.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G023 | تغطية فحص العقوبات | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G023.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_ofac_coverage.py | stop |
| G024 | استعمال المكتبات (المعجم والبنك والفجوات) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G024.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G025 | عدد المصادر (مصدر واحد) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G025.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G026 | قابلية النقل (مسارات) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G026.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_portable_paths.py، tools/portable_paths.py | stop |
| G028 | حصاد الألفاظ الجديدة | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G028.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/harvest_terms.py | stop |
| G030 | فصل فضاءات الرموز MN-/EST- | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G030.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G031 | قاعدة النقاط في المصدر | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G031.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G032 | فاحص النقل بين الإصدارات | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G032.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G033 | اكتمال التشغيل (الأعطال المعروفة) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G033.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_run_completeness.py | stop |
| G034 | عيوب الكتابة (الصياغة والترقيم) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G034.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_prose_defects.py | stop |
| G035 | تسرّب المحتوى الداخلي إلى المتن | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G035.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_internal_leak.py | stop |
| G036 | المفردات المبسطة (تنبيهي حتى الموافقة) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G036.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_vocabulary.py | stop |
| G040 | اختبارات المراجعة الثانية (أ · ب · ج · د · هـ · ز) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G040.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tests/test_review2.sh | stop |
| G041 | اختبار انحدار المصلح (12→23) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G041.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tests/test_repair_regression.sh | stop |
| B010 | بناء الموقع من البيانات | script |  |  | file_exists:{site}/dist/reports/{date}.html | س1 — النشر | {site}/generator/build_site.py، {site}/generator/sync_from_brain.py، tools/build_source_reliability.py، tools/sync_backup.sh، tools/build_macr_docx.py، tools/build_provenance.py، tools/build_styles_docx.py، tools/build_audit_report.py، tools/build_ambiguity_map.py، tools/build_instructions_doc.py، tools/build_report_docx.py، tools/build_report_docx_exact.py، tools/sync_profile_hash.py، {site}/generator | stop |
| B020 | تصدير PDF المعتمد | script |  |  | min_bytes:{site}/dist/reports/pdf/{date}.pdf | س1 — النشر | tools/export_report_assets.py، tools/pdf_change_guard.py | stop |
| B030 | بوابتا جودة الطباعة على PDF نفسه | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/B030.log | ف5 — شكل PDF وجودة الطباعة | validators/check_pdf_format.py، validators/check_print_quality.py | stop |
| B035 | خط الأساس الرسمي (virgin) — تنبيهي | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/B035.log | س1 — النشر | tools/check_baseline.py | stop |
| B040 | نسخة Word طبق الأصل (بوابة المخرج 9 تمنع التسليم بدونها) | script |  |  | cmd:bash -lc ls reports/docx/*{date}*.docx >/dev/null 2>&1 | س1 — النشر | tools/build_report_docx_exact.py | stop |
| G005 | تطابق أرقام المصادر في كل المواضع | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G005.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G027 | الأرقام (0-9 لاتينية) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G027.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_numerals.py | stop |
| G029 | سياسة الرموز في المخرجات | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G029.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_code_policy.py | stop |
| G037 | بوابات المخرج العشر | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G037.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/qa_gates.py | stop |
| G042 | تطابق النص المبني مع النص النهائي | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G042.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh | stop |
| G043 | سجل البوابات gate.json من سجل المحرّك | script |  |  | cmd:bash -lc grep -q 'runbook-ledger' logs/gate-{date}/gate.json | ف1–ف5 — بوابة التحقق | tools/runbook.py، tools/write_mark.py | stop |
| G038 | كتابة العلامة بعد البوابة | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G038.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، tools/write_mark.py | stop |
| G039 | مخطط العلامة الثابت | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/G039.log | ف1–ف5 — بوابة التحقق | tools/final_gate.sh، validators/check_mark_schema.py | stop |
| D010 | نشر الموقع (بعد كل البوابات) | script |  |  | cmd:python3 -c import json,sys;d=json.load(open('logs/publish-{date}.json'));sys.exit(0 if d.get('status')=='ok' else 1) | س2 — الإغلاق والدفع | tools/publish_site.sh، tools/publish_changes.sh | stop |
| D020 | التحقق الحي من النشر (قراءة فقط) | script |  |  | cmd:python3 -c import json,sys;d=json.load(open('logs/live-{date}.json'));sys.exit(0 if d.get('status')=='ok' else 1) | س2 — الإغلاق والدفع | tools/check_live.sh، tools/live_visual_audit.py | stop |
| D030 | إرسال الملخص وPDF على تلغرام (اختيارية) | script |  |  | cmd:python3 -c import json,sys;d=json.load(open('logs/publish-{date}-telegram.json'));sys.exit(0 if d.get('status')=='ok' else 1) | س4 — قناة التسليم | tools/publish_site.sh، tools/make_tg_digest.py، tools/telegram_send.py، tools/telegram_bot.py، secrets/secrets.env.example، secrets/README.md | continue |
| D040 | النسخة الاحتياطية والتحقق من التماثل | script |  |  | cmd:bash -lc grep -q 'النتيجة: مطابق' logs/runbook/{date}/D040.log | س2 — الإغلاق والدفع | tools/github_backup.sh، validators/check_backup_parity.py، tools/github_backup.py، tools/apply_from_github.sh، tools/apply_from_github.py، tools/code_paths.py | stop |
| D045 | فهرس التقارير (المستودع مقابل الأرشيف الخاص) (اختيارية) | script |  |  | cmd:bash -lc grep -q '{date}' docs/reports-index.md | س2 — الإغلاق والدفع | tools/reports_index.py، appendices/reports-archive.json | continue |
| D050 | التعلم الذاتي وتسجيل الدروس | script |  |  | file_exists:memory/learning-log.jsonl | س2 — الإغلاق والدفع | tools/self_improve.py، tools/skill_lessons.py، tools/self_test.py | stop |
| D060 | تسجيل رموز التقدير والأحداث | script |  |  | cmd:bash -lc grep -q 'رمز تقدير مسجّل' logs/runbook/{date}/D060.log | ب2 — ترتيب الأقسام | tools/register_estimate.py | stop |
| Q010 | تدقيق المكتبات والمهارات (أسبوعي) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/Q010.log | ف3 — بوابات المكتبات | validators/check_library_use.py، validators/check_libraries_skills.py | stop |
| Q015 | تدقيق المكتبات اللغوية (أسبوعي) (اختيارية) | script |  |  | cmd:bash -lc test -s logs/runbook/{date}/Q015.log | ف1–ف5 — بوابة التحقق | tools/audit_corpus.py | continue |
| Q020 | قياس دقة التقدير (ربع سنوي) | script |  |  | cmd:bash -lc grep -q 'نسبة التحقق' logs/runbook/{date}/Q020.log | ف4 — التحليل الاستخباري | tools/estimate_accuracy.py | stop |

## أقسام التقرير وارتباطاتها

| الترتيب | القسم | كتلة التوليد | المدقق | مقتطف البرومت | الاختبارات | ملفات أخرى |
|---|---|---|---|---|---|---|
| 1 | ما تغيّر منذ التقرير السابق (يُركَّب من ملف الواجهة) (what-changed) | {site}/generator/blocks.py | validators/check_carryover.py | runbook/prompts/sections/what-changed.md | tests/test_sections_registry_vs_report.py |  |
| 2 | الخلاصة (summary) | {site}/generator/blocks.py | validators/validate_report.py | runbook/prompts/sections/summary.md | tests/test_sections_registry_vs_report.py |  |
| 3 | بطاقة القرار (تُركَّب من ملف الواجهة) (general) | {site}/generator/blocks.py | validators/check_comprehension.py | runbook/prompts/sections/general.md | tests/test_sections_registry_vs_report.py |  |
| 4 | التوزيع الجغرافي للوقائع (incident-map) | {site}/generator/blocks.py | validators/check_pdf_format.py | runbook/prompts/sections/incident-map.md | tests/test_sections_registry_vs_report.py |  |
| 5 | مؤشرات الموقف (indicators) | {site}/generator/blocks.py | validators/check_style.py | runbook/prompts/sections/indicators.md | tests/test_sections_registry_vs_report.py |  |
| 6 | مستوى التهديد (threat-level) | {site}/generator/blocks.py | validators/check_intel.py | runbook/prompts/sections/threat-level.md | tests/test_sections_registry_vs_report.py |  |
| 7 | التوجيهات التشغيلية (directives) | {site}/generator/blocks.py | validators/check_points_rule.py | runbook/prompts/sections/directives.md | tests/test_sections_registry_vs_report.py |  |
| 8 | الوقائع الجديدة (new-incidents) | {site}/generator/blocks.py | validators/check_language.py | runbook/prompts/sections/new-incidents.md | tests/test_sections_registry_vs_report.py |  |
| 9 | التحذيرات والنشرات الرسمية (warnings) | {site}/generator/blocks.py | validators/check_code_spaces.py | runbook/prompts/sections/warnings.md | tests/test_sections_registry_vs_report.py |  |
| 10 | سجل IMO والحوادث المؤكدة (imo-log) | {site}/generator/blocks.py | validators/check_carryover.py | runbook/prompts/sections/imo-log.md | tests/test_sections_registry_vs_report.py |  |
| 11 | التحليل الاستخباري (intel-analysis) | {site}/generator/blocks.py | validators/check_intel.py | runbook/prompts/sections/intel-analysis.md | tests/test_sections_registry_vs_report.py |  |
| 12 | الاحتمالات والإسناد (attribution) | {site}/generator/blocks.py | validators/check_comprehension.py | runbook/prompts/sections/attribution.md | tests/test_sections_registry_vs_report.py |  |
| 13 | الحركة الملاحية والتكدس (traffic) | {site}/generator/blocks.py | validators/check_style.py | runbook/prompts/sections/traffic.md | tests/test_sections_registry_vs_report.py |  |
| 14 | ما لم يُحسم (open-questions) | {site}/generator/blocks.py | validators/check_comprehension.py | runbook/prompts/sections/open-questions.md | tests/test_sections_registry_vs_report.py |  |
| 15 | المراقبة المستمرة (monitoring) | {site}/generator/blocks.py | validators/check_style.py | runbook/prompts/sections/monitoring.md | tests/test_sections_registry_vs_report.py |  |
| 16 | الخلفية (background) | {site}/generator/blocks.py | validators/check_carryover.py | runbook/prompts/sections/background.md | tests/test_sections_registry_vs_report.py |  |
| 17 | المصادر والمراجع (sources) | {site}/generator/blocks.py | validators/check_sources_count.py | runbook/prompts/sections/sources.md | tests/test_sections_registry_vs_report.py |  |
