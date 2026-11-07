# خطة ربط أدوات وأدلة الجولة 2026-10-30

## السبب
أضافت جولتا hermetic وgoverning-chain أدوات واختبارات وأدلة دون ربطها بمانيفست `runbook/runbook.json`؛ لذلك يعرض `tools/runbook.py verify` الملفات غير المتصلة ويمنع برمز 2. لا نخفّض الفحص ولا نحذف أدلة أو اختبارات.

## التغيير المحدود
- إضافة خطوات `gates` قبل `G001`: لقطة Merkle وإلحاق ledger، بوابة ledger+الأصول، مالك أدوات التشغيل، واختبار `test_hermetic_run.py`.
- استعمال `links.files` للأدوات/الوثائق، و`links.folders` لمجلدات الأدلة recursive، و`links.tests` للاختبار.
- إبقاء `on_fail=stop` و`ok_rc=[0]`؛ ربط السلسلة بـ`&&` ثم حفظ رمز الخروج بـ`rc=$?; exit "$rc"`. نُظّف ملف `.pytest_cache/README.md` المولّد وحده بدل استثناءه من المنع.
- توليد `docs/runbook.md` من المانيفست، لا تحريره يدويًا.

## القبول القابل للقياس
1. `python3 tools/runbook.py handbook` ثم `python3 tools/runbook.py verify` يخرجان 0 بعد التغيير.
2. `python3 tests/test_manifest_commands.py` يخرج 0.
3. `python3 -m pytest -p no:cacheprovider -q tests/test_hermetic_run.py` يخرج 0.
4. اختبار سلبي حقيقي يثبت أن فشل الأمر الثاني في سلسلة `&&` يمنع الثالث ويحفظ الرمز.
5. ملف شارد مؤقت داخل `evidence/` يجعل `verify` يخرج 2، ثم تزال التجربة ويعود 0.
6. `append_only_ledger.py --verify` و`check_governing_assets.py --json` يعملان فشلًا مغلقًا؛ أي رمز غير صفري يوقف خطوة البوابة.
7. تشغيل `bash tools/restore_skills.sh` ثم `python3 validators/check_skills_integrity.py` في البداية، والتحقق مرتين في النهاية.
8. نافذة inotify مستقلة لا تقل عن 600 ثانية، و`CAUSALITY.md` يميز ما رُصد عما لم يثبت.

## الأثر والرجوع
نسخة المانيفست قبل التعديل: `/home/ubuntu/audit-2026-10-30/runbook.json.before`. الرجوع يقتصر على استعادة هذه النسخة ثم إعادة توليد الكتيب؛ لا تعديل للمهارات القائمة أو متن التقرير، ولا نشر أو Telegram أو git push.
