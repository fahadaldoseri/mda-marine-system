# دليل قياس مسارات المصدر 58 — 2026-11-06

المصدر: `58 · المركز الإعلامي للقوات المسلحة اليمنية` — الرابط الأساسي: `https://yafm.net/`.

طريقة القياس: رؤوس ومستخرج `tools/check_feeds.py` (`_payload_items` و`content_extractors.is_real_item`)؛ ومسار المتصفح من `tools/browser_fetch.py`. شرط القبول غير المعدّل: استخراج مشتق لا يُقبل إلا إذا بقيت 3 عناصر حقيقية على الأقل.

| المسار | HTTP/النتيجة | الحمولة | العناصر المرشحة الحقيقية | نتيجة الأداة | الملاحظة |
|---|---:|---:|---:|---|---|
| `https://yafm.net/` | 200 | 8126B | 1 | مرفوض: `derived items without real content (1)` | صفحة `Account Suspended`، نص مرئي 120 حرفًا |
| `https://yafm.net/feed/` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/feed` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/rss/` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/rss.xml` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/atom.xml` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/index.xml` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/category/news/` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق؛ لم تظهر بنية أقسام قابلة للقراءة |
| `https://yafm.net/news/` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/posts/` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/blog/` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/sitemap.xml` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://yafm.net/wp-json/wp/v2/posts?per_page=10` | 200 | 8126B | 1 | مرفوض | نفس صفحة التعليق |
| `https://r.jina.ai/https://yafm.net/` | 200 | 361B | 1 | مرفوض: `derived items without real content (1)` | الوسيط نقل صفحة `Account Suspended` فقط |
| `https://r.jina.ai/http://yafm.net/` | 200 | 360B | 1 | مرفوض: `derived items without real content (1)` | الوسيط نقل صفحة `Account Suspended` فقط |
| `https://archive.org/wayback/available?url=yafm.net/&timestamp=20261106` | 429 | 117B | 0 | مرفوض | خدمة الاستعلام رفضت الطلب بـ429 |
| `https://web.archive.org/cdx/search/cdx?url=yafm.net/*...` | مهلة القراءة | 0B مقاسة | 0 | مرفوض | لم يُعدّ نجاحًا بعد مهلة 25 ثانية |
| `https://web.archive.org/web/20240101000000id_/https://yafm.net/` | 200 | 16449B | 0 | مرفوض: `derived items without real content (0)` | لقطة بلا عناوين حقيقية مقبولة |
| `https://web.archive.org/web/20250101000000id_/https://yafm.net/` | 200 | 6782B | 0 | مرفوض: `derived items without real content (0)` | لقطة بلا عناوين حقيقية مقبولة |
| `https://web.archive.org/web/20260101000000id_/http://yafm.net/` | 200 | 16449B | 0 | مرفوض: `derived items without real content (0)` | نفس نتيجة لقطة 2024 عبر HTTP |
| مسار المتصفح `tools/browser_fetch.py` إلى `https://yafm.net/` | 200 | 8031B | 1 | مرفوض: `derived items without real content (1)` | `مسار المتصفح (مرئي)`؛ صفحة التعليق نفسها |
| `https://web.archive.org/web/20260101000000id_/https://yafm.net/` | 200 | **31161B** | **19** | **مقبول** | `content_chars=4269`؛ بصمة الحمولة `5de06be749936a13faeae95c3223a37a8f0a0fcdbc9b1a5a6edcf3734f5ca0` |

## القرار

اعتمد المسار الأخير فقط في `tools/check_feeds.py` داخل `FALLBACK_ROUTES[58]`:

```text
https://web.archive.org/web/20260101000000id_/https://yafm.net/
via=archive:yafm-home-20260101
```

أُبقي المسار الأساسي والمتصفح كما هما. بعد التعديل، سجل `feeds/feeds-2026-11-06.status.json` يعلن للمصدر 58: `ok=true`, `items_count=19`, `content_chars=4269`, و`via=archive:yafm-home-20260101`. لا يُعدّ هذا المسار دليل حداثة: العناصر المؤرشفة بلا طوابع زمنية، ولذلك بقي `latest_age_days=null`، ويجب ألا تُستعمل وحدها لإثبات واقعة جديدة.

النتيجة التشغيلية بعد إعادة الاشتقاق: `check_feeds.py` خرج `0` وحالة التغذية `ok` مع `failed=0`; علامة pipeline حُدّثت عبر `tools/mark_components.py --component feeds`، وبقيت حالة عامة `degraded` بسبب ستة مصادر متقادمة معروفة ومفصح عنها، لا بسبب المصدر 58.
