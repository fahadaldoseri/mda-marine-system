# الحاوية المحكمة `hermetic_run.sh`

## البنية

`tools/hermetic_run.sh` لا يمرر الأمر إلى shell المضيف؛ كل ما بعد الفاصل `--` يتحول إلى `argv`. المسار الأساسي يستخدم:

```text
bwrap --unshare-all --die-with-parent --unshare-net \
  --ro-bind / / --tmpfs /tmp --proc /proc --dev /dev \
  --bind <workdir> <workdir> --chdir <workdir>
```

مجلد العمل يُنشأ افتراضيًا تحت `/var/tmp`، ويُرفض صراحةً إذا كان داخل `/home/ubuntu/brain-marine-news` أو `/home/ubuntu/seawatch`. لذلك لا يُفتح أي bind قابل للكتابة داخل شجرتَي المشروع. الجذر للقراءة فقط، و`/tmp` داخل الحاوية `tmpfs`. البيئة تُمسح وتُعاد تهيئتها بقيم آمنة (`PATH`, `HOME=/tmp`, `TMPDIR=/tmp`).

كل تشغيل يلتف بـ`timeout` (الافتراضي 60 ثانية، قابل للتغيير بـ`--timeout`) وبـ`strace -f -qq -o <trace> -e trace=%file,%network,execve`. إذا رفض strace صيغة الاختصار يستخدم `openat,open,connect,execve`. يلخص parser داخلي ملفات الفتح للكتابة، ومحاولات `connect`، و`execve`.

يحاول السكربت أولًا `systemd-run --scope -p MemoryMax=… -p CPUQuota=… -p TasksMax=…`. في هذه البيئة كان `systemd-run` موجودًا لكن إنشاء scope فشل فعليًا بـ`Access denied` (رمز 1)، فاستُخدم `ulimit` للذاكرة/زمن CPU/عدد الخيوط مع `timeout`. حد `RLIMIT_NPROC` في fallback يُحسب من عدد خيوط المستخدم القائمة + `TasksMax` حتى لا يُخنق الغلاف نفسه.

## إعادة التشغيل

من جذر المشروع:

```bash
./tools/hermetic_run.sh --help
./tools/hermetic_run.sh --timeout 60 -- python3 -c "print('read-only')"
python3 -m pytest -q tests/test_hermetic_run.py
```

كل تشغيل يكتب:

- `evidence/hermetic/<tool>-<timestamp>-<pid>.json`
- `evidence/hermetic/traces/<tool>-<timestamp>-<pid>.strace`
- بصمات قبل/بعد لكل ملف عادي أو رابط رمزي في الشجرتين تحت `evidence/hermetic/fingerprints/`.

مقارنة الأثر تستبعد فقط `evidence/hermetic/**` لأنها مخرجات الحارس نفسه؛ كل المسارات الأخرى في `/home/ubuntu/brain-marine-news` و`/home/ubuntu/seawatch` داخلة في بصمات SHA-256. هذا الاستثناء يمنع أن يُحسب إنشاء الدليل الذاتي كضرر من الأداة.

## التجارب الحية والقياسات

| التجربة | الأمر/السلوك | رمز الخروج | `net_packets` | الملفات المتغيرة خارج العزل | دليل JSON |
|---|---|---:|---:|---:|---|
| قراءة موجبة | قراءة أول سطر من `CLAUDE.md` | 0 | 0 | 0 | [`read-only-proof-20261030T174758Z-1418733.json`](./read-only-proof-20261030T174758Z-1418733.json) |
| كتابة سالبة | سكربت يحاول إنشاء `.hermetic-direct-write-*` داخل المشروع؛ طبع `WRITE_FAILED:OSError` | 7 | 0 | 0 | [`write-attempt-20261030T174804Z-1418802.json`](./write-attempt-20261030T174804Z-1418802.json) |
| شبكة سالبة | `socket.create_connection(('1.1.1.1',80),3)` | 1 | 0 | 0 | [`network-attempt-20261030T174809Z-1418889.json`](./network-attempt-20261030T174809Z-1418889.json) |
| مهلة سالبة | `while True: pass` مع `--timeout 1` | 124 | 0 | 0 | [`timeout-limit-20261030T174814Z-1418956.json`](./timeout-limit-20261030T174814Z-1418956.json) |

في التجارب الأربع فشل probe الشبكة الداخلي المعروف برمز 1 مع `OSError: [Errno 101] Network is unreachable`. وفي تجربة الشبكة سجل trace محاولتي `connect` (probe + الأداة)، وفي القراءة/الكتابة/المهلة سجل probe محاولة واحدة. عدّ الحزم من فروق عدادات `/proc/net/dev` داخل namespace، وبقي صفرًا في كل تجربة. تجربة المهلة استغرقت 1036ms تقريبًا وأعاد `timeout` الرمز 124.

مسارات trace الخام للتجارب الأربع:

- `/home/ubuntu/brain-marine-news/evidence/hermetic/traces/read-only-proof-20261030T174758Z-1418733.strace`
- `/home/ubuntu/brain-marine-news/evidence/hermetic/traces/write-attempt-20261030T174804Z-1418802.strace`
- `/home/ubuntu/brain-marine-news/evidence/hermetic/traces/network-attempt-20261030T174809Z-1418889.strace`
- `/home/ubuntu/brain-marine-news/evidence/hermetic/traces/timeout-limit-20261030T174814Z-1418956.strace`

## الإصدارات والقياسات الحرفية

- `bubblewrap 0.9.0`.
- `unshare from util-linux 2.39.3`.
- `strace 6.8`.
- `systemd 255.4-1ubuntu8.17`؛ scope مرفوض بـ`Access denied`، ولذلك كان `resource_limits.mode=ulimit+timeout` في الأدلة.
- تثبيت الحزم الأول قبل تحديث الفهارس خرج 100 (`Unable to locate package`). بعد `sudo apt-get update` خرج 0، ثم `sudo apt-get install -y bubblewrap strace python3-pytest` خرج 0.

## الفرق بين `bwrap` و`unshare`

`bwrap` يركب root للقراءة فقط صراحةً، وينشئ `tmpfs` لـ`/tmp`، ويمنح الكتابة لـworkdir المحدد فقط؛ لذلك هو المسار المعتمد. fallback `unshare --user --map-root-user --mount --pid --net --ipc --uts --fork --mount-proc` ينشئ namespaces مماثلة، ثم يحاول remount للـroot وشجرتَي المشروع للقراءة فقط وworkdir للكتابة. لكنه لا يقدم ضمان bind-root نفسه الذي يقدمه bwrap، ولذلك هو أضعف ومذكور صراحةً في JSON؛ وإذا فشلت mounts يخرج 70 بدل التشغيل غير الآمن. لم يُستخدم fallback في التجارب الحية لأن bwrap كان متاحًا.

لم تُعدّل هذه المهمة `runbook/runbook.json` أو أي مهارة أو متن تقرير، ولم تلمس `/home/ubuntu/mda-marine-system`، ولم تنفذ نشرًا أو Telegram أو `git push`. ملفات الفريق الموازي `tools/governing_assets_merkle.py` و`tools/append_only_ledger.py` خارج النطاق.
