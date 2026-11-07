# خطة قنوات النشر — 2026-11-07

هذه الخطة تُنفّذ داخل `/home/ubuntu/mda-marine-system/brain` بوصفه نسخة Git الفعلية؛ التسليم سيكون من الفرع `feat/two-channel-publish-20261107` عبر طلب دمج ودمج عادي. مجلد `/home/ubuntu/brain-marine-news` ليس نسخة Git مستقلة في هذه الجلسة.

**الهدف:** إزالة اعتماد التقرير اليومي على إضافة Manus الواحدة. مصدر الحقيقة لجهوزية Manus هو `manus-mcp-cli tool list --server webdev-mcp` فقط؛ وعند خطأ `addon workspace recovery has not completed` تكون القناة `down` حتى لو أعادت أداة السجلات نجاحًا.

**البنية:** يبقى `tools/publish_site.sh` ناشر Manus الأساسي دون تغيير داخلي. تُضاف وحدة Python مشتركة للجهوزية والتحقق، وناشر بديل يدفع `dist/` إلى جذر مستودع عام جديد `fahadaldoseri/seawatch-live` على `main`. يستخدم العقد روابط raw.githack وjsDelivr، ويعيد D020 فحص القناة المستخدمة فعليًا.

**Tech Stack:** Bash, Python 3 stdlib, GitHub CLI/API, GitHub Actions Pages, existing JSON runbook manifest and generated handbook.

## Global Constraints

- Do not force-push or write directly to `main` in the code mirror; use a feature branch, pull request, and normal merge.
- Do not enable printing/PDF or weaken any gate.
- Do not report `status=ok` without a fresh HTTP 200, non-zero body, and report-date marker.
- Keep the existing Manus publisher functionally unchanged except for orchestration around it.
- Do not store secrets in the repository; use the session's `gh`/Git credentials.

## Acceptance Criteria

1. `fahadaldoseri/seawatch-live` is public; `tools/publish_fallback.sh DATE` pushes `dist/` to repository root on `main`.
2. `tools/publish_fallback.sh DATE` returns explicit rc and writes `logs/publish-D-fallback.json` with `channel`, `url`, `urls[]`, `rc`, `at`, `head`, and deterministic `content_sha256`.
3. `S085` precedes build steps and writes `logs/publish-channel-D.json` with literal `ready`/`down` states and reasons for both channels; it exits non-zero only when both are down.
4. D010 chooses a ready Manus channel first, falls back to GitHub Pages, and writes `logs/publish-D.json`; `ok` requires the selected channel's verified HTTP 200.
5. D020 verifies 200, non-zero size, and date marker on the used channel, and fails closed on 404/0.
6. `tests/test_publish_channels.py` demonstrates RED before implementation and GREEN after implementation for five required behaviors.
7. `python3 tools/runbook.py handbook` followed by `python3 tools/runbook.py verify --root .` returns rc 0; the new test is linked in manifest and impact map.
8. Fault/lesson/traceability records identify the single-channel failure and the preflight + two-channel + live-200 barrier.
9. Mirror delivery is through a non-main branch and a normal PR merge; record PR number and merge commit.

## Implementation Tasks

- [ ] Add the failing channel-contract test and run it to record RED.
- [ ] Create the public fallback repository and publish the fallback with fingerprinted JSON logging.
- [ ] Add shared channel readiness/live verification helpers and integrate D010/D020 orchestration without changing Manus internals.
- [ ] Add S085 and regenerate the handbook; update D010/D020 links and impact map.
- [ ] Run focused tests, full verification, and live fallback publication/HTTP check if Pages becomes ready.
- [ ] Record fault, lesson, traceability, and delivery evidence; synchronize the changed brain tree into the mirror branch.
- [ ] Open and merge the PR normally, then report evidence and any blocked runbook steps verbatim.
