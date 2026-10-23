# PROJECT-DELTA — جولة 23 أكتوبر 2026 (ب): الشيفرة والمخرجات

البيان الأول حمل بصمات وشروحًا بلا شيفرة. هذا يحمل الشيفرة الكاملة في `شيفرة-الجولة-23-10-2026.md` والمخرجات الكاملة في `مخرجات-الجولة-23-10-2026.md`.

## 1) ملفات النظام والشيفرة والوثائق

| المسار | sha256 (16) | بايت | الشرح |
|---|---|---:|---|
| `PROJECT-DELTA.md` | `13e167bfd3041190` | 12459 | تحديث مرتبط بهذه الجولة. |
| `appendices/forbidden-coinages.json` | `33a97676ae3aca36` | 1256 | تحديث مرتبط بهذه الجولة. |
| `appendices/known-faults.json` | `0b632cce4c6e0914` | 2897 | لكل بند تاريخ بدء وانتهاء ومرجع عطل؛ والمنتهي يمنع. |
| `appendices/libraries/findings-2026-10-23.json` | `363617711ba1bb52` | 441476 | تحديث مرتبط بهذه الجولة. |
| `appendices/libraries/findings-register.md` | `ad9285ebd0d71c1b` | 2373 | تحديث مرتبط بهذه الجولة. |
| `appendices/libraries/lexicon-library.json` | `6b5e795ac02d59b0` | 269407 | تحديث مرتبط بهذه الجولة. |
| `appendices/libraries/lexicon-library.md` | `5c7291652797bb80` | 8784 | تحديث مرتبط بهذه الجولة. |
| `appendices/libraries/new-terms-register.json` | `64848dda9c085910` | 17219 | تحديث مرتبط بهذه الجولة. |
| `appendices/libraries/new-terms-register.md` | `38b67ff235a2bc55` | 8147 | تحديث مرتبط بهذه الجولة. |
| `appendices/libraries/orthography-consistency.md` | `e146a0a9d98b4609` | 4965 | تحديث مرتبط بهذه الجولة. |
| `appendices/libraries/recurring-phrases.md` | `ba83589a07b1b75f` | 4172 | تحديث مرتبط بهذه الجولة. |
| `appendices/libraries/terminology-gaps.md` | `ef11e8e4c67cd786` | 938 | تحديث مرتبط بهذه الجولة. |
| `appendices/simplified-vocabulary.json` | `3b3bf2c2fc6b8c9a` | 1795 | تحديث مرتبط بهذه الجولة. |
| `appendices/writing-rules.json` | `80f7d597699390cb` | 1193 | جديد — قواعد ما قبل الكتابة: حدّ القالب وبدائله والألفاظ التي تُستبدل آليًا. |
| `audit/تدقيق-شامل-كل-الإصدارات-2026-10-23.md` | `d409f07312e87af1` | 10818 | تحديث مرتبط بهذه الجولة. |
| `audit/سجل-الأعطال-والثغرات.md` | `1228610d314f7af0` | 123001 | تحديث مرتبط بهذه الجولة. |
| `memory/learning-log.jsonl` | `8a894d3b8f19ea38` | 230375 | تحديث مرتبط بهذه الجولة. |
| `notes/ع-2-ع-3-ع-4-2026-10-23.md` | `1f86407de33216b4` | 4253 | تحديث مرتبط بهذه الجولة. |
| `reports/2026-10-23-sectioned.md` | `82d785afe7b9ebf7` | 31011 | تصحيح لغوي لتقرير 23 (لغة فقط: لفظ مصطنع وقالب متكرر). |
| `sections/20-language.md` | `2a34d88ef3bf45f4` | 6916 | تحديث مرتبط بهذه الجولة. |
| `sections/60-validation.md` | `ab8f898ca6b77bb0` | 27460 | تحديث مرتبط بهذه الجولة. |
| `skills/marine-news-brain/SKILL.md` | `650aa6f665249a53` | 8499 | قواعد ما قبل الكتابة الملزمة في مهارة التشغيل. |
| `templates/mark-schema.json` | `74f394f91064d11d` | 731 | تحديث مرتبط بهذه الجولة. |
| `tests/run_checks.sh` | `fd75d675f327cf6f` | 9151 | تحديث مرتبط بهذه الجولة. |
| `tests/test_language.sh` | `0ff73f87e650768a` | 4640 | تحديث مرتبط بهذه الجولة. |
| `tests/test_ofac.sh` | `0f01bf87a2fad268` | 2686 | تحديث مرتبط بهذه الجولة. |
| `tools/daily_pipeline.sh` | `50f9fa353da8b483` | 13255 | تحديث مرتبط بهذه الجولة. |
| `tools/final_gate.sh` | `3f663984e2a8b9a1` | 15576 | ربط خطوة الإصلاح الآلي، وتنبيه إيقاف التسليم في logs/alerts/. |
| `tools/known_faults.py` | `212e007667f57dfd` | 4609 | انتهاء صلاحية العطل المعروف يمنع التسليم؛ وفصل النص المختصر عن الكامل. |
| `tools/merge_ledger_daily.py` | `3913f2552dae6c6f` | 15853 | تحديث مرتبط بهذه الجولة. |
| `tools/ofac_screen.py` | `49fbfd38ac4f4255` | 9977 | تحديث مرتبط بهذه الجولة. |
| `tools/ofac_targets_from_report.py` | `1e66324e1ee523e6` | 2892 | تحديث مرتبط بهذه الجولة. |
| `tools/repair_prose.py` | `d07e712e698c3b3b` | 4033 | جديد — خطوة الإصلاح الآلي الواحدة قبل إعادة البوابة (البند 8). |
| `tools/source_counts.py` | `9d8edf3f78bf5429` | 10154 | سطر الإفصاح في المتن يحمل مرجع العطل وتاريخ انتهاء صلاحيته. |
| `tools/write_mark.py` | `21751a2d5079556f` | 4194 | تحديث مرتبط بهذه الجولة. |
| `validators/_guard.py` | `6207157bab105f14` | 1898 | تحديث مرتبط بهذه الجولة. |
| `validators/check_backup_parity.py` | `81cdbca4c93c7100` | 9318 | تحديث مرتبط بهذه الجولة. |
| `validators/check_carryover.py` | `91d67ca92316105c` | 10978 | تحديث مرتبط بهذه الجولة. |
| `validators/check_code_policy.py` | `8d3eb15457c70cd8` | 3884 | تحديث مرتبط بهذه الجولة. |
| `validators/check_code_spaces.py` | `f54a0c4936bfede9` | 5795 | تحديث مرتبط بهذه الجولة. |
| `validators/check_comprehension.py` | `e27f39629c01c154` | 20869 | تحديث مرتبط بهذه الجولة. |
| `validators/check_findings_closed.py` | `7549868dae14d128` | 7118 | تحديث مرتبط بهذه الجولة. |
| `validators/check_intel.py` | `e71ba7b350e080ca` | 9352 | تحديث مرتبط بهذه الجولة. |
| `validators/check_internal_leak.py` | `4ed7c9b0b4264d52` | 5491 | تحديث مرتبط بهذه الجولة. |
| `validators/check_language.py` | `aebb65070ef229d2` | 5248 | تحديث مرتبط بهذه الجولة. |
| `validators/check_libraries_skills.py` | `e4f8eba3774aa4d2` | 16526 | تحديث مرتبط بهذه الجولة. |
| `validators/check_library_use.py` | `1333f53031d39000` | 10660 | تحديث مرتبط بهذه الجولة. |
| `validators/check_mark_schema.py` | `1a82f99de7aa8093` | 3180 | تحديث مرتبط بهذه الجولة. |
| `validators/check_numerals.py` | `909ea9767dcbdbff` | 3953 | تحديث مرتبط بهذه الجولة. |
| `validators/check_ofac_coverage.py` | `6cbfd210963e26b8` | 3243 | تحديث مرتبط بهذه الجولة. |
| `validators/check_pdf_format.py` | `d53707d870d440c0` | 11300 | تحديث مرتبط بهذه الجولة. |
| `validators/check_points_rule.py` | `ffea0730f01fd04b` | 4512 | تحديث مرتبط بهذه الجولة. |
| `validators/check_portable_paths.py` | `5952d8a71bc4f118` | 3775 | تحديث مرتبط بهذه الجولة. |
| `validators/check_print_quality.py` | `d794e3657debe620` | 16897 | تحديث مرتبط بهذه الجولة. |
| `validators/check_prose_defects.py` | `425224eae6fdfcb2` | 17647 | إصلاح إنذار كاذب: أسطر الجداول تُستثنى من قاعدة القالب المتكرر. |
| `validators/check_run_completeness.py` | `2da64d62e3ffa150` | 3102 | الإفصاح بالنص المختصر، والعرض في المتن بالنص الكامل مع مرجع العطل وتاريخ الانتهاء. |
| `validators/check_skills_integrity.py` | `9b6556d7a6ccd9c0` | 3769 | تحديث مرتبط بهذه الجولة. |
| `validators/check_sources_count.py` | `a6a3ce056e299511` | 7242 | تحديث مرتبط بهذه الجولة. |
| `validators/check_style.py` | `71ebc124a14ea419` | 13789 | تحديث مرتبط بهذه الجولة. |
| `validators/check_vocabulary.py` | `53e65f22970512c4` | 2599 | تحديث مرتبط بهذه الجولة. |
| `validators/validate_report.py` | `1ebc74f16efcee34` | 14744 | تحديث مرتبط بهذه الجولة. |
| `watchlist/ofac-targets.txt` | `9f694820b9708e24` | 102 | تحديث مرتبط بهذه الجولة. |
| `شيفرة-الجولة-23-10-2026.md` | `4a79cb07f1deeb94` | 104346 | الشيفرة الكاملة للملفات المتغيّرة والجديدة. |
| `فرق-تصحيح-تقرير-23.md` | `9b393f60e356577d` | 7893 | فرق النص قبل/بعد لتصحيح تقرير 23. |
| `مخرجات-الجولة-23-10-2026.md` | `fa0b4736c8abef15` | 24511 | مخرجات كاملة: الاختبارات والبوابة وgate.json والعلامة. |
| `معايرة-البوابات-11-تقريرًا.md` | `36fb391e11c90e0b` | 3230 | معايرة البوابتين على التقارير الإحدى عشر والإنذارات الكاذبة. |

## 2) ملفات مُنتَجة آليًا بإعادة البناء (بيانات ومزامنة، لا شيفرة)

| المسار | sha256 (16) | بايت |
|---|---|---:|
| `archive/ofac-screen-latest.json` | `d3a2726c301b9eb3` | 2242 |
| `web/meta/2026-10-23.json` | `814e2e04efb34e30` | 32063 |

## 3) أرقام الالتزامات — ما يغطيه كل رقم

| الالتزام | ما يغطيه |
|---|---|
| `9462146` | نسخة الاحتياط بعد إصلاحات ح-1..ح-4 وع-2..ع-4 (قبل قواعد ما قبل الكتابة). |
| `7b9b61d` | إضافة قواعد الكتابة الملزمة في `sections/20-language.md` وتحديث البيان. |
| `d69d9ae` | تحديث سطر الالتزامات داخل `PROJECT-DELTA.md` نفسه. |
| التزام هذه الجولة | `tools/repair_prose.py` · `appendices/writing-rules.json` · انتهاء صلاحية الأعطال · إصلاح قاعدة الجداول · تصحيح لغة تقرير 23 · ملفات المخرجات والشيفرة والمعايرة والفرق. |

سبب الخلط في البيان الأول: بصماته قِيست على شجرة عمل تغيّرت بعده. هذا البيان مقيس بعد آخر تعديل.

## 4) ملفات الموقع المنشورة: تغيّر الملف لا النص

- 24 صفحة HTML متعقّبة · **21 صفحة متنها مطابق تمامًا** بين `HEAD` وشجرة العمل.
- 3 صفحات تغيّر متنها: `index.html` و`404.html` (بطاقة «آخر إصدار») و`reports/2026-10-23.html` (تصحيح لغة اليوم).
- الصفحات الخاصة الست تغيّر ملفها فقط (هيكل مشترك) ونصّها مطابق حرفيًا.
- **لا نشر ولا إرسال إلى تلغرام**: صفر التزامات غير مدفوعة في مستودع الموقع، والتغييرات غير مُلتزمة، ولم يُشغَّل أمر الإغلاق.

