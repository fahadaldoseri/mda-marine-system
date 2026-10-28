#!/usr/bin/env python3
"""يبني `references/ambiguity-map.md` لمهارة التدقيق العربي العسكري.

المصدر: مكتبات التدقيق المبنية من عدّ فعلي في كل الإصدارات.
يُعاد توليده بعد كل تدقيق شامل: python3 tools/audit_corpus.py --date <YYYY-MM-DD>
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "appendices" / "libraries"
import os
SKILLS_DIR = Path(os.environ.get("SKILLS_DIR", "/home/ubuntu/skills"))
DEST = SKILLS_DIR / "military-arabic-editing" / "references" / "ambiguity-map.md"

D = json.loads((LIB / "findings-2026-10-20.json").read_text(encoding="utf-8"))
lex = D["lexicon"]
gaps = sorted(((k, v) for k, v in lex.items()
               if not v["defined_in_terminology"] and v["kind"] == "لاتيني" and v["count"] >= 3),
              key=lambda x: -x[1]["count"])
ortho = D.get("orthography", [])
variants = [(r["date"], c, f) for r in D["per_document"] for c, f in r["variants"].items()
            if len(f) > 1]

out = ["# خريطة الالتباس — مرصودة فعليًا في كل الإصدارات", "",
       "مبنية على عدّ آلي في 14 إصدارًا (9 يومية · 4 خاصة · 1 تراكمي)، لا على تقدير.",
       "استخدمها قبل الصياغة: كل بند هنا أوقع قارئًا فعليًا في الالتباس.", "",
       "## 1. الرموز المستخدمة بلا تعريف", "",
       "لا تستخدم أيًّا منها قبل تعريفه في «قاموس الرموز والمصطلحات» المنشور.", "",
       "| الرمز | مرات الظهور | إصدارات |", "|---|---|---|"]
for k, v in gaps:
    out.append(f"| {k} | {v['count']} | {len(v['documents'])} |")

out += ["", "## 2. الكلمة الواحدة برسمين", "",
        "التشكيل هو ما يفرّق بين «قُطر» و«قطر» وبين «العدّ» و«العد». تذبذب الرسم يُسقط القارئ", "",
        "| بالشكل | بلا تشكيل | الأول | الثاني |", "|---|---|---|---|"]
for o in ortho:
    out.append(f"| «{o['بالشكل']}» | «{o['بلا تشكيل']}» | {o['الأول']} | {o['الثاني']} |")

out += ["", "## 3. المفهوم الواحد بأكثر من صيغة", "",
        "| الإصدار | المفهوم | الصيغ |", "|---|---|---|"]
for d_, concept, forms in variants:
    out.append(f"| {d_} | {concept} | " + " · ".join(f"«{k}»={v}" for k, v in forms.items()) + " |")

out += ["", "## 4. قاعدة الاستخدام", "",
        "- ثبّت رسمًا واحدًا لكل كلمة، واكتب التشكيل في الكلمات التي يفرّقها.",
        "- لا تستخدم كلمة بمعنيين في السياق البحري بلا قرينة؛ «قُطر» مثالها الأشهر.",
        "- لا تُدخل رمزًا جديدًا قبل تعريفه في القاموس المنشور مع الإصدار.",
        "- حدّث هذه الخريطة بعد كل تدقيق شامل، ولا تعدّلها يدويًا.", ""]

DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text("\n".join(out), encoding="utf-8")
print(f"كُتبت: {DEST}")
print(f"  رموز بلا تعريف: {len(gaps)} · رسم متذبذب: {len(ortho)} · تعارض صيغ: {len(variants)}")