#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص سياسة عرض رموز الأحداث (2+5) على صفحات الموقع المبنية.

القاعدة الملزمة:
- الرمز الكامل `MN-YYYY-MM-DD-NN` يظهر **فقط** داخل قسم الوقائع (عنوانه يبدأ بـ«الوقائع»).
- أي ظهور كامل خارج ذلك القسم = مخالفة مانعة.
- الرمز المختصر (`DD-NN` أو `MM-DD-NN`) هو الصيغة المعروضة في بقية المواضع،
  ويُدمج مع رقم البلاغ الرسمي (`#172 · 15-04`) عند وجوده.

الاستخدام: python3 validators/check_code_policy.py [مجلد الموقع أو ملف]
"""
import re
import sys
from pathlib import Path

CODE_RE = re.compile(r"MN-\d{4}-\d{2}-\d{2}-\d{2}")
SECTION_RE = re.compile(r"<section\b[^>]*>(.*?)</section>", re.S)
H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
TAGS_RE = re.compile(r"<[^>]+>")


def section_title(html):
    m = H2_RE.search(html)
    return TAGS_RE.sub("", m.group(1)).strip() if m else ""


def check_file(path: Path):
    html = path.read_text(encoding="utf-8", errors="ignore")
    sections = SECTION_RE.findall(html)
    inside = outside = 0
    outside_samples = []
    for sec in sections:
        title = section_title(sec)
        n = len(CODE_RE.findall(sec))
        if not n:
            continue
        if title.startswith("الوقائع"):
            inside += n
        else:
            outside += n
            ctx = TAGS_RE.sub(" ", sec)
            m = CODE_RE.search(ctx)
            outside_samples.append(f"{title}: {ctx[max(0, m.start() - 50):m.end() + 30].strip()[-90:]}")
    # ما قبل أول قسم (الترويسة والمقدمة) وبعده
    head = html.split("<main", 1)[0]
    tail = html.rsplit("</main>", 1)[-1]
    pre = len(CODE_RE.findall(head)) + len(CODE_RE.findall(tail))
    merged = re.findall(r"#\d{2,4}\s*·\s*\d{2}-\d{2}", html)
    return {"file": path.name, "inside": inside, "outside": outside, "pre": pre,
            "merged": len(merged), "samples": outside_samples}


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/ubuntu/seawatch/dist")
    files = sorted(target.glob("reports/*.html")) if target.is_dir() else [target]
    fails = 0
    print("  فحص سياسة عرض الرموز (2+5):")
    for f in files:
        r = check_file(f)
        bad = r["outside"] + r["pre"]
        mark = "✔" if bad == 0 else "✘"
        if bad:
            fails += 1
        print(f"   {mark} {r['file']}: كامل داخل الوقائع {r['inside']} · خارجها {r['outside']} · "
              f"في الترويسة/المقدمة {r['pre']} · مدموج برقم بلاغ {r['merged']}")
        for s in r["samples"][:3]:
            print(f"      - {s}")
    print(f"  النتيجة: {'اجتاز الفحص' if fails == 0 else f'{fails} صفحة مخالفة'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
