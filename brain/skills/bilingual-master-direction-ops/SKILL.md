---
name: bilingual-master-direction-ops
description: Govern the direction of truth in a bilingual report pipeline — declare one master language, render the other by meaning, and close the runbook blockers that follow. Use when a bilingual report keeps failing on missing translations, when translation runs sources→Arabic→English (double hop), when the owner decides which language is authoritative, when a governed build stops on "text without translation", or when a parity/backup step blocks after a language-direction change.
---

# Bilingual Master-Direction Ops

Make one language the **master of truth** and the other a **meaning-based rendering** of it, so the pipeline never translates twice and never blocks on a unit that has no counterpart.

## When to use

- The pipeline authors Arabic from sources, then translates to English (or the reverse) — a double hop that loses precision and blocks the build.
- A build stops with "text without translation" / "unit not in glossary" for content that does exist in the master text.
- The owner declares which language is authoritative, or asks whether the current direction is correct.
- A language-direction change leaves backup/parity/publication steps failing.

## The rule of direction

1. **One master.** Pick the language the sources are written in (usually English for official sources). The master text is written once, from the sources, in their own wording.
2. **The other language is rendered by meaning.** Paragraph by paragraph, never word by word. Literal word-for-word rendering is forbidden.
3. **Missing units are derived, not machine-translated.** If a rendering unit has no counterpart, lift the counterpart from the master text and record it in the glossary with its exact wording.
4. **Facts are language-neutral.** Numbers, units, warning numbers, vessel names, IMO numbers and coordinates keep their official form in both languages.
5. **Record the policy in the manifest.** A machine-readable key (`i18n.master`, `i18n.since`, `i18n.master_file`) makes the direction auditable and lets a gate fail closed when it is violated.

## Procedure

1. **Declare the direction.** Write the policy key in the runbook manifest and restate it in the writing prompt: master language, master file path, the by-meaning rule, and the fact-preservation rule.
2. **Insert a governed derivation step** before the build step (for example `B009` before `B010`). It runs the derivation tool, then the wrapper build.
3. **Derive the missing units** from the master text, then write them into the glossary with exact strings. Do not add a pattern that silently swallows a whole sentence.
4. **Run the step and read the exit code.** `0` = proceed; `10` = read the printed prompt and execute only it, then complete and re-run; `2` = stop, no publish, no messaging.
5. **Close the blockers in the order they appear** (see `references/playbook.md`): step-definition type errors, untracked code, parity deviation, dirty mirror tree, stuck merge state.
6. **Publish and verify live**: the master page must show no visible text of the other language, and the derived unit must be readable on the live page, not only in the local build.
7. **Re-run the closure steps** (backup · parity · final close) until all are `done`, then record the round.

## Fail-closed rules

- Never hand-edit a generated interface file to satisfy a gate; fix the generator or the source.
- Never publish outside the governed publish step; never push directly to `main`; use a branch and a merge request.
- Never let a checker accept a unit whose counterpart does not exist in the master text.
- A gate that cannot prove the direction is satisfied must fail, not warn.
- When a governed step is skipped because it is already marked `done`, re-run it explicitly with the step-redo flag before claiming its outcome for the new build.

## Verifying the direction

Run the bundled checker before and after a direction change:

```bash
python3 scripts/verify_master_direction.py --brain /path/to/brain --site /path/to/site --date YYYY-MM-DD
python3 scripts/verify_master_direction.py --selftest
```

It checks the manifest policy key, that every rendered unit has a counterpart in the master text, and that no machine-translation fallback marker is present. Exit `0` = satisfied, `2` = violation.

## References

- `references/playbook.md` — the exact blocker sequence, symptoms, causes and proven fixes from a real round.

## حدود المهارة
هذه المهارة لا تؤلف الوقائع أو تقدير التهديد؛ المهارة الجارة `marine-news-brain` تفعل ذلك.


## حلقة التعلم الذاتي
بعد كل عطل أو ملاحظة: **عطل** (العرض ورمز الخروج) ← **درس** (السبب الجذري) ← **حاجز** (قاعدة أو فحص قابل للتنفيذ) ← **اختبار** (حالة سليمة تمر وحالة مخالفة تمنع). إذا لم يوجد أمر ومخرج فعليان للحاجز، اكتب «وعْد غير مقيس/لم أختبره» ولا تعلن نجاحًا.
