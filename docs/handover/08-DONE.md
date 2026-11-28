# 08 — ما اكتمل وتم تسليمه

> تاريخ الكتابة: 2026-11-28 (البحرين)
> الفرع: handover/grok-2026-11-28
> الالتزام الأب: 66f16c9364e744db4697c622dec508ac16248e67
> المشغّل المنتهية مهمته: Claude


مرتّب من الأحدث. كل بند له دليل قابل للفتح وأمر تحقق واحد للقراءة. الأوامر من جذر المستودع بعد `git fetch origin main`.

| # | التاريخ | البند | الدليل | أمر إعادة التحقق |
|---|---|---|---|---|
| 1 | 2026-11-28 | دمج التشغيل اليومي على GitHub Actions بلا جلسة Claude: `daily.yml` بجدول 01:40 UTC وتشغيل يدوي، وكتابة خطوات الوكيل بنموذج عبر `tools/agent_write_llm.py`، والنشر بحكم 0 أو 3 فقط | الالتزام `66f16c9364e744db4697c622dec508ac16248e67` (#675) | `git show --stat 66f16c9 -- .github/workflows/daily.yml` |
| 2 | 2026-11-27 | نشر تقرير 26 نوفمبر على `mda-bh.pages.dev` بحكم 3 (منقوص مُفصح). كُتب المتن من إجابات احتياطية داخل المستودع `fallback-answers/2026-11-26/` (أربعة ملفات: B004 وW010 وW020 وW030) لا من النموذج المجاني، بحسب رسائل التزام الدمج 675 | نشر Cloudflare `8ff25a37-694a-4e92-8be0-db90240b0126` والتزام `seawatch-live` `cfade5c08590be37ec658ce458fbe745971fbb50`، وتشغيل Actions رقم 64 | `curl -s -o /dev/null -w '%{http_code}' https://mda-bh.pages.dev/reports/2026-11-26` والمتوقع 200 |
| 3 | 2026-11-27 | إصلاح رجوع `cloud_deliver` إلى التحقق الحي بالبصمة عند تعذر قراءة واجهة Cloudflare | `brain/tests/test_cloud_deliver_api_unreadable.py` و`brain/CHANGELOG.md` قسم «إصلاحات تشغيل 26 نوفمبر» | `python3 -m pytest brain/tests/test_cloud_deliver_api_unreadable.py -q` |
| 4 | 2026-11-27 | حذف الزناد المؤقت من `daily.yml` وإبقاء الجدول والتشغيل اليدوي | `brain/CHANGELOG.md` قسم «تنظيف daily.yml قبل الدمج» | `sed -n 1,30p .github/workflows/daily.yml` |
| 5 | 2026-11-26 | ربط FreeLLMAPI بالخطوتين الاختياريتين S080 وS090 (اختياري، فشله لا يوقف الخط) | `brain/tools/freellmapi_up.sh` و`brain/tools/llm.mjs` و`brain/tools/llm_compat.mjs` (#674) | `ls brain/tools/freellmapi_up.sh brain/tools/llm_compat.mjs` |
| 6 | 2026-11-22 | نشر تقرير 22 نوفمبر (منشور بالنشر `b8a655d2` والتزام الموقع `0ecfebb`) | `brain/reports/2026-11-22-sectioned.md` | `curl -s -o /dev/null -w '%{http_code}' https://mda-bh.pages.dev/reports/2026-11-22` والمتوقع 200 |
| 7 | 2026-11-21 | رقم الحادث `YY-NNNN` ورقم البلاغ `YY-NNNN/k` فوق رمز الواقعة (قرار المالك، الصيغة أ) | الالتزام `261fca0` (#670)، `brain/appendices/incident-id-map.json`، `brain/tests/test_incident_ids.py` | `python3 brain/tests/test_incident_ids.py` |
| 8 | 2026-11-21 | الإصلاح الذاتي للخط اليومي: جدول قواعد ثابت يعيد الخطوة المتأثرة وحدها ويعزل الإنجليزية عند عطل الترجمة | الالتزام `b654c19` ودمج #672 `27270dc`، `brain/tests/test_auto_heal.py` | `python3 -m pytest brain/tests/test_auto_heal.py -q` |
| 9 | 2026-11-21 | دمج مصادر الواقعة الواحدة وعدم احتساب التكرار (S074)، ومسار Lloyd's List الرسمي | الالتزام `44500a9` ودمج #673 `7f3813a`، `brain/tests/test_merge_event_sources.py` | `python3 brain/tests/test_merge_event_sources.py` |
| 10 | 2026-11-21 | تشغيل 2026-11-21: حكم 3، نشر 02:43 UTC، تلغرام مُرسل | الالتزام `9edc19e` | `git show --stat 9edc19e \| head -20` |
| 11 | 2026-11-20 | نقل ثلاث فجوات من الطلبات القديمة، وتسريع G001 (S015 فحص مسبق)، وتسريع G064 من 252 إلى 68 ثانية | الدمج `8c2d1a5` (#669) و`51d09ab` (#668) و`f9a3ea5` (#663) | `git show --stat 51d09ab \| head` |
| 12 | 2026-11-20 | إصلاح 18 بندًا من التدقيق البصري الحي | الدمج `8b49dd0` (#666)؛ لقطات في ملفات المشروع `visual-audit-2026-11-20/` (خارج المستودع) | `git show --stat 8b49dd0 \| head` |
| 13 | 2026-11-20 | إثبات منشورات X عبر oEmbed الرسمي بدل المتصفح الآلي المحجوب (ب-03) | الدمج `14d367a` (#660) | `grep -n "oembed" -ril brain/tools \| head -3` |
| 14 | 2026-11-20 | تدقيق المعجم العسكري: تطبيق التصحيحات الخمسة عشر؛ صيغة المصدر بدل الأمر | الالتزام `9868339`؛ تقرير التدقيق في ملفات المشروع `lexicon-audit-2026-11-19/` (خارج المستودع) | `git show --stat 9868339 \| head` |
| 15 | 2026-11-20 | حل G033 وG062 من جذرهما: مسارات رسمية بديلة لأربعة مصادر تحجب السحابة، ووثائق دليل D-0641 وD-0646 داخل المستودع | `brain/CHANGELOG.md` قسمان بتاريخ 20 نوفمبر | `grep -n "G033\|G062" brain/CHANGELOG.md \| head -6` |
| 16 | 2026-11-19 | فتح إرسال تلغرام اليومي (D030) بأمر المالك المكتوب، والإجراء بصيغة المصدر | الالتزام `818c630` | `git show --stat 818c630 \| head` |
| 17 | 2026-11-19 | الخط الأسرع: بوابة واحدة G069 من سجل المحرّك، وتسليم سحابي `cloud_deliver.py` | الالتزام `f7f18fa` (#656) | `python3 -m pytest brain/tests/test_single_gate_verdict.py -q` |
| 18 | 2026-11-19 | حارس الأرقام المنشورة (G054) وتفعيله | الالتزام `8b1c337` | `git show --stat 8b1c337 \| head` |
| 19 | 2026-11-18 | اعتماد `https://mda-bh.pages.dev` رابطًا وحيدًا، وتحويل `seawatch-live.pages.dev` إلى 301 | الدمج `91f9a5c` (#645) | `curl -s -o /dev/null -w '%{http_code} %{redirect_url}' https://seawatch-live.pages.dev/` والمتوقع `301 https://mda-bh.pages.dev/` |
| 20 | 2026-11-18 | أول تشغيل رسمي كامل من السحابة ونشر تقرير 18 نوفمبر | الدمج `204652d` (#644) و`brain/reports/2026-11-18-sectioned.md` | `ls brain/reports/2026-11-18-sectioned.md` |
| 21 | 2026-11-12 | إصلاحات G030 وG034 وG036 وG048 | الدمج `abd8f3a` (#637) و`684b81a` (#636) و`4a53bfc` (#635) و`aa771dc` (#634) | `git log --oneline abd8f3a -4` |
| 22 | 2026-11 (حتى 12) | دفتر قرارات المالك: 61 قرارًا، منها 47 «منفَّذ» بدليل | `brain/decisions/registry.json` | `(cd brain \&\& python3 validators/check_decisions_registry.py)` |
| 23 | 2026-11-28 | تحقق هذه الجلسة: اتساق المانيفست وتصنيف كل المسارات | انظر مخرج الأمرين في `15-FIRST-72-HOURS.md` | `python3 brain/tools/runbook.py verify --root brain && python3 brain/tools/code_paths.py check --root .` |

ملاحظة: بنود الأيام 18–21 نوفمبر مصدرها `brain/CHANGELOG.md` وتاريخ الدمج في `git log`. أُعيد تشغيل اختبارات بنود 3 و7 و8 و17 في هذه الجلسة ونجحت (بند 3: 2 passed، بند 7: «فشل 0»، بند 8: 12 passed، بند 17: 4 passed) وفحص بند 22 أعاد 61 قرارًا (47 منفَّذ). بند 9: سكربت مباشر؛ ظهرت أسطر ✔ ولم أقرأ ملخصه كاملًا فلا أدّعي نجاحه.

تنبيه: أوامر `check_decisions_registry.py` تُشغَّل من داخل `brain` لا من الجذر (من الجذر تبحث عن `decisions/registry.json` في الجذر وتفشل). واختبارا 7 و9 سكربتان مباشران لا يعملان تحت `pytest`.
