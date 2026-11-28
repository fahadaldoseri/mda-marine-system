# SKILLS-USED — المهارات

> تاريخ الكتابة: 2026-11-28 (البحرين)
> الفرع: handover/grok-2026-11-28
> الأساس: الالتزام الأب 66f16c9364e744db4697c622dec508ac16248e67، بعد دمج main (يضم a214ac7d4331f467e406aaa104dfedcc760fb988)
> المشغّل المنتهية مهمته: Claude

## 1. ما يستدعيه الخط اليومي فعلًا (من `brain/runbook/runbook.json`)

لا خطوة في المانيفست تستدعي مهارة وقت التشغيل العادي إلا ما يُقرأ في `reads` أو يُشار إليه في مسار الإصلاح. مسارات المهارات داخل `brain/skills/`، وتُنسخ في السحابة إلى `/home/ubuntu/skills` بـ`brain/tools/cloud_env_prep.sh`.

| المهارة | المسار | الخطوة | الوظيفة |
|---|---|---|---|
| runbook-operations-ops | `brain/skills/runbook-operations-ops/SKILL.md` | W010 (يقرؤها الكاتب) | تنفيذ المانيفست المقفل وتفسير رموز الخروج وإتمام الجولة |
| approved-output-change-ops | `brain/skills/approved-output-change-ops/SKILL.md` | G018A | ضبط أي تغيير يمس مخرجًا معتمدًا بقياس قبل/بعد |
| macr-system | `brain/skills/macr-system/SKILL.md` | G018A | إطار إعداد التقارير العسكرية التكيفي |
| map-clarity-ops | `brain/skills/map-clarity-ops/SKILL.md` | G018A | وضوح تسميات الخريطة وفصل العلامات |
| marine-news-brain | `brain/skills/marine-news-brain/SKILL.md` | G018A | إعداد تقرير الصباح البحري العربي |
| military-arabic-editing | `brain/skills/military-arabic-editing/SKILL.md` | G018A | تحرير عربي عسكري لا يبدو مترجمًا |
| source-coverage-route-ops | `brain/skills/source-coverage-route-ops/SKILL.md` | G018A | إغلاق فجوات تغطية المصادر |
| bilingual-master-direction-ops | `brain/skills/bilingual-master-direction-ops/SKILL.md` | B009 | اتجاه الحقيقة بين اللغتين (الأصل العربي) |
| portable-paths-repair-ops | `brain/skills/portable-paths-repair-ops/SKILL.md` | G026 | إصلاح موانع قابلية النقل |
| rerun-step-to-live-parity-ops | `brain/skills/rerun-step-to-live-parity-ops/SKILL.md` | G068 | استئناف خطوة نشر وإثبات تطابق القناة الحية |

القائمة من قراءة أسماء المسارات في `runbook.json` فقط؛ كون الخطوة تستدعي المهارة فعلًا في كل تشغيل **غير مقاس** (التشغيل الأخير لم يبلغ هذه الخطوات). مجلد `brain/skills/` يضم مهارات أخرى كثيرة (نحو 30 فأكثر) غير مذكورة في المانيفست.

## 2. المهارات الثلاث المعلّقة منذ 20 نوفمبر

مهارات المستخدم (لا في هذا المستودع): `seawatch-daily-run` و`seawatch-geo-style-guide` و`seawatch-blocked-sources-registry`. **ليست في هذا المستودع** (لا ملف بهذه الأسماء). القاعدة (فهد 20 نوفمبر 15:46 بالبحرين): تُحدَّث مع كل تغيير، لكن لا يُطبَّق تحديث قبل موافقته عبر بطاقة اقتراح مهارة.

ما تغيّر بعد 20 نوفمبر ويحتاج موافقة (بلا تعديل للمهارة، ولا أعرف محتواها الحالي فأحكم عليها): 
- **seawatch-daily-run**: انتقل التشغيل من مهمة Claude المجدولة 04:40 إلى GitHub Actions `daily.yml` (دمج 675)، ثم أُوقف cron بالالتزام a214ac7 (28 نوفمبر)؛ حكم النشر 0/3؛ الإصلاح الذاتي (#672)؛ S074 (#673)؛ رقم الحادث `YY-NNNN` (#670)؛ إجابات احتياطية `fallback-answers/`.
- **seawatch-geo-style-guide**: صيغة الإجراء بصيغة المصدر (19 نوفمبر)، المعجم العسكري (15 تصحيحًا، `9868339`)، رقم الحادث ورقم البلاغ.
- **seawatch-blocked-sources-registry**: بدائل رسمية لمصادر 30 و36 و45 و46 و47 (20 نوفمبر)، وG033 بحدّ 12 وأنماط الحجب (27 نوفمبر).
لا بطاقة اقتراح لأي منها سُجّلت بعد 20 نوفمبر في الذاكرة (**غير مسترجع** إن وُجدت).

## 3. graphify

حُفظت مهارة «graphify» بتاريخ 26 نوفمبر (غلاف يثبّت graphifyy 0.9.120) بحسب الذاكرة. **ليست في هذا المستودع.** المخرج الوحيد المعروف: `/mnt/project-files/graphify-2026-11-26/` (`GRAPH_REPORT.md` و`graph.html`) في ملفات المشروع لا في Git. قاعدتها: التحليل الدلالي للوثائق مكلف فيُسأل فهد قبله.
