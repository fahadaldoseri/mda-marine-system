# Hermetic Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** بناء `tools/hermetic_run.sh` لتشغيل أدوات سطر الأوامر داخل `bubblewrap` مع عزل القراءة/الكتابة والشبكة والموارد، وإخراج دليل JSON قابل لإعادة التشغيل.

**Architecture:** يفسر السكربت خياراته قبل `--`، ثم يلتقط بصمات شاملة لمجلدي المشروع و`seawatch` (مع استثناء ملفات الدليل التي ينشئها الحارس نفسه عند مقارنة الأثر)، ويشغّل الأمر تحت `bwrap --unshare-all --die-with-parent --unshare-net --ro-bind / / --tmpfs /tmp --bind <workdir> <workdir> --proc /proc`. يلتف التشغيل بـ`strace` و`timeout`، ويحاول `systemd-run` لحدود الذاكرة/المعالج/المهام ثم يسقط إلى `ulimit` عند تعذره. بعد التشغيل يكتب JSON يحوي رمز الخروج والمدة وملخص الأثر وإثبات اتصال فاشل وعدّ الحزم.

**Tech Stack:** Bash، bubblewrap، util-linux `unshare`، GNU `timeout`، `strace`، Python 3 stdlib، pytest.

**Spec:** طلب فريق «الحاوية المحكمة» المؤرخ 2026-10-30؛ لا تعديل لـ`runbook/runbook.json` أو المهارات أو متن التقرير أو `/home/ubuntu/mda-marine-system`، ولا نشر/Telegram/git push.

## Global Constraints

- `bwrap --unshare-all --die-with-parent` هو المسار الأساسي؛ fallback موثق لـ`unshare --mount,pid,net,ipc,uts`.
- الجذر للقراءة فقط، `/tmp` طبقة `tmpfs`، ومجلد العمل المضبوط فقط قابل للكتابة.
- `timeout` إلزامي، افتراضيه 60 ثانية وقابل للتغيير.
- `strace` يسجل `%file,%network,execve` أو البديل الصريح عند غياب الاختصار.
- كل تشغيل يخرج `evidence/hermetic/<tool>-<ts>.json` ومسار trace خام.
- التشغيل قبل/بعد: `python3 validators/check_skills_integrity.py` و`scons` أو `python3 tools/runbook.py verify`؛ رمز 2 المعروف في فحص المهارات لا يُصلح هنا.
- لا حذف لملفات المشروع ولا لمس ملفات الفريق الموازي `tools/governing_assets_merkle.py` و`tools/append_only_ledger.py`.

---

### Task 1: الاختبار الأحمر

**Files:**
- Create: `tests/test_hermetic_run.py`

- [ ] اكتب اختبارات `--help` ورمز 2 لوسيط مجهول، ثم الاختبارات الموجبة/السالبة الأربع باستدعاء حقيقي للسكربت.
- [ ] شغّل `pytest tests/test_hermetic_run.py -q` قبل وجود الأداة وتحقق من فشل متوقع بسبب غياب السكربت/الأدلة.

### Task 2: أداة الحاوية

**Files:**
- Create: `tools/hermetic_run.sh`

- [ ] ثبّت bubblewrap وstrace عند الحاجة وسجّل الإصدارين.
- [ ] نفّذ parsing مغلقًا للخيارات، وعزل bwrap، وfallback موثقًا، وtimeout/حدود الموارد، والتقاط trace، وبصمات قبل/بعد، وملخص JSON.
- [ ] شغّل الاختبارات حتى GREEN ثم افحص `bash -n` وكتلة Python المضمنة.

### Task 3: الدليل والتجارب الحية

**Files:**
- Create: `evidence/hermetic/HERMETIC-RUN.md`
- Create: `evidence/hermetic/preflight/*`, `evidence/hermetic/postflight/*`, `evidence/hermetic/traces/*`, `evidence/hermetic/*.json` (مخرجات تشغيل فقط)

- [ ] شغّل التجارب الأربع حرفيًا وسجّل الأمر والمخرج الخام ورمز الخروج والبصمة.
- [ ] وثّق الفرق بين bwrap وunshare، وما تعذّر، ونطاق استثناء ملفات الدليل من مقارنة الأثر.

### Task 4: بوابات ما بعد التنفيذ

- [ ] شغّل `pytest tests/test_hermetic_run.py -q` حديثًا.
- [ ] شغّل `python3 validators/check_skills_integrity.py` و`scons` أو `python3 tools/runbook.py verify` حديثًا واحفظ الرموز والمخرجات.
- [ ] راجع `git diff` إن كان متاحًا، و`find` للتأكد من عدم لمس الملفات المحظورة، ثم جهّز تقريرًا عربيًا مختصرًا بلا ادعاء غير مسند.

## معايير القبول القابلة للقياس

1. `tools/hermetic_run.sh --help` يخرج 0، ووسيط غير معروف يخرج 2 مع مخرج استخدام.
2. اختبار القراءة يخرج النص، وتجربة الكتابة تفشل/تُحتوى ويكون `changed_files_outside_isolation=0`.
3. اتصال `1.1.1.1:80` يفشل، و`net_packets=0`، وtrace يحتوي `connect` فاشلًا.
4. أداة الحلقة تُقتل بـ`timeout` وتخرج رمزًا واضحًا (`124` أو رمز قتل موثقًا).
5. كل JSON يحتوي الأداة والوسائط والرمز والمدة وملخص الأثر و`net_packets` وعدد الملفات المتغيرة ومسار trace.
6. لا تعديل في `runbook/runbook.json` أو المهارات أو متن التقرير أو `/home/ubuntu/mda-marine-system`.

## أثر الرجوع

الملفات الجديدة الوحيدة القابلة للإزالة عند الرجوع هي `tools/hermetic_run.sh` و`tests/test_hermetic_run.py` و`notes/hermetic-run-plan.md` و`evidence/hermetic/*`; لا تُحذف ملفات قائمة ولا تُعاد كتابة بوابة أو مانيفست. المخرجات المؤقتة خارج المشروع محصورة في `/var/tmp` وتُنظّفها الأداة.
