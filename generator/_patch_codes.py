#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تطبيق سياسة عرض رموز الأحداث (2 + 5) على مولّد الموقع وتعليمات العقل."""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
SITE = _Path(_os.environ.get("SITE_DIR") or _ROOT)

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
BRAIN = _tree("BRAIN_DIR", _ROOT, "brain-marine-news", "brain")
from pathlib import Path

GEN = Path(f"{SITE}/generator")
BRAIN = Path(f"{BRAIN}")
done, missed = [], []


def patch(path, pairs, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        if b in s:
            continue
        if a in s:
            s = s.replace(a, b, 1)
            done.append(f"{label}: {a[:46]}")
        else:
            missed.append(f"{label}: {a[:46]}")
    p.write_text(s, encoding="utf-8")


# ---------------------------------------------------------------- blocks.py
patch(GEN / "blocks.py", [
    ("import html\nimport re\n",
     "import html\nimport re\n\nfrom codes import label as _code_label, demote as _demote  # سياسة عرض الرموز (2+5)\n\n"
     "_CODE_CTX = {\"date\": None, \"official\": {}}\n\n\n"
     "def set_code_context(report_date=None, official=None):\n"
     "    \"\"\"يضبط سياق عرض الرموز: تاريخ الإصدار وخريطة الأرقام الرسمية.\"\"\"\n"
     "    _CODE_CTX[\"date\"] = report_date\n"
     "    _CODE_CTX[\"official\"] = official or {}\n\n\n"
     "def code_label(code, ref=\"\", note=\"\"):\n"
     "    \"\"\"صيغة العرض: مختصرة، ومدموجة برقم البلاغ الرسمي عند وجوده.\"\"\"\n"
     "    off = _CODE_CTX[\"official\"].get(str(code or \"\"), \"\")\n"
     "    return _code_label(code, ref, note or off, _CODE_CTX[\"date\"])\n"),
    ("            meta_bits.append(f'<bdi class=\"bidi ev-code\">{esc(code)}</bdi>')",
     "            meta_bits.append(f'<bdi class=\"bidi ev-code\">{esc(code_label(code, ref))}</bdi>')"),
    ("            Raw(f'<bdi class=\"bidi ev-code\">{esc(it.get(\"code\", \"\"))}</bdi>'),",
     "            Raw(f'<bdi class=\"bidi ev-code\">{esc(code_label(it.get(\"code\", \"\"), it.get(\"ref\", \"\"), it.get(\"note\", \"\")))}</bdi>'),"),
    ("'<h3>تتبع الوقائع</h3><p class=\"blk-lede\">الرمز الثابت · المنطقة · الحالة.</p>'\n        + _table([\"الرمز الثابت\", \"الحدث\", \"المنطقة\", \"الحالة\", \"ملاحظة\"], rows, inline)",
     "'<h3>تتبع الوقائع</h3><p class=\"blk-lede\">الرمز المختصر (والكامل في «الوقائع الجديدة») · المنطقة · الحالة.</p>'\n        + _table([\"الرمز\", \"الحدث\", \"المنطقة\", \"الحالة\", \"ملاحظة\"], rows, inline)"),
], "blocks.py")

# -------------------------------------------------------------- map_gulf.py
patch(GEN / "map_gulf.py", [
    ("import json\nimport math\n",
     "import json\nimport math\n\nfrom codes import short_code  # عرض مختصر لرموز الوقائع على الخريطة\n\nREPORT_DATE = None\n"),
    ("            bits.append(f'<bdi class=\"bidi ev-code\">{code}</bdi>')",
     "            bits.append(f'<bdi class=\"bidi ev-code\">{short_code(code, REPORT_DATE)}</bdi>')"),
], "map_gulf.py")

# ----------------------------------------------------------- build_report.py
patch(GEN / "build_report.py", [
    ("import blocks as BLK", "import blocks as BLK\nimport codes"),
    ("    validate_meta(meta)\n",
     "    validate_meta(meta)\n"
     "    # سياسة عرض الرموز (2+5): كامل مرة واحدة في «الوقائع الجديدة»، ومختصر مدموج برقم البلاغ الرسمي في بقية المواضع\n"
     "    _mdate = re.search(r\"(\\d{4}-\\d{2}-\\d{2})\", md_path.name)\n"
     "    report_date = _mdate.group(1) if _mdate else \"\"\n"
     "    official = codes.official_map(meta)\n"
     "    BLK.set_code_context(report_date, official)\n"
     "    try:\n"
     "        import map_gulf as _mg\n"
     "        _mg.REPORT_DATE = report_date\n"
     "    except Exception:\n"
     "        pass\n"),
    ("        section_html = render_section_body(t, sec[\"lines\"], defs)\n",
     "        section_html = render_section_body(t, sec[\"lines\"], defs)\n"
     "        if codes.PRIMARY_SECTION not in t:\n"
     "            section_html = codes.demote(section_html, report_date, official)\n"),
], "build_report.py")

# ------------------------------------------------------------ تعليمات العقل
patch(BRAIN / "sections/40-blocks.md", [
    ("- الرمز المرجعي الثابت لكل حدث `MN-YYYY-MM-DD-NN` يُذكر في النص كما هو، ويأتي رقم المصدر بعده كمرجع ثانوي.",
     "- الرمز المرجعي الثابت لكل حدث `MN-YYYY-MM-DD-NN` يُذكر **كاملًا مرة واحدة** في «الوقائع الجديدة»، ويُعرض مختصرًا في بقية المواضع وفق سياسة العرض أدناه."),
    ("2. كل حدث يحمل رمزًا ثابتًا بالصيغة `MN-YYYY-MM-DD-NN` في النص والخريطة وتتبع الوقائع.",
     "2. كل حدث يحمل رمزًا ثابتًا بالصيغة `MN-YYYY-MM-DD-NN`: كاملًا في «الوقائع الجديدة»، ومختصرًا في الخريطة وتتبع الوقائع وبقية الأقسام."),
], "sections/40-blocks.md")

# إضافة سياسة العرض الرسمية
POLICY = """

---

## سياسة عرض رموز الأحداث (معتمدة 15 أكتوبر 2026 — الخيار 2 + 5)

**الغرض:** تقليل تكرار الرموز على القارئ مع الحفاظ على ثبات المرجع داخليًا.

| الموضع | صيغة العرض |
|---|---|
| «الوقائع الجديدة» (نص كل واقعة) | الرمز الكامل `MN-YYYY-MM-DD-NN` — مرة واحدة لكل واقعة |
| بطاقة «ما تغيّر» · جدول «تتبع الوقائع» · الخريطة التشغيلية · بقية الأقسام | مختصر `DD-NN` لواقعة الشهر نفسه، و`MM-DD-NN` لواقعة شهر آخر |
| عند وجود رقم بلاغ رسمي (UKMTO أو ما يماثله) | يُدمج قبل المختصر: `#172 · 15-04` |

**قواعد ملزمة:**
1. الرمز الداخلي لا يتغير: يبقى كاملًا في ملف الواجهة والدفتر التراكمي وخريطة الرموز.
2. لا يُكتب رمز كامل في أي قسم غير «الوقائع الجديدة».
3. لا يُخترع رقم بلاغ رسمي: الدمج يقع فقط عند وجود رقم في مصدر رسمي.
4. التطبيق آلي في المولّد عبر `generator/codes.py`؛ لا يُعدَّل الناتج يدويًا.
"""
for rel in ("sections/40-blocks.md", "appendices/report-blocks.md"):
    p = BRAIN / rel
    s = p.read_text(encoding="utf-8")
    if "سياسة عرض رموز الأحداث" not in s:
        p.write_text(s.rstrip() + POLICY, encoding="utf-8")
        done.append(f"{rel}: سياسة العرض")

patch(BRAIN / "appendices/report-blocks.md", [
    ("صيغة الرمز: `MN-YYYY-MM-DD-NN` بحسب تاريخ أول رصد ورقم تسلسلي داخل اليوم.",
     "صيغة الرمز: `MN-YYYY-MM-DD-NN` بحسب تاريخ أول رصد ورقم تسلسلي داخل اليوم. ويُعرض كاملًا مرة واحدة في «الوقائع الجديدة» ومختصرًا في بقية المواضع وفق سياسة عرض الرموز أدناه."),
], "appendices/report-blocks.md")

print("  · مطبَّق:", len(done))
for d in done:
    print("     ✔", d)
if missed:
    print("  · لم يُطابق:", len(missed))
    for m in missed:
        print("     ✘", m)
