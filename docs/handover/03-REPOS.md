# 03 — المستودعات

> تاريخ الكتابة: 2026-11-28 (البحرين)
> الفرع: handover/grok-2026-11-28
> الالتزام الأب: 66f16c9364e744db4697c622dec508ac16248e67
> المشغّل المنتهية مهمته: Claude


القياس بتاريخ 28 نوفمبر 2026 من نسخ مستنسخة داخل هذه الجلسة، بعد `git fetch origin main`.

## الجدول

| المستودع | الغرض | الفرع الحي | آخر التزام (main) | الحالة |
|---|---|---|---|---|
| `mda-marine-system` | النظام الكامل: الخط اليومي والبوابات والمولّد والقواعد ونسخة الموقع المصدرية. المصدر الوحيد للشيفرة | `main` | `66f16c9364e744db4697c622dec508ac16248e67` بتاريخ 2026-11-28 | إنتاج |
| `seawatch-live` | الموقع المنشور (HTML جاهز: 163 ملفًا). يبنيه Cloudflare Pages للمشروع `mda-bh` | `main` | `cfade5c08590be37ec658ce458fbe745971fbb50` بتاريخ 2026-11-27 (`نشر تقرير 2026-11-26`) | إنتاج |
| `seawatch-brain` | نسخة جزئية قديمة من الدماغ (282 ملفًا) وسجل `HANDOFF.md` بقرارات 16 و17 نوفمبر | `main` | `99f9694a4927129055b844659f1da8102c86f0da` بتاريخ 2026-11-19 | متروك: نسخته أقدم من `mda-marine-system`. مصدره الصحيح للقرارات التاريخية فقط |
| `seawatch-web` | نسخة الموقع القديمة (389 ملفًا، فيها `dist` ووثائق مانوس) | `main` | `375200563d60cc38e7827be28f0b4f3a1fa91010` بتاريخ 2026-11-17 | متروك. نُقلت منه فجوات في 20 نوفمبر (`brain/CHANGELOG.md`) |
| `seawatch-site` | بديل GitHub Pages احتياطي «مستقل» (ملفان: `.github` و`README.md`) | `main` | `dfe28ad0b2562feabc928a3892c5150cf44a0e44` بتاريخ 2026-11-07 | غير موصول: لا محتوى منشور |
| `seawatch-replica-build` | سكربت يبني نسخة ثابتة من موقع منشور وينشرها على Cloudflare Pages (116 ملفًا) | `main` | `1eae1906b59007e4450527b936986daf64f91bb2` بتاريخ 2026-11-16 | غير مسند: صلته بالتشغيل اليومي غير مذكورة في `mda-marine-system` |
| `mda-marine-system-independent` | نسخة من النظام (2106 ملفًا) أقدم بكثير | `main` | `459194c53ba0ddee0d18f244935b06f2658ee4dc` بتاريخ 2026-10-26 | متروك، غير مسند الغرض بعد 26 أكتوبر |

عام أم خاص: `README.md` و`brain/secrets/README.md` يشترطان أن يبقى `mda-marine-system` خاصًّا. طلب `https://api.github.com/repos/fahadaldoseri/NAME` بلا مصادقة من هذه الجلسة أعاد 200 للمستودعات السبعة. قد يحقن وكيل الشبكة صلاحية، فالنتيجة لا تثبت أنها عامة. **غير محسوم**: يتحقق المالك من إعداد الرؤية في GitHub. انظر `18-OPEN-QUESTIONS.md`.

## ما يُنشر من أين وإلى أين

```
mda-marine-system (brain/ + site/generator)
   └─ tools/cloud_deliver.py --push
        └─> seawatch-live (main)  ── تلقائيًا ──>  Cloudflare Pages: mda-bh  ──>  https://mda-bh.pages.dev
```

- مشروع Cloudflare Pages `mda-bh`: المصدر `fahadaldoseri/seawatch-live`، الفرع الإنتاجي `main`، أمر البناء فارغ، المجلد الخارج فارغ (استعلام `GET /accounts/61ff6efbe480affd36a24facac92040d/pages/projects/mda-bh`).
- مشروع Pages القديم `seawatch-live.pages.dev`: يعيد 301 إلى `mda-bh.pages.dev` (قياس هذه الجلسة). مصدره فرع يتيم `claude/project-thread-7y5m9j` في `seawatch-live` يحوي `_redirects` فقط (من ذاكرة المشروع 18 نوفمبر؛ لم يُفحص الفرع هنا). لا يُحذف الفرع ولا يُعاد المشروع إلى `main`.
- العنوان الرسمي الوحيد: `https://mda-bh.pages.dev` (قرار المالك 18 نوفمبر 2026، `brain/CHANGELOG.md` وذاكرة المشروع).

## ما لا يجوز أن يكون مصدر حقيقة

| المصدر | السبب |
|---|---|
| `seawatch-brain` و`seawatch-web` و`mda-marine-system-independent` | نسخ قديمة. الأولى فيها شيفرة ناقصة صراحة («ما لم يصلنا من الخادم» في `HANDOFF.md`) |
| `site/README.md` في `mda-marine-system` | يقول إن النشر بإيداع `dist/`، و`site/dist/` مستثنى في `.gitignore` وغير موجود |
| `brain/docs/runbook.md` يدويًا | مولَّد من `runbook.json`؛ يُعاد توليده بـ`python3 brain/tools/runbook.py handbook --root brain` |
| `docs/فهرس-الملفات.tsv` | قديم (11 نوفمبر)، انظر `02-SOURCE-OF-TRUTH.md` |
| أرقام عدد المصادر في `README.md` (40) | المصدر الواحد `brain/appendices/sources-manifest.json` يقول 62 |
| القناة المرآة Manus | غير مطلوبة وغير مثبتة |

## الفروع المفتوحة في `mda-marine-system`

- طلب الدمج 676 مسودة: `claude/project-thread-sb5htc`، «W010: تقسيم طلب الكتابة إلى خمس مجموعات». لم يُدمج.
- طلب 670 (رقم الحادث `26-0417`): الذاكرة تقول إنه ينتظر قرار الدمج، لكن التاريخ يُظهر التزامه `261fca0` على `main` (`git log`). الحالة: مدموج. تصحيح ذاكرة المشروع.
- فروع `daily/DATE` و`fallback/DATE` تُنشأ من التشغيل اليومي (انظر `04-RUNBOOK-AS-OPERATED.md`).
