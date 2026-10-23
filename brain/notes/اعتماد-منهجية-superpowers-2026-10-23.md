# اعتماد مهارة المنهجية `superpowers-method` — 23 أكتوبر 2026

## أمر صاحب القرار
«gh repo clone obra/superpowers — أضف هذه المهارة سوف تساعدنا في عملنا حسب ما قرأته عنها».

## ما نُفِّذ
1. استُنسخ المستودع العام إلى `/home/ubuntu/superpowers` للفحص: الالتزام `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b` (2026-10-21)، 11 م.ب، 15 مهارة، رخصة MIT (`Copyright (c) 2025 Jesse Vincent`).
2. كُتب تقرير مطابقة كامل بالعربية: 15 مهارة (ما يُعتمد وما لا يُعتمد، والفروق الجوهرية، والنص الحرفي للرخصة) — `language-pack-01/10-superpowers-mapping.md`.
3. أُنشئت مهارة عربية مُكيّفة (لا نسخ ملفات إنجليزية): `/home/ubuntu/skills/superpowers-method/SKILL.md`، ونسختها في المستودع `skills/superpowers-method/SKILL.md` (المزامنة تُثبت التماثل: 15 ملفًا · مطابق 15).
4. رُبطت ببوابات التنفيذ:
   - `tools/skill_lessons.py` — حلقة التعلم الذاتي: تُستدعى في نهاية `tools/final_gate.sh` في كل تشغيل، وتسجّل نتيجة البوابة وعدد الموانع والتحذيرات والأعطال الجديدة، وتُحدّث كتلة «الدروس المتراكمة» في المهارة و`memory/learning-log.jsonl`.
   - `tools/restore_skills.sh` — أُدرجت في نطاق المزامنة ثنائية الاتجاه (`OUR_SKILLS` و`in_scope`).
   - `CLAUDE.md` — قاعدة «منهجية التطوير والتشخيص» بستة بنود (خطة قبل التغيير · اختبار يفشل أولًا · تشخيص بعد الفشل · دليل قبل الادعاء · حلقة تعلم دائمة · حدّ صريح).
   - `INDEX.md` — قسم «منهجية التطوير والتشخيص».

## المهارات الخمس المعتمدة (من الخمس عشرة)
`verification-before-completion` · `systematic-debugging` · `test-driven-development` · `writing-plans` · `diagnosing-superpowers`.

## ما لم يُعتمد
الخطافات (`hooks`) وإضافات محررات أخرى · `worktrees` وPR · استيراد المستودع كاملًا كطبقة تشغيل ثانية · `writing-skills` كمهارة يومية (مرجع صيانة فقط) · استعماله لكتابة الخبر أو تحديد المصطلح العسكري.

## أول تشغيل لحلقة التعلم (دليل)
```
$ python3 tools/skill_lessons.py --date 2026-10-23 --dry-run
{"gate_status": "warn", "gate_exit": 1, "steps": 44, "block": 0, "warn": 9,
 "new_faults": [], "report_sha16": "b68d144ea1a183e6"}
$ python3 tools/skill_lessons.py --date 2026-10-23
  • حلقة التعلم: نتيجة warn · أعطال جديدة: 0 · حُدّثت كتلة الدروس
```
