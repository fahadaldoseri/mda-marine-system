# PROJECT-DELTA — تغييرات جولة أمر التنفيذ (23 أكتوبر 2026)

التاريخ: 2026-10-23 08:11Z · التزام المستودع الخاص: `4108d71`
عدد الملفات المتغيّرة المعروضة: **62** — البصمة = أول 12 حرفًا من sha256.

| # | الملف | البصمة | الشرح |
|---:|---|---|---|
| 1 | `brain/PROJECT-DELTA.md` | `88ff5ee0bf30` | تعديل مرتبط بهذه الجولة |
| 2 | `brain/appendices/forbidden-coinages.json` | `33a97676ae3a` | الألفاظ المصطنعة الممنوعة |
| 3 | `brain/appendices/known-faults.json` | `38dbfa69dd31` | الأعطال المعروفة المسموح إفصاحها |
| 4 | `brain/appendices/libraries/new-terms-register.json` | `3e25d658e427` | تعديل مرتبط بهذه الجولة |
| 5 | `brain/appendices/libraries/new-terms-register.md` | `8381f6de1f2f` | تعديل مرتبط بهذه الجولة |
| 6 | `brain/appendices/simplified-vocabulary.json` | `3b3bf2c2fc6b` | المفردات المبسطة (معلّقة حتى الموافقة) |
| 7 | `brain/memory/learning-log.jsonl` | `8a894d3b8f19` | دروس الجولة |
| 8 | `brain/reports/2026-10-23-sectioned.md` | `f4d094340a0c` | سطر الأرقام وسطر الإفصاح في «ما لم يُحسم» |
| 9 | `brain/sections/20-language.md` | `e747b7cb7164` | قواعد الترجمة بالمعنى (معلّقة) |
| 10 | `brain/sections/60-validation.md` | `ab8f898ca6b7` | توثيق بوابات أمر التنفيذ |
| 11 | `brain/templates/mark-schema.json` | `74f394f91064` | مخطط العلامة الثابت |
| 12 | `brain/tests/run_checks.sh` | `fd75d675f327` | اختبارات 5–8 |
| 13 | `brain/tests/test_language.sh` | `0ff73f87e650` | اختبارات اللغة والتسرب (بلا مسار مطلق) |
| 14 | `brain/tests/test_ofac.sh` | `0f01bf87a2fa` | اختبارات العقوبات |
| 15 | `brain/tools/daily_pipeline.sh` | `50f9fa353da8` | عدم ابتلاع فشل أهداف العقوبات |
| 16 | `brain/tools/final_gate.sh` | `f075ac4653df` | ربط البوابات السبع + قاعدة 70 + العلامة بعد البوابة |
| 17 | `brain/tools/known_faults.py` | `0b84c9633603` | تصنيف الأعطال المعروفة |
| 18 | `brain/tools/merge_ledger_daily.py` | `3913f2552dae` | تعريف DATE (ع-4) |
| 19 | `brain/tools/ofac_screen.py` | `49fbfd38ac4f` | مطابقة IMO ثم الاسم الكامل (ع-3) |
| 20 | `brain/tools/ofac_targets_from_report.py` | `1e66324e1ee5` | فشل الاستخراج يمنع (ع-2) |
| 21 | `brain/tools/source_counts.py` | `3cddb99ec28f` | أرقام المصادر الثلاثة + حقن السطر في المتن والواجهة |
| 22 | `brain/tools/write_mark.py` | `21751a2d5079` | كتابة العلامة بعد البوابة بمخطط ثابت |
| 23 | `brain/validators/_guard.py` | `6207157bab10` | حارس الانهيار الموحّد — رمز 70 لكل مدقق |
| 24 | `brain/validators/check_backup_parity.py` | `81cdbca4c93c` | ربط الحارس الموحّد (رمز 70) |
| 25 | `brain/validators/check_carryover.py` | `91d67ca92316` | إضافة `import sys` (كشفه رمز 70) |
| 26 | `brain/validators/check_code_policy.py` | `8d3eb15457c7` | ربط الحارس الموحّد (رمز 70) |
| 27 | `brain/validators/check_code_spaces.py` | `f54a0c4936bf` | ربط الحارس الموحّد (رمز 70) |
| 28 | `brain/validators/check_comprehension.py` | `e27f39629c01` | ربط الحارس الموحّد (رمز 70) |
| 29 | `brain/validators/check_findings_closed.py` | `7549868dae14` | إضافة `import sys` (كشفه رمز 70) |
| 30 | `brain/validators/check_intel.py` | `e71ba7b350e0` | ربط الحارس الموحّد (رمز 70) |
| 31 | `brain/validators/check_internal_leak.py` | `4ed7c9b0b426` | بوابة منع تسرّب المحتوى الداخلي (تصحيح ك-136) |
| 32 | `brain/validators/check_language.py` | `aebb65070ef2` | ربط الحارس الموحّد (رمز 70) |
| 33 | `brain/validators/check_libraries_skills.py` | `e4f8eba3774a` | ربط الحارس الموحّد (رمز 70) |
| 34 | `brain/validators/check_library_use.py` | `1333f53031d3` | إصلاح `date` غير المعرّف (ع-4) |
| 35 | `brain/validators/check_mark_schema.py` | `1a82f99de7aa` | بوابة مخطط العلامة الثابت |
| 36 | `brain/validators/check_numerals.py` | `909ea9767dcb` | ربط الحارس الموحّد (رمز 70) |
| 37 | `brain/validators/check_ofac_coverage.py` | `6cbfd210963e` | إكمال الربط بالحارس الموحّد |
| 38 | `brain/validators/check_pdf_format.py` | `d53707d870d4` | ربط الحارس الموحّد (رمز 70) |
| 39 | `brain/validators/check_points_rule.py` | `ffea0730f01f` | ربط الحارس الموحّد (رمز 70) |
| 40 | `brain/validators/check_portable_paths.py` | `5952d8a71bc4` | ربط الحارس الموحّد (رمز 70) |
| 41 | `brain/validators/check_print_quality.py` | `d794e3657deb` | ربط الحارس الموحّد (رمز 70) |
| 42 | `brain/validators/check_prose_defects.py` | `e0f39a9aaf8e` | بوابة عيوب الكتابة (تصحيح ك-134 داخل الملف) |
| 43 | `brain/validators/check_run_completeness.py` | `0cb9ea151af6` | بوابة اكتمال التشغيل (الأعطال المعروفة) |
| 44 | `brain/validators/check_skills_integrity.py` | `9b6556d7a6cc` | ربط الحارس الموحّد (رمز 70) |
| 45 | `brain/validators/check_sources_count.py` | `a6a3ce056e29` | ربط الحارس الموحّد (رمز 70) |
| 46 | `brain/validators/check_style.py` | `71ebc124a14e` | ربط الحارس الموحّد (رمز 70) |
| 47 | `brain/validators/check_vocabulary.py` | `53e65f229705` | بوابة المفردات المبسطة (تنبيهية) |
| 48 | `brain/validators/validate_report.py` | `1ebc74f16efc` | ربط الحارس الموحّد (رمز 70) |
| 49 | `brain/web/meta/2026-10-23.json` | `814e2e04efb3` | حقول أرقام المصادر الثلاثة |
| 50 | `site/dist/404.html` | `a5c91e5dc725` | تعديل مرتبط بهذه الجولة |
| 51 | `site/dist/index.html` | `6b6ac0406896` | تعديل مرتبط بهذه الجولة |
| 52 | `site/dist/reports/2026-10-23.html` | `aec363d048d6` | تعديل مرتبط بهذه الجولة |
| 53 | `site/dist/reports/pdf/2026-10-23.pdf` | `950ce2cd949e` | تعديل مرتبط بهذه الجولة |
| 54 | `site/dist/reports/special-2026-10-15-GFS.html` | `b1d20042da6c` | تعديل مرتبط بهذه الجولة |
| 55 | `site/dist/reports/special-2026-10-17-Jubail-incidents.html` | `af66bf15c8e3` | تعديل مرتبط بهذه الجولة |
| 56 | `site/dist/reports/special-ach-hormuz-targeting-2026-10-16.html` | `960343268bd4` | تعديل مرتبط بهذه الجولة |
| 57 | `site/dist/reports/special-ach-hormuz-targeting-v3-2026-10-16.html` | `8968ece99104` | تعديل مرتبط بهذه الجولة |
| 58 | `site/dist/reports/special-exposure-denominator-2026-10-16.html` | `4117fd141cc1` | تعديل مرتبط بهذه الجولة |
| 59 | `site/dist/reports/special-gfs-pride-giselle-2026-10-15.html` | `95d7d4b3655e` | تعديل مرتبط بهذه الجولة |
| 60 | `site/generator/build_site.py` | `4329cbae2fdb` | تصحيح تسمية أرقام المصادر |
| 61 | `site/sources/meta/2026-10-23.json` | `814e2e04efb3` | تعديل مرتبط بهذه الجولة |
| 62 | `site/sources/reports/2026-10-23-sectioned.md` | `d049dd4a3fb2` | تعديل مرتبط بهذه الجولة |

## ما لم يُختبر
- لم تُشغَّل مهمة تلغرام ولم يُنشر الموقع (بطلب صاحب القرار).
- البوابة شُغّلت على 2026-10-23 فقط.
- مطابقة قائمة OFAC الحيّة عبر الشبكة لم تُختبر؛ المنطق اختُبر ببيانات اختبارية.
- المفردات المبسطة وقواعد الترجمة بالمعنى معلّقة ولم تُطبَّق على أي تقرير.

## الحالة الفعلية للبوابة
الخطوة المانعة الوحيدة: **عيوب الكتابة** — التقرير المنشور نفسه يحمل «عبورات» 6 مرات،
وقالب «- نفّذوا —» 8 مرات، ولم يُعدَّل النص المُسلَّم بلا موافقة صريحة.
