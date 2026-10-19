# مركز الوعي بالمجال البحري — النظام الاحتياطي الكامل

نسخة احتياطية كاملة وموثّقة لنظام **التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة** وللموقع الدائم الذي ينشره. الغرض: مرجع واحد يعيد بناء النظام كاملًا لو فُقدت بيئة التشغيل.

## ما يحتويه المستودع

```
mda-marine-system/
├── .devcontainer/  تهيئة البيئة السحابية (GitHub Codespaces) — تُبنى تلقائيًا من المستودع
├── brain/          نظام «Brain»: القواعد والبوابات والأدوات والبيانات والتقارير
└── site/           مشروع الموقع: المولّد والخدمة والأصول والخطة
```

### `brain/` — النظام

| المجلد | المحتوى |
|---|---|
| `INDEX.md` | الفهرس الملزم — يُقرأ أولًا في كل تشغيل يومي |
| `sections/` | قواعد التشغيل: `10-sources` · `20-...` · `30-structure` · `40-blocks` · `55-intelligence` · `60-validation` · `70-delivery` · `75-style` · `90-automation` |
| `validators/` | البوابات المانعة (الأسلوب · اللغة · الرموز · الشكل · النقاط · المصادر · العقوبات) |
| `tools/` | أدوات التشغيل اليومي (`daily_pipeline.sh` · `final_gate.sh` · `merge_ledger_daily.py` · `telegram_send.py` · مولّدات PDF/Word) و`tools/_oneoff/` أدوات تاريخية لمرة واحدة |
| `reports/` | كل الإصدارات (Markdown + DOCX + PDF) والتقارير الخاصة |
| `cumulative-2026/` | دفتر الأحداث التراكمي (`event-ledger-master.json` + سجلات يومية) والتقرير التراكمي |
| `appendices/` | الملاحق: المصادر · القائمة السوداء · سياسة تلغرام · خرائط الرموز · ملاحظات أمنية |
| `archive/originals/` | أصول البلاغات الرسمية كما نُشرت (UKMTO · NAVAREA · JMIC …) |
| `feeds/` | خلاصات المصادر المفحوصة يوميًا |
| `memory/` | سجل التعلم (`learning-log.jsonl`) والتكيّف التحليلي (`intel-adaptation.md`) |
| `web/meta/` | ملفات الواجهة اليومية (مخطط الإصدار 2.1) |
| `audit/` | سجل الأعطال والثغرات وتقارير التدقيق |
| `docs/` | دليل الأوامر والتعليمات الكاملة · `سجل-المراحل-والمكتبات-والمنهجية.md` (المراحل · طرائق التفكير · المكتبات · المعاجم) · `تشغيل-Codespaces.md` · `الاستقلال-عن-مانوس.md` |
| `skills/` | مهارات النظام: `marine-news-brain` · `military-arabic-editing` · `macr-system` |

### `site/` — الموقع

| المجلد | المحتوى |
|---|---|
| `generator/` | `build_site.py` (الموقع والأرشيف) · `build_report.py` (صفحة الإصدار) · `blocks.py` (الكتل) · `map_gulf.py` (الخريطة) · `monthly_dashboard.py` · `sync_from_brain.py` |
| `sources/` | مصادر الصفحات (تقارير · خاصة · تراكمي) |
| `server/` | خدمة الويب هوك لبوت تلغرام + قاعدة المشتركين |
| `public/` | الأصول العامة وملف المسارات |
| `plan.md` · `app.config.ts` · `Dockerfile` | خطة المشروع وإعداداته وبناء الحاويات |

## كيف يعمل النظام يوميًا

1. **07:00 بتوقيت البحرين (04:00 UTC):** يُشغَّل الخط اليومي `bash brain/tools/daily_pipeline.sh <التاريخ>`.
2. فحص التغذيات (40 مصدرًا) وحفظ أصول البلاغات الرسمية في `archive/originals/<التاريخ>/`.
3. فحص قوائم العقوبات على سفن الإصدار.
4. كتابة التقرير في `reports/<التاريخ>-sectioned.md` وملف الواجهة `web/meta/<التاريخ>.json`.
5. دمج الذاكرة التراكمية `tools/merge_ledger_daily.py` (دفتر الأحداث + خريطة الرموز).
6. بوابات التحقق: الأسلوب · اللغة · مدقق التقرير · التحليل الاستخباري · سياسة الرموز · فصل فضاءات الرموز · قاعدة النقاط.
7. بناء الموقع وتصدير PDF المعتمد ثم نسخة Word طبق الأصل.
8. بوابة التسليم النهائية `tools/final_gate.sh` (فشل مغلق) وبوابات المخرج الاثنتا عشرة `tools/qa_gates.py`.
9. النشر على الموقع الدائم، ثم رسالة تلغرام المختصرة (نص + PDF + رابط).

## البوابات المانعة (لا يُسلَّم إصدار يفشل فيها)

| البوابة | الملف | الرمز عند المخالفة |
|---|---|---|
| الأسلوب (القائمة السوداء · طول الجملة) | `validators/check_style.py` | 2 |
| اللغة والمصطلحات | `validators/check_language.py` | 2 |
| مدقق التقرير والواجهة | `validators/validate_report.py` | 2 |
| التحليل الاستخباري (ح1–ح12) | `validators/check_intel.py` | 2 |
| سياسة الرموز في المخرجات | `validators/check_code_policy.py` | 2 |
| فصل فضاءات الرموز MN-/EST- | `validators/check_code_spaces.py` | 2 |
| قاعدة النقاط في المصدر | `validators/check_points_rule.py` | 2 |
| الشكل المطبوع المعتمد | `validators/check_pdf_format.py` | 2 |
| تغطية فحص العقوبات | `validators/check_ofac_coverage.py` | 1 |
| عدد المصادر (مصدر واحد للحقيقة) | `validators/check_sources_count.py` | 1 |
| قابلية النقل (لا مسار مطلق في الشيفرة) | `validators/check_portable_paths.py` | 2 |
| بوابات المخرج (12) | `tools/qa_gates.py` | 2 |

## سجل الأعطال

`brain/audit/سجل-الأعطال-والثغرات.md` — كل عطل أو ثغرة أو ازدواج مع سببه الجذري ولماذا لم يُكتشف سابقًا والمانع الذي يمنع تكراره. **لا يُغلق عطل قبل تسجيل مانع.**

## الأمن

- لا تُخزَّن في هذا المستودع أي أسرار: رمز البوت ومعرّف المحادثة وكلمة سر الويب هوك محجوبة أو مستثناة (التفصيل في `docs/نقل-إلى-جيت-هب.md`).
- رمز البوت في بيئة التشغيل فقط، وخدمة الويب هوك تعمل بفشل مغلق عند غياب السر.

## الفهرس والتحقق

`docs/فهرس-الملفات.tsv` يحمل مسار كل ملف وحجمه وتاريخ آخر تعديل وبصمة `sha256`. للتحقق بعد التنزيل:

```bash
cd mda-marine-system
python3 - <<'PY'
import hashlib, pathlib
bad = 0
for line in pathlib.Path("docs/فهرس-الملفات.tsv").read_text(encoding="utf-8").splitlines()[1:]:
    rel, size, mtime, digest = line.split("\t")
    p = pathlib.Path(rel)
    if not p.exists():
        print("مفقود:", rel); bad += 1; continue
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h != digest:
        print("بصمة مختلفة:", rel); bad += 1
print("النتيجة:", "مطابق ✓" if bad == 0 else f"{bad} اختلافًا")
PY
```
## التشغيل من أي جهاز

النظام **محمول بالكامل**: لا مسار مطلق مكتوب في أي ملف تنفيذي، وكل ملف يستنتج جذره من موقع الملف أو يقبله من `BRAIN_DIR`/`SITE_DIR`.

```bash
# ١) استنساخ
git clone https://github.com/fahadaldoseri/mda-marine-system.git   # الرابط كما في زر Code بالمستودع
cd mda-marine-system

# ٢) تهيئة كاملة بأمر واحد (حزم النظام · بايثون · متصفح Playwright · خطوط عربية)
bash brain/bootstrap.sh

# ٣) فحص أن كل شيء جاهز
bash brain/bootstrap.sh --verify-only
```

الأدلة: `brain/SETUP.md` (التهيئة التفصيلية) · `brain/docs/تشغيل-Codespaces.md` (تشغيل سحابي من أي جهاز بلا تثبيت).

**على GitHub Codespaces:** زر **Code** ← **Codespaces** ← **Create codespace on main**، وتُبنى البيئة تلقائيًا من `.devcontainer/devcontainer.json` في ٥–٨ دقائق. ملاحظة: النشر على الموقع وخدمة الويب هوك والمهام المجدولة تبقى على المنصة، وCodespaces بيئة تشغيل وتحرير.

## كيف يعمل النظام يوميًا
