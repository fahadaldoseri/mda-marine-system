# 06 — الموقع

> تاريخ الكتابة: 2026-11-28 (البحرين)
> الفرع: handover/grok-2026-11-28
> الالتزام الأب: 66f16c9364e744db4697c622dec508ac16248e67
> المشغّل المنتهية مهمته: Claude


لا يُعاد بناء الموقع ولا يُنشر في هذا التسليم. كل ما يلي قياس قراءة فقط.

## بناء الموقع من `site/generator`

الأمر المعتمد في التحقق (`.github/workflows/verify.yml`)، من جذر المستودع:

```bash
cd site
python3 generator/build_site.py --check
```

الخيار `--site-root` يغيّر الجذر. المخرج مجلد `site/dist/` يضم `index.html` و`reports/DATE.html` و`reports/cumulative-2026.html` و`reports/monthly-YYYY-MM.html` و`manus-routes.json` و`favicon.svg` (`site/generator/build_site.py` رأس الملف). النتيجة المتوقعة: بناء كامل بلا `CRITICAL_FAIL`. لم يُشغَّل في هذه الجلسة.

خطوات البناء اليومي داخل المحرّك (خطوة B010) بالترتيب:

```bash
cd "$SITE_DIR"
python3 "$BRAIN_DIR/tools/sync_card_layers.py" --date DATE
python3 "$BRAIN_DIR/tools/build_hero_kpis.py" --date DATE --apply
python3 generator/sync_from_brain.py --date DATE
python3 generator/build_site.py          # ثم بقية أوامر الخطوة كما في runbook.json
```

شرط كل تقرير يومي: زوج مصدر `site/sources/reports/DATE-sectioned.md` و`site/sources/meta/DATE.json`. الزوج الناقص يُسجَّل ويُتجاوز ولا يُسقط البناء. أصل الترجمة الإنجليزية في `site/sources/i18n/en/`.

## لماذا `dist` غير موجود

| الحقيقة | السند |
|---|---|
| `site/dist/` مستبعد من git | `.gitignore` السطر «site/dist/» |
| `site/shots/` مستبعد أيضًا | `.gitignore` |
| `site/README.md` يقول «يُلتزم مجلد dist/ ثم يُنشر» | نص قديم لا يطابق التشغيل |
| `verify.yml` يبني الموقع من المصادر في كل طلب دمج لأن الفحوص تشترط `site/dist` | تعليق الخطوة «بناء الموقع» |
| النشر الفعلي: `tools/cloud_deliver.py` ينسخ ملفات اليوم المبنية إلى `seawatch-live` | رأس `brain/tools/cloud_deliver.py` |

## أين يعيش المخرج المنشور

في مستودع `seawatch-live` فرع `main`: 163 ملفًا (`404.html` و`about.html` و`additions.html` و`feed.xml` و`index.html` و`sitemap.xml` و`sources.html` و`robots.txt` و`manus-routes.json` و`assets/` و`reports/`). آخر التزام `cfade5c08590be37ec658ce458fbe745971fbb50` بتاريخ 2026-11-27 21:01 UTC.

## علاقة Cloudflare Pages بالمستودع

القياس بـ`GET https://api.cloudflare.com/client/v4/accounts/61ff6efbe480affd36a24facac92040d/pages/projects/mda-bh` (قراءة فقط، حساب Cloudflare معرّفه ظاهر في المسار ولا قيمة سرية فيه):

| البند | القيمة |
|---|---|
| المشروع | `mda-bh` (النطاق `mda-bh.pages.dev`) |
| المصدر | GitHub `fahadaldoseri/seawatch-live` |
| الفرع الإنتاجي | `main` |
| أمر البناء | فارغ |
| مجلد الإخراج | فارغ |
| معاينة الفروع | `none` |
| تاريخ إنشاء المشروع | 2026-11-18 |
| آخر نشر ناجح | `8ff25a37-694a-4e92-8be0-db90240b0126`، 2026-11-27 21:01:17 UTC، التزام `cfade5c` |
| نشر ناجح قبله | `45319ad7` (27 نوفمبر 14:53) و`81223a99` (27 نوفمبر 13:18) و`b8a655d2` (22 نوفمبر 04:02) |
| آخر نشر فاشل | لا يظهر في آخر 12 نشرًا مقروءًا (من 18 نوفمبر)، والاستعلام الأوسع رُفض. **غير مثبت خارج هذه النافذة** |
| نشر معاينة معلّق | `03635dd9` بتاريخ 2026-11-18، الحالة `queued/idle`، فرع `bced706` |

مشروع Pages القديم `seawatch-live.pages.dev` يعيد 301 إلى `https://mda-bh.pages.dev/` (قياس هذه الجلسة).

## صفحات يطابقها المشغّل الجديد

قياس 28 نوفمبر 2026 من هذه الجلسة بـ`curl -s -o /dev/null -w '%{http_code} %{size_download}'`:

| الصفحة | الرد | الحجم (بايت) |
|---|---|---|
| `https://mda-bh.pages.dev/` | 200 | 91702 |
| `https://mda-bh.pages.dev/reports/2026-11-22` | 200 | 216992 |
| `https://mda-bh.pages.dev/reports/2026-11-26` (آخر تقرير منشور بتاريخه الفعلي) | 200 | 232613 |
| `https://mda-bh.pages.dev/reports/2026-11-23` و`24` و`25` و`27` و`28` | 404 | — |

الصفحة الرئيسية تسرد آخر أربعة تقارير: 2026-11-20 و21 و22 و26. التقارير المنشورة 43 صفحة من 2026-10-12 إلى 2026-11-26.

الفجوة المعلنة 23–25 نوفمبر (قرار المالك بإعلانها: التزام «ضم مخرجات 22 نوفمبر وإعلان فجوة 23-25 نوفمبر بقرار المالك» ضمن الدمج 675). تقرير 27 نوفمبر لم يُنشر (تشغيل Actions رقم 65 فشل).

## ما في الموقع المنشور وليس في GitHub، والعكس

| الاتجاه | النتيجة |
|---|---|
| تواريخ التقارير في `seawatch-live/reports/` مقابل `brain/reports/*-sectioned.md` | مطابقة: 43 تاريخًا في كل منهما، لا فرق في المجموعتين |
| الصفحات المبنية HTML | في `seawatch-live` فقط. `mda-marine-system` يحوي المصادر والمولّد فقط (`site/dist` غائب) |
| شيفرة المولّد (`site/generator`) ومصادر الصفحات | في `mda-marine-system` فقط |
| محتوى الصفحة الحية مقابل بنائها من مصدر `main` | غير مقاس: يتطلب بناء الموقع وهو ممنوع هنا. أمر المقارنة لاحقًا: `bash brain/tools/publish_site.sh` ممنوع، فيُستعمل `python3 brain/validators/check_deployment_freshness.py` بعد قراءة رأسه |
| أصول `seawatch-live/assets/` مقابل `site/` | غير مقاس |
