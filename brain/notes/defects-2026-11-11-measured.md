# جرد العيوب المقيسة — إصدار 2026-11-11

طريقة القياس: ثلاثة وكلاء قراءة فقط على المادة الخام (ملف الواجهة · سجل الوقائع اليومي · المتنان · المولّدات · الصفحات المبنية)، وكل بند بدليل مسار:سطر. لا إصلاح بلا قياس.

## الموانع الثلاثة

1. **تاريخ التذييل** — المعروض «11 ديسمبر 2026» في `seawatch/dist/reports/2026-11-11.html:1585` و`dist/additions.html:1573`. الصواب 11/11/2026 من `brain/web/meta/2026-11-11.json:4`. السبب: قاموس أسماء الأشهر 1-based في `generator/build_site.py:108-109` تطغى عليه قائمة صفرية الفهرسة في `:353-354`، فيُقرأ الشهر 11 كـ«ديسمبر». الحقن عبر `:229` و`:348`.
2. **سطر IMO في سطح الخريطة** — المعروض «آخر تحديث 30 أكتوبر 2026» في `dist/reports/2026-11-11.html:1425`. ملف الواجهة يثبت `updated.value = 03/11/2026` في `brain/web/meta/2026-11-11.json:596-601`. السبب: `generator/build_report.py:166` يقرأ `source.list_updated` تحديدًا ثم يحوّله للعرض في `:169-177`. تنبيه: مصدر IMO متعارض حقليًا: `source.list_updated = 2026-10-30` و`source.as_at = 3 November 2026` في `brain/appendices/imo-incidents.json:8-10`.
3. **بطاقة «أهم الأخبار» في صفحة الإضافات** — تُسقط «أعلى قطاع» و«الوقائع المؤهلة» و«إجراء اليوم»: `dist/additions.html:1311` مقابل القيم في `dist/reports/2026-11-11.html:1366`. السبب: `generator/build_report.py:2705-2713` يرسم بطاقة الإضافات بصفوف ثلاثة، وشريط الخريطة في `:2477-2479` محجوب في الإضافات، و`generator/build_site.py:328-330` يزيل `decision_card` قبل البناء. القيم الخام: القطاع `meta:381,396-399`، العداد `meta:383-385`، إجراء اليوم `meta:165-168`.

## العيوب المهمة المقيسة

4. **تسمية الموثوقية** — «درجة الموثوقية: منخفضة» في `dist/reports/2026-11-11.html:1425` بينما المصدر `A/2` في `brain/reports/2026-11-11-sectioned.md:47-48,86` و`brain/cumulative-2026/daily/2026-11-11.json:9`. السبب: `generator/build_report.py:1501-1503,1829-1830` يشتق الموثوقية من `confidence`. المطلوب فصل «موثوقية المصدر» عن «درجة الثقة التحليلية».
5. **رمز الواقعة مختصر** — `MN-11-02` بلا وسم اختصار في `dist/reports/2026-11-11.html:1425`؛ الكامل `MN-2026-11-11-02` في `brain/cumulative-2026/daily/2026-11-11.json:34` و`brain/web/meta/2026-11-11.json:124`. السبب: `generator/map_gulf.py:820-823,887,895-907`.
6. **سجل الوقائع بلا وقت واقعة والنص مبتور** — `data-event-has-time="0"`، والنص ينتهي بعلامة حذف تحت وسم «النص الأصلي كما في المصدر» في `dist/reports/2026-11-11.html:1425`؛ السجل يحمل `time_kind = نشر` فقط في `brain/cumulative-2026/daily/2026-11-11.json:33-63` (خصوصًا 41,47). السبب: `generator/build_report.py:1739-1743,1772-1781`.
7. **رابط المصدر عام** — `https://www.ukmto.org/` في `dist/reports/2026-11-11.html:1425` بدل مرساة الدليل `recent-incidents#c151e68e-75d0-4014-b192-491812e31aac` في `brain/cumulative-2026/daily/2026-11-11.json:17`. السبب: `generator/build_report.py:1752-1757` يفضّل `source_url` على `evidence_ref`.
8. **تراكميات بلا سند مؤرخ** — 222 و168 و33 في `dist/reports/2026-11-11.html:1311`؛ الحقول في `brain/web/meta/2026-11-11.json:31-36,49-52,65-68` تحمل `source` عامًا و`updated` بلا قراءة رسمية مؤرخة. السبب: `generator/build_report.py:2509-2516`.
9. **قيم IMO وMSCIO بلا سجل دليل يومي** — «29 سبتمبر» و«Recent Incidents (0)» في `dist/reports/2026-11-11.html:1429-1430`؛ ملف الواجهة `brain/web/meta/2026-11-11.json:202-217`، وسجل اليوم `brain/cumulative-2026/daily/2026-11-11.json:1-63` لا يحوي إلا مدخلي UKMTO. السبب: `generator/blocks.py:647-657`.
10. **النسخة الإنجليزية تسقط اسم أعلى قطاع** وتُبتر عبارة التغطية إلى `During the previous 24 hoursUTC)` — `dist/reports/en/2026-11-11.html:1311`؛ الصواب في `brain/web/meta/2026-11-11.json:6-7` و`site/sources/i18n/en/2026-11-11-sectioned.en.md:26`. السبب: `generator/threat_card.py:219` و`generator/i18n_en.py:2093-2103`.
11. **«1 / 2» بلا عزل اتجاه** — داخل `<span class="mds-v">` في `dist/reports/2026-11-11.html:1366`؛ المصدر `brain/web/meta/2026-11-11.json:378-385`. السبب: `generator/build_report.py:2184,2188-2190`.
12. **عبارة مخاطبة مباشرة** — «اسحب أفقيًا لاستعراض كامل الخريطة» في `dist/reports/2026-11-11.html:1425`؛ نمط الغائب في `brain/reports/2026-11-11-sectioned.md:122`. السبب: `generator/build_report.py:2164`.
13. **الربط أحادي الاتجاه** — رابط من التقرير إلى الإضافات بلا عكس في `dist/additions.html:1228`. السبب: `generator/build_report.py:2347-2353` و`generator/site_chrome.py:438-445`.
14. **وسم وصف الصفحة الإنجليزية ينتهي بـ`>` زائد** — `dist/reports/en/2026-11-11.html:7`؛ الوصف الخام سليم في `brain/web/meta/2026-11-11.json:13`. السبب: `generator/i18n_en.py:2113-2114`.

## مرآة Manus

`https://seawatch-xp4qirmr.manus.space/reports/2026-11-11.html` تُعيد 404 بينما Cloudflare تُعيد 200 بحجم 208616 بايت. سجلات النشر `brain/logs/publish-2026-11-11.json:3-8,23-30` و`publish-channel-2026-11-11.json:7-25` تسجّل Cloudflare وraw.githack فقط ولا تسجّل Manus. مخرج الموقع `seawatch/dist/index.html` (84208 بايت) و`dist/reports/2026-11-11.html` (208616 بايت) موجودان، وGit على main متزامن مع origin. السبب المرجّح: إعداد `build.outputDirectory` في منصة Manus غير مضبوط على `dist` أو المرآة لم تُنشر بعد آخر بناء.