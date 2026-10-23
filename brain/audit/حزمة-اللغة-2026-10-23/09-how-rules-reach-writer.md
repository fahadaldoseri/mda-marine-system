# 09 — كيف تتصل القواعد بالكاتب (بأدلة: ملف وسطر)

## 1) ما يدخل فعلاً في سياق الكاتب لحظة الكتابة

| ما يدخل | عدد الكلمات |
| --- | ---: |
| `الأمر اليومي المجدول (detail)` | 685 |
| `مهارة marine-news-brain/SKILL.md` | 792 |
| `مهارة military-arabic-editing/SKILL.md` | 599 |
| `CLAUDE.md (الأوامر المستديمة)` | 278 |
| `sections/20-language.md` | 860 |
| `sections/75-style.md` | 2619 |
| `sections/40-blocks.md` | 1252 |
| `appendices/terminology.md` | 2996 |
| `appendices/commander-style.md` | 124 |
| `appendices/style-blacklist.json` | 2319 |
| `appendices/forbidden-coinages.json` | 107 |
| `appendices/simplified-vocabulary.json` | 158 |
| `appendices/writing-rules.json` | 300 |
| `appendices/libraries/lexicon-library.md` | 1833 |

**الترتيب الفعلي**: (1) الأمر اليومي المجدول (685 كلمة) يوجب قراءة `INDEX.md` أولًا؛ (2) `INDEX.md` يوجب ترتيب القراءة 1→12، وفيه `sections/20-language.md` في الترتيب 3 و`sections/75-style.md` في الترتيب 9 (سطرا 18 و24 من `INDEX.md`)؛ (3) الأمر يستدعي مهارتين بالاسم: Marine News Brain وmilitary-arabic-editing؛ (4) جداول الملاحق مرتبطة داخل `INDEX.md` (سطور 52 و53 و57: `terminology.md` لـ20-language · `report-blocks.md` لـ40-blocks · `commander-style.md` لـ20-language).

## 2) ما لا يدخل تلقائيًا — يبقى في ملفات يقرؤها الفحص لا الكاتب

بقياس فعلي على نص الأمر اليومي (عدد مرات الذكر):

| المُصطلح في نص الأمر | عدد الذكر |
| --- | ---: |
| CLAUDE | 0 |
| style-blacklist | 0 |
| 75-style | 0 |
| 20-language | 0 |
| commander | 0 |
| terminology | 0 |
| military-arabic | 1 |
| أسلوب | 1 |

أي: قائمة المحظورات (`style-blacklist.json`) وقائمة الألفاظ المصطنعة (`forbidden-coinages.json`) وقائمة المفردات المبسطة (`simplified-vocabulary.json`) وقواعد الإصلاح (`writing-rules.json`) و`CLAUDE.md` **لا تُذكر في الأمر**، فلا تصل للكاتب إلا إن قرأها بنفسه من `INDEX.md` (و`INDEX.md` يذكر `style-blacklist` في سطر 158 و`forbidden-coinages` في سطر 58 من `20-language.md`).

## 3) هل يرى الكاتب قائمة المحظورات قبل الكتابة أم بعدها فقط؟

- **بعد الكتابة في البوابة** بالدرجة الأولى: `tools/final_gate.sh:80` (`repair_prose.py`) و`:99` (`check_style.py`) و`:100` (`check_language.py`) و`:139` (`check_prose_defects.py`).
- **قبل الكتابة** لا يصل إليه منها إلا ما يقرؤه طوعًا: `sections/20-language.md:58` (قاعدة منع اللفظ المصطنع، وتحيل إلى `forbidden-coinages.json`) و`sections/75-style.md` (يذكر `style-blacklist`).
- مَن يقرأ أي ملف من قوائم المنع (بأمر بحث): `forbidden-coinages.json` → `validators/check_prose_defects.py` · `simplified-vocabulary.json` → `validators/check_vocabulary.py` · `writing-rules.json` → `tools/repair_prose.py` · `style-blacklist.json` → `validators/check_style.py` و`check_prose_defects.py` و`tools/style_learn.py` و`tools/audit_corpus.py`.

## 4) هل يُعطى أمثلة «قبل/بعد» في سياقه؟

- **لا**. الأمر الذي أثبت العدم:
```
$ grep -rln "قبل:\s*$\|بعد:\s*$" appendices/ sections/ docs/ audit/  → لا نتائج
$ grep -rn "«قبل» و«بعد»\|قبل وبعد" appendices/*.md sections/*.md  → لا نتائج
```
- الموجود بدلًا منها: استبدالات مباشرة في `appendices/simplified-vocabulary.json` (شكل: `term` ← `plain`) و`appendices/writing-rules.json` (`term` ← `replacement`)، وهي أقرب إلى قاموس استبدال من مثال «قبل/بعد» سياقي.

## 5) ملاحظة القياس
- أعداد الكلمات محسوبة بـ `wc -w` على الملفات نفسها، والأمر اليومي من `manus-config schedule status` (الحقل `detail`).
