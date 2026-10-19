# حالة نشر خدمة بوت تلغرام — 19 أكتوبر 2026

## المُنجَز
- صورة البوت = الشعار الرسمي للمركز (MDA — Kingdom of Bahrain) بدقة 640×641 ← 512×512، مطبَّقة عبر `setMyProfilePhoto` ✓
- الاسم: «مركز الوعي بالمجال البحري | MDA.BH» · النبذة والوصف ✓ · أمر `/start` ✓ · زر القائمة «التقرير اليومي» → `https://seawatch-xp4qirmr.manus.space` ✓
- معالج الأوامر المحلي: `tools/telegram_bot.py` · سجل الاشتراكات: `appendices/telegram-subscriptions.json` · بوابة الموافقة مطبَّقة.
- خدمة الويب هوك: `server/app.py` · الحاوية: `Dockerfile` (python:3.12-slim + pymysql, EXPOSE 3000) · مسارات: `/healthz` و `/api/telegram/webhook` (تحقق رأس `X-Telegram-Bot-Api-Secret-Token`).
- إعدادات مشروع seawatch: `features.server=true` · `features.database=true` · `deploy={Dockerfile, healthPath:/api/health}` · `routes=[/api/* → server, /healthz → server]`.
- جداول قاعدة البيانات تُنشأ تلقائيًا عند الإقلاع: `subscribers(chat_id PK,label,username,chat_type,status,requested_utc,decided_utc)` و `bot_state`.

## المتبقّي
1. **توكن البوت** سرًّا في المشروع (`TELEGRAM_BOT_TOKEN`) — بانتظار تجديده من BotFather (`/revoke`) ثم إدخاله في بطاقة السر.
2. **سر الويب هوك** (`TELEGRAM_WEBHOOK_SECRET`) و**معرّف صاحب القرار** (`TELEGRAM_OWNER_CHAT_ID=7792142387`).
3. `setWebhook` على `https://seawatch-xp4qirmr.manus.space/api/telegram/webhook` مع `secret_token` و`allowed_updates=[message,channel_post]`، ثم `deleteWebhook` لإنهاء مسار الاستقصاء القديم.
4. إعادة نشر بعد إضافة الأسرار (الحاوية تقرأها وقت التشغيل).
5. تحديث الموصل (connector) بالتوكن الجديد.
6. `can_join_groups=false` حاليًا — لإضافة البوت لمجموعة يجب تفعيله من BotFather (`/setjoingroups`).

## قواعد ملزمة
- لا مشترك بلا `/approve` من صاحب القرار · الجهات «قيد الانتظار» لا تستلم شيئًا.
- الرسالة اليومية = ملخّص + رابط + نسخة PDF.
- القناة للتصنيف «عام» وللتقرير اليومي وحده؛ لا إصدارات خاصة أو مقيّدة.

## تصحيح مهم (19 أكتوبر)
- الحاوية **منشورة وتعمل**: `GET /api/telegram/webhook` يردّ من خدمتنا (`{"ok":false,"error":"not found"}`) أي أن توجيه `/api/*` إلى الخادم ناجح.
- `/healthz` لم يكن موجَّهًا للخدمة (ردّ 404 من المنصة)، فصُحّح مسار الفحص إلى `/api/health` (تحت `/api/*` المضمون).
- قاعدة البيانات المُدارة صارت مُهيّأة للمشروع وتُمرَّر إلى الخدمة عبر `DATABASE_URL` وقت التشغيل.
