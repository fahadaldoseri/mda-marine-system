# كتاب مصائد التوقف — بأدلة تشغيل حقيقية (جولة 2026-10-29)

كل مصيدة هنا رُصدت فعليًا في المشروع، مع الأمر والدليل. لا تُضِف مصيدة بلا دليل تشغيل.

## 1) تأخر انتشار الموقع: النشر ينجح والتحقق الحي يفشل

- العَرَض: `D010` (نشر) رمز 0، ثم `D020` (تحقق حي) يفشل 5 محاولات:
  `✘ خلل: ['/reports/<date>.html', '/reports/pdf/<date>.pdf', 'pdf-differs-from-local']`.
- السبب: أمر النشر أُرسل، والانتشار لم يكتمل بعد؛ الموقع الحيّ كان لا يزال يخدم إصدار اليوم السابق.
- الإثبات: `curl` على الإصدار السابق يُعيد 200 والجديد 404 خلال دقائق الانتشار.
- العلاج: انتظار متكرر حتى يظهر الإصدار (20 محاولة × 25 ثانية مثلًا)، ثم إعادة `run` — تكتمل `D020` وحدها بلا أي تعديل في التقرير.

## 2) انحراف التماثل من ملفات `.bak` ومن ملفات مُولَّدة على الخادم

- العَرَض (أولًا): `D040` رمز 2 — «انحراف مانع (16)» ومنها
  `✘ محتوى مختلف: brain/templates/approved-pdf/print-profile.json` و`new brain/tools/export_report_assets.py.bak-k257`.
- السبب: النسخ الاحتياطي ينسخ **البيانات فقط** (`tools/github_backup.py`)، بينما الشيفرة تُطبَّق **من GitHub إلى الخادم**
  (`tools/apply_from_github.py`). فأي شيفرة عُدّلت على الخادم تظهر انحرافًا، وأي ملف `.bak` جديد يظهر «جديدًا غير متتبَّع».
- العَرَض (ثانيًا): `D070` رمز 2 — «انحراف مانع (2)»: `brain/docs/reports-index.md` و`skills/superpowers-method/SKILL.md`
  (مُولَّد/مُحرَّر على الخادم بعد النسخ).
- العلاج المعتمد:
  1. انقل ملفات `.bak` الجديدة خارج الشجرة (مثال: `/home/ubuntu/audit-<date>/backups/<date>/`) — بلا حذف.
  2. زامن الخادم→المستودع: `python3 tools/sync_to_repo.py --brain <brain> --repo <repo>/brain --site <site> --repo-site <repo>/site --skills /home/ubuntu/skills --repo-skills <repo>/skills`
  3. ادمج في فرع + طلب دمج (لا دفع مباشر إلى `main`)، ثم أعد `run` — يمرّ `D040`/`D070` رمز 0.
- مصيدة داخلها: إن مرّرت `--repo <repo-root>` بدل `<repo-root>/brain` ستخطّط المزامنة لحذف آلاف الملفات
  (`SYNC_GUARD: الحذف 6037 ملفًا يتجاوز السقف 20`). تحقّق دائمًا بـ`--dry-run` قبل التنفيذ.

## 3) بوابة خطوة نفّذها المحرّك ترفض `complete`

- العَرَض: `python3 tools/runbook.py complete G045 --date <date>` → `✘ هذه الخطوة ينفذها المحرّك لا الوكيل`.
- العلاج: لا تكملها يدويًا؛ أعد `runbook.py run` فقط، وهي تُنفَّذ وتُسجَّل `done` من المحرّك.

## 4) بوابة أوقفت التسليم بعد نجاح المحتوى (طباعة/أسطح/تماثل)

- الطريق: شخّص البوابة بـ`validators/<gate>.py` مباشرة قبل أي تعديل، ثم أصلح جذريًا.
- مثال طباعة (جولة ك-297): الفراغ الداخلي كان من `break-after:avoid` + كتلة ذرّية — التفاصيل والقياس في مهارة
  `print-layout-gate-ops`؛ والقاعدة: أصلح التدفّق لا التباعد.

## 5) تسلسل الإغلاق الصحيح بعد آخر إصلاح

```
measure (حي) → fix (فرع) → test (بعد القياس) → PR + merge (بتفويض) → run (استئناف)
  → publish → live verify (انتظار انتشار) → parity strict → fault + lesson (بدليل)
```

## أوامر مرجعية سريعة

```bash
pgrep -af 'runbook.py run --date <date>'                     # لا تشغّل موازيًا
python3 tools/runbook.py status --date <date>                # أين توقف بالضبط
tail -30 logs/runbook/<date>/<STEP>.log                      # سبب التوقف الحقيقي
gh pr merge <N> --repo <owner/repo> --merge --delete-branch   # دمج غير تفاعلي
python3 validators/check_backup_parity.py --mode strict      # «مطابق» = الشجرة = المستودع
```
