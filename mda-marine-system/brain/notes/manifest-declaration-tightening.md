# 运行簿声明收紧设计

日期：2026-10-30

## 问题与基线

`tools/runbook.py` 的 `static_paths()` 在 `tools/runbook.py:382-385` 读取 `links.folders`；`reachability()` 在 `tools/runbook.py:477-482` 对每个声明路径执行 `os.path.isdir()`，随后把该目录下所有已跟踪文件加入 `seeds`。因此目录声明会把新文件自动纳入可达集合，不能发现目录内的“文件漂移”。`verify()` 仍在 `tools/runbook.py:564-569` 对这些声明做存在性检查；`render_handbook()` 在 `tools/runbook.py:636-641` 将其打印到生成手册。

当前 `links.folders` 的逐项基线（递归文件数）：

| 步骤 | 字段 | 目录 | 当前文件数 |
|---|---|---|---:|
| G000 | `links.folders` | `evidence/merkle` | 6 |
| G000 | `links.folders` | `evidence/governing-chain` | 11 |
| G000A | `links.folders` | `evidence/merkle` | 6 |
| G000A | `links.folders` | `evidence/governing-chain` | 11 |
| G000B | `links.folders` | `evidence/hermetic` | 376 |
| G000B | `links.folders` | `evidence/watch` | 2 |
| G000C | `links.folders` | `evidence/hermetic` | 376 |
| G000C | `links.folders` | `.pytest_cache` | 5 |
| B010 | `links.folders` | `{site}/generator` | 0 |

القياس المطلوب قبل وبعد: `check_skills_integrity` = 0 و`runbook verify` = 0 في الحالة الطبيعية. الحالة الحالية المقاسة: كلاهما 0، و`verify` يطبع تحذير D005 فقط.

## القاعدة المعتمدة

1. لا تُستخدم `links.folders` لإثبات اتصال ملفات الأدلة؛ كل ملف ثابت يُدرج بمساره الصريح في `links.files`.
2. كل مخرج يتولد في كل تشغيل يملك اسمًا قياسيًا ثابتًا ويُستبدل (overwrite) في مكانه؛ لا تُنتج الأدوات أسماءً زمنية داخل شجرة الأدلة الحاكمة.
3. الأدلة الزمنية القديمة لا تُترك كملفات شاردة: تُحفظ في `/home/ubuntu/audit-2026-10-30/backups-declare/` قبل الإزالة، ويُعلن فقط البديل القياسي داخل المشروع.
4. لا تغيير في `tools/runbook.py` أو تخفيف لأي بوابة أو شرط `&&` أو `rc=$?; exit "$rc"`.

## التنفيذ الأدنى

- تعديل `tools/hermetic_run.sh` ليستخدم `evidence/hermetic/<name>.json`، و`traces/<name>.strace`، و`raw/<name>/...`، و`fingerprints/<name>/...` بأسماء ثابتة؛ يبقى timestamp داخل metadata فقط عند الحاجة، لا في اسم ملف الدليل.
- تحديث `tests/test_hermetic_run.py` و`evidence/hermetic/HERMETIC-RUN.md` لتثبت overwrite والمسارات القياسية.
- نقل/أرشفة الملفات الزمنية القديمة من الأدلة المعلنة إلى مجلد النسخ الاحتياطية المحدد، دون حذف دليل له بديل قبل حفظ النسخة.
- إزالة كل `links.folders` من المانيفست واستبدالها بقائمة صريحة للملفات الحالية/القياسية اللازمة لكل خطوة، مع تحديث `docs/runbook.md` بواسطة المولد.

## بوابات القبول

- `python3 tools/runbook.py verify` = 0 طبيعيًا.
- إنشاء `evidence/__stray-test.txt` يجعل verify = 2 ويذكر الاسم حرفيًا؛ إزالة الملف تعيد 0.
- تكرار الاختبار داخل `evidence/merkle/` يجعل verify = 2 ويذكر الملف؛ إزالة الملف تعيد 0.
- `python3 tests/test_manifest_commands.py` = 0.
- تشغيل اختبارات hermetic ذات الصلة يثبت أن الاسم القياسي يُستبدل ولا يتراكم ملف زمني.
- تشغيل `G000`/`G000A`/`G000C` فقط عند الإمكان، بلا نشر أو Telegram أو `runbook.py run`.
- تسجيل الأوامر والرموز حرفيًا في `evidence/governing-chain/declaration-tightening.md`، ثم إعادة فحص السلامة وverify في النهاية.
