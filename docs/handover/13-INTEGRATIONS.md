# 13 — التكاملات

> تاريخ الكتابة: 2026-11-28 (البحرين)
> الفرع: handover/grok-2026-11-28
> الالتزام الأب: 66f16c9364e744db4697c622dec508ac16248e67
> المشغّل المنتهية مهمته: Claude


كل أمر فحص هنا **قراءة فقط**: لا يرسل ولا ينشر ولا يكتب. الفحوص التي تحتاج سرًّا تقرؤه من البيئة ولا تطبعه. «غير مقاس» تعني أن هذه الجلسة لم تقس الحالة.

## الجدول

| التكامل | الدور | الحالة المقيسة 28 نوفمبر | آخر نجاح | آخر فشل |
|---|---|---|---|---|
| GitHub Actions `daily` | التشغيل اليومي 01:40 UTC (04:40 البحرين) | الجدول فعّال بعد دمج 675؛ لم يظهر تشغيل مجدول بعد. يدوي فقط حتى الآن | تشغيل رقم 64 (نشر 26 نوفمبر) | تشغيل رقم 65 (27 نوفمبر، W010) |
| GitHub Actions `verify` | بناء الموقع والفحوص في كل طلب دمج | غير مقاس | غير مقاس | غير مقاس |
| Cloudflare Pages `mda-bh` | استضافة الموقع، المصدر `seawatch-live` فرع `main`، بلا أمر بناء | نشط، يرد 200 | نشر `8ff25a37-694a-4e92-8be0-db90240b0126` 2026-11-27 21:01:17 UTC | لا فشل في آخر 12 نشرًا؛ ما قبلها غير مثبت |
| مستودع `seawatch-live` | الناشر الفعلي: الدفع إلى `main` = نشر | 163 ملفًا، آخر التزام `cfade5c` | 2026-11-27 21:01 UTC | |
| تلغرام `@MDA_BH_bot` | رسالة يومية واحدة بعد نشر متحقق منه | الإرسال مفتوح بأمر D030؛ الحالة الحية غير مقاسة بلا سر | إرسال 21 نوفمبر (08-DONE بند 10) | غير مسند بعد ذلك التاريخ |
| ويب هوك تلغرام | استقبال أوامر البوت (`site/server/app.py`) | **غير مقاس.** لا دليل على خادم يستقبله اليوم | غير مسترجع | غير مسترجع |
| نماذج الكتابة (W010 وW020 وW030 وB004) | `brain/tools/agent_write_llm.py` | Anthropic إن وُجد `ANTHROPIC_API_KEY`، وإلا freellmapi. لا مفتاح Anthropic مؤكد في أسرار Actions (بطاقة قرار 27 نوفمبر بلا جواب) | كتابة 26 نوفمبر من إجابات احتياطية داخل `fallback-answers/2026-11-26/` لا من النموذج المجاني | 27 نوفمبر عند W010 |
| freellmapi (S080 وS090) | نماذج مجانية عبر خادم وسيط، اختياري | 12 اسم سر في `daily.yml` (أدناه) | 26 نوفمبر (#674) | 27 نوفمبر |
| مصادر الأخبار والبلاغات | `brain/appendices/sources-manifest.json` (62 معتمدًا) | فحص 60 تغذية في 21 نوفمبر | 21 نوفمبر | G033 وG062: مصادر تحجب السحابة، أُصلحت بمسارات بديلة 20 نوفمبر |
| X (oEmbed) | إثبات المنشورات بدل المتصفح الآلي | منفَّذ (#660) | 20 نوفمبر | |
| Codespaces | بيئة تحقق (`.devcontainer/Dockerfile`، `brain/tools/verify_codespace.sh`) | غير مقاس. محتوى السكربت لم يُقرأ كاملًا؛ **لا تشغّله قبل قراءته** | غير مسترجع | غير مسترجع |
| Manus | الخادم القديم والمنصة | قناة مرآة اختيارية (`brain/tools/manus_channel_attempt.py`)؛ ملفات حالتها `brain/state/manus-channel-2026-11-{08,09,11}.json` | 11 نوفمبر (آخر ملف حالة) | الخادم غير منظور |
| الخادم `/home/ubuntu/brain-marine-news` | الأصل القديم للبيانات | **الخادم غير منظور في هذه الجلسة** | | |
| نسخ احتياطي لـGitHub | `brain/tools/github_backup.sh` (بلا معاملات، حتى `--help` ممنوع) | غير مقاس | غير مسترجع | |

## أوامر الفحص بلا إرسال ولا نشر

الأوامر من جذر المستودع.

```bash
# موقع حي: يجب 200
curl -s -o /dev/null -w '%{http_code}\n' https://mda-bh.pages.dev/
# التحويل القديم: يجب 301 https://mda-bh.pages.dev/
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' https://seawatch-live.pages.dev/
# آخر تقرير منشور: يجب 200
curl -s -o /dev/null -w '%{http_code}\n' https://mda-bh.pages.dev/reports/2026-11-26
```

```bash
# Cloudflare Pages: قراءة فقط، يطبع حقولًا غير سرية. يتطلب CLOUDFLARE_API_TOKEN في البيئة
curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/61ff6efbe480affd36a24facac92040d/pages/projects/mda-bh" \
  | python3 -c 'import sys,json;r=json.load(sys.stdin)["result"];print(r["name"],r["source"]["config"]["repo_name"],r["production_branch"],r["latest_deployment"]["id"],r["latest_deployment"]["created_on"])'
```

النتيجة المتوقعة: `mda-bh seawatch-live main` ثم معرّف آخر نشر وتاريخه.

```bash
# تلغرام: getMe فقط (قراءة). يطبع ok واسم البوت ولا يطبع الرمز
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("ok"),d.get("result",{}).get("username"))'
```

النتيجة المتوقعة: `True MDA_BH_bot`. الرمز يظهر في سطر الأمر وفي سجل الطرفية؛ لا تنسخ السطر إلى أي مخرج.

```bash
# حكم نص قبل أي إرسال، بلا إرسال ولا ضبط سجل
python3 brain/tools/telegram_send.py --file /tmp/digest.txt --validate-only
```

```bash
# حضور سر في البيئة بلا طباعة قيمته
for v in ANTHROPIC_API_KEY CLOUDFLARE_API_TOKEN TELEGRAM_BOT_TOKEN TELEGRAM_OWNER_CHAT_ID; do
  [ -n "${!v:-}" ] && echo "$v موجود" || echo "$v غائب"; done
```

حالة تشغيلات Actions تُقرأ من صفحة Actions للمستودع، أو بأداة قراءة المستودع. لا تُطلق تشغيلًا.

ملاحظة: صيغة استخراج الحقول في أمر Cloudflare وفي `getMe` كتبتُها من بنية الاستجابة المعروفة ولم أجرّب الأمرين بهذه الصياغة نفسها في هذه الجلسة (**غير مختبر هنا**). إن اختلفت الحقول فاطبع الاستجابة بلا ترويسة المصادقة.

## أسماء أسرار freellmapi المقروءة في `daily.yml`

`FREELLMAPI_GOOGLE_KEY` و`FREELLMAPI_GROQ_KEY` و`FREELLMAPI_OPENROUTER_KEY` و`FREELLMAPI_CEREBRAS_KEY` و`FREELLMAPI_MISTRAL_KEY` و`FREELLMAPI_NVIDIA_KEY` و`FREELLMAPI_COHERE_KEY` و`FREELLMAPI_CLOUDFLARE_KEY` و`FREELLMAPI_ZHIPU_KEY` و`FREELLMAPI_AION_KEY` و`FREELLMAPI_MODELSCOPE_KEY` و`FREELLMAPI_SILICONFLOW_KEY`. وجودها في أسرار GitHub غير مقاس.

## تحذيرات

| الأداة | التحذير |
|---|---|
| `brain/tools/check_api_keys.py` | يطبع أول 7 أحرف من كل مفتاح. **لا تشغّله**: يخالف قاعدة عدم طباعة الأسرار |
| `brain/tools/publish_site.sh` | ينشر. ممنوع في التسليم |
| `brain/tools/cloud_deliver.py --push` | ينشر. بلا `--push` لا نشر، لكن اقرأ رأسه أولًا |
| `brain/tools/telegram_send.py` بلا `--dry-run` أو `--validate-only` | يرسل |
| `brain/tools/github_backup.sh` | لا يقبل معاملات؛ يكتب. لا تشغّله |
