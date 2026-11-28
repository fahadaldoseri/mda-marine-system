# 14 — خريطة الأسرار

> تاريخ الكتابة: 2026-11-28 (البحرين)
> الفرع: handover/grok-2026-11-28
> الالتزام الأب: 66f16c9364e744db4697c622dec508ac16248e67
> المشغّل المنتهية مهمته: Claude


**أسماء فقط.** لا قيمة هنا ولا جزء منها. الحضور لم يُقس إلا حيث ذُكر.

## الأسماء والقارئ والأثر

| الاسم | أين يُحفظ | من يقرؤه | عند أي خطوة | ما ينكسر إن غاب |
|---|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | سر GitHub Actions؛ وسابقًا `brain/secrets/secrets.env` على الخادم | `brain/tools/telegram_send.py` (البيئة أولًا ثم `.env` ثم `secrets/secrets.env`) و`brain/tools/telegram_bot.py` و`site/server/app.py` | خطوة «ملخص تلغرام» في `daily.yml`؛ `publish_site.sh --telegram` | لا إرسال. النشر نفسه لا ينكسر |
| `TELEGRAM_OWNER_CHAT_ID` | سر Actions؛ ومتغير بيئة SeaWatch | `telegram_send.py` السطر 153 و`site/server/app.py` | مع الإرسال | لا جهة تسليم مالكة |
| `TELEGRAM_WEBHOOK_SECRET` | `brain/secrets/secrets.env` على الخادم؛ حالة التدوير في `brain/state/webhook-secret.txt` (مسار تكتبه الأداة؛ **وعد في الكود والمسار غائب** من المستودع) | `site/server/app.py` و`brain/tools/rotate_webhook_secret.py` | استقبال ويب هوك البوت | يتعطل استقبال الأوامر؛ لا أثر على النشر. حضوره في Actions غير موجود (غير مقروء في `daily.yml`) |
| `DATABASE_URL` | `secrets.env` | `site/server/app.py` | خادم الموقع الحيّ المحلي | خادم الواجهة المحلي فقط |
| `ANTHROPIC_API_KEY` | سر Actions (حضوره غير مؤكد) | `brain/tools/agent_write_llm.py` السطر 136 | خطوة كتابة الوكيل W010/W030/W020/B004 | يرجع الكاتب إلى freellmapi؛ فشل 27 نوفمبر عند W010 بنموذج مجاني. **هذا قرار المالك المعلق** |
| `OPENAI_API_KEY` | `secrets.env` (في القالب) | `brain/tools/check_api_keys.py` فقط | فحص مفاتيح | لا أثر تشغيلي مؤكد |
| `CLOUDFLARE_API_TOKEN` | سر Actions؛ ومفتاح شبكة بيئة SeaWatch (Pages:Edit) | `brain/tools/cloud_deliver.py`؛ ويحقنه وكيل الشبكة في جلسات Claude السحابية | التحقق الحي بعد الدفع إلى `seawatch-live` | تعود `cloud_deliver` إلى التحقق الحي بالبصمة (الإصلاح بند 3 في 08-DONE) |
| `SEAWATCH_LIVE_TOKEN` | سر Actions (يُمرَّر باسم `LIVE_TOKEN`) | `daily.yml` خطوة النشر ← `cloud_deliver.py` | الدفع إلى `seawatch-live` | لا نشر |
| `GITHUB_TOKEN` (`github.token`) | يوفره GitHub | `daily.yml` خطوة حفظ المخرجات وطلب الدمج | بعد النشر | لا فرع `daily/D` ولا طلب دمج |
| 12 اسمًا `FREELLMAPI_*_KEY` | أسرار Actions | `daily.yml` الأسطر 70–81 ← `brain/tools/freellmapi_up.sh` | خطوتا S080 وS090 الاختياريتان | تسقط الخطوتان بلا إيقاف الخط، ويضعف الكاتب الاحتياطي |
| `LLM_BASE_URL`, `LLM_API_KEY` | تُضبط داخل الخطوة | `brain/tools/llm_compat.mjs` و`agent_write_llm.py` | الكتابة بنموذج متوافق | |
| `TELEGRAM_DISABLED` | بيئة | `telegram_send.py` السطر 267 | يعطّل الإرسال عند `1` | مفتاح إيقاف مفيد، لا سر |

الأسماء المعتمدة في قالب `brain/secrets/secrets.env.example`: `TELEGRAM_BOT_TOKEN` و`TELEGRAM_OWNER_CHAT_ID` و`TELEGRAM_WEBHOOK_SECRET` و`DATABASE_URL` و`ANTHROPIC_API_KEY` و`OPENAI_API_KEY`.

## الحضور المقيس

| الموضع | القياس |
|---|---|
| `brain/secrets/secrets.env` في المستودع | **غائب** (لا في `git ls-files` ولا على القرص). مستبعد في `.gitignore` السطران 28–29 |
| أسرار GitHub Actions | لم تُقرأ من هذه الجلسة (واجهة الأسرار لا تُظهر القيم، وصلاحية القراءة غير ثابتة). الحضور غير مقاس |
| متغيرات بيئة هذه الجلسة | مفتاح `CLOUDFLARE_API_TOKEN` يحقنه الوكيل (يعمل على المسار المسموح فقط)؛ غيره غير مقاس |

## التناقض المفتوح

`brain/secrets/README.md` (قرار 24 أكتوبر) يقول إن الأسرار تُحفظ نصًّا في المستودع، و`.gitignore` يمنعه، وD-0638 يقول «قرار مالك مطلوب»، والمالك قرر 20 نوفمبر عدم تدوير ما ظهر في الطلبات القديمة (محادثة، غير مُودَع). الاتساق بين الأربعة غير قائم. لا تحلّه بنفسك: السؤال في 18-OPEN-QUESTIONS.

## قواعد التعامل

| القاعدة | السند |
|---|---|
| لا يُطبع سر في سجل أو مخرج أو تعليق أو التزام | `brain/secrets/README.md` الحد 2 و`CLAUDE.md` القاعدة 6 |
| فحص الأسرار قبل أي إيداع | `python3 brain/validators/check_repo_secrets.py` (يستدعيه `daily.yml` قبل الالتزام) |
| عند الشك في تسرب: تدوير من المزوّد أولًا ثم التحديث | `brain/secrets/README.md` الحد 5. التدوير بقرار المالك |
| تدوير ويب هوك بسكربت | `python3 brain/tools/rotate_webhook_secret.py --dry-run` أولًا (يكتب بلا `--dry-run`) |
