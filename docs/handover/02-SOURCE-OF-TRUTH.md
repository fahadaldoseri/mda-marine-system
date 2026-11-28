# 02 — مصدر الحقيقة

> تاريخ الكتابة: 2026-11-28 (البحرين)
> الفرع: handover/grok-2026-11-28
> الالتزام الأب: 66f16c9364e744db4697c622dec508ac16248e67
> المشغّل المنتهية مهمته: Claude


## حالة الخادم الآن

**الخادم غير منظور في هذه الجلسة.** لا يُفترض أنه مطابق لـGitHub.

| السؤال | الجواب | السند |
|---|---|---|
| هل `apply_from_github` متأخر على الخادم؟ | غير مسترجع. لا وصول إلى الخادم من هذه الجلسة | لا اتصال بـ`/home/ubuntu/brain-marine-news` |
| هل يوجد `logs/alerts/code-drift` حي؟ | غير مسترجع من الخادم. المتوفر نسخ احتياطية في المستودع: 18 ملفًا من `code-drift-2026-10-24.txt` إلى `code-drift-2026-11-11.txt` | `brain/logs/alerts/` |
| آخر انحراف مسجّل في النسخ الاحتياطية | 11 نوفمبر 2026: ملفات `site/generator/*` وترجمات `site/sources/i18n/en/` ومسارات `new` | `brain/logs/alerts/code-drift-2026-11-11.txt` |
| هل الخادم ما زال يشغّل الخط اليومي؟ | غير مثبت. آخر علامة `pipeline-DATE.json` في المستودع للتاريخ 2026-11-21، وآخر تقرير في المستودع 2026-11-26 كُتب في GitHub Actions | `brain/logs/pipeline-2026-11-21.json` |
| قناة Manus المرآة | الجذر `https://seawatch-xp4qirmr.manus.space/` يردّ 200 (محتواه لم يُفحص: غير مثبت)، و`/reports/2026-11-22.html` يردّ 404، قياس 28 نوفمبر 2026 من هذه الجلسة | `curl` |

أوامر القراءة التي يشغّلها من يملك الوصول إلى الخادم (قراءة فقط):

```bash
cd /home/ubuntu/brain-marine-news
ls logs/alerts/ | grep code-drift | tail -5
bash tools/apply_from_github.sh --dry-run
git -C /home/ubuntu/mda-marine-system log -1 --format='%H %cd'
```

النتيجة المتوقعة للتطابق: لا ملف `code-drift` بتاريخ اليوم، والأمر الجاف لا يعرض فروقًا، والالتزام يساوي `66f16c9364e744db4697c622dec508ac16248e67` أو أحدث منه.

## الجدول

التصنيف الحاكم هو `brain/appendices/code-paths.json` (حقلا `code` و`data`)، ويفحصه `python3 brain/tools/code_paths.py check --root .` وقد نجح في هذه الجلسة (12223 مسارًا مصنَّفًا).

| النوع | المصدر الوحيد | النسخة الاحتياطية | من يكتبه | من يُمنع من كتابته | أمر كشف الانحراف |
|---|---|---|---|---|---|
| الشيفرة (`brain/tools` و`validators` و`tests` و`site/generator`) | GitHub فرع `main` من `mda-marine-system` | نسخة الخادم تُطبَّق من GitHub بـ`apply_from_github.sh` | فرع ثم طلب دمج | الخادم مباشرة (يُعدّ انحرافًا) وأي دفع إلى `main` | `bash brain/tools/apply_from_github.sh --dry-run` على الخادم، و`python3 brain/tools/code_paths.py check --root .` هنا |
| القواعد (`brain/sections` و`appendices` و`runbook` و`templates`) | GitHub `main` | الخادم | فرع وطلب دمج | الخادم، والنسخ الاحتياطي (`backup_may_overwrite`) | `python3 brain/tools/runbook.py verify --root brain` |
| التقارير (`brain/reports`) | الخادم عند الكتابة، والنسخة المنشورة في `seawatch-live` | المستودع يحتفظ بآخر 30 يومًا (`reports-archive.json`) | التشغيل اليومي وحده | أي تعديل يدوي لتقرير منشور | `python3 brain/tools/publish_verdict.py --date DATE` وبصمة الصفحة الحية |
| دفتر الأحداث (`brain/cumulative-2026/event-ledger-master.json`) | الخادم، نسخته في GitHub احتياطية | GitHub | `tools/merge_ledger_daily.py` وحده | الكتابة اليدوية | `python3 brain/validators/check_ledger_continuity.py --date DATE` |
| الذاكرة (`brain/memory/learning-log.jsonl` و`intel-adaptation.md`) | الخادم | GitHub | التعلم الذاتي (D050) | الكتابة اليدوية | غير مسند أمر مخصص |
| التغذيات (`brain/feeds`) | الخادم، يكتبها S020 | GitHub | `tools/check_feeds.py` | أي كتابة يدوية | `ls brain/feeds/feeds-DATE.json` |
| الأرشيف الطويل | جهاز المالك (`reports-archive.json`، حقل `device_archive`) | لا نسخة | المالك | الوكلاء | المسار على الجهاز غير مسند |
| الأسرار | متغيرات بيئة التشغيل وأسرار GitHub Actions. ملف `brain/secrets/secrets.env` غير موجود في `main` (انظر الحاشية) | لا نسخة في المستودع | المالك | أي وكيل: لا يطبع ولا ينسخ | `python3 brain/validators/check_repo_secrets.py` |
| الموقع المنشور | مستودع `seawatch-live` فرع `main`، يبنيه Cloudflare Pages للمشروع `mda-bh` | سجل Git لـ`seawatch-live` | `tools/cloud_deliver.py --push` من التشغيل اليومي | الدفع اليدوي بلا أمر المالك | `curl -s -o /dev/null -w '%{http_code}' https://mda-bh.pages.dev/reports/DATE` |
| دفتر قرارات المالك | `brain/decisions/registry.json` | GitHub | وكيل بأمر المالك | الحذف (لا يُحذف قرار) | `python3 brain/validators/check_decisions_registry.py` |

## حاشية: الأسرار

`AGENTS.md` القاعدة 9 تنص على قرار المالك 24 أكتوبر 2026 بحفظ الأسرار نصًّا في `brain/secrets/secrets.env` داخل المستودع الخاص. القياس في `main`:

- `git ls-files brain/secrets` يعيد ملفين فقط: `README.md` و`secrets.env.example`.
- `.gitignore` يحوي السطر `secrets/`.
- `daily.yml` يقرأ الأسرار من `secrets.*` في GitHub Actions، والتشغيل اليومي يستعمل `check_repo_secrets.py` قبل الإيداع.

الحالة الفعلية المقيسة: الأسرار خارج المستودع. التعارض مع نص القاعدة 9 قائم وغير محسوم في وثيقة. انظر `10-DECISIONS.md` و`18-OPEN-QUESTIONS.md`.

## انحراف الفهرس المقيس

`docs/فهرس-الملفات.tsv` (آخر تحديث 2026-11-11) يسرد 9110 ملفًا. المقيس على `main` بأمر التحقق الوارد في `README.md`: 48 مسارًا مفقودًا و457 بصمة مختلفة، والشجرة الآن 12223 ملفًا. الفهرس قديم ولا يُعتمد للتحقق. الفهرس الحالي لهذه الحزمة هو `17-MANIFEST.tsv`.
