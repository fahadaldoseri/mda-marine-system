# مواصفة هندسية لطباعة تقرير عربي RTL طويل إلى PDF عبر Chromium

_إصدار مقترح: 2026-10-18 — موجّه إلى مولّد `build_report.py` ومصدّر Playwright_

---

## القرار التنفيذي

المسار المفضّل هو **التدفّق العمودي أولًا**: حاويات المحتوى الطويلة `block` عادية، بلا `overflow` حاجب، مع حماية الذرات الصغيرة فقط من الكسر. يسمح بعمودين محدودين للفهرس ومفتاح الخريطة، وببطاقات KPI القصيرة بعد إثبات أنها دون حد الذرة. لا يجوز استعمال `grid` أو `flex` كحاوية كبيرة قد تعبر حد الصفحة.

هذه ليست دعوة إلى ضغط التقرير. النسخة الحالية تخفي سبب المشكلة تحت سلسلة من قواعد `!important`: حجم المتن ينتهي إلى `10.2pt`، ووسيلة الخريطة إلى `8.4pt`، وتباعد السطر إلى `1.36`، بينما القياس السابق سجّل تحسنًا من 19 صفحة ومتوسط تعبئة 90.1% وفجوة 117 مم إلى 15 صفحة ومتوسط 95.7% وفجوة 41 مم. المطلوب الآن **استعادة القراءة المريحة مع إبقاء بوابة الفجوات**، لا العودة إلى كثافة النسخة الحالية.

> **ملاحظة حاسمة:** يوجد عنوان مكرر في HTML: `sec-00` و`sec-01` كلاهما «ما تغيّر منذ التقرير السابق». لذلك لا يجوز أن تكون خريطة الفهرس keyed بالعنوان؛ يجب أن تكون keyed بالمعرّف الفريد للقسم.

## 1. نطاق التنفيذ والحالة المقيسة

### 1.1 الملفات التي بُنيت عليها المواصفة

- `seawatch/generator/build_report.py`: كتلة `@media print` الحالية تنتهي بإعادة ضبط عامة `*{break-inside:auto !important}` ثم تحويل حاويات كثيرة إلى `block` وأبنائها إلى `inline-block`، مع ضغط إضافي للخطوط.
- `seawatch/dist/reports/2026-10-18.html`: صفحة `lang="ar" dir="rtl"`، وبها `section.doc` من `sec-00` إلى `sec-16`، و`h2` ذات معرّفات، و`kpis` و`dc-grid` و`tbl-wrap` و`tbl-scroll` و`map-viz` و`map-legend`.
- `brain-marine-news/tools/export_report_assets.py`: يستخدم A4 وهوامش Playwright مقدارها `top 16mm / bottom 18mm / left 18mm / right 18mm`، ويضيف `headerTemplate` و`footerTemplate`، ويطبع بتمريرتين للفهرس، مع `tagged=True` و`outline=True`.
- `notes/print-fix-2026-10-18.md`: يثبت أن السبب الجذري هو الحاويات الكبيرة `grid/flex` و`overflow:hidden` والعناصر غير القابلة للانقسام، لا نقصًا في النص.

### 1.2 تعارضات يجب إغلاقها قبل تعديل CSS

1. `build_report.py` يعرّف `@page{size:A4;margin:14mm 12mm}`، بينما Playwright يمرّر هوامش مختلفة. يجب اعتماد مصدر واحد للقيم؛ هذه المواصفة تعتمد هوامش Playwright المذكورة أعلاه.
2. أداة التصدير تضيف CSS بعد CSS الصفحة. يجب ألا تبقى قواعد تشخيصية قديمة في آخر `@media print` بعد لصق السياسة الجديدة؛ وإلا ستنتصر `!important` القديمة وتعيد تصغير الخط.
3. `inject_toc()` و`locate_titles()` الحاليان يعتمدان على نص العنوان. هذا يفشل مع العناوين المكررة، وقد يطبع رقم صفحة لقسم غير المقصود. استخدم `id`/`data-print-anchor` كهوية، واستخدم النص فقط للتحقق.
4. بوابة `check_pdf_format.py` تستخدم منطقة قياس من 9 مم إلى 12 مم، بينما إعداد PDF الفعلي 16 مم و18 مم. يجب توثيق هذه المنطقة بوصفها منطقة المحتوى الفعلية أو معايرتها على PDF النهائي؛ لا تخلط بين هامش الصفحة وارتفاع رأس/تذييل القالب.

## 2. سياسة تجزئة الصفحات المضمونة ضد الفراغات

### 2.1 مبدأ الحاوية والذرة

نقسم DOM المطبوع إلى نوعين:

- **حاوية تدفّق (`flow container`)**: يجوز أن تعبر الصفحة وأن تُقسّم بين صفحتين. تكون `display:block`، و`break-inside:auto`، و`overflow:visible`، ولا تحتوي `transform` أو `contain` أو `position:sticky`.
- **ذرة (`atomic item`)**: وحدة قصيرة ينبغي ألا تنقسم، مثل عنوان مع سطره، صف جدول قصير، KPI صغير، عنصر من مفتاح الخريطة، أو SVG الخريطة نفسه. لها `break-inside:avoid`، لكن لا يجوز أن يتجاوز ارتفاعها الفعلي **60 مم**.

حد 60 مم عقد قياس لا تعليمة قص. لا نستخدم `max-height:60mm` مع `overflow:hidden`؛ ذلك يخفي النص ويعيد المشكلة. إذا تجاوزت الذرة 60 مم، نفكّك محتواها إلى ذرات أصغر، أو نجعلها حاوية قابلة للتدفّق، أو نصغّر أصلًا (مثل SVG) مع إبقاء النص كاملًا.

> `break-inside:avoid` ليس ضمانًا مطلقًا في Chromium إذا كان العنصر أطول من الصفحة المتاحة؛ لذلك يجب أن يثبت القياس أن كل عنصر محمي أصغر من 60 مم.

### 2.2 ما يجوز وما لا يجوز من Grid/Flex في مسار الطباعة

| الحالة | السياسة في print | أمثلة من التقرير |
|---|---|---|
| حاوية طويلة أو قائمة قد تتجاوز حد الصفحة | **ممنوع `grid` و`flex`**؛ حوّلها إلى `block` | `.wrap`, `main`, `.changes`, `.dc-grid`, `.src-grid`, `.tl-viz`, `.viz`, `.decision`, `.map-viz` |
| بطاقات قصيرة مستقلة، وثبت بقياسها أنها `<60mm` | مسموح `inline-block` أو `grid/flex` محلي، مع `break-inside:avoid` لكل بطاقة، وليس للحاوية كلها | `.kpis > .kpi` |
| صف بصري صغير داخل ذرة، لا يعبر الصفحة | مسموح `flex` أو `grid`، بشرط ألا يحمل نصًا طويلًا وألا يستخدم `overflow` قصّيًا | أيقونة + وسم، أو شريط قياس صغير |
| ترويسة/تذييل Playwright | `flex` في قالب الهامش مقبول لأنه ليس صندوق محتوى متعدد الصفحات؛ حافظ على أبعاد ثابتة | `HEADER_TPL`, `FOOTER_TPL` |
| جدول حقيقي | اتركه `table` حقيقيًا؛ لا تستبدله بـ`display:grid` على الخلايا | `.tbl-wrap table`, `.rel-tbl` |

`masthead` يمكن أن يبقى `block`؛ لا حاجة إلى محاكاة ترتيب الشاشة في PDF. و`dc-grid`/`dc-row` يعرضان label ثم value عموديًا عند الحاجة؛ سلامة القراءة أهم من الحفاظ على عمودين ضيقين.

### 2.3 سياسة `break-*` على مستوى العناصر

- `section.doc`: `break-inside:auto` و`break-after:auto`. لا تُجبر كل الأقسام على صفحة جديدة ولا تمنع انقسام القسم الطويل.
- `section.doc > h2`, `h3`, `h4`: `break-after:avoid` فقط كي لا يبقى العنوان وحيدًا؛ لا تطبق `break-inside:avoid` على القسم كله.
- `.h-rule` و`.sec-lede`: `break-after:avoid`؛ يجب أن يتبع العنوان/الفاصل شيء من محتواه، لا أن تُحمى الكتلة كاملة.
- `.print-page-start`: `break-before:page` فقط للأقسام التي اتُّخذ قرار تحريري أن تبدأ صفحة؛ لا تُنشأ تلقائيًا لكل `section.doc`.
- الفقرات والقوائم: `orphans:3; widows:3`، ويمكن النزول إلى 2 في الجداول الكثيفة بعد الفحص البصري.
- صف الجدول، KPI القصير، عنصر الخريطة، وسطر التغيير القصير: `break-inside:avoid`؛ لا تطبقها على wrapper طويل.
- لا تستخدم `break-after:page` بعد كل قسم؛ غالبًا ينتج نصف صفحة فارغة.
- لا تستخدم `*{break-inside:auto !important}` أو `*{overflow:visible !important}` كحل تشخيصي دائم؛ فهي تلغي سياسة الذرات وقد تفسد الجداول والشارات. عيّن القاعدة على الحاويات المعروفة فقط.

### 2.4 `overflow`

أي `overflow:hidden/clip/auto/scroll` على ancestor طويل ممنوع في print؛ فهو قد يحوّل الحاوية إلى صندوق غير قابل للتجزئة أو يقص النص. في التقرير الحالي، يجب إزالة `overflow:hidden` من `.map-wrap` و`.kpi` إن كانا سيحملان محتوى قابلًا للكسر، وإزالة `overflow:auto` من `.tbl-wrap` و`.tbl-scroll` في print.

الاستثناء الوحيد هو زخرفة قصيرة ثبت أنها ذرة، مثل `.bar-track` الذي لا يحمل نصًا؛ يمكنه الاحتفاظ بـ`overflow:hidden`. لا تستخدم الاستثناء للخريطة أو الجدول.

### 2.5 بدائل العمودين ومساوئها

1. **التدفّق العمودي العادي (المفضّل):** أقل اعتمادًا على سلوك fragmentation في Chromium. استخدمه لكل النص والبطاقات والتحليل والجداول. عيبه أنه قد يزيد الصفحات.
2. **`columns:2`:** مناسب فقط لـ`#sec-toc ol` و`.map-legend` وقوائم قصيرة متجانسة؛ كل `li` ذرة. يوفر مساحة، لكن ترتيب القراءة RTL، موازنة الأعمدة، ونقل العنصر الطويل بين الأعمدة قد تختلف مع Chromium. لا تستخدمه للنثر أو البطاقات أو الجدول.
3. **`display:table/table-cell`:** يمكن أن يحافظ على عمود label/value أو KPI compact، لكنه يجعل الصف أقرب إلى ذرة غير قابلة للكسر، ويعقد الوصولية وترتيب القراءة، وقد يعيد دفع صف عريض أو طويل إلى الصفحة التالية. استخدمه فقط كحل fallback لصفوف قصيرة ومقاسة، وليس كبديل عام لـ`grid`.

## 3. مقاسات القراءة المريحة على A4

### 3.1 المقاس الفيزيائي والمنطقة القابلة للقراءة

A4 هو `210 × 297mm` وفق ISO 216. نعتمد:

- أعلى: **16 مم**؛ أسفل: **18 مم**؛ يمين/يسار: **18 مم**.
- عرض المحتوى النظري: `210 - 18 - 18 = 174 مم`.
- ارتفاع المحتوى النظري: `297 - 16 - 18 = 263 مم`، قبل احتساب المساحة البصرية التي يشغلها قالب الرأس/التذييل.
- متن النثر: لا يُدفع إلى عرض أصغر من اللازم؛ استهدف **60–75 حرفًا عربيًا في السطر**، أو `max-inline-size:72ch` إذا كان الخط يدعم قياس `ch` بشكل متوقع. لا تستخدم عمودين للنثر العربي الطويل.
- اترك padding داخليًا لا يقل عن 3–4 مم داخل البطاقة أو الجدول؛ لا تحوّل كامل عرض 174 مم إلى كتلة بلا تنفس.

### 3.2 القيم الموصى بها

| العنصر | القيمة الموصى بها للطباعة | الحد الأدنى العملي | ملاحظة |
|---|---:|---:|---|
| متن الفقرة والقائمة | **11.5pt** | 10.8pt | لا تستخدم `10.2pt` للمتن؛ هذا هو سبب الشكوى الحالية |
| تباعد أسطر المتن | **1.65** (نحو 19pt عند 11.5pt) | 1.5 | العربية تحتاج فراغًا رأسيًا لتمييز الحركات واتصال السطور |
| lead/ملخص القسم | 12–12.5pt، line-height 1.65–1.7 | 11.5pt | يظل أوضح من المتن لا أصغر منه |
| عنوان التقرير H1 | 22–24pt، line-height 1.2–1.3 | 20pt | لا يجعل الغلاف عنوانًا ضخمًا على حساب الملخص |
| عنوان القسم H2 | 15.5–16pt، line-height 1.35–1.45 | 14pt | `break-after:avoid` مع أول محتوى |
| عنوان فرعي H3 | 12.5–13.5pt، line-height 1.45–1.55 | 12pt | أغمق/أثقل، لا أصغر كثيرًا |
| KPI label | 10.5–11pt، line-height 1.45–1.55 | 10pt | لا تنزل إلى 8.6pt |
| KPI value | 18–20pt، line-height 1.2–1.3 | 16pt | الأرقام العربية/اللاتينية في `bdi` و`white-space:nowrap` عند اللزوم |
| KPI note/badge | 10–10.5pt، line-height 1.45–1.55 | 9.5pt | يفضل حذف الوصف غير الضروري بدل تصغيره |
| جدول: نص الخلية | 10.5–11pt، line-height 1.4–1.5 | 10pt | الجداول الطويلة تُجزّأ منطقيًا لا تُضغط إلى 8pt |
| جدول: header | 10.5–11pt، line-height 1.35–1.45 | 10pt | `thead` متكرر |
| padding رأسي للخلية | **2.0–2.5 مم** | 1.5 مم | الحالي 1.5 مم كثيف؛ زدّه حيث يسمح عدد الصفحات |
| padding أفقي للخلية | 2.5–3 مم | 2 مم | امنع التصاق الحروف بحدود الجدول |
| مفتاح الخريطة | 9.5–10pt، line-height 1.4–1.5 | 9pt | كل عنصر أقل من 60 مم |
| رأس/تذييل Playwright | 7.5–8.5px | 7px | هذا استثناء هامشي، وليس متنًا |

لا يوجد في WCAG حد إلزامي عام لحجم خط PDF المطبوع. القيم أعلاه قرار قراءة عملي، وتستند إلى **قاعدة طول السطر في The Elements of Typographic Style (Robert Bringhurst)**، ومبادئ **Typography: A Manual of Design (Emil Ruder)**، وإرشادات **WCAG 2.2، Success Criterion 1.4.8 Visual Presentation** بوصفها معيارًا استرشاديًا (AAA) لطول السطر وتباعد السطور، لا بوصفها شرطًا قانونيًا خاصًا بهذا التقرير. يجب التحقق بعينة مطبوعة فعلية؛ الخط العربي المختار قد يغيّر الإحساس بالحجم عند نفس `pt`.

### 3.3 قاعدة عدم الضغط

إذا زاد عدد الصفحات بعد رفع المتن إلى 11.5pt، فالترتيب الصحيح للتقليل هو: إزالة الحشو الزخرفي، حذف التكرار التحريري، فصل الجداول العريضة، أو نقل الخريطة إلى موضع أفضل. لا نقلل المتن إلى أقل من 10.8pt ولا مفتاح الخريطة إلى أقل من 9pt لمجرد البقاء عند 15 صفحة.

## 4. آلية الفهرس وترقيم الصفحات

### 4.1 الهوية: anchor فريد لكل قسم

الأفضل استخدام `section.id` الموجود (`sec-00` ...)، وإضافة `data-print-anchor` إلى `h2` إن لم يكن له معرّف فريد:

```html
<section class="doc" id="sec-03">
  <h2 id="h-03" data-print-anchor="sec-03">التوزيع الجغرافي للوقائع</h2>
  ...
</section>
```

قواعد الهوية:

- كل `section.doc` المطبوع له `id` فريد؛ افشل البناء عند التكرار أو الفراغ.
- الفهرس يخزن `{id, title}` ولا يخزن `{title: page}`.
- روابط الفهرس تكون `<a href="#sec-03">...`، والرقم عنصر منفصل `<span class="toc-n" data-page-for="sec-03">ص 7</span>`.
- تعارض النص المكرر لا يهم؛ الهوية هي `sec-00`/`sec-01`.

### 4.2 القياس الحي ثم PDF: تمريرات قابلة للتقارب

القياس الحي مفيد لتحديد موضع anchor بعد اكتمال الخطوط والصور، لكنه لا يكفي وحده لأن Chromium لا يعرض API موثوقًا يعيد «رقم fragment/page» لكل عنصر قبل إنشاء PDF. لذلك الضمان يكون بالمزيج التالي:

1. طبّق CSS النهائي، `emulate_media("print")`، وانتظر `document.fonts.ready` و`img.decode()` وSVG/صور الخريطة.
2. احذف أي فهرس قديم وأدرج فهرسًا مؤقتًا بعلامة `…`؛ لا تغيّر ارتفاع كل بند بين التمريرات.
3. نفّذ **live measure** لكل `[data-print-anchor]`: خذ `getBoundingClientRect()`/`getClientRects()`، وسجّل الارتفاع، وأقرب موضع رأسي، وهل تجاوز الذرة 60 مم. استخدم ارتفاع منطقة المحتوى المتوقع `263mm` فقط كرقم مرشح، لا كحقيقة نهائية.
4. اطبع pass 1 بنفس `format="A4"` وهوامش Playwright والرأس والتذييل النهائيين.
5. استخرج نص pass 1 بـ`pdftotext -layout`، وطبّع محارف RTL، ثم ابحث عن **العنوان المرتبط بالـid** في الصفحات. إذا كان النص مكررًا، اربط المرشح بترتيب الـanchor والصفحة؛ لا تسمح بمطابقة عنوان منفرد غير فريد.
6. اكتب أرقام الصفحات داخل HTML ثم اطبع pass 2. بعد pass 2 أعد القياس والاستخراج. إذا تغيّر أي رقم، أعد الإدراج والطباعة حتى ثبات الخريطة أو ثلاث دورات كحد أقصى؛ عند عدم التقارب افشل الإصدار بدل طباعة فهرس تخميني.
7. افحص أن كل `data-page-for` له رقم حقيقي، وأن كل رقم يساوي أول صفحة يظهر فيها القسم في PDF. أرقام الفهرس ليست «حسابًا من ارتفاع DOM»؛ PDF النهائي هو مصدر الحقيقة.

مثال هيكلي مختصر لتعديل `sections_of` وحقن الفهرس:

```python
# لا تستخدم العنوان كمفتاح؛ العنوان قد يتكرر.
def sections_of(page):
    return page.evaluate("""() => [...document.querySelectorAll('section.doc')]
      .filter(s => s.id !== 'sec-16' && getComputedStyle(s).display !== 'none')
      .map(s => {
        const h = s.querySelector('h2');
        return {id: s.id, title: (h?.textContent || '').replace(/\\s+/g, ' ').trim(),
                anchor: h?.id || s.id};
      }).filter(x => x.id && x.title)""")

# كل عنصر في TOC يجب أن يشير إلى section id، والرقم قابل للاستبدال.
items = ''.join(
    f'<li><a href="#{s["id"]}">{escape(s["title"])}</a> '
    f'<span class="toc-n" data-page-for="{s["id"]}">ص {pages.get(s["id"], "…")}</span></li>'
    for s in sections
)
```

وللقياس الحي، استخدم قيمة الصفحة كمرشح تشخيصي لا كبوابة وحيدة:

```javascript
// تُستدعى بعد fonts.ready وdecode للصور، مع print media.
({ pageHeightMm = 263, pxPerMm = 96 / 25.4 } = {}) => {
  const pageHeightPx = pageHeightMm * pxPerMm;
  return [...document.querySelectorAll('[data-print-anchor]')].map(el => {
    const r = el.getBoundingClientRect();
    const top = r.top + window.scrollY;
    return {
      id: el.dataset.printAnchor,
      liveCandidate: Math.floor(top / pageHeightPx) + 1,
      topPx: top,
      heightPx: Math.max(...[...el.getClientRects()].map(x => x.height), 0)
    };
  });
}
```

### 4.3 أرقام الصفحات في التذييل

الإعداد الحالي في `export_report_assets.py` صحيح من حيث المبدأ:

```python
kwargs = dict(
    format="A4", print_background=True,
    margin={"top":"16mm", "bottom":"18mm", "left":"18mm", "right":"18mm"},
    tagged=True, outline=True,
    display_header_footer=True,
    header_template=HEADER_TPL,
    footer_template=FOOTER_TPL,
)
```

وفي `footerTemplate`:

```html
<span>صفحة <span class="pageNumber"></span> من <span class="totalPages"></span></span>
```

`pageNumber` و`totalPages` رمزا Playwright/Chromium، ويستبدلهما المتصفح عند إنشاء PDF؛ لا تحاول حسابهما من DOM ولا تستخدم CSS counter لهذا الغرض في Chromium. أبقِ القالب بسيطًا: inline styles، خط مثبت، بلا JavaScript أو روابط خارجية أو عناصر تحتاج تحميلًا. لفّ الأرقام داخل `direction:ltr; unicode-bidi:isolate` إذا أدى RTL إلى عكس ترتيبها.

### 4.4 حدود الترقيم

- `totalPages` معروف للـPDF النهائي فقط؛ لا يمكن للفهرس أن يقرأه من `footerTemplate` أثناء بناء HTML.
- `outline=True` يضيف bookmarks حسب العناوين في الإصدارات التي تدعم ذلك، لكنه لا يغني عن فهرس HTML ولا يضمن رقم صفحة ظاهرًا.
- تغيير خط، هامش، ارتفاع header/footer، حجم الفهرس، أو تحميل SVG بعد pass 1 يغيّر pagination؛ لذلك يجب أن تكون كل التمريرات بنفس الإعدادات وأن ننتظر استقرار الموارد.
- استخراج العربية من PDF قد يعكس ترتيب RTL أو يضع علامات تشكيلًا مختلفة؛ دالة `norm` الحالية مناسبة كطبقة تحقق، لكن يجب الاحتفاظ أيضًا بالـid وبصمة نص العنوان القصيرة.
- لا يوجد ضمان عام بأن `getBoundingClientRect()` وحده يرى كسور الصفحات؛ لهذا لا تُسلّم pass 2 قبل مطابقة PDF.

## 5. مقتطف CSS جاهز للصق

> **طريقة الاستخدام:** ضع هذا المقتطف في نهاية كتلة الطباعة النهائية بعد توحيد `@page`، أو استخدمه بدل الجزء التشخيصي الذي يبدأ في `build_report.py` عند سياسة «التدفّق الموحّدة». لا تلصقه قبل القواعد القديمة التي تحتوي `!important` ثم تتوقع أن ينتصر عليها. احذف/استبدل القواعد القديمة المتعارضة، خصوصًا `line-height:1.36` وأحجام KPI `8.6pt/7.6pt`.

```css
/* ================= سياسة PDF RTL ثابتة — Chromium / Playwright ================= */
@page {
  size: A4;
  /* مصدر واحد للقيم: يطابق margin في page.pdf() */
  margin: 16mm 18mm 18mm 18mm;
}

@media print {
  :root {
    --print-atomic-limit: 60mm; /* حد قياس، وليس max-height ولا قصًا */
  }

  html {
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }

  body {
    background: #fff !important;
    color: #111 !important;
    font-size: 11.5pt !important;
    line-height: 1.65 !important;
    text-rendering: optimizeLegibility;
  }

  /* الحركة والزخرفة لا تدخل في هندسة الصفحة */
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
    box-shadow: none !important;
  }
  body::before,
  .site-nav, .sn-foot, .topbar, .no-print { display: none !important; }
  .wrap { max-width: none !important; padding: 0 !important; }

  /* الحاويات الطويلة: block عادي قابل للتدفق، لا overflow حاجب */
  main,
  section.doc,
  .changes, .dc-grid, .src-grid, .tl-viz,
  .viz, .decision, .map-viz, .tbl-wrap, .tbl-scroll {
    display: block !important;
    min-width: 0 !important;
    max-width: 100% !important;
    break-inside: auto !important;
    page-break-inside: auto !important;
    overflow: visible !important;
  }

  /* العنوان يبقى مع أول محتوى فقط؛ القسم نفسه لا يُحمى */
  section.doc > h2,
  section.doc h3,
  section.doc h4,
  section.doc > .h-rule,
  section.doc > .sec-lede {
    break-after: avoid !important;
    page-break-after: avoid !important;
  }
  section.doc { break-after: auto !important; page-break-after: auto !important; }
  .print-page-start { break-before: page !important; page-break-before: always !important; }

  p, li, blockquote, .sec-lede, .blk-lede, .note {
    orphans: 3;
    widows: 3;
  }

  /* الذرات: لا تضع هذا الصنف إلا على عنصر مقاسه < 60mm فعليًا */
  .print-atomic,
  .kpi,
  .changes > li,
  .map-legend > li,
  .glossary > li,
  tbody tr,
  .tl-viz .tl-row {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }
  /* لا تضف max-height/overflow:hidden هنا؛ تجاوز 60mm خطأ قياس يجب إصلاحه */

  /* KPI: عمودان فقط لبطاقات قصيرة؛ النص داخل كل بطاقة لا يُقص */
  .kpis { display: block !important; font-size: 0; }
  .kpis > .kpi {
    display: inline-block !important;
    vertical-align: top;
    width: 48.5% !important;
    margin: 0 0 3mm 1% !important;
    padding: 3mm 3.2mm !important;
    font-size: 11.5pt;
    background: #fff !important;
    border: .4pt solid #b8c4d1;
    border-radius: 2mm;
  }
  .kpi .k-l { font-size: 10.8pt !important; line-height: 1.5 !important; min-height: 0 !important; }
  .kpi .k-v { font-size: 19pt !important; line-height: 1.25 !important; }
  .kpi .k-d, .kpi .k-n { font-size: 10pt !important; line-height: 1.5 !important; }

  /* قرار طويل وتحليل طويل: label/value عموديان يمنعان دفع صف كامل */
  .dc-grid, .dc-row { display: block !important; width: 100% !important; }
  .dc-row { margin: 0 0 3mm !important; }
  .dc-row > * { display: block !important; width: 100% !important; }
  .dc-l { font-size: 10.5pt !important; line-height: 1.45 !important; }
  .dc-v { font-size: 11.5pt !important; line-height: 1.65 !important; }

  /* لا نحافظ على flex/grid في قوائم التغيّر والمخططات */
  .changes > li, .tl-viz .tl-row, .viz .bar-row { display: block !important; }
  .viz .bar-track { display: block !important; margin: 1.5mm 0 !important; overflow: hidden !important; }

  /* عمودان مسموحان لقوائم قصيرة متجانسة فقط */
  #sec-toc ol, .map-legend {
    columns: 2;
    column-gap: 8mm;
    column-fill: auto;
    display: block !important;
  }
  #sec-toc li, .map-legend li {
    break-inside: avoid;
    page-break-inside: avoid;
    font-size: 10pt !important;
    line-height: 1.45 !important;
    margin: 0 0 2mm !important;
  }

  /* الجداول: جدول حقيقي، wrapper لا يحجز التجزئة، ورأس يتكرر */
  .tbl-wrap, .tbl-scroll { overflow: visible !important; }
  table {
    width: 100% !important;
    min-width: 0 !important;
    table-layout: auto;
    border-collapse: collapse;
    font-size: 10.8pt !important;
    line-height: 1.45 !important;
  }
  thead { display: table-header-group; }
  thead tr { break-after: avoid; page-break-after: avoid; }
  th { padding: 2mm 2.5mm !important; line-height: 1.4 !important; }
  td { padding: 2mm 2.5mm !important; line-height: 1.45 !important; vertical-align: top; }
  td.num, th.num { white-space: nowrap; direction: ltr; unicode-bidi: isolate; }

  /* SVG/صورة الخريطة ذرة واحدة؛ المفتاح هو الذي ينقسم منفصلًا */
  .map-wrap { overflow: visible !important; }
  .map-viz svg, .map-viz img {
    display: block !important;
    width: 100% !important;
    height: auto !important;
    max-height: 58mm !important;
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }
  .map-caption, .map-viz figcaption { font-size: 10pt; line-height: 1.45; }

  /* حدود وألوان صديقة للطباعة؛ لا تعتمد على shadow/gradient لتمييز المعنى */
  section.doc, .card, .viz, .decision, .kpi, .src, .map-wrap {
    background: #fff !important;
    border-color: #b8c4d1 !important;
    background-image: none !important;
  }
  a { color: #0a1524 !important; text-decoration: none; }

  /* لا تخفِ القيمة صفر؛ أخفِ الزخرفة أو الحقول الغائبة فقط */
  .k-v, td.num, th.num { direction: ltr; unicode-bidi: isolate; }
}
```

## 6. خطة الإصلاح التدريجية والبدائل

### 6.1 ترتيب البدائل

| الترتيب | البديل | التغيير | الأثر المتوقع على الصفحات | سلامة القراءة والمخاطر |
|---:|---|---|---|---|
| 1 | **A — Flow-first موصى به** | استبدال حاويات `grid/flex` الطويلة بـ`block`، إبقاء KPI القصيرة في عمودين، جعل القرار/التحليل/الجداول تدفقًا، رفع المتن إلى 11.5pt والخلايا 10.8–11pt | من baseline v4 ذي 15 صفحة إلى **16–18 صفحة غالبًا**؛ النطاق المعتمد الحالي 13–18 | أعلى سلامة، أقل فجوات؛ قد يحتاج حذف تكرار أو نقل الخريطة كي تبقى البوابة داخل 18 صفحة |
| 2 | **B — Flow + أعمدة محدودة** | A مع `columns:2` للفهرس ومفتاح الخريطة وبعض القوائم القصيرة، وinline-block للكروت المثبتة تحت 60 مم | **15–17 صفحة غالبًا** | قراءة جيدة إذا بقيت الأعمدة للقوائم القصيرة؛ خطر ترتيب RTL/موازنة الأعمدة، لذلك يلزم PDF diff لا CSS inspection فقط |
| 3 | **C — Table fallback** | تحويل صفوف KPI أو label/value القصيرة إلى table layout، إبقاء النص الطويل block | **14–16 صفحة** وقد يقل الهدر | أكثر كثافة وأعلى احتمال صف طويل غير قابل للكسر؛ أصعب وصولية، ولا يُستخدم إلا للكتل القصيرة التي فشل قياسها في B |

الأرقام توقعات وليست عقدًا؛ عدد الصفحات يتأثر بالنص والخط ونسخة Chromium. لا تُصغّر الخط لإجبار A على 15 صفحة. إذا احتاجت القراءة المريحة 18 صفحة، فذلك مقبول داخل profile الحالي.

### 6.2 خطوات التنفيذ والمقاييس

**المرحلة 0 — تثبيت القياس قبل تغيير الشكل**

1. احفظ PDF baseline الحالي، واطبع `pdfinfo`, و`pdftoppm -r 80`, و`pdftotext -layout`.
2. أضف فاحص DOM يرفض: حاوية print `grid/flex` طويلة، ancestor ذي `overflow` حاجب، duplicate section id، وذرة `>60mm`.
3. صحح بوابة القياس لتستخدم منطقة موثقة ومتسقة مع هوامش 16/18 مم، ولا تعتمد على آخر بكسل داكن إذا كان من التذييل.

**المرحلة 1 — تنفيذ A**

1. استبدل نهاية `@media print` بالسياسة الموحدة أعلاه، وامنع قواعد `!important` القديمة من الظهور بعدها.
2. فعّل live anchor measurement وانتظار الخطوط والصور.
3. نفّذ تمريرات الفهرس حتى convergence، ثم شغّل `check_pdf_format.py` مع `--allow-css-change` أثناء التطوير فقط.

**المرحلة 2 — تحسين محدود إلى B عند الحاجة**

1. فعّل عمودين للفهرس/المفتاح فقط بعد إثبات أن كل `li` أقل من 60 مم.
2. قارن PDF pass 2 مع A: الصفحات، مواضع العناوين، ترتيب بنود الفهرس، أطول فجوة، ونسبة التعبئة.

**المرحلة 3 — C كحل fallback**

1. استخدم table layout لكتلة قصيرة محددة، لا للمقال أو البطاقات الطويلة.
2. افحص `thead` والتكرار والوصولية النصية، ثم اعتمد البديل فقط إذا قلّت الفجوات دون نزول المتن عن القيم الموصى بها.

### 6.3 بوابة النجاح الإلزامية

لا يعتبر الإصدار ناجحًا إلا إذا تحققت كل الشروط التالية:

- PDF A4، وهوامش مطابقة للإعداد الواحد الموثق.
- عدد الصفحات داخل `print-profile.json` (13–18 حاليًا) أو اعتماد profile جديد إذا كان التغيير التحريري يستحق أكثر.
- متوسط تعبئة منطقة المحتوى **≥92%**، ولا صفحة محتوى أقل من **70%** إلا باستثناء موثق للغلاف/الصفحة الأخيرة.
- لا فجوة داخلية **≥45 مم**، مع إصلاح فجوة الخريطة ذات 41 مم بدل اعتبارها مقبولة تلقائيًا.
- صفر حاويات كبيرة `grid/flex` أو `overflow` حاجب في مسار الطباعة.
- صفر ذرات محمية أكبر من **60 مم**.
- الفهرس: كل anchor فريد، كل بند له رقم، ولا فرق بين رقم الفهرس وأول صفحة للقسم في PDF.
- التذييل موجود في **100% من الصفحات**، لا 80% فقط؛ ويحتوي `pageNumber` و`totalPages` قابلين للاستخراج.
- كل `thead` يعاد عند انقسام الجدول، ولا يوجد صف مقطوع أو header يتكرر مرتين داخل الصفحة.
- حجم المتن الفعلي ≥11.5pt، line-height ≥1.5، وحجم الخلية ≥10.5pt، باستثناء header/footer الهامشي.
- القيم الصفرية المتوقعة ظاهرة (`0`, `0.0`, أو `0%`) ولا تحولت إلى فراغ.
- مراجعة بشرية على 100% وعلى نسخة مطبوعة: عناوين عربية متصلة، لا clipping، لا انقلاب أرقام، والخريطة مقروءة.

## 7. فخاخ يجب تجنبها

### 7.1 الجداول ورأس الجدول

- لا تضع `overflow:auto` على `.tbl-wrap` في print؛ يخلق صندوق تمرير غير قابل للتجزئة.
- استخدم `thead{display:table-header-group}` على جدول حقيقي فقط. لا تستخدم `display:block` على `thead`/`tbody` لأن ذلك يعطل تكرار الرأس وتطابق الأعمدة.
- `tbody tr{break-inside:avoid}` مناسب للصف القصير؛ إذا كان صف واحد يحمل فقرة تتجاوز 60 مم، قسّم البيانات إلى صفوف منطقية أو عناصر block قبل الجدول.
- لا تكرر `thead` يدويًا في HTML؛ وإلا سيظهر رأس مضاعف عند حدود الصفحات.
- لا تصغر الجدول إلى 8pt لحل عرض زائد؛ احذف عمودًا ثانويًا، أو افصل الجدول، أو اتخذ قرارًا بالوضع الأفقي في تقرير مستقل.

### 7.2 العنوان و`break-after:avoid`

`break-after:avoid` (وليس `since-avoid`؛ لا توجد قيمة CSS قياسية بهذا الاسم) يصلح للعنوان مع الفاصل/السطر التمهيدي فقط. إذا طُبق على `section.doc` أو كتلة كبيرة، قد يدفع كتلة كاملة ويترك فراغًا. لا يوجد في Chromium ضمان أن «keep with next» سيحل كل الحالات؛ القياس البصري وPDF النهائي هما الحكم.

### 7.3 الصور وSVG والخريطة

- انتظر `document.fonts.ready` و`img.decode()` قبل pass 1، وإلا يتغير ارتفاع المحتوى بين التمريرات.
- اجعل SVG الخريطة `display:block;width:100%;height:auto;max-height:58mm`، ولا تقصه بـ`overflow:hidden`؛ إذا لم يتسع فصغّر الرسم أو افصل الرسم عن المفتاح.
- لا تستخدم `transform:scale()` على كتلة الخريطة لتجاوز قياس الصفحة؛ قد يبقى صندوق layout كبيرًا رغم أن الرسم يبدو صغيرًا.
- لا تسمح بفصل caption عن الصورة إذا كان caption جزءًا من معناها؛ اجعل caption مع SVG ذرة واحدة بشرط أن يظل المجموع تحت 60 مم.
- لا تجعل نصوص SVG العربية ذات `letter-spacing` موجبًا؛ يفك اتصال الحروف. حافظ على `direction:rtl` للمحارف العربية وعزل الأرقام بـ`unicode-bidi:isolate`.

### 7.4 الظلال والخلفيات

- عطّل `box-shadow` و`backdrop-filter` و`gradient` في print؛ هي مكلفة بصريًا، وقد لا تطبع باتساق.
- `print_background=True` مفيد، لكنه ليس ضمانًا لإخراج كل background في كل مسار. اجعل المعنى في نص/حدود/تباين، واستخدم خلفيات صلبة فاتحة.
- تحقق من تباين النص والحدود بعد تحويل الألوان الداكنة إلى أبيض؛ لا تعتمد على لون وحده لتمييز حالة.

### 7.5 الحقول الصفرية والفراغات الكاذبة

- في Python/Jinja لا تستخدم `if value` لإظهار رقم؛ الصفر قيمة صحيحة. استخدم اختبار `is not None`، واطبع `0` أو `0.0` حسب دقة المؤشر.
- لا تستخدم `:empty`, `display:none`, أو `min-height` كبيرة لتعويض الحقول الصفرية. الحقل الغائب يوسم بـ`—` مع `aria-label`، والصفر يظل `0`.
- افصل الأرقام المركبة بـ`bdi`/`unicode-bidi:isolate`، ولا تسمح بانقسام `109.86 $` أو رمز الحدث بين السطور.
- اختبر خصوصًا KPI التي قيمتها صفر؛ فهي قصيرة وقد يكشف إخفاؤها فراغًا بصريًا أو يغيّر ارتفاع البطاقة.

## 8. أوامر تحقق مقترحة

```bash
# تصدير pass النهائي، ثم فحص الشكل
python3 /home/ubuntu/brain-marine-news/tools/export_report_assets.py \
  --date 2026-10-18 --only pdf
python3 /home/ubuntu/brain-marine-news/validators/check_pdf_format.py \
  --pdf /home/ubuntu/seawatch/dist/reports/pdf/2026-10-18.pdf \
  --date 2026-10-18 --allow-css-change

# معلومات الصفحات والنص الخام للتحقق من التذييل والفهرس
pdfinfo /home/ubuntu/seawatch/dist/reports/pdf/2026-10-18.pdf
pdftotext -layout /home/ubuntu/seawatch/dist/reports/pdf/2026-10-18.pdf /tmp/report.txt
```

أضف إلى CI فحصًا صغيرًا يقرأ `/tmp/report.txt` صفحةً صفحة: يتطلب `صفحة` ورقمًا في كل صفحة، ويقارن أرقام `data-page-for` مع العناوين، ويكشف ظهور «المصادر والمراجع» و«موثوقية المصادر» بعد إخفاء `sec-16`. ثم استخدم `pdftoppm`/Pillow لقياس التعبئة والفجوة من منطقة المحتوى المعايرة، لا من التذييل.

## 9. المراجع المهنية

- **ISO 216 — Writing paper and certain classes of printed matter: Trimmed sizes — A and B series**: مرجع مقاس A4.
- **W3C CSS Fragmentation Module Level 3**: تعريف `break-inside`, `break-before`, `break-after`, وقيود تجزئة الصناديق.
- **W3C CSS Paged Media Module Level 3**: `@page` وهوامش الوسائط الصفحية.
- **MDN Web Docs — `break-inside`, `orphans`, `widows`, و`table-header-group`**: سلوك المتصفحات وصيغ التوافق العملية.
- **Playwright API — `page.pdf()`**: `format`, `margin`, `displayHeaderFooter`, `headerTemplate`, `footerTemplate`, `pageNumber`, و`totalPages`.
- **Web Content Accessibility Guidelines (WCAG) 2.2 — SC 1.4.8 Visual Presentation**: طول السطر، تباعد الأسطر، وإعادة التدفق؛ يستخدم هنا كإرشاد قراءة لا كحد حجم خط PDF.
- **Robert Bringhurst, The Elements of Typographic Style**: طول السطر، التراتب، والـleading كقواعد مطبعية عامة.
- **Emil Ruder, Typography: A Manual of Design**: الشبكة، التباعد، وضبط العلاقة بين النص والمساحة.
- **Huda Smitshuijzen AbiFarès, Arabic Typography: A Comprehensive Sourcebook**: خصائص تصميم الحرف العربي واتصال الحروف وتجنب العبث بـletter-spacing.

[^1]: القياسات الرقمية الخاصة بالمشروع مأخوذة من `notes/print-fix-2026-10-18.md` و`templates/approved-pdf/print-profile.json`؛ وهي baseline تشغيلية وليست قاعدة مطبعية عامة.
[^2]: توثيق Playwright API المقصود هو صفحة `page.pdf()` في توثيق Playwright الرسمي؛ سلوك القوالب يعتمد إصدار Chromium/Playwright المثبت في بيئة التصدير.
