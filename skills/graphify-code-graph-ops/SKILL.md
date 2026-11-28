---
name: graphify-code-graph-ops
description: "استعلام رسم الكود المحلي قبل فتح الملفات، لتوفير التوكن. يُبنى بـ graphify extract --code-only بلا إرسال المستندات إلى نموذج. لا يكتب تقريرًا ولا بوابة ولا ينشر."
---

# Graphify — رسم الكود للاستعلام

المصدر المثبت: `Graphify-Labs/graphify` عند `a7295bc`، والأداة `graphifyy` 0.9.110.

## الفرق عن المهارات المجاورة

| المهارة | الحد |
|---|---|
| `project-evidence-and-coverage-ops` | تلك تقيس جولة وتغطي أدلتها. هذه ترسم الكود فقط وتجيب عن «أين الدالة». |
| `runbook-operations-ops` | الكتيب يشغّل اليوم. Graphify لا يغيّر خطوة فيه. |

## متى تُستدعى

قبل قراءة ملف في `brain/tools` أو `brain/validators` أو `brain/runbook`، إذا كان السؤال عن الربط لا عن نص القاعدة.

## الأمر

```bash
graphify extract . --code-only --no-cluster
graphify query "السؤال" --budget 800 --depth 2
```

`--code-only` إلزامي. لا يُستخدم استخراج المستندات لأنه قد يرسلها إلى نموذج.

## القياس في 2026-11-28

استخراج 422 ملفًا كتب `graphify-out/graph.json`: 4659 عقدة و11245 حافة. الاستعلام عن `check_ledger_continuity` أعاد الملف `brain/validators/check_ledger_continuity.py`.
