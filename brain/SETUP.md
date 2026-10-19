# دليل التهيئة والتشغيل — مركز الوعي بالمجال البحري

هذا الدليل يجعل النظام يعمل على **أي جهاز أو بيئة سحابية** (Linux · macOS · ويندوز عبر WSL · GitHub Codespaces) من نسخة المستودع نفسها.

---

## ١) ما الذي نُهيّئه

المشروع شجرتان متكاملتان:

| الشجرة | الدور | ما تحتاجه للتشغيل |
|---|---|---|
| `brain/` (هنا) | القواعد والبوابات والأدوات والبيانات والإصدارات | بايثون + LibreOffice + poppler + متصفح |
| `site/` (`seawatch`) | مولّد الموقع الدائم وخدمة الويب هوك | بايثون (+ قاعدة بيانات للخدمة فقط) |

الشجرتان مترابطتان: الموقع يُبنى من مخرجات النظام، والنظام يستدعي مولّد الموقع.

---

## ٢) المتطلبات

**إلزامية:**
- Python **3.10 أو أحدث**
- **LibreOffice** (`soffice`) — توليد نسخة Word وPDF العربي
- **poppler-utils** (`pdftoppm` · `pdftotext` · `pdfinfo`) — قياس الصفحات والتدقيق الطباعي
- **خطوط عربية** — بدونها يظهر PDF بمربعات (Amiri · Noto Kufi Arabic)

**إلزامية لتوليد PDF والتدقيق البصري:**
- متصفح **Chromium** الخاص بـ Playwright

**اختيارية:**
- Node.js / pnpm — لأدوات المنصة فقط، لا لتوليد الموقع
- مفاتيح نماذج لغوية (`ANTHROPIC_API_KEY` · `OPENAI_API_KEY`) — للتكيّف التحليلي والمراجعة الآلية

---

## ٣) التثبيت بأمر واحد

```bash
bash bootstrap.sh                 # تثبيت كامل (يحتاج sudo لحزم النظام)
bash bootstrap.sh --skip-system   # تثبيت حزم بايثون والمتصفح فقط
bash bootstrap.sh --verify-only   # فحص ما هو مثبّت بلا تثبيت
bash bootstrap.sh --link-default-paths   # إنشاء /home/ubuntu/{brain-marine-news,seawatch} كروابط
```

`--link-default-paths` مفيد للتوافق مع أي أداة أو توثيق ما زال يشير إلى المسارات التاريخية؛ النظام نفسه لم يعد يحتاجها.

---

## ٤) التثبيت اليدوي

**Ubuntu / Debian:**
```bash
sudo apt-get install -y libreoffice poppler-utils fonts-hosny-amiri fonts-noto-core python3-pip
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium --with-deps
```

**macOS:**
```bash
brew install --cask libreoffice && brew install poppler
python3 -m pip install -r requirements.txt && python3 -m playwright install chromium
```

**ويندوز:** استخدم **WSL** (Ubuntu) واتبع خطوات Ubuntu أعلاه. التشغيل الأصلي على ويندوز غير مُختبَر بسبب اعتماد توليد PDF على LibreOffice ومتصفح Playwright.

**GitHub Codespaces:** البيئة تُبنى تلقائيًا من `.devcontainer/devcontainer.json` عند إنشاء الـCodespace (تشغيل `bootstrap.sh` ضمن التهيئة)، ثم:
```bash
bash brain/bootstrap.sh --verify-only     # تأكيد أن كل شيء جاهز
bash brain/bootstrap.sh                   # إعادة التهيئة إن ظهر نقص
```
الدليل الكامل خطوة بخطوة: `docs/تشغيل-Codespaces.md`. والمسارات تُستنتج تلقائيًا من موقع الملفات، فلا حاجة لتعديل أي شيء.

---

## ٥) متغيّرات البيئة

كل قيمة لها افتراضي آمن؛ التغيير مطلوب فقط عند نقل المسارات أو تشغيل الخدمات:

| المتغيّر | الافتراضي | الوظيفة |
|---|---|---|
| `BRAIN_DIR` | جذر شجرة النظام (يُستنتج من موقع الملف) | مسار النظام |
| `SITE_DIR` | مجلد شقيق باسم `seawatch` أو `site` | مسار الموقع |
| `BACKUP_REPO_DIR` | `../mda-marine-system` | وجهة النسخة الاحتياطية على GitHub |
| `SKILLS_HOME` | المجلد الأعلى للنظام | تثبيت مهارة MACR |
| `TELEGRAM_BOT_TOKEN` | — | تسليم تلغرام اليومي |
| `TELEGRAM_OWNER_CHAT_ID` | — | صاحب القرار (موافقات المشتركين) |
| `TELEGRAM_WEBHOOK_SECRET` | `state/webhook-secret.txt` | التحقق من الويب هوك |
| `SITE_ORIGIN` · `PORT` | نطاق الموقع · 3000 | خدمة الويب هوك |
| `DATABASE_URL` | — | قاعدة بيانات مشتركي تلغرام (تُوفَّرها المنصة) |

القالب الكامل: `.env.example` في كل شجرة.

**ملف البيئة المحلي:** انسخ القالب إلى `.env` في الشجرة نفسها وضع القيم الحقيقية فيه (لا يُرفع إلى المستودع):
```bash
cp .env.example .env && chmod 600 .env
```
أدوات التسليم تقرأ `brain/.env` تلقائيًا عند غياب المتغيّر من بيئة التشغيل — وهذا ما يجعل تسليم تلغرام يعمل في بيئة سحابية مثل Codespaces.

---

## ٦) أول تشغيل — أوامر التحقق بالترتيب

```bash
# ١) فحص عدد المصادر من مصدر واحد
python3 validators/check_sources_count.py

# ٢) بناء الموقع (يقرأ ملفات الواجهة من النظام ويكتب في site/dist)
python3 ../site/generator/build_site.py        # أو: python3 $SITE/generator/build_site.py

# ٣) توليد PDF المعتمد لإصدار معيّن
python3 tools/export_report_assets.py --date 2026-10-19 --only pdf

# ٤) نسخة Word طبق الأصل
python3 tools/build_report_docx_exact.py --date 2026-10-19

# ٥) خط التسليم الكامل: يبني ← يصدّر ← يفحص كل البوابات (فشل مغلق)
bash tools/final_gate.sh 2026-10-19
```

`final_gate.sh` هو المرجع: أي مخالفة مانعة تُسقط التسليم برمز خروج `2`.

---

## ٧) التشغيل اليومي

- **داخل Manus:** مهمة مجدولة عند **06:40 بتوقيت البحرين** تشغّل الخط اليومي وتنشر وتسلّم على تلغرام.
- **خارج Manus:** أضف مهمة `cron` (أو GitHub Actions — انظر `docs/الاستقلال-عن-مانوس.md`):
```bash
40 3 * * *  cd /path/to/brain-marine-news && bash tools/final_gate.sh "$(date -u +%F)" >> logs/cron.log 2>&1
```
(03:40 UTC = 06:40 بتوقيت البحرين)

---

## ٨) ما يحدث عند غياب الأسرار

| الغائب | الأثر | السلوك |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | لا تسليم على تلغرام | الإصدار يُبنى ويُنشر على الموقع ويُسلَّم في المحادثة، ويُسجَّل السبب |
| `TELEGRAM_WEBHOOK_SECRET` | البوت لا يستقبل أوامر | الخدمة ترفض كل الطلبات (فشل مغلق) — لا تُشغَّل بلا سر |
| `DATABASE_URL` | لا حفظ لمشتركي البوت | تسليم تلغرام الأساسي يستمر (المعرّف يُقرأ من `appendices/telegram-chat.json`) |
| مفاتيح النماذج | لا مراجعة لغوية آلية | البوابات الحتمية تعمل كاملة |

---

## ٩) استكشاف الأخطاء الشائعة

| العَرَض | السبب | الحل |
|---|---|---|
| PDF عربي بمربعات | لا خط عربي | ثبّت `fonts-hosny-amiri` و`fonts-noto-core` ثم `fc-cache -f` |
| `soffice: not found` | LibreOffice غير مثبّت | `apt-get install libreoffice` |
| `playwright` يفشل في التوليد | متصفح غير مثبّت | `python3 -m playwright install chromium --with-deps` |
| أدوات تشير إلى مسار قديم | مسار مغلق في نص حرفي | مرّر `BRAIN_DIR`/`SITE_DIR` — راجع `tools/portable_paths.py` |
| بوابة الشكل تفشل بعد تعديل المولّد | تغيّر شكل PDF المعتمد | أعد التجميد بعد الاعتماد: `templates/approved-pdf/` |
| تحذير تغذيات 403/شهادة | حجب من المصدر | مسار الجلب البديل آلي، ويُسجَّل في `logs/` |

---

## ١٠) ما يُستثنى من النسخة الاحتياطية ولماذا

| المستثنى | السبب |
|---|---|
| `.env` · `state/webhook-secret.txt` | أسرار — وجودها في مستودع يعني كشفها |
| `.env.example` | **مُضمَّن** في المستودع (قالب بلا قيم سرية)، وتُستثنى منه استثناءً صريحًا قاعدة `.env.*` |
| معرّفات تلغرام (`chat_id` · `bot_id`) | تُحجب قيمتها داخل الملف مع بقاء البنية |
| `site/dist/` · `shots/` | مخرجات مولّدة تُعاد بأمر واحد |
| `__pycache__/` · `node_modules/` | مخلفات تشغيل |

سجل النقل الكامل مع بصمات التحقق: `docs/فهرس-الملفات.tsv` و`docs/نقل-إلى-جيت-هب.md`.
