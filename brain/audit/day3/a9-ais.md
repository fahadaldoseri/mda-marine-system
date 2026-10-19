# تدقيق AIS مستقل ومزدوج: GFS PRIDE وGFS GISELLE

**تاريخ التدقيق:** 17 أكتوبر 2026.  
**هوية السفن:** GFS PRIDE — IMO 9349045، MMSI 563115400؛ GFS GISELLE — IMO 9704661، MMSI 566456000.

## النتيجة التنفيذية

- قيمة **GFS PRIDE** المعتمدة `032231Z OCT 26` مدعومة مباشرة فقط إذا قُرئت ساعة Shipnext غير الموسومة (`10/03/2026, 10:31 PM`) على أنها UTC؛ Shipnext لا يعلن منطقة الوقت، لذلك لا يجوز وصف المطابقة بأنها يقينية. MarineTraffic يعطي لقطة قريبة: `2026-10-04 03:10 (UTC+4)` = `032310Z OCT 26`، وMarineRadar يعطي أحدث وقت UTC صريح في الصفحات المفتوحة: `032314Z OCT 26`. التصحيح العملي هو اعتماد **نطاق `032231–032314Z`**، مع اعتبار `032314Z` أحدث لقطة UTC منشورة لا لحظة انقطاع فعلية.
- قيمة **GFS GISELLE** المعتمدة `120431Z OCT 26` مطابقة حرفيًا لصفحة Tradlinx (`12-Oct-2026 04:31 (UTC+00:00)`)؛ وهي القيمة المؤكدة المستقلة. MarineTraffic يعرض لقطة محلية لاحقة بـ16 دقيقة (`120447Z`) بعد تحويل `UTC+4`، وShipnext يعرض `10/12/2026, 03:39 AM` بلا منطقة وقت. التصحيح العملي هو اعتماد **نطاق `120431–120447Z`** بدل الادعاء بدقيقة وحيدة مشتركة.
- الإجماع الزمني القابل للدفاع هو **اليوم والمنطقة** لا الدقيقة: PRIDE حول 3 أكتوبر قرب فجيرة، وGISELLE حول 12 أكتوبر قرب الخليج/مرسى فجيرة. أما DTG الدقيقة فتصنيفها شبكة واحدة لكل قيمة، لا إجماع ثلاث شبكات.
- آخر موضع مستقبَل قابل للتثبيت زمنيًا لـPRIDE: `25.2481°N, 56.4739°E`، قرب مرسى الفجيرة/الخليج الفارسي؛ Shipnext وMarineRadar يتفقان على الإحداثيات تقريبًا (**شبكتان**).
- أقرب موضع زمني/جغرافي لـGISELLE في لقطة 12 أكتوبر: `25°10'52"N 056°31'13"E` = `25.1811°N, 56.5203°E`، قرب مرسى الفجيرة/خليج عُمان، من Shipnext؛ MarineTraffic يؤكد «Oman Gulf» لكنه يحجب الإحداثيات. MarineRadar يعرض سجلًا آخر بلا زمن في `19.3603°N, 72.4246°E`، لذلك لا أدمج السجلين.
- لم يُعثر على **إشارة AIS أحدث من 12 أكتوبر** لـGFS GISELLE في الشبكات المفتوحة المفحوصة. خبر إصابتها في 14 أكتوبر ليس إشارة تتبع.
- لا تعرض صفحات الشبكات المفحوصة حالة PRIDE «غارقة»؛ MarineTraffic وMarineRadar تعرضان لقطة قديمة «At Anchor/No recent signal»، وMyShipTracking تعرض «Active/out of coverage». لكن تحذير NAVAREA IX الرسمي `373/26` المؤرخ `141045 UTC OCT 2026` يقول: `COMMERCIAL VESSEL 'GFS PRIDE' REPORTED SUNK WITH FLOATING CONTAINERS...`. وقت الغرق الفعلي غير منشور بدقة؛ المعروف أنها أُصيبت في 13 أكتوبر ثم غرقت لاحقًا، وبحلول تحذير 14 أكتوبر 10:45Z كانت مُبلّغة غارقة.

## 1) النقل الحرفي من كل شبكة

### GFS PRIDE

| الشبكة | العبارة الحرفية ذات الصلة | المنطقة الزمنية المعلنة | التوحيد إلى UTC/DTG | التصنيف والملاحظة |
|---|---|---|---|---|
| [VesselFinder](https://www.vesselfinder.com/vessels/details/9349045) | “The current position of **GFS PRIDE** is at Arabian Sea reported 14 days ago by AIS. The vessel arrived at the port of **Al Fujayrah Anch., United Arab Emirates (UAE)** on Oct 3, 16:16 UTC.” وفي البطاقة: “Position Received 14 days ago”. | `UTC` معلنة للنص الخاص بالوصول. | `031616Z OCT 26`، لكنه **زمن وصول ATA** وليس بالضرورة زمن آخر رسالة موقع. | **شبكة واحدة** لقيمة `031616Z`. لا أستخدمها لتصحيح `032231Z` دون سجل موضع مستقل. |
| [MarineTraffic](https://www.marinetraffic.com/en/ais/details/ships/shipid:685887/mmsi:563115400/imo:9349045/vessel:GFS%20PRIDE) | “**Summary:** Container Ship **GFS PRIDE** is currently located in the **Oman Gulf** (reported **13 days, 6 hours ago**)”. وفي AIS: “**Position received** 13 d 6 h 58 mins ago”; “**Vessel is Out-of-Range**”; “**Vessel's local time** 2026-10-04 03:10 (UTC+4)”; “Navigational status **At Anchor**”. | `UTC+4` لوقت السفينة؛ أزمنة الرحلة الأخرى موسومة `UTC+5` و`UTC+4`. | `2026-10-04 03:10 (UTC+4)` = `032310Z OCT 26`. | **شبكة واحدة**؛ أقرب من حيث اليوم والموقع إلى القيمة المعتمدة، لكن بفارق 39 دقيقة عنها. الفارق المتبقي بعد طرح المنطقة الزمنية هو فرق لقطة/استيعاب، لا فرق منطقة وقت. |
| [Shipnext](https://shipnext.com/vessel/9349045-gfs-pride) | “**Last Position update: 10/03/2026, 10:31 PM**”; “Ship's current position is **025° 14' 53\" N / 056° 28' 26\" E.**”؛ “According to the latest AIS and Satellite data, the ship is currently on route to **Fujairah, United Arab Emirates**.” | **لم تُعلن** الصفحة منطقة الوقت. | لا يمكن تحويله يقينًا. إذا كانت الساعة UTC فهو `032231Z OCT 26`، لكن ذلك **افتراض غير مثبت**. | **شبكة واحدة** للمطابقة المحتملة، و**شبكتان** للإحداثيات مع MarineRadar. لا تُرفع إلى إجماع DTG بسبب غياب المنطقة الزمنية. |
| [MyShipTracking](https://www.myshiptracking.com/vessels/gfs-pride-mmsi-563115400-imo-9349045) | “**GFS PRIDE** is out of coverage.”؛ “**Position Received** 2026-07-16 18:29”؛ “Area **Red Sea**”; “The current position ... is in **Red Sea** with coordinates **18.44199° / 39.45793°** as reported on **2026-07-16 18:29**”. | الصفحة تعرض خيارات `MT / UTC` في التذييل، لكن حقل السجل نفسه بلا وسم منطقة. | `20260716 1829` مع منطقة **غير مثبتة في الحقل**؛ وحتى على فرض UTC فهي أقدم بنحو 79 يومًا من لقطة أكتوبر. | **شبكة واحدة، سجل شاذ/قديم**؛ لا يصلح لتأكيد قيمة أكتوبر أو الموضع قرب فجيرة. حالة الصفحة “Active” لا تعني أن السفينة كانت نشطة في 17 أكتوبر. |
| [MarineRadar](https://www.marineradar.com/vessel/mmsi-563115400/gfs-pride) | “**Current Position No recent signal**”; “GFS PRIDE has not broadcast an AIS position for 4 days. Its most recent report placed it in the Persian Gulf, at **25.2481° N, 56.4739° E**, on **3 Oct 2026, 23:14 UTC**.” وفي الحقائق: “**AIS last updated 2026-10-03T23:14:00Z**”. | `UTC` معلنة صراحة. | `032314Z OCT 26`. | **شبكة واحدة** للقيمة الدقيقة؛ **شبكتان** للإحداثيات مع Shipnext؛ فرق `+43 دقيقة` عن `032231Z`. الصفحة نفسها تنص أن انقطاع terrestrial AIS لا يثبت أن السفينة غير نشطة. |
| [Tradlinx](https://www.tradlinx.com/vessel-tracking/3309-GFS-PRIDE-MMSI-563115400-IMO-9349045) | “**Last Update** 30-Sep-2026 00:30 (UTC+00:00)”; “AIS Type **Terrestrial**”; “Coordinates **Enable Satellite Coverage**”. | `UTC+00:00` معلنة. | `300030Z SEP 26`. | **شبكة واحدة، لقطة متأخرة** بنحو 3 أيام عن القيمة المعتمدة؛ الإحداثيات محجوبة. |
| [FleetMon](https://www.fleetmon.com/vessels/gfs-pride_9349045_10014388/) | **لم يُعثر** على صفحة قابلة للفتح. فشل الوصول بسبب `ERR_NAME_NOT_RESOLVED` من بيئة التدقيق. | لم يُعثر. | لم يُعثر. | **لا تصنيف شبكي**؛ لا يجوز تعويض غيابها بمقتطفات مواقع أخرى. |
| [Equasis](https://www.equasis.org/EquasisWeb/public/HomePage) | الصفحة العامة تقول: “**You need to register as a user**” لاستخدام بحث السفن والشركات؛ لم تُفتح صفحة عامة خاصة بالسفينة. | لم يُعثر على سجل AIS عام أو منطقة وقت. | لم يُعثر. | **لا تصنيف شبكي**؛ Equasis مصدر سلامة/تسجيل وليس بديلًا عن سجل AIS مفتوح في هذه الجلسة. |

**خلاصة PRIDE الزمنية:** توجد أربع صفحات مفتوحة حول 3 أكتوبر/فجيرة (VesselFinder، MarineTraffic، Shipnext، MarineRadar)، لكن دقة الدقيقة ليست موحدة. القيمة `032231Z` هي **إجماع شبكة واحدة فقط** إذا اعتُبرت ساعة Shipnext UTC؛ MarineTraffic وMarineRadar يضعان آخر لقطة عند `032310Z` و`032314Z` على التوالي. Tradlinx متأخر، وMyShipTracking شاذ وقديم.

### GFS GISELLE

| الشبكة | العبارة الحرفية ذات الصلة | المنطقة الزمنية المعلنة | التوحيد إلى UTC/DTG | التصنيف والملاحظة |
|---|---|---|---|---|
| [VesselFinder](https://www.vesselfinder.com/vessels/details/9704661) | “The current position of **GFS GISELLE** is at Arabian Sea reported **8 days ago by AIS**. The vessel is en route to the port of **Fujairah, United Arab Emirates (UAE)**”; وفي البطاقة: “Position Received 8 days ago”. | لا تُعلن الصفحة ساعة/منطقة للعبارة النسبية؛ تعرض فقط `ATD: Oct 5, 15:51 UTC` للرحلة السابقة و`ETA: Oct 8, 15:00` بلا منطقة. | لا يمكن تحويل “8 days ago” إلى DTG يقيني من الصفحة. | **شبكة واحدة** لإسناد المنطقة/الرحلة، لا لقيمة دقيقة. |
| [MarineTraffic](https://www.marinetraffic.com/en/ais/details/ships/shipid:3560154/mmsi:566456000/imo:9704661/vessel:GFS%20GISELLE) | “**Summary:** Container Ship **GFS GISELLE** is currently located in the **Oman Gulf** (reported **4 days, 2 hours ago**)”. وفي AIS: “**Position received** 4 d 2 h 34 mins ago”; “**Vessel is Out-of-Range**”; “**Vessel's local time** 2026-10-12 08:47 (UTC+4)”; “Navigational status **At Anchor**”. | `UTC+4` معلنة لوقت السفينة. | `2026-10-12 08:47 (UTC+4)` = `120447Z OCT 26`. | **شبكة واحدة**؛ اللقطة أحدث بـ16 دقيقة من `120431Z` بعد تحويل المنطقة. الفرق المتبقي تأخر/اختلاف لقطة، وليس منطقة وقت. |
| [Shipnext](https://shipnext.com/vessel/9704661-gfs-giselle) | “**Last Position update: 10/12/2026, 03:39 AM**”; “Ship's current position is **025° 10' 52\" N / 056° 31' 13\" E.**”؛ “According to the latest AIS and Satellite data, the ship is currently on route to **Fujairah, United Arab Emirates**.” | **لم تُعلن** الصفحة منطقة الوقت. | لا يمكن تحويله يقينًا. إذا كان UTC فهو `120339Z OCT 26`؛ وإذا كان `UTC+1` فهو `120439Z`، لكن لا أساس لاختيار أي منهما. | **شبكة واحدة**؛ يثبت يوم 12 أكتوبر فقط. مع MarineTraffic وTradlinx يوجد إجماع **ثلاث شبكات على اليوم/اللقطة حول 12 أكتوبر**، لا على الدقيقة. |
| [MyShipTracking](https://www.myshiptracking.com/vessels/gfs-giselle-mmsi-566456000-imo-9704661) | “**GFS GISELLE** is out of coverage.”؛ “**Position Received** 2026-02-25 09:48”؛ “Area **Persian Gulf**”; “The current position ... is in **Persian Gulf** with coordinates **26.05786° / 55.80998°** as reported on **2026-02-25 09:48**”. | الصفحة تعرض خيار `UTC` ضمن إعدادات العرض، لكن السجل نفسه بلا وسم منطقة ملاصق للوقت. | `20260225 0948` مع منطقة **غير مثبتة في الحقل**؛ سجل أقدم بكثير من 12 أكتوبر. | **شبكة واحدة، سجل شاذ/قديم**؛ لا يصح استعماله لنفي لقطة 12 أكتوبر. |
| [MarineRadar](https://www.marineradar.com/vessel/mmsi-566456000/gfs-giselle) | “**Current Position Last report**”; “GFS GISELLE was last reported in the **Arabian Sea**, at **19.3603° N, 72.4246° E**.”؛ “This fix came from a shore antenna, and those stop at the coast.” | **لم تُعلن** الصفحة زمنًا أو منطقة وقت لهذا السجل. | لا يمكن إنشاء DTG؛ لا تاريخ/ساعة في الصفحة المفتوحة. | **شبكة واحدة** لموضع بلا زمن؛ لا يمكن إثبات أنه أحدث من `120431Z`. يتعارض جغرافيًا مع لقطة Shipnext/MarineTraffic القريبة من فجيرة، ولذلك يُعرض كتناقض لا يُدمج. |
| [Tradlinx](https://www.tradlinx.com/vessel-tracking/5017-GFS-GISELLE-MMSI-566456000-IMO-9704661) | “**Last Update** 12-Oct-2026 04:31 (UTC+00:00)”; “AIS Type **Terrestrial**”; “Destination **AEFJR**”; “Course / Speed **162.5° / 0.1 kn**”. | `UTC+00:00` معلنة صراحة. | `120431Z OCT 26`. | **شبكة واحدة** للمطابقة الحرفية، لكنها جزء من **إجماع ثلاث شبكات على يوم 12 أكتوبر** مع MarineTraffic وShipnext. |
| [FleetMon](https://www.fleetmon.com/vessels/gfs-giselle_9704661_10014388/) | **لم يُعثر** على صفحة قابلة للفتح. فشل الوصول بسبب `ERR_NAME_NOT_RESOLVED` من بيئة التدقيق. | لم يُعثر. | لم يُعثر. | **لا تصنيف شبكي**؛ لا تُستبدل بصفحة بحث أو مقتطف مواصفات. |
| [Equasis](https://www.equasis.org/EquasisWeb/public/HomePage) | الصفحة العامة تقول: “**You need to register as a user**” لاستخدام بحث السفن والشركات؛ لم تُفتح صفحة عامة خاصة بالسفينة. | لم يُعثر على سجل AIS عام أو منطقة وقت. | لم يُعثر. | **لا تصنيف شبكي**. |

**خلاصة GISELLE الزمنية:** ثلاثة مصادر مفتوحة (MarineTraffic، Shipnext، Tradlinx) تضع آخر لقطة في 12 أكتوبر، لكن الدقيقة المؤكدة `120431Z` تظهر حرفيًا في Tradlinx فقط. MarineTraffic يعطي `120447Z` بعد تحويل `UTC+4`، وShipnext يعطي `03:39 AM` بلا منطقة وقت. MarineRadar وMyShipTracking يقدمان سجلات جغرافية بلا توافق زمني أو بسجل قديم، فلا يصلحان لتصحيح القيمة المعتمدة.

## 2) آخر موضع جغرافي معروف

### GFS PRIDE

**الموضع الزمني الأقوى:** `25.2481°N, 56.4739°E`، وهو نفس موضع Shipnext تقريبًا (`025°14'53"N, 056°28'26"E` = `25.2480556°N, 56.4738889°E`) وMarineRadar. الاسم الجغرافي في الصفحات هو **مرسى الفجيرة/Al Fujayrah Anch.**؛ MarineRadar يسمي النطاق **Persian Gulf**، وMarineTraffic يسميه **Oman Gulf**. اختلاف “الخليج الفارسي/خليج عُمان” تسمية نطاقية عند المدخل البحري قرب فجيرة، وليس دليلًا على موضعين مختلفين في هذه اللقطة. **درجة الإحداثيات: شبكتان.**

لا يعني هذا أن السفينة بقيت هناك حتى 14 أكتوبر. إنه آخر موضع **مُستقبَل** في سجل AIS المفتوح، لا آخر موضع فيزيائي قبل الإصابة أو الغرق.

### GFS GISELLE

**الموضع المرتبط بلقطة 12 أكتوبر:** Shipnext يعرض `025°10'52"N, 056°31'13"E` = `25.1811111°N, 56.5202778°E`، في نطاق **مرسى الفجيرة/خليج عُمان**. MarineTraffic يؤكد “Oman Gulf” و“At Anchor” لكنه يحجب الإحداثيات. **درجة الموضع الزمني: شبكة واحدة بالإحداثيات، وشبكتان بالمنطقة/الحالة.**

يوجد سجل متعارض في MarineRadar: `19.3603°N, 72.4246°E`، **Arabian Sea**، من دون تاريخ أو ساعة. ويوجد سجل MyShipTracking أقدم: `26.05786°N, 55.80998°E`، **Persian Gulf**، بتاريخ `2026-02-25 09:48`. لا يمكن ترتيب هذين السجلين زمنيًا أمام `120431Z OCT 26`، لذلك لم أسمهما “آخر موضع مؤكد”.

## 3) هل توجد إشارة أحدث لـGFS GISELLE بعد 12 أكتوبر؟

**النتيجة: لم يُعثر على إشارة AIS أحدث من 12 أكتوبر في السجلات المفتوحة المفحوصة.** Tradlinx يثبت آخر تحديث عند `120431Z`. MarineTraffic يثبت آخر وقت محلي عند `2026-10-12 08:47 (UTC+4)` = `120447Z` ثم يصف السفينة بأنها “Out-of-Range”. Shipnext يعرض آخر تحديث في 12 أكتوبر، بلا منطقة وقت. لا توجد في هذه الصفحات رسالة موضع مؤرخة 13 أو 14 أو 15 أو 16 أو 17 أكتوبر.

توجد **إفادة حادث** لا **إشارة تتبع**: Reuters نقل عن هيئة الموانئ البحرية السنغافورية أن GFS GISELLE أُصيبت في 14 أكتوبر ووصلت إلى مرسى آمن بقدرتها الذاتية، مع سلامة الطاقم؛ هذا لا يثبت أن شبكة AIS سجلت موضعًا بعد 12 أكتوبر. [Reuters](https://www.reuters.com/world/asia-pacific/two-singapore-registered-vessels-struck-strait-hormuz-one-sinks-2026-10-14/) و[BBC](https://www.bbc.com/news/articles/crkg7q97z078o).

## 4) هل تسجّل الشبكات GFS PRIDE كغارقة أو خارج الخدمة؟

**الشبكات المفتوحة لا تسجّل الغرق كتحديث AIS.** MarineTraffic يعرض `At Anchor` و`Vessel is Out-of-Range`، وMarineRadar يعرض `No recent signal` و`At anchor`، وMyShipTracking يعرض `Status Active` و`out of coverage`. VesselFinder وShipnext لا يعرضان وسم “sunk” في الصفحتين المفتوحتين، وTradlinx يعرض فقط آخر تحديث قديم. هذه حالات لقطة/تغطية وليست شهادة أن السفينة كانت سليمة بعد 14 أكتوبر.

**السجل الرسمي اللاحق:** نص تحذير [NAVAREA IX 373/26](https://hydrography.paknavy.gov.pk/wp-content/plugins/navarea-warnings/custom_uploaded_warnings_for_navarea/20261014SEC%20373.txt) يقول حرفيًا:

> `141045 UTC OCT 2026`  
> `COMMERCIAL VESSEL 'GFS PRIDE' REPORTED SUNK WITH FLOATING CONTAINERS IN 26-16.8N 056-08.6E APPROXIMATELY 4NM NORTHWEST RAS SHAYKH MASUD (.) MARINERS CAUTIONED`

وتحوّل الإحداثيات إلى نحو `26.2800°N, 56.1433°E`، شمال غرب رأس الشيخ مسعود في مسندم، عُمان. كما نقل Reuters عن MPA أن PRIDE أُصيبت في **13 أكتوبر**، تضررت واشتعلت ثم غرقت، وأن أفراد الطاقم الـ21 أُجلوا سالمين؛ وذكر المصدر أن GISELLE أُصيبت في **14 أكتوبر** ووصلت إلى مرسى آمن. [Reuters](https://www.reuters.com/world/asia-pacific/two-singapore-registered-vessels-struck-strait-hormuz-one-sinks-2026-10-14/) و[Seatrade Maritime](https://www.seatrade-maritime.com/security/iran-claims-mine-sank-container-ship-amid-fresh-hormuz-attacks).

**الزمن الذي يمكن الجزم به:** كان الغرق مُبلّغًا به في `141045Z OCT 26`. **الزمن الفعلي للغرق:** لم يُعثر على ساعة دقيقة مستقلة؛ لا يجوز تحويل وقت إصدار التحذير إلى وقت الغرق نفسه. **زمن الإصابة:** MPA/Reuters يحدد تاريخ إصابة PRIDE في 13 أكتوبر، لا ساعة دقيقة في النص المنشور. وUKMTO، كما نقل BBC، أبلغ عن سفينتين غير مسمّاتين ضُربتا بين `16:40–17:00 GMT` يوم الثلاثاء؛ لا يجوز إسناد هذه النافذة إلى PRIDE وحدها دون بيان يحدد الهوية.

## 5) فصل أزمنة AIS عن الانقطاع والإصابة

1. **آخر موضع مُستقبَل (Last received position):** آخر رسالة AIS وصلت إلى مزود/مستقبل الشبكة، مع زمنها كما تسجله الشبكة. مثال PRIDE: MarineRadar `032314Z`، وGISELLE: Tradlinx `120431Z`.
2. **لحظة انقطاع الإرسال الفعلية:** غير معروفة من هذه الصفحات. عبارة `Out-of-Range` أو `No recent signal` تعني أن الشبكة لم تستقبل تحديثًا، وقد يكون السبب خروجًا من تغطية مستقبل ساحلي، تأخر مزود، إطفاء/تعطل جهاز، أو تغير مسار استقبال. لا تساوي وقتًا دقيقًا لإطفاء AIS.
3. **زمن الإصابة:** واقعة مستقلة عن آخر لقطة AIS. PRIDE أُصيبت في 13 أكتوبر وفق MPA/Reuters، ثم غرقت لاحقًا؛ GISELLE أُصيبت في 14 أكتوبر وفق المصدر نفسه. لا تثبت لقطة 3 أو 12 أكتوبر أن السفينة كانت في ذلك الموضع لحظة الإصابة، ولا تثبت فجوة AIS أن الإصابة وقعت عند أول دقيقة صمت.

## ملخص نهائي ≤12 سطرًا

1. **PRIDE:** القيمة `032231Z OCT 26` محتملة من Shipnext فقط؛ المنطقة الزمنية غير معلنة، لذا لا يوجد إجماع DTG دقيق.
2. MarineTraffic يثبت `032310Z` بعد تحويل `03:10 UTC+4`، وMarineRadar يثبت `032314Z`؛ فرق لقطة، لا فرق منطقة وقت.
3. **GISELLE:** `120431Z OCT 26` مؤكدة حرفيًا في Tradlinx؛ MarineTraffic يعطي `120447Z`، وShipnext يعطي 12 أكتوبر بلا منطقة وقت.
4. يوجد إجماع **ثلاث شبكات على يوم 12 أكتوبر** لـGISELLE، لا على الدقيقة.
5. آخر موضع PRIDE الزمني: `25.2481N, 56.4739E` قرب مرسى الفجيرة؛ الإحداثيات مدعومة من Shipnext وMarineRadar (**شبكتان**).
6. موضع GISELLE المرتبط بلقطة 12 أكتوبر: `25.1811N, 56.5203E` من Shipnext؛ MarineRadar يعرض سجلًا عربيًّا بلا زمن فلا يُدمج.
7. **لم يُعثر** على AIS أحدث لـGISELLE بعد 12 أكتوبر؛ خبر 14 أكتوبر ليس إشارة تتبع.
8. الشبكات لا تسجل PRIDE كغارقة؛ تعرض لقطة قديمة «At Anchor/Out-of-Range/Active».
9. NAVAREA IX 373/26 أبلغ عن غرق PRIDE عند `141045Z OCT 26` مع حاويات طافية؛ وقت الغرق الفعلي غير معلوم.
10. MPA/Reuters: إصابة PRIDE في 13 أكتوبر وغرقها لاحقًا؛ إصابة GISELLE في 14 أكتوبر ووصولها إلى مرسى آمن.
11. أهم ثلاثة مصادر: [Tradlinx GFS GISELLE](https://www.tradlinx.com/vessel-tracking/5017-GFS-GISELLE-MMSI-566456000-IMO-9704661)، [MarineRadar GFS PRIDE](https://www.marineradar.com/vessel/mmsi-563115400/gfs-pride)، [NAVAREA IX 373/26](https://hydrography.paknavy.gov.pk/wp-content/plugins/navarea-warnings/custom_uploaded_warnings_for_navarea/20261014SEC%20373.txt).
