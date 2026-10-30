# دليل تشديد إعلانات الأدلة

التاريخ: 2026-10-30

هذا الدليل يسجل الأوامر الفعلية ورموزها. لم يُشغّل `runbook.py run`، ولم يحدث نشر أو Telegram.

## 1. الحواجز والمانيفست

```text
$ bash tools/restore_skills.sh
RC=0
المخرج: ملفات المستودع 3247 · نُزّل 0 · رُفع 0 · مطابق 41 · التماثل سليم

$ python3 validators/check_skills_integrity.py
RC=0
المخرج: كل القواعد المعتمدة مثبتة

$ python3 tools/runbook.py verify
RC=0
المخرج: تحذير D005 فقط، ثم المانيفست متسق
```

أُزيل الاستثناء العام `"*.txt"` من `runbook/runbook.json`، وأُعيد توليد `docs/runbook.md`:

```text
$ python3 tools/runbook.py handbook
RC=0
$ python3 tools/runbook.py verify
RC=0
```

حالة الإعلانات بعد التضييق: `NONEMPTY_LINKS_FOLDERS=0`، ولا توجد مفاتيح `links.folders` متبقية (`ALL_LINKS_FOLDERS_KEYS=0`).

## 2. اختبار الشارد المعمّم

بعد الإصلاح، أُنشئ `evidence/hermetic/__stray-a.txt` و`evidence/merkle/__stray-b.txt`:

```text
$ python3 tools/runbook.py verify
RC=2
النتيجة: 2 خلل؛ سُمّي الملفان حرفيًا:
- evidence/hermetic/__stray-a.txt
- evidence/merkle/__stray-b.txt

بعد حذف الملفين:
$ python3 tools/runbook.py verify
RC=0

أُنشئ `evidence/hermetic/__stray-unusual.bin`:
$ python3 tools/runbook.py verify
RC=2
النتيجة: 1 خلل؛ سُمّي evidence/hermetic/__stray-unusual.bin

بعد حذفه:
$ python3 tools/runbook.py verify
RC=0
```

كل الشوارد التجريبية غائبة الآن. العطل المكتشف قبل الإصلاح (تجاهل `.txt`) سُجل كـك-364 وأُغلق بالدليل الحي.

## 3. الاختبارات

```text
$ python3 tests/test_manifest_commands.py
RC=0
106 استدعاء سكربت في المانيفست: كلها موجودة وخياراتها معرَّفة

$ python3 -m pytest -p no:cacheprovider -q tests/test_hermetic_run.py
RC=0
7 passed in 27.77s
```

## 4. البوابات المطلوبة

G000 شُغّل بالنص الداخلي المطابق للمانيفست مباشرة، بعد فشل غلاف اقتباس أولي غير مطابق للأمر (ذلك الغلاف فقط خرج 2):

```text
$ python3 tools/governing_assets_merkle.py --snapshot && snapshot="evidence/merkle/snapshot.json" && root="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["root"])' "$snapshot")" && files="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["file_count"])' "$snapshot")" && python3 tools/append_only_ledger.py --append --kind snapshot --root "$root" --files "$files"; rc=$?; exit "$rc"
RC=0
snapshot root=c6396949f426da93dfce8229ace3ff851b166bcd9fe76c552a79a05fc630ade7 · files=2629 · ledger seq=6

$ python3 tools/append_only_ledger.py --verify && python3 tools/check_governing_assets.py --json; rc=$?; exit "$rc"
G000A RC=2
ledger: verified, entries=6; check_governing_assets: BLOCK; violations=5
```

مخالفات G000A الخمس: غياب `hermetic-live-probe-ops/SKILL.md` و`hermetic-live-probe-ops/scripts/live_probe_batch.py` من المرآة، اختلاف `writing-rules-wiring-ops/SKILL.md`، ووجود `approved-output-change-ops/references/print-fingerprint-contract.md` و`writing-rules-wiring-ops/references/writer-visibility-contract.md` في المرآة دون المحلي. لم تُعدّل أي مهارة أو مرآة ضمن القيود.

لم تُشغّل G000B ولا G000C لأن G000A مانعة، تطبيقًا لقاعدة عدم تجاوز خطوة فاشلة. لذلك لا يوجد رمز نجاح لهما.

## 5. الأعطال والإغلاق

- **ك-363:** انحراف مرآة المهارات الذي منع G000A؛ الحالة التشغيلية مفتوحة/محجوبة، مع استثناء مؤقت ودليل `G000A RC=2`.
- **ك-364:** الاستثناء العام `*.txt` الذي أخفى شوارد الأدلة؛ الإصلاح منفذ والحالة مغلقة.
- `python3 tools/closure_round.py --apply` الأخير: `RC=0`، 399 صفًا، 0 دروس مشتقة، وثبات كامل.
- `python3 validators/check_closure.py` (التمرير الأول): `RC=0`، فاشل 0.
- `python3 validators/check_closure.py` (التمرير الثاني): `RC=0`، فاشل 0.
- التحقق النهائي بعد الإغلاق: `python3 tools/runbook.py verify` → `RC=0` (D005 تحذير غير مانع).

## 6. الأرشيف

`/home/ubuntu/audit-2026-10-30/backups-declare/` يحتوي 395 ملف دليل قديمًا بعد تحقق SHA-256، و`backup-manifest.json`، ونسخة `runbook-runbook.json` السابقة. بصمة النسخة السابقة المتحققة: `b4ec6e5e0f64278b1bceace1b33a43235723836db89d81ff04939cdf2a32324b`. إجمالي الملفات في الأرشيف: 397.

المخرج غير المكتمل الوحيد: G000A بقي مانعًا بسبب انحراف المهارات/المرآة الذي لا تسمح القيود بإصلاحه؛ وبناءً عليه لم تُنفّذ G000B/G000C.
