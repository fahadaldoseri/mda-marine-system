#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
المرحلة الأولى من تنظيم التعليمات: إنشاء INDEX.md و sections/ و appendices/.

المبادئ:
- لا يُحذف محتوى: كل ملف قديم له موضع جديد، ونسخة كاملة منه تُحفظ في brain/_legacy/ للتراجع.
- ملفات brain/*.md تتحول إلى ملفات إشارة قصيرة توجّه إلى المرجع الجديد، فلا تبقى قاعدة قديمة سارية.
- sections/ هي المرجع الملزم الوحيد، وappendices/ للتفاصيل الطويلة.

الاستخدام: python3 tools/migrate_phase1.py
"""

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAIN = ROOT / "brain"
SECTIONS = ROOT / "sections"
APPENDICES = ROOT / "appendices"
LEGACY = BRAIN / "_legacy"

TODAY = "2026-10-12"

# خريطة الانتقال: الملف القديم ← الملف الجديد
MAP = {
    "mission.md": "sections/00-identity.md",
    "approved-sources-37.md": "sections/10-sources.md",
    "daily-report-sections.md": "sections/30-structure.md",
    "validation-rules.md": "sections/60-validation.md",
    "adaptive-learning.md": "sections/80-learning.md",
    "terminology.md": "appendices/terminology.md",
    "report-blocks.md": "appendices/report-blocks.md",
    "web-delivery.md": "appendices/web-delivery.md",
    "historical-baseline.md": "appendices/historical-baseline.md",
}

# أقسام تُبنى بتجميع كتل من operating-rules.md
OPERATING_SPLIT = {
    "المصادر": "10-sources",
    "التحرير العسكري واللغوي": "20-language",
    "كتل التقرير وقواعد الصياغة": "40-blocks",
    "الزمن": "50-analysis",
    "المؤشرات": "50-analysis",
    "التحليل": "50-analysis",
    "الاتساق": "50-analysis",
    "الإخراج والتسليم": "70-delivery",
    "التصنيف": "70-delivery",
    "التعلم والتطوير التكيفي": "80-learning",
}

PREFIX = {"00-identity": "هـ", "10-sources": "ص", "20-language": "ل", "30-structure": "ب",
          "40-blocks": "ك", "50-analysis": "ت", "60-validation": "ف", "70-delivery": "س",
          "80-learning": "ع", "90-automation": "أ"}


def match_key(heading, key):
    """يطابق عنوان الكتلة مع القسم المقصود، بالاسم الدقيق أو بالبداية."""
    for h, k in OPERATING_SPLIT.items():
        if k == key and (heading == h or heading.startswith(h)):
            return True
    return False


def pick(blocks, want):
    """يختار الكتلة المطابقة بالاسم الدقيق أو بالبداية (لعناوين تحمل تاريخًا)."""
    for h, b in blocks.items():
        if h == want or h.startswith(want):
            return h, b
    return None, None


def split_blocks(text):
    """يقسم نص قواعد التشغيل إلى كتل بحسب عناوين المستوى الثاني."""
    blocks, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if cur:
                blocks[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1), []
        elif cur:
            buf.append(line)
    if cur:
        blocks[cur] = "\n".join(buf).strip()
    return blocks


def number_headings(body, prefix):
    """يحوّل عناوين المستوى الثاني إلى قواعد مرقّمة يمكن الإشارة إليها."""
    out, n = [], 0
    for line in body.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            n += 1
            out.append(f"## {prefix}{n} — {m.group(1)}")
        else:
            out.append(line)
    return "\n".join(out).strip(), n


def header(key, title, purpose, reads_with, forbidden, refs, source):
    lines = [f"# {key} — {title}", "",
             f"**الغرض:** {purpose}",
             f"**يُقرأ مع:** {reads_with}"]
    if forbidden:
        lines.append(f"**ممنوعات:** {forbidden}")
    if refs:
        lines.append(f"**مراجع تفصيلية:** {refs}")
    lines += [f"**آخر تعديل:** {TODAY} · **المصدر:** {source}", "", "---", ""]
    return "\n".join(lines)


SPECS = {
    "00-identity": ("الهوية والمهمة والمخرج",
                    "يحدد لماذا يوجد التقرير وما مخرجه ومن يقرأه، فلا يُغيَّر بلا قرار.",
                    "INDEX.md ثم كل الأقسام",
                    "لا يُضاف نطاق جديد بلا اعتماد المدير.",
                    "لا شيء",
                    "من brain/mission.md"),
    "10-sources": ("المصادر وطرق الوصول",
                   "سجل المصادر السبعة والثلاثين وطرق الوصول المؤكدة وقاعدة الاستقلالية.",
                   "20-language (لنقل البيان)، 50-analysis (للإسناد)",
                   "لا يُخترع محتوى، ولا يُسجَّل تعذر وصول قبل تجربة المسار البديل.",
                   "appendices/historical-baseline.md",
                   "من brain/approved-sources-37.md وكتلة المصادر في operating-rules"),
    "20-language": ("اللغة والمصطلحات",
                    "تحدد اللغة المعتمدة وطبقات الصياغة والاستبدالات الإلزامية.",
                    "10-sources (لصيغة النقل)، 30-structure و40-blocks (لصياغة العناوين والكتل)",
                    "لا عبارات داخلية، ولا أسماء حقول برمجية، ولا كلمات نظام في المتن.",
                    "appendices/terminology.md",
                    "من كتلة التحرير العسكري واللغوي في operating-rules وterminology.md"),
    "30-structure": ("أقسام التقرير وترتيبها",
                     "يحدد أقسام التقرير وترتيبها واهتمام كل قسم.",
                     "40-blocks (لكتل كل قسم)، 90-automation (لتسلسل التنفيذ)",
                     "لا قسم بلا بيانات؛ ويُحذف أو يُدمج عند غياب المحتوى.",
                     "لا شيء",
                     "من brain/daily-report-sections.md"),
    "40-blocks": ("كتل العرض وقواعد الصياغة",
                  "يحدد كتل الصفحة الثابتة وبنية كل بند وعلامات الصياغة وكثافة المعلومات.",
                  "30-structure (لترتيب الأقسام)، 20-language (للصياغة)",
                  "لا كتلة بلا بيانات، ولا رمز حدث بلا صيغة MN-YYYY-MM-DD-NN.",
                  "appendices/report-blocks.md",
                  "من كتلة كتل التقرير في operating-rules وreport-blocks.md"),
    "50-analysis": ("التحليل والمؤشرات والزمن",
                    "يحدد نافذة الزمن، وفصل الحقيقة عن التقدير، والمؤشرات، ودرجة الثقة، والاتساق.",
                    "10-sources (للإسناد)، 60-validation (للفحص قبل التسليم)",
                    "لا يُساوى بين عدد البلاغات وعدد الهجمات، ولا تُبنى مقارنة بين مؤشرين مختلفي التعريف.",
                    "لا شيء",
                    "من كتل الزمن والمؤشرات والتحليل والاتساق في operating-rules"),
    "60-validation": ("بوابة التحقق",
                      "قواعد الرفض قبل التسليم، بما فيها بوابة بساطة اللغة الآلية.",
                      "50-analysis، وvalidators/ المنفّذة لها",
                      "لا تسليم بلا اجتياز البوابة؛ والفشل يُصلح لا يُتجاوَز.",
                      "validators/check_language.py وvalidators/validate_report.py",
                      "من brain/validation-rules.md"),
    "70-delivery": ("التسليم والنشر والتصنيف",
                    "يحدد صيغ التسليم وقنواته وحاجز التصنيف وضوابط الموقع الدائم.",
                    "40-blocks (لكتل الصفحة)، 60-validation (للإذن بالتسليم)",
                    "لا يُنشر إصدار مقيّد أو حساس، ولا يُسلَّم رابط مؤقت بعد اعتماد الموقع الدائم.",
                    "appendices/web-delivery.md",
                    "من كتلتي الإخراج والتسليم والتصنيف في operating-rules وweb-delivery.md"),
    "80-learning": ("التعلم التكيفي",
                    "دورة التعلم في كل تشغيل، ومستويات التغيير، وقواعد الحماية من الانحراف.",
                    "كل الأقسام (لأن الدرس يُرقّى إلى قاعدة في القسم المناسب)",
                    "لا يُعدَّل قسم بلا درس مسجّل وسبب موثّق.",
                    "memory/learning-log.jsonl",
                    "من brain/adaptive-learning.md وكتلة التعلم في operating-rules"),
    "90-automation": ("سلسلة التشغيل اليومي",
                      "الترتيب الملزم لتنفيذ التقرير الصباحي من جمع المصادر حتى النشر.",
                      "كل الأقسام، وINDEX.md قبل البدء",
                      "لا يُنشر تقرير لم يجتز بوابة 60-validation.",
                      "web/publish_report.sh وgenerator/sync_from_brain.py",
                      "من تفاصيل المهمة المجدولة وأدوات التشغيل"),
}

AUTOMATION_BODY = """## الترتيب الملزم للتشغيل الصباحي

1. اقرأ `INDEX.md` ثم الأقسام المطلوبة في هذه السلسلة.
2. افحص المصادر السبعة والثلاثين حسب طرق الوصول في 10-sources، وسجّل لكل مصدر حالته.
3. ابنِ التقرير وفق 30-structure، واملأ كتل 40-blocks من المصادر فقط.
4. طبّق 50-analysis: افصل الحقيقة عن التقدير، واذكر درجة الثقة، وراجع الاتساق.
5. مرّر 60-validation: بوابة اللغة آليًا، ومراجعة المصطلحات، وحاجز التصنيف.
6. سلّم وفق 70-delivery: نص داخل المحادثة، ورابط الموقع الدائم، وPDF عند الطلب فقط.
7. أضف وقائع اليوم إلى الدفتر التراكمي، وأعد توليد اللوحة الشهرية.
8. سجّل أي تصحيح في `memory/learning-log.jsonl` عبر `memory/record_learning.py`.

## أوامر التنفيذ المعتمدة

```bash
# بناء صفحة التقرير
python3 web/build_report.py --md reports/<التاريخ>-sectioned.md --meta web/meta/<التاريخ>.json --out web/out/
# فحص المصادر واللغة قبل التسليم
python3 validators/check_sources_37_browser.py
python3 validators/check_language.py reports/<التاريخ>-sectioned.md
# تحديث الموقع الدائم ونشره
python3 /home/ubuntu/seawatch/generator/sync_from_brain.py --date <التاريخ>
cd /home/ubuntu/seawatch && git add -A && git commit -m "إصدار <التاريخ>" && git fetch origin main && git push origin main
# ثم النشر عبر أداة الاستضافة: webdev.config {"method":"POST","path":"publish","body":{}}
```

## قواعد الأتمتة

- الجدولة اليومية عند 07:00 بتوقيت البحرين، ومراقبة التغذيات للتنبيه الفوري عند تطوّر أمني.
- لا يُعاد نشر تقرير منشور، ويُفحص وجود تقرير اليوم لمنع التكرار.
- عند فشل خطوة، يُسجَّل السبب ويُستأنف من الخطوة التالية دون إسقاط التقرير كله."""


def src(name):
    """يقرأ الأصل من النسخ المحفوظة، ويرجع إلى brain عند غيابها."""
    f = LEGACY / name
    return (f if f.exists() else BRAIN / name)


def main():
    if not BRAIN.exists():
        print("مجلد brain غير موجود")
        return 2
    for d in (SECTIONS, APPENDICES, LEGACY):
        d.mkdir(parents=True, exist_ok=True)

    # 1) نسخ احتياطية كاملة للتراجع
    for f in sorted(BRAIN.glob("*.md")):
        if not (LEGACY / f.name).exists():
            shutil.copy2(f, LEGACY / f.name)
    print(f"نسخ للتراجع: {len(list(LEGACY.glob('*.md')))} ملف في brain/_legacy/")

    op_text = src("operating-rules.md").read_text(encoding="utf-8")
    blocks = split_blocks(op_text)

    # 2) الملاحق: نقل الملفات الطويلة كما هي مع ترويسة ملحق
    for name, dest in MAP.items():
        if not dest.startswith("appendices/"):
            continue
        body = src(name).read_text(encoding="utf-8").strip()
        body = re.sub(r"^#\s+.+?\n", "", body, count=1).strip()
        num = Path(dest).stem
        out = (f"# ملحق — {num}\n\n**الغرض:** تفصيل مرجعي طويل يُستدعى من قسم في `sections/`.\n"
               f"**يُقرأ مع:** القسم المُشير في `sections/`.\n"
               f"**آخر تعديل:** {TODAY}\n\n---\n\n{body}\n")
        (ROOT / dest).write_text(out, encoding="utf-8")

    # 3) الأقسام
    made = {}
    for key, spec in SPECS.items():
        title, purpose, reads, forbidden, refs, source = spec
        head = header(key, title, purpose, reads, forbidden, refs, source)
        body = ""

        if key == "00-identity":
            body = re.sub(r"^#\s+.+?\n", "", src("mission.md").read_text(encoding="utf-8"),
                          count=1).strip()
        elif key == "10-sources":
            body = re.sub(r"^#\s+.+?\n", "",
                          src("approved-sources-37.md").read_text(encoding="utf-8"),
                          count=1).strip()
            picked = []
            for h in blocks:
                if match_key(h, key):
                    picked.append(f"## {h}\n\n{blocks[h]}")
            if picked:
                body += "\n\n" + "\n\n".join(picked)
        elif key == "30-structure":
            body = re.sub(r"^#\s+.+?\n", "",
                          src("daily-report-sections.md").read_text(encoding="utf-8"),
                          count=1).strip()
        elif key == "60-validation":
            body = re.sub(r"^#\s+.+?\n", "",
                          src("validation-rules.md").read_text(encoding="utf-8"),
                          count=1).strip()
        elif key == "80-learning":
            body = re.sub(r"^#\s+.+?\n", "",
                          src("adaptive-learning.md").read_text(encoding="utf-8"),
                          count=1).strip()
            picked = []
            for h in blocks:
                if match_key(h, key):
                    picked.append(f"## {h}\n\n{blocks[h]}")
            if picked:
                body += "\n\n" + "\n\n".join(picked)
        elif key == "90-automation":
            body = AUTOMATION_BODY
        else:
            picked = []
            for h in blocks:
                if match_key(h, key):
                    picked.append(f"## {h}\n\n{blocks[h]}")
            body = "\n\n".join(picked) if picked else ""

        numbered, count = number_headings(body, PREFIX[key])
        text = head + numbered + "\n"
        (SECTIONS / f"{key}.md").write_text(text, encoding="utf-8")
        made[key] = (count, len(text))

    # 4) ملفات brain تتحول إلى إشارات قصيرة
    for name, dest in MAP.items():
        (BRAIN / name).write_text(
            f"# ملف متجاوَز — لا تُكتب فيه قواعد جديدة\n\n"
            f"**المرجع الملزم الآن:** `{dest}`\n\n"
            f"سبب الإشارة: نُقل المحتوى في المرحلة الأولى من تنظيم التعليمات بتاريخ {TODAY}. "
            f"النسخة الكاملة الأصلية محفوظة في `brain/_legacy/{name}` للتراجع فقط.\n",
            encoding="utf-8")
    (BRAIN / "operating-rules.md").write_text(
        f"# ملف متجاوَز — قواعد التشغيل موزّعة الآن على الأقسام\n\n"
        f"**المرجع الملزم الآن:** `INDEX.md` ثم `sections/`\n\n"
        f"توزيع الكتل: المصادر ← sections/10-sources · التحرير اللغوي ← sections/20-language · "
        f"كتل التقرير ← sections/40-blocks · الزمن والمؤشرات والتحليل والاتساق ← sections/50-analysis · "
        f"الإخراج والتصنيف ← sections/70-delivery · التعلم ← sections/80-learning.\n\n"
        f"النسخة الكاملة الأصلية محفوظة في `brain/_legacy/operating-rules.md` للتراجع فقط.\n",
        encoding="utf-8")

    print("الأقسام المنشأة:")
    for k, (n, size) in made.items():
        print(f"  sections/{k}.md — {n} قاعدة · {size} بايت")
    return 0


if __name__ == "__main__":
    sys.exit(main())