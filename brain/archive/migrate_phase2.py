#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
المرحلة الثانية: نقل قواعد المهارتين الفريدة إلى الأقسام والملاحق بلا فقدان.

المبدأ: لا تُحذف قاعدة من مهارة قبل أن تستقر في قسمها الواحد أو ملحقها.
كل كتلة تُنقل نصًّا كما هي، ويُوسم موضع النقل بترويسة تحفظ أصلها.

الاستخدام: python3 tools/migrate_phase2.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SK = Path("/home/ubuntu/skills")
MARINE = SK / "marine-news-brain"
MIL = SK / "military-arabic-editing"
TODAY = "2026-10-12"


def blocks_of(text):
    """يقسم نص المهارة إلى كتل بحسب عناوين المستوى الثاني."""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if cur:
                out[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1), []
        elif cur is not None:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


def next_index(path, prefix):
    """يحسب الرقم التالي للقواعد في ملف قسم."""
    pat = re.compile(r"^##\s+" + re.escape(prefix) + r"(\d+)\s+—", re.M)
    nums = [int(m.group(1)) for m in pat.finditer(path.read_text(encoding="utf-8"))]
    return (max(nums) + 1) if nums else 1


def append_rule(section_file, prefix, title, body, origin):
    p = ROOT / "sections" / section_file
    n = next_index(p, prefix)
    text = p.read_text(encoding="utf-8").rstrip()
    text += (f"\n\n## {prefix}{n} — {title}\n\n"
             f"> منقول من {origin} في المرحلة الثانية ({TODAY}) — نص أصلي بلا تغيير.\n\n"
             f"{body.strip()}\n")
    p.write_text(text, encoding="utf-8")
    return f"{prefix}{n}"


def append_appendix(name, title, body, ref_from):
    p = ROOT / "appendices" / name
    head = (f"# ملحق — {title}\n\n**الغرض:** تفصيل مرجعي طويل يُستدعى من `{ref_from}`.\n"
            f"**يُقرأ مع:** `{ref_from}`.\n**آخر تعديل:** {TODAY}\n\n---\n\n")
    p.write_text(head + body.strip() + "\n", encoding="utf-8")
    return p


def append_to_appendix(name, title, body, origin):
    p = ROOT / "appendices" / name
    text = p.read_text(encoding="utf-8").rstrip()
    text += (f"\n\n---\n\n## {title}\n\n"
             f"> منقول من {origin} في المرحلة الثانية ({TODAY}) — نص أصلي بلا تغيير.\n\n"
             f"{body.strip()}\n")
    p.write_text(text, encoding="utf-8")
    return p


def main():
    log = []

    # ---- مهارة Marine News Brain ----
    m = blocks_of((MARINE / "SKILL.md").read_text(encoding="utf-8"))
    for name, body in m.items():
        if name.startswith("ترتيب التنفيذ"):
            log.append(("أ4", append_rule("90-automation.md", "أ", "سلسلة التنفيذ المفصّلة",
                                          body, "مهارة marine-news-brain")))
        elif name.startswith("قواعد حاكمة"):
            log.append(("ت5", append_rule("50-analysis.md", "ت", "قواعد حاكمة للتحليل والصياغة",
                                          body, "مهارة marine-news-brain")))
        elif name.startswith("كتل التقرير"):
            log.append(("ك2", append_rule("40-blocks.md", "ك", "كتل التقرير المعتمدة وضوابطها",
                                          body, "مهارة marine-news-brain")))

    sp = (MARINE / "references" / "source-policy.md").read_text(encoding="utf-8")
    sp = re.sub(r"^#\s+.+?\n", "", sp, count=1)
    sp = re.sub(r"^## طرق الوصول المؤكدة.*$", "", sp, flags=re.S).strip()  # منقول سابقًا في ص2
    log.append(("ص4", append_rule("10-sources.md", "ص", "سياسة المصادر التفصيلية",
                                  sp, "مرجع سياسة المصادر في المهارة")))

    va = (MARINE / "references" / "validation.md").read_text(encoding="utf-8")
    va = re.sub(r"^#\s+.+?\n", "", va, count=1).strip()
    log.append(("ف4", append_rule("60-validation.md", "ف", "قائمة فحوص التحقق الكاملة",
                                  va, "مرجع التحقق في المهارة")))

    ad = (MARINE / "references" / "adaptive-learning.md").read_text(encoding="utf-8")
    ad = re.sub(r"^#\s+.+?\n", "", ad, count=1).strip()
    log.append(("ع6", append_rule("80-learning.md", "ع", "دورة التعلم التشغيلية",
                                  ad, "مرجع التعلم في المهارة")))

    # ---- مهارة التدقيق العربي العسكري ----
    mi = blocks_of((MIL / "SKILL.md").read_text(encoding="utf-8"))
    for name, body in mi.items():
        if name.startswith("منهج التدقيق"):
            log.append(("ل2", append_rule("20-language.md", "ل", "منهج التدقيق العربي العسكري",
                                          body, "مهارة military-arabic-editing")))
        elif name.startswith("قواعد دلالية"):
            log.append(("ت6", append_rule("50-analysis.md", "ت", "قواعد دلالية للصياغة",
                                          body, "مهارة military-arabic-editing")))
        elif name.startswith("معايير الوسم"):
            log.append(("ك3", append_rule("40-blocks.md", "ك", "معايير الوسم ودرجة الثقة",
                                          body, "مهارة military-arabic-editing")))

    cs = (MIL / "references" / "commander-style.md").read_text(encoding="utf-8")
    cs = re.sub(r"^#\s+.+?\n", "", cs, count=1).strip()
    append_appendix("commander-style.md", "أسلوب القائد والملخص التنفيذي", cs, "sections/20-language.md")
    log.append(("ملحق", "appendices/commander-style.md"))

    tm = (MIL / "references" / "terminology-map.md").read_text(encoding="utf-8")
    tm = re.sub(r"^#\s+.+?\n", "", tm, count=1).strip()
    append_to_appendix("terminology.md", "خريطة الاستبدالات العسكرية",
                       tm, "مرجع خريطة الاستبدالات في مهارة التدقيق")
    log.append(("ملحق", "appendices/terminology.md (مُوسَّع)"))

    # مرجع الأسلوب يُضاف إلى قسم اللغة
    p = ROOT / "sections" / "20-language.md"
    t = p.read_text(encoding="utf-8")
    t = t.replace("**مراجع تفصيلية:** appendices/terminology.md",
                  "**مراجع تفصيلية:** appendices/terminology.md · appendices/commander-style.md")
    p.write_text(t, encoding="utf-8")

    print("نُقلت القواعد التالية:")
    for k, v in log:
        print(f"  {k:<6} ← {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())