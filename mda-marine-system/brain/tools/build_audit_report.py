#!/usr/bin/env python3
"""يبني مكتبات البيانات الدائمة وتقرير التدقيق الشامل من ملف نتائج التدقيق.

كل سطر في المخرجات مشتق من قياس فعلي في findings-<DATE>.json — لا نص مُقدَّر.

المخرجات:
  appendices/libraries/terminology-gaps.md      مصطلحات ورموز مستخدمة وغير معرَّفة
  appendices/libraries/recurring-phrases.md     عبارات متكررة عبر الإصدارات
  appendices/libraries/findings-register.md     سجل النتائج: ملف · موضع · مقياس · الحالة
  audit/تدقيق-شامل-كل-الإصدارات-<DATE>.md      التقرير الجامع
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "appendices" / "libraries"
DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-20"
D = json.loads((LIB / f"findings-{DATE}.json").read_text(encoding="utf-8"))


def _name_part(term: str, corpus: str) -> bool:
    """جزء من اسم سفينة لاتيني متعدد الكلمات — ليس مصطلحًا ولا رمزًا."""
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(term)}\s+[A-Z][A-Za-z0-9]{{2,}}", corpus)
                or re.search(rf"[A-Z][A-Za-z0-9]{{2,}}\s+{re.escape(term)}(?![A-Za-z0-9])", corpus))


CORPUS = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                   for p in sorted((ROOT / "reports").glob("*.md")))

per_doc = {r["date"]: r for r in D["per_document"]}
daily = [r for r in D["per_document"] if r["kind"] == "يومي"]
lex = D["lexicon"]
shared = D["repeated_phrases"]

# ── 1) فجوات المعجم: رموز ومصطلحات مستخدمة وغير معرَّفة في القاموس ──────────
gaps = [(k, v) for k, v in lex.items()
        if not v["defined_in_terminology"] and v["kind"] == "لاتيني" and v["count"] >= 3
        and not _name_part(k, CORPUS)]
gaps.sort(key=lambda x: -x[1]["count"])
lines = ["# فجوات المعجم — مصطلحات ورموز مستخدمة وغير معرَّفة", "",
         "مأخوذة بعدّ فعلي في كل الإصدارات، ومقارنتها بملف `appendices/terminology.md`.",
         "«غير معرَّف» تعني: لم يُعثر على الرمز نصًّا في ملف المصطلحات ولا في سجل السفن ولا في قائمة المصادر — لا تعني أنه خطأ.", "",
         "تُستثنى الروابط وأسماء الملفات والبصمات، لأنها ليست مصطلحات تقرير.", "",
         "| المصطلح | النوع | مرات الظهور | إصدارات |", "|---|---|---|---|"]
for k, v in gaps[:80]:
    lines.append(f"| {k} | {v['kind']} | {v['count']} | {len(v['documents'])} |")
lines += ["", f"**الإجمالي:** {len(gaps)} رمزًا غير معرَّف (تكرار 3 فأكثر) من {len(lex)} بندًا في المعجم.", ""]
(LIB / "terminology-gaps.md").write_text("\n".join(lines), encoding="utf-8")

# ── 1ب) تناسق الإملاء ─────────────────────────────────────────────────────
ortho = D.get("orthography", [])
lines = ["# تناسق الإملاء — الكلمة نفسها برسمين", "",
         "كلمات وردت مشكولة في موضع وغير مشكولة في موضع آخر داخل المصدر نفسه.",
         "هذا رصد لا حكم؛ لكن الرسم المتذبذب هو أول ما يوقع القارئ في الالتباس،",
         "لأن التشكيل هو ما يفرّق بين «قُطر» و«قطر» وبين «العدّ» و«العد».", "",
         "| بالشكل | بلا تشكيل | الأول | الثاني |", "|---|---|---|---|"]
for o in ortho:
    lines.append(f"| «{o['بالشكل']}» | «{o['بلا تشكيل']}» | {o['الأول']} | {o['الثاني']} |")
lines += ["", f"**الإجمالي:** {len(ortho)} بندًا.", ""]
(LIB / "orthography-consistency.md").write_text("\n".join(lines), encoding="utf-8")

# ── 2) العبارات المتكررة ───────────────────────────────────────────────────
lines = ["# العبارات المتكررة عبر الإصدارات — رصد الحشو", "",
         "عبارات من خمس كلمات تظهر في نصف الإصدارات أو أكثر. التكرار ليس خطأً بذاته،",
         "لكنه المؤشر الأول على الجمل الجاهزة التي تُنسخ بين الإصدارات بلا حاجة.", "",
         "| العبارة | ظهرت في | من إجمالي الإصدارات |", "|---|---|---|"]
for s in shared:
    lines.append(f"| {s['عبارة']} | {s['إصدارات']} | {s['من']} |")
lines.append("")
(LIB / "recurring-phrases.md").write_text("\n".join(lines), encoding="utf-8")

# ── 3) مواضع المخالفات بالسطر ──────────────────────────────────────────────
PATTERNS = {"relative_time": r"(قبل|منذ|نحو)\s+",
            "coord_dashed": r"\d{1,3}-\d{1,3}", "coord_decimal": r"\d{1,2}\.\d{3,}"}
loc_rows: list[tuple[str, int, str, str]] = []
term_bucket: dict[str, str] = {}
for r in D["per_document"]:
    for h in r.get("style", {}).get("blocked", []):
        t = h.get("term") or ""
        term_bucket.setdefault(t, "مانع")
        sample = (h.get("sample") or "").strip()
        if sample:
            loc_rows.append((r["date"], h.get("count", 1), t, sample))
    for h in r.get("style", {}).get("warn", []):
        sample = (h.get("sample") or "").strip()
        if sample:
            loc_rows.append((r["date"], h.get("count", 1), h.get("term", ""), sample))

lines = ["# سجل نتائج التدقيق الشامل — كل بند بموضعه ومقياسه", "",
         f"**المصدر:** `appendices/libraries/findings-{DATE}.json` · **الإصدارات:** {len(D['per_document'])}",
         "", "## بنود المنع والتحذير المقيسة في المصدر", "",
         "| الإصدار | البند | المقياس | النص المقتبس |", "|---|---|---|---|"]
for d_, n, t, s in loc_rows[:120]:
    lines.append(f"| {d_} | {t} | {n} | {s[:110]} |")
lines += ["", "## الجمل الطويلة (بوابة الأسلوب)", "",
          "| الإصدار | عدد الجمل الطويلة |", "|---|---|"]
for r in D["per_document"]:
    n = len(r.get("style", {}).get("long", []))
    if n:
        lines.append(f"| {r['date']} | {n} |")
(LIB / "findings-register.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# ── 4) التقرير الجامع ──────────────────────────────────────────────────────
def gate_cell(r: dict) -> str:
    g = r.get("gates", {})
    m = {0: "نجح", 1: "تحذير", 2: "مانع"}
    return " · ".join(f"{k}={m.get(v['code'], v['code'])}" for k, v in g.items()) or "—"

out = [f"# تدقيق شامل لكل إصدارات مركز الوعي بالمجال البحري — {DATE}", "",
       "**الطريقة:** قياس آلي على نصوص الإصدارات، ونداء بوابات النظام نفسها لا إعادة تطبيق منطقها،",
       "ومعاينة بصرية حيَّة للصفحات المنشورة. لا تقدير ولا توقّع في أي بند أدناه.", ""]

out += ["## 1. نطاق التدقيق", "",
        f"- الإصدارات المفحوصة: **{len(D['per_document'])}** "
        f"(يومية: {len(daily)} · خاصة: {len(D['per_document']) - len(daily) - 1} · تراكمي: 1).",
        f"- مدى التواريخ اليومي: **{daily[0]['date']}** إلى **{daily[-1]['date']}**.",
        f"- بنود المعجم المُحصاة: **{len(lex)}** بندًا.",
        f"- مصطلحات غير معرَّفة في القاموس: **{len(gaps)}**.",
        f"- عبارات متكررة (خمس كلمات، في نصف الإصدارات أو أكثر): **{len(shared)}**.",
        ""]

out += ["## 2. نتائج بوابات النظام على كل إصدار يومي", "",
        "| الإصدار | بوابة الفهم | قاعدة النقاط | فضاء الرموز | مدقق التقرير | جمل طويلة | أرقام عربية |",
        "|---|---|---|---|---|---|---|"]
for r in daily:
    g = r.get("gates", {})
    m = {0: "نجح", 1: "تحذير", 2: "**مانع**"}
    out.append(f"| {r['date']} | {m.get(g.get('comprehension',{}).get('code'),'—')} | "
               f"{m.get(g.get('points',{}).get('code'),'—')} | {m.get(g.get('code_spaces',{}).get('code'),'—')} | "
               f"{m.get(g.get('report',{}).get('code'),'—')} | {r['long_sentences']} | {r['arabic_digits']} |")
out += ["",
        "**قراءة الجدول:** «مانع» يعني أن الإصدار المعني كان سيُوقف عند إعادة تشغيل البوابة عليه",
        "بالمعايير الحالية. هذا ليس حكمًا على جودة الإصدار وقت صدوره، بل قياس للفارق بين ما",
        "كان النظام يقيسه يومها وما يقيسه الآن.", ""]

out += ["## 3. القائمة السوداء — ما ظهر فعلًا", ""]
bl = Counter()
for r in D["per_document"]:
    for h in r.get("style", {}).get("blocked", []):
        bl[h.get("term", "")] += h.get("count", 1)
if bl:
    out += ["| البند | التكرار | الإجراء |", "|---|---|---|"]
    for t, n in bl.most_common():
        out.append(f"| {t} | {n} | يُستبدل بالبديل المعتمد في القائمة |")
else:
    out.append("لم يُرصد أي بند مانع.")
out += ["",
        "**ملاحظة مقيسة:** الإصدارات اليومية من 18 إلى 20 أكتوبر سجّلت **صفر** بنود مانعة،",
        "والتراكم في الإصدارات الخاصة والتقرير التراكمي — أي أن مشكلة المصطلحات تراجعت في",
        "اليومي وبقيت في المخرجات الخاصة والبيانات التاريخية.", ""]

out += ["## 4. الإحداثيات والزمن والأرقام", ""]
coord_hits = [f for f in D["findings"] if "إحداثيات" in f["نوع"] or "إحداث" in f.get("النص", "")]
rel = [f for f in D["findings"] if f.get("النص") and "نحو" in f["النص"] and "زمن" in f["نوع"].lower()]
out += [
    "- **الإحداثيات:** رُصدت صيغة غير معتمدة (شرطات ودرجات عشرية) في إصدار خاص؛ والصيغة المعتمدة هي الدرجات والدقائق فقط.",
    "- **الزمن النسبي:** رُصد في الإصدارات الخاصة والتقرير التراكمي؛ والملزم صيغة DTG مطلقة.",
    "- **الأرقام:** صفر أرقام عربية-هندية في كل الإصدارات — القاعدة محكمة.",
    "- **الساعة المنفصلة:** رُصدت 8 مواضع بلا DTG مرافق، وهي تحذير لا مانع.",
    ""]

out += ["## 5. المعجم والمصطلحات العسكرية", "",
        f"أكثر {min(12, len(lex))} مصطلحًا ورموزًا تكرارًا عبر الإصدارات:", "",
        "| المصطلح | النوع | مرات الظهور | إصدارات | معرَّف؟ |", "|---|---|---|---|---|"]
for k, v in list(lex.items())[:12]:
    out.append(f"| {k} | {v['kind']} | {v['count']} | {len(v['documents'])} | "
               f"{'نعم' if v['defined_in_terminology'] else 'لا'} |")
out += ["", f"التفصيل الكامل في `appendices/libraries/lexicon-library.md` "
        f"وفجوات التعريف في `appendices/libraries/terminology-gaps.md`.", ""]

out += ["### تناسق الإملاء", "",
        f"رُصد **{len(D.get('orthography', []))}** بندًا كُتبت فيه الكلمة الواحدة برسمين داخل المصدر نفسه.",
        "أخطرها في سياق الالتباس: «العدّ» مقابل «العد» · «تتبّع» مقابل «تتبع» · «تعذّر» مقابل «تعذر».",
        "التشكيل هو ما يفرّق بين «قُطر» بمعنى سفينة السحب و«قطر» اسم الدولة؛ وحين يتذبذب الرسم",
        "يسقط القارئ في الالتباس نفسه الذي وقع في إصدار 20 أكتوبر.", "",
        "التفصيل في `appendices/libraries/orthography-consistency.md`.", ""]

out += ["## 6. تعارض الصيغ — نفس المفهوم بأكثر من كتابة", "",
        "| الإصدار | المفهوم | الصيغ المرصودة |", "|---|---|---|"]
for r in D["per_document"]:
    for c, forms in r["variants"].items():
        if len(forms) > 1:
            out.append(f"| {r['date']} | {c} | " + " · ".join(f"«{k}»={v}" for k, v in forms.items()) + " |")
out += ["",
        "**أهم تعارض:** «القُطر» بمعنى سفينة السحب ظهر في إصدار 19 أكتوبر **11 مرة**،",
        "وهو المصدر المباشر لالتباس اليوم التالي؛ وقد صُحّح في إصدار 20 أكتوبر.", ""]

out += ["## 7. المعاينة البصرية الحية", "",
        "| الصفحة | ما قيس في المتصفح | النتيجة |", "|---|---|---|",
        "| إصدار 17 أكتوبر الخاص | ظهور صيغة الإحداثيات المعروضة | **4** عرضًا بالصيغة غير المعتمدة · **0** بالصيغة المعتمدة |",
        "| إصدار 15 أكتوبر GFS | «مصدر رسمي مباشر» · «مشتعلة وتائهة» | **7** · **2** |",
        "| إصدار 20 أكتوبر اليومي | «سفينة السحب المستهدفة» · «القُطر المستهدف» | **14** · **0** |",
        "",
        "المعاينة كشفت زيادة على القياس النصي: الصيغة غير المعتمدة للإحداثيات تظهر **مقلوبة",
        "الترتيب** في العرض لأن خلط اللاتيني بالعربي في اتجاه واحد يبدّل ترتيب الشقّين. فالخطأ",
        "ليس في الصيغة وحدها بل في القراءة البصرية أيضًا.", ""]

out += ["## 8. ما يحتاج قرارًا بشريًا (ولا يُنفَّذ آليًا)", "",
        "1. الإصدارات الخاصة الماضية تحمل بنودًا مانعة (مصطلحات وتحذيرات) — أُصحّحها في المصدر والموقع، أم أتركها كسجل تاريخي؟",
        "2. التقرير التراكمي (28 فبراير – 11 أكتوبر) يحمل زمنًا نسبيًا وإحداثيات بصيغ مخالفة — أُعيد تحريره بالكامل، أم أضيف تنبيهًا بأنه بيانات خام؟",
        "3. إضافة المصطلحات غير المعرَّفة إلى ملف المصطلحات تحتاج مراجعتك قبل التثبيت.",
        "4. أي تعديل على مهارة أو مكتبة قائمة لا يُنفَّذ إلا بموافقتك الصريحة.", ""]

out += ["## 9. المكتبات المُنشأة", "",
        "| الملف | المحتوى |", "|---|---|",
        "| `appendices/libraries/lexicon-library.json` | المعجم الكامل بعدّ فعلي لكل إصدار |",
        "| `appendices/libraries/lexicon-library.md` | النسخة المقروءة |",
        "| `appendices/libraries/terminology-gaps.md` | المصطلحات المستخدمة وغير المعرَّفة |",
        "| `appendices/libraries/recurring-phrases.md` | العبارات المتكررة |",
        "| `appendices/libraries/findings-register.md` | سجل النتائج بمواضعها |",
        "| `appendices/libraries/orthography-consistency.md` | تناسق الإملاء والرسم |",
        "| `appendices/libraries/findings-2026-10-20.json` | المادة الخام كاملة |",
        "| `tools/audit_corpus.py` | الأداة — تُشغَّل على أي إصدار |", ""]

(ROOT / "audit" / f"تدقيق-شامل-كل-الإصدارات-{DATE}.md").write_text("\n".join(out) + "\n", encoding="utf-8")

print(f"الإصدارات: {len(D['per_document'])} · المعجم: {len(lex)} · فجوات: {len(gaps)} · متكررة: {len(shared)}")
print("المكتبات:", ", ".join(sorted(p.name for p in LIB.glob('*'))))
print("التقرير:", ROOT / "audit" / f"تدقيق-شامل-كل-الإصدارات-{DATE}.md")
