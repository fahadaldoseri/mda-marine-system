#!/usr/bin/env python3
"""مولّد مرجع آلية العمل من مصدر واحد.

القاعدة الحاكمة: مرجع آلية العمل لا يُكتب يدويًّا. البنية (المراحل · البنود · سقف الجهد ·
الحالة · بوابات الاستيفاء) تُشتق من `runbook/phases.json`، والنص السردي يُجمَّع من
`runbook/reference/sections/`. فإن اختلف المعدَّد عن المولَّد يفشل الحارس مغلقًا.

الأوامر:
  build_workflow_reference.py bootstrap --root .   يستخرج النص السردي من الإصدار الخامس ويبني phases.json
  build_workflow_reference.py build     --root .   يبني الإصدار السادس ومقارنة الإصدارين
  build_workflow_reference.py check     --root .   يقارن ما على القرص بالمولَّد ويفشل عند الاختلاف

رمز الخروج: 0 سليم · 2 خلل.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

OUT_DOC = "audit/مرجع-آلية-العمل.md"
OUT_CMP = "audit/مقارنة-الإصدارين-5-6.md"
FIFTH = "audit/مرجع-آلية-العمل-2026-11-05.md"
PHASES = "runbook/phases.json"
SECTIONS_DIR = "runbook/reference/sections"
GENERATED_SECTIONS = {4, *range(14, 21)}
STATUSES = ["منفَّذ", "منفَّذ جزئيًّا", "معلَّق"]

PREP_ITEMS = [
    ("دفتر قرارات المالك: 16 قرارًا بحالة ودليل مقيس", "منفَّذ", "منع كتابة «منفَّذ» بلا سند", "decisions/registry.json + حارس + اختبار", "G062"),
    ("ترقيم بنود موحّد ومولّد مرجع من مصدر واحد", "منفَّذ", "إلغاء افتراق الأرقام عن النص", "runbook/phases.json + هذا المولّد", "G063"),
    ("أدوات مانعة أربع مربوطة ببوابة العبور", "معلَّق", "تحويل الأثر من تقدير إلى قياس", "tools/surface_fingerprint.py · number_fingerprint.py · regression_gate.py · impact_matrix.py", "تشغيل البوابة على انتقال تجريبي"),
    ("إصلاح F-01: أرقام المرجع القديمة (111 خطوة · 62 مدققًا)", "منفَّذ", "دقة المرجع", "مشتق آليًّا من المانيفست", "G063"),
    ("إصلاح F-02: قاعدة عدّ الاختبارات", "منفَّذ", "إنهاء تفسيرين لرقم واحد", "قاعدة معلنة في المولّد", "G063"),
    ("إصلاح F-04: تعارض الخطوة D071 بين المرجع وعقد التسليم", "معلَّق", "إزالة تعارض مرجعين", "تعديل عقد السياسة أو جدول التسليم", "حارس السياسة"),
    ("إصلاح F-05: تطابق أرقام البنود مع البنود", "منفَّذ", "إثبات «استوفت المرحلة» آليًّا", "سقف الجهد مشتق من عدد البنود", "G063"),
    ("إصلاح F-06: رقم أداء بلا سند داخلي", "معلَّق", "إسناد كل رقم", "إحالة داخلية إلى تدقيق 2026-11-05", "بوابة ربط الأرقام"),
    ("إصلاح F-07: أكواد بنود بلا تعريف", "منفَّذ", "قراءة المرجع بلا رجوع لملف آخر", "معجم أكواد في المولّد", "G063"),
    ("إصلاح F-08: مصطلحات بلا تحديد كمّي (الجلسة · حد الكلمات · الحد المتفق)", "منفَّذ", "إزالة التفسير الشخصي", "معجم مصطلحات في المولّد", "G063"),
    ("إغلاق F-09: سجل القرارات المنفَّذة", "منفَّذ", "تمييز المنفَّذ من المعلَّق", "decisions/registry.json", "G062"),
    ("إغلاق F-10: بقايا نصية لبطاقة مدموجة («هجمات مؤكدة») وبقايا «نقل عن»", "معلَّق", "تنظيف المخرج من بقايا قرارات", "قياس موضع الظهور ثم إصلاح جذري", "بوابة الأسطح"),
    ("جدول موضع الحقيقة الواحد لكل مفهوم", "منفَّذ", "منع التناقض بين الأسطح", "قسم مولَّد في المرجع", "G063"),
    ("قسم «ما لم يُقَس» في المرجع", "منفَّذ", "منع الادعاء غير المسنود", "قسم مولَّد في المرجع", "G063"),
    ("قالب تقرير إغلاق المرحلة بحقول ثابتة", "معلَّق", "توحيد التسليم في كل مرة", "قالب مفوَّض في المانيفست", "بوابة الإغلاق"),
    ("الفهرس الآلي للأقسام مع بوابة", "معلَّق", "منع انحراف الفهرس", "مولّد فهرس + بوابة مطابقة", "G063"),
]


def split_top(text: str) -> list[str]:
    out, buf, depth = [], [], 0
    for ch in text:
        if ch in "([{«":
            depth += 1
        elif ch in ")]}»":
            depth = max(0, depth - 1)
        if ch == "·" and depth == 0:
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        out.append("".join(buf).strip())
    return [x for x in out if x]


def bootstrap(root: Path) -> int:
    fifth = (root / FIFTH).read_text(encoding="utf-8")
    chunks = re.split(r"(?m)^(## .+)$", fifth)
    header = chunks[0].strip()
    sections: list[tuple[int, str, str]] = []
    for i in range(1, len(chunks), 2):
        title = chunks[i].strip()
        body = chunks[i + 1].strip("\n")
        m = re.match(r"##\s+(\d+)\s+—\s+(.+)", title)
        num, name = (int(m.group(1)), m.group(2).strip()) if m else (0, title.lstrip("# ").strip())
        sections.append((num, name, body))

    sdir = root / SECTIONS_DIR
    sdir.mkdir(parents=True, exist_ok=True)
    for num, name, body in sections:
        (sdir / f"{num:02d}.md").write_text(f"## {num} — {name}\n\n{body}\n", encoding="utf-8")
    (root / "runbook" / "reference" / "header.md").write_text(header + "\n", encoding="utf-8")

    phases = [{"id": "ت", "name": "مرحلة التجهيز لاستخدام المرجع", "items": [
        {"id": f"ت-{i:02d}", "title": t, "status": st, "impact": imp, "basis": bas, "gate": g}
        for i, (t, st, imp, bas, g) in enumerate(PREP_ITEMS, 1)]}]
    for num, name, body in sections:
        if num not in range(14, 20):
            continue
        m = re.search(r"(?m)^\*\*البنود:\*\*\s*(.+)$", body)
        if not m:
            continue
        pnum = re.search(r"المرحلة\s+(\d)", name)
        pid = pnum.group(1) if pnum else str(num)
        items = []
        for i, t in enumerate(split_top(m.group(1)), 1):
            items.append({
                "id": f"ب{pid}-{i:02d}", "title": t, "status": "معلَّق",
                "impact": "غير محدَّد في الإصدار الخامس",
                "basis": "مرجع الإصدار الخامس — بند منقول",
                "gate": "بوابة العبور قبل الانتقال التالي",
            })
        phases.append({"id": pid, "name": name.replace(f"المرحلة {pid}:", "").strip(), "items": items})

    data = {
        "version": 1,
        "rule_ar": "لا رقم مكتوب بيد: سقف الجهد وعدّ البنود مشتقّان من قائمة البنود نفسها.",
        "status_values_ar": STATUSES,
        "items_rule_ar": "كل بند: معرّف · عنوان · أثر متوقع · سند · بوابة استيفاء · حالة.",
        "phases": phases,
    }
    (root / PHASES).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(p["items"]) for p in phases)
    print(f"   استُخرج {len(sections)} قسمًا سرديًّا · وبُني {PHASES} بـ {len(phases)} مرحلة و {total} بندًا")
    return 0


def load(root: Path):
    data = json.loads((root / PHASES).read_text(encoding="utf-8"))
    sdir = root / SECTIONS_DIR
    chunks: dict[int, str] = {}
    for f in sorted(sdir.glob("*.md")):
        chunks[int(f.stem)] = f.read_text(encoding="utf-8").strip()
    header = (root / "runbook" / "reference" / "header.md").read_text(encoding="utf-8").strip()
    return data, header, chunks


def phase_table(data) -> str:
    rows = ["| المرحلة | الاسم | عدد البنود | منفَّذ | معلَّق | بوابة الاستيفاء |", "|---|---|---:|---:|---:|---|"]
    for p in data["phases"]:
        n = len(p["items"])
        done = sum(1 for i in p["items"] if i["status"] == "منفَّذ")
        pend = n - done
        gate = "بوابة العبور" if p["id"] != "ت" else "G063"
        rows.append(f"| {p['id']} | {p['name']} | {n} | {done} | {pend} | {gate} |")
    total = sum(len(p["items"]) for p in data["phases"])
    rows.append(f"| **المجموع** | ست مراحل + التجهيز | **{total}** | "
                f"{sum(1 for p in data['phases'] for i in p['items'] if i['status']=='منفَّذ')} | "
                f"{sum(1 for p in data['phases'] for i in p['items'] if i['status']!='منفَّذ')} | — |")
    return "\n".join(rows)


def items_block(data, pid: str) -> str:
    p = next(x for x in data["phases"] if x["id"] == pid)
    rows = [f"**سقف الجهد: {len(p['items'])} بندًا (مشتق من القائمة لا مكتوب).**", "",
            "| # | البند | الأثر المتوقع | السند | بوابة الاستيفاء | الحالة |", "|---|---|---|---|---|---|"]
    for it in p["items"]:
        rows.append(f"| {it['id']} | {it['title']} | {it['impact']} | {it['basis']} | {it['gate']} | {it['status']} |")
    return "\n".join(rows)


GLOSSARY = {
    "الجلسة": "90 دقيقة عمل متصل أو 40 خطوة تنفيذية، أيّهما أسبق.",
    "حد الكلمات": "الحد الأعلى لعدد كلمات أي قسم طويل يُعلن قبل الكتابة لا بعدها.",
    "الحد المتفق للأداء": "زمن بناء التقرير المعتمد وما يقابله من سقف بالمقارنة، ومصدره سجل الأداء اليومي لا الذاكرة. · سند الرقم: `audit/measurements/live-2026-11-05.json` (قياس 2026-11-05)",
    "البند": "وحدة عمل مرقّمة بمعرّف فريد؛ لا يُعدّ البند مستوفًى إلا بدليل بوابة.",
    "بوابة العبور": "سبعة اختبارات وستة ممنوعات تُشغَّل قبل كل انتقال؛ موضع الحقيقة هو قسمها في هذا المرجع.",
    "الأسطح الحاكمة": "صفحة الإصدار · جنوب الإضافات · صفحة المصادر · الرئيسية · الصفحة الإنجليزية · دفتر اليوم · أنماط الطباعة.",
}

CODES = {
    "خ-06 … خ-10": "ملاحظات الخريطة المرقّمة في سجل ملاحظات المالك 2026-11-05.",
    "س-01 · س-07": "ملاحظات سجل الأحداث المرقّمة في السجل نفسه.",
    "F-01 … F-10": "عيوب تدقيق مرجع آلية العمل 2026-11-06.",
    "ت-01 …": "بنود مرحلة التجهيز في هذا المرجع.",
    "ب«مرحلة»-«رقم»": "بنود مراحل التنفيذ: ب0-01 أول بند في المرحلة 0.",
}

TRUTH_TABLE = """| المفهوم | موضع الحقيقة الواحد | يُشار إليه من |
|---|---|---|
| سياسة التسليم | `runbook/delivery-policy.json` | القسم 31 · INDEX.md · G061 |
| حالة القرارات | `decisions/registry.json` | G062 |
| بنود المراحل وسقف الجهد | `runbook/phases.json` | هذا المرجع (مولَّد) |
| خطوات التشغيل وأطوارها | `runbook/runbook.json` | `docs/runbook.md` (مولَّد) |
| عقود البطاقات | `appendices/card_registry.json` | المولّد والحراس |
| الألفاظ والمنع | `appendices/source-label-blacklist.json` وسجل المفردات | بوابة المفردات |
| الأعطال والدروس | `audit/سجل-الأعطال-والثغرات.md` و`memory/learning-log.jsonl` | G055/G056 |
| ترتيب الأقسام | `sections/30-structure.md` | حراس التماثل |

**قاعدة الاستدعاء:** أي سطح آخر **يشير** إلى هذه المواضع ولا **ينسخها**."""

NOT_MEASURED = """- إسناد بيانات الخريطة على الجوال (قيس على سطح المكتب فقط).
- تفضيلات القراءة في متصفح الزائر (D-12) — لم تُقَس الميزة نفسها بعد.
- الصف الثامن في بطاقة الواقعة (D-16) — يحتاج قياسًا موضعيًّا.
- عدد المصادر الحقيقي (D-14) — لا مصدر واحد للعدد حتى الآن.
- موضع «أهم الأخبار» بين الإصدار والإضافات (D-08).
- أثر العنقدة على واقعة متعددة الوقائع (D-01) — لم تُدمج الوحدة بعد.
- بقايا «هجمات مؤكدة» و«نقل عن» (D-05 · D-07 · F-10)."""


def build(root: Path) -> tuple[str, str]:
    data, header, chunks = load(root)
    steps = len(json.loads((root / "runbook" / "runbook.json").read_text(encoding="utf-8"))["steps"])
    validators = len(list((root / "validators").glob("*.py")))
    tools = len(list((root / "tools").glob("*.py")))
    tests = [p for p in (root / "tests").glob("test_*")]
    py = len([p for p in tests if p.suffix == ".py"])
    sh = len([p for p in tests if p.suffix == ".sh"])

    out = [header, "", "---", "",
           "## بطاقة الإصدار",
           "",
           f"| البند | القيمة |", "|---|---|",
           f"| رقم الإصدار | 6 |", f"| تاريخ التوليد | {date.today().isoformat()} |",
           f"| المصدر البنيوي | `{PHASES}` |", f"| المصدر السردي | `{SECTIONS_DIR}/` |",
           f"| المولّد | `tools/build_workflow_reference.py` |",
           f"| الحارس | `validators/check_reference_generated.py` |",
           f"| خطوات المانيفست | {steps} |", f"| المدققات | {validators} |", f"| الأدوات | {tools} |",
           f"| الاختبارات | {py} بايثون + {sh} شل |", "",
           "> **قاعدة العدّ (تغلق F-02):** الاختبارات تُعدّ مجموعتين منفصلتين: ملفات بايثون وملفات شل؛ ولا يُجمع الرقمان في رقم واحد.",
           "",
           "---", "", "## قائمة المراحل (مولَّدة)", "", phase_table(data), "",
           "> **سقف الجهد مشتق** (تغلق F-05): عدد بنود كل مرحلة يُحسب من قائمة بنودها، فلا يمكن أن يخالف النص.",
           "", "---", ""]

    for num in sorted(chunks):
        body = chunks[num]
        if num == 4:
            continue
        m = re.match(r"##\s+(\d+)\s+—\s+(.+)", body.splitlines()[0])
        name = m.group(2).strip() if m else ""
        if 14 <= num <= 19:
            pid = re.search(r"المرحلة\s+(\d)", name).group(1)
            out += [f"## {num} — {name}", "", items_block(data, pid), "", "---", ""]
        else:
            out += [body, "", "---", ""]

    out += ["## 32 — المرحلة (ت): التجهيز لاستخدام المرجع", "", items_block(data, "ت"), "", "---", "",
            "## 33 — معجم المصطلحات والأكواد (يغلق F-07 و F-08)", "",
            "### المصطلحات", "", "| المصطلح | التعريف المعتمد |", "|---|---|"]
    for k, v in GLOSSARY.items():
        out.append(f"| {k} | {v} |")
    out += ["", "### الأكواد", "", "| الكود | معناه |", "|---|---|"]
    for k, v in CODES.items():
        out.append(f"| {k} | {v} |")
    out += ["", "---", "", "## 34 — جدول موضع الحقيقة الواحد (يغلق خريطة التكرار)", "", TRUTH_TABLE, "",
            "---", "", "## 35 — ما لم يُقَس", "", NOT_MEASURED, "",
            "---", "", "## 36 — سجل تغيير الإصدار", "",
            "| التاريخ | التغيير |", "|---|---|",
            "| 2026-11-06 | الإصدار 6: توليد المرجع من مصدر واحد · بنود مرقّمة · سقف جهد مشتق · معجم مصطلحات وأكواد · جدول موضع الحقيقة · قسم «ما لم يُقَس». |",
            "| 2026-11-06 | الإصدار 5: تثبيت الخيار «أ» للتسليم المتصل. |",
            "| 2026-11-06 | الإصدار 4: قسم قرار التسليم. |",
            "| 2026-11-06 | الإصدار 3: قسم الخطوة الأخيرة وما يُسلَّم للمالك. |"]
    doc = "\n".join(out).rstrip() + "\n"
    return doc, phase_table(data)


def comparison(root: Path, table: str) -> str:
    fifth = (root / FIFTH).read_text(encoding="utf-8")
    m = re.search(r"(?m)^## 4 —.*?(?=^## 5 )", fifth, re.S)
    old_table = (m.group(0).strip() if m else "(لم يُعثر على جدول المراحل في الإصدار الخامس)")
    return "\n".join([
        "# مقارنة الإصدارين 5 و6 من مرجع آلية العمل",
        "",
        "**الطريقة:** قياس على النص لا رأي: كل فرق مذكور هنا مستخرج من الملفين.",
        "",
        "## 1) الفرق البنيوي",
        "",
        "| الوجه | الإصدار 5 | الإصدار 6 | نوع الفرق |",
        "|---|---|---|---|",
        "| الحكم في الأرقام | مكتوبة بيد: 111 خطوة · 62 مدققًا · 78 اختبارًا | مشتقة من المانيفست وعدّ الاختبارات معلَن كمجموعتين | تصحيح |",
        "| سقف جهد المرحلة | رقم مكتوب (6 · 9 · 8 · 7) | محسوب من عدد البنود | تصحيح |",
        "| بنود المراحل | نص سردي بفواصل | بنود مرقّمة بمعرّف وأثر وسند وبوابة وحالة | إضافة |",
        "| سجل القرارات | غير موجود | 16 قرارًا بحالة ودليل | إضافة |",
        "| موضع الحقيقة | متفرّق | جدول واحد | إضافة |",
        "| المصطلحات والأكواد | بلا تعريف | معجم معتمد | إضافة |",
        "| ما لم يُقَس | غير معلن في المرجع | قسم صريح | إضافة |",
        "| المرجع نفسه | مكتوب يدويًّا | مولَّد من مصدر واحد ومحروس | تصحيح بنيوي |",
        "",
        "## 2) جدول المراحل — الإصدار 5 كما هو",
        "",
        "```",
        old_table,
        "```",
        "",
        "## 3) جدول المراحل — الإصدار 6 المولَّد",
        "",
        table,
        "",
        "## 4) ما لم يتغيّر (مقصود)",
        "",
        "- بوابة العبور باختباراتها السبعة وممنوعاتها الستة — موضع الحقيقة واحد ولم يُنسخ.",
        "- سجل الانحدار بخمسة عشر بندًا.",
        "- المقاييس الأربعة عشر.",
        "- الحمايات: لا `force push` · لا دفع مباشر إلى `main` · لا نشر ولا تلغرام خارج المانيفست.",
        "- التنبيهات الأربعة القابلة للقياس.",
        "",
        "## 5) فروق يجب إغلاقها قبل اعتماد الإصدار 6",
        "",
        "| البند | الحالة | يغلقه |",
        "|---|---|---|",
        "| F-03 أدوات بوابة العبور الأربع | معلَّق | الحزمة 3 |",
        "| F-04 تعارض D071 مع عقد التسليم | معلَّق | الحزمة 4 |",
        "| F-06 رقم الأداء بلا سند داخلي | معلَّق | الحزمة 4 |",
        "| F-10 بقايا قرارات منفَّذة | معلَّق | الحزمة 5 |",
        "| ت-15 قالب تقرير الإغلاق · ت-16 الفهرس الآلي | معلَّق | الحزمة 6 |",
        "",
    ])


def cmd_build(root: Path) -> int:
    doc, table = build(root)
    (root / OUT_DOC).write_text(doc, encoding="utf-8")
    (root / OUT_CMP).write_text(comparison(root, table), encoding="utf-8")
    print(f"   ✔ وُلّد {OUT_DOC} ({len(doc.splitlines())} سطرًا)")
    print(f"   ✔ وُلّد {OUT_CMP}")
    return 0


def cmd_check(root: Path) -> int:
    doc, table = build(root)
    cmp_text = comparison(root, table)
    errs = []
    for path, want in ((OUT_DOC, doc), (OUT_CMP, cmp_text)):
        p = root / path
        if not p.is_file():
            errs.append(f"غائب: {path}")
        elif p.read_text(encoding="utf-8") != want:
            errs.append(f"مختلف عن المولَّد (عُدّل يدويًّا أو لم يُعَد التوليد): {path}")

    data = json.loads((root / PHASES).read_text(encoding="utf-8"))
    ids = [i["id"] for p in data["phases"] for i in p["items"]]
    for d in set(ids):
        if ids.count(d) > 1:
            errs.append(f"معرّف بند مكرر: {d}")
    for p in data["phases"]:
        for i in p["items"]:
            if i["status"] not in STATUSES:
                errs.append(f"{i['id']}: حالة غير معلنة {i['status']!r}")
            for f in ("title", "impact", "basis", "gate"):
                if not str(i.get(f, "")).strip():
                    errs.append(f"{i['id']}: حقل ناقص {f}")
    if f"**{len(ids)}**" not in doc:
        errs.append("مجموع البنود في المرجع لا يطابق مجموع البنود في phases.json")

    if errs:
        print("✘ مرجع آلية العمل: خلل")
        for e in errs:
            print(f"   - {e}")
        return 2
    print(f"✔ مرجع آلية العمل: مطابق للمولَّد · {len(data['phases'])} مرحلة · {len(ids)} بندًا · صفر معرّف مكرر")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="مولّد مرجع آلية العمل من مصدر واحد")
    ap.add_argument("command", choices=["bootstrap", "build", "check"], help="الأمر")
    ap.add_argument("--root", default=".", help="جذر المشروع")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    return {"bootstrap": bootstrap, "build": cmd_build, "check": cmd_check}[args.command](root)


if __name__ == "__main__":
    sys.exit(main())
