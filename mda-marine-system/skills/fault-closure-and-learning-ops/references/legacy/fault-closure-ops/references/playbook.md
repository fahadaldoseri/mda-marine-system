# دليل الجولة الكاملة — مرجع

## قبل البدء
1. **نسخة احتياطية** للسجلين قبل أي تحويل: `audit/backups/<round>-<طابع زمني>/`.
2. حدّد `BRAIN` (جذر المشروع) و`SITE` (جذر الموقع) — ولا تكتب مسارًا مطلقًا في أي ملف تنفيذي.

## الجولة

### المرحلة 1 — قياس الوضع
```bash
python3 scripts/check_closure.py --brain "$BRAIN" | tail -3      # الحالة قبل
python3 scripts/closure_round.py --brain "$BRAIN" --dry-run      # ما سيُغيَّر
grep -c '^| ' "$BRAIN/audit/سجل-الأعطال-والثغرات.md"             # عدد الصفوف
wc -l "$BRAIN/memory/learning-log.jsonl"                          # عدد الدروس
```

### المرحلة 2 — التوحيد والاشتقاق
```bash
python3 scripts/closure_round.py --brain "$BRAIN" --apply
```
المخرَج المتوقّع: `استثناءات · تتبع · مغطى بدرس · دروس مشتقة` + `ثبات كامل (سجل + تعلم): نعم ✔`.

### المرحلة 3 — الأدلة الحيّة
لكل صف «مغلق» لا يظهر له دليل:
1. اقرأ نصّه واستخرج **اسم الأداة/البوابة** المذكورة.
2. شغّلها الآن وسجّل رمز الخروج.
3. اكتب الأدلة في ملف `evidence.json` بالصيغة:
```json
{"ك-04": "تحقق حي 2026-10-28: python3 validators/check_portable_paths.py → خرج 0"}
```
4. أدخلها:
```bash
python3 scripts/insert_live_evidence.py --brain "$BRAIN" --map evidence.json
python3 scripts/closure_round.py --brain "$BRAIN" --apply
```

**إن فشلت أداة فعلًا:** لا تُجمّل الدليل. أصلح العطل، سجّله بـ`record_fault.py`، ثم أثبت بعد الإصلاح.

### المرحلة 4 — الحارس والاختبار العدائي
```bash
python3 scripts/check_closure.py --brain "$BRAIN"; echo "exit=$?"
python3 scripts/test_closure_gate.py
```
الاختبار العدائي يحقن: دليلًا فارغًا · دليلًا نصّيًا · حالة غير معروفة · صفًا بلا درس · معرّفًا غير موجود — وكلها يجب أن **تُمنع**؛ وصفًا صحيحًا يجب أن **يمرّ**.

### المرحلة 5 — الإصلاحات البنيوية
```bash
python3 scripts/check_portable_paths.py --brain "$BRAIN" --site "$SITE"   # لا مسار مطلق
python3 tools/preflight_check.py                                          # ما قبل التشغيل
```
أي فشل هنا عطل حقيقي يُسجَّل ويُصلح، لا يُستثنى.

### المرحلة 6 — الدفع والتماثل
```bash
git -C "$BRAIN" status --porcelain
python3 tools/sync_to_repo.py --brain "$BRAIN" --repo <REPO>/brain
git -C <REPO> checkout -b fix/<round> && git -C <REPO> add -A && git -C <REPO> commit -m "<وصف>"
git -C <REPO> push -f origin HEAD
gh pr create --repo <OWNER/REPO> --base main --head fix/<round> --title "<عنوان>" --body "<مضمون>"
gh pr merge <N> --repo <OWNER/REPO> --merge --delete-branch
```
ثم: `git fetch origin main && git checkout main && git merge --ff-only origin/main` وتحقق التماثل.
**لا دفع مباشر إلى الفرع الرئيسي** حتى لو لم توجد حماية تقنية.

## قواعد التوقف
| الحالة | الفعل |
|---|---|
| الحارس يمنع وسببه نقص دليل | أضف دليلًا حيًّا ثم أعد |
| الحارس يمنع وسببه عطل فعلي | أصلحه وسجّله ثم أعد |
| عطل موروث بلا أي أثر تشغيل | استثناء بمهلة + مالك، لا إغلاق |
| أداة انهارت | عالج الانهيار كمنع (رمز 70) وأصلح المدقق |

## الأثر المطلوب في نهاية الجولة
- `check_closure` = مجتاز، و`exit=0`.
- `test_closure_gate` = كل الحالات ✔.
- `check_portable_paths` = 0.
- تماثل الشجرة والمستودع = مطابق.
- الأعطال الجديدة مسجّلة بسبب جذري ودرس وحاجز.
- تقرير أرقام فعلي: صفوف · مغلق · مستثنى · فاشل · ثبات · دروس مشتقة.