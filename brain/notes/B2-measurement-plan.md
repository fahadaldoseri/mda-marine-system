# B2 Measurement and Closure Plan

**Goal:** تنفيذ قياس كل صف من `scope-B-measurable.json` وعددها 115، مع سجل خام وبصمة وحالة تراكمية، دون إعلان إغلاق بلا دليل.

**Architecture:** تُستخدم سجلات `logs/B/` الناجحة كما هي دون إعادة قياس، وتُنقل إلى `logs/B2/` مع التحقق من الأمر والرمز والبصمة. الصفوف غير المسجلة تُشغّل بأوامر مشتقة فقط من حاجز الصف أو أثر موثق في `result-C.json`، وكل أمر يُغلّف حرفيًا بـ`timeout 120`. تُكتب `state-B2.json` و`result-B.json` بعد كل 10 صفوف. أي فشل يُحفظ أولًا، ثم يُشخّص ويُصلح في مصدره فقط عند وجود سبب جذري قابل للإثبات، ويُعاد تشغيل نفس الحاجز.

**Files:**
- Read: `audit/measurements/batches/scope-B-measurable.json`, `audit/measurements/batches/logs/B/`, `audit/measurements/batches/result-C.json`.
- Create/update: `audit/measurements/batches/logs/B2/*.log`, `audit/measurements/batches/state-B2.json`, `audit/measurements/batches/result-B.json`.
- Possible source fixes only after RED evidence: the directly implicated tool/validator/test file; never the prohibited files listed by the owner.

**Acceptance criteria:**
1. Exactly 115 result objects, unique IDs, all IDs equal the scope IDs.
2. Every B2 log contains COMMAND, STARTED_AT, RC, output, and SHA-256 recorded in the corresponding result.
3. Every executed command visibly includes `timeout 120`; reused successful B logs retain the original command and are marked reused rather than rerun.
4. No Git, publish, Telegram, backup, or `tools/runbook.py run` operation.
5. Final summary separates closed/not closed and records root fixes with file paths and fresh verification evidence.

**Execution:**
- [ ] Inventory and match prior logs.
- [ ] Diagnose explicit failures, starting with z-01 Python syntax/source issue and tracking-contract failures.
- [ ] Execute missing rows in bounded groups, persist every 10 rows.
- [ ] Re-run only rows whose source was fixed, preserving pre-fix evidence.
- [ ] Run final structural verification for count, uniqueness, log existence, command timeout coverage, and hashes.
