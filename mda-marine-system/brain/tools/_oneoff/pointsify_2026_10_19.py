#!/usr/bin/env python3
"""إظهار النقاط المطموسة في تقرير 19 أكتوبر 2026 + إزالة قسم «ما تغيّر» المكرر.
قواعد صارمة: لا تغيير في أي كلمة ولا رقم ولا صياغة — فقط إعادة ترقيم النقاط وتقسيم الفقرة
إلى بنود ظاهرة (نقاط رئيسة ونقاط فرعية). ويُحفظ النص الأصلي كاملًا في نسخة احتياطية.
"""
from __future__ import annotations
import re
from pathlib import Path

B = Path("/home/ubuntu/brain-marine-news")
SRC = B / "reports" / "2026-10-19-sectioned.md"
BAK = B / "reports" / "_backup" / "2026-10-19-sectioned.pre-points.md"
AUD = B / "audit" / "نص-قسم-ما-تغيّر-المكرر-2026-10-19.md"

md = SRC.read_text(encoding="utf-8")
BAK.parent.mkdir(parents=True, exist_ok=True)
BAK.write_text(md, encoding="utf-8")


def section(text: str, title: str) -> tuple[int, int]:
    i = text.find("## " + title)
    if i < 0:
        return -1, -1
    j = text.find("\n## ", i + 3)
    return i, (j if j > 0 else len(text))


def sentences(par: str) -> list[str]:
    """يقسّم فقرة إلى جمل على علامة الوقف النهائية، دون تغيير أي حرف."""
    parts = re.split(r"(?<=\.)\s+(?=[وف]?[\u0621-\u064A«(])", par.strip())
    return [p.strip() for p in parts if p.strip()]


changed = []

# ---------------------------------------------------------------- 1) إزالة القسم المكرر
i, j = section(md, "ما تغيّر منذ التقرير السابق")
dup = md[i:j]
AUD.write_text(
    "# نصّ قسم «ما تغيّر منذ التقرير السابق» المسحوب من المصدر (2026-10-19)\n\n"
    "**السبب:** القسم كان يُولَّد مرتين في الصفحة — مرة من قائمة `changes` في ملف الواجهة "
    "(بالوسوم والأكواد والإسناد) ومرة من نص المصدر السردي. أُبقي القسم المنظّم وأُزيل النص "
    "السردي المكرر. النصّ المسحوب محفوظ هنا حرفيًا للمرجعية، ومحتواه الفعلي حاضر في "
    "«الوقائع الجديدة» وفي بنود القائمة المنظّمة.\n\n```\n" + dup.strip() + "\n```\n",
    encoding="utf-8",
)
md = md[:i] + md[j:].lstrip("\n")
changed.append(("إزالة القسم المكرر", f"{len(dup)} حرفًا"))

# ---------------------------------------------------------------- 2) الخلاصة → نقاط
i, j = section(md, "الخلاصة")
seg = md[i:j]
lines = [l for l in seg.split("\n") if l.strip()]
head, body = lines[0], lines[1:]
bullets = []
for par in body:
    m = re.match(r"^([^:]{3,40}):\s*(.+)$", par.strip())
    if m:
        bullets.append(f"- **{m.group(1)}:** {m.group(2)}")
    else:
        bullets.append("- " + par.strip())
md = md[:i] + "\n".join([head, ""] + bullets) + "\n" + md[j:].lstrip("\n")
changed.append(("الخلاصة", f"{len(body)} فقرة → {len(bullets)} نقطة"))

# ---------------------------------------------------------------- 3) الوقائع الجديدة → نقاط فرعية
i, j = section(md, "الوقائع الجديدة")
seg = md[i:j]
lines = [l for l in seg.split("\n") if l.strip()]
head, body = lines[0], lines[1:]
out = [head, ""]
for par in body:
    par = par.strip()
    m = re.match(r"^(\*\*.+?\*\*)\s*—\s*(.+)$", par)
    if not m:
        out.append("- " + par)
        continue
    title, rest = m.group(1), m.group(2)
    # فصل الإسناد: (... ) والأثر: ...
    attrib = ""
    ma = re.search(r"\s*\((?:[^()]*\*\*[^()]*|[^()]*)\)\s*", rest)
    if ma:
        attrib = ma.group(0).strip()
        rest = (rest[:ma.start()] + " " + rest[ma.end():]).strip()
    effect = ""
    me = re.search(r"(?:و)?الأثر\s*:\s*(.+)$", rest)
    if me:
        effect = me.group(1).strip()
        rest = rest[:me.start()].strip()
    out.append(f"- {title}")
    if rest:
        out.append(f"  - **الواقعة:** {rest}")
    if attrib:
        out.append(f"  - **الإسناد:** {attrib.strip('()').strip()}")
    if effect:
        out.append(f"  - **الأثر:** {effect}")
md = md[:i] + "\n".join(out) + "\n" + md[j:].lstrip("\n")
changed.append(("الوقائع الجديدة", f"{len(body)} فقرة → {len([l for l in out if l.startswith('- ')])} نقطة رئيسة"))

# ---------------------------------------------------------------- 4) الحركة الملاحية → نقاط
i, j = section(md, "الحركة الملاحية والتكدس")
seg = md[i:j]
lines = [l for l in seg.split("\n") if l.strip()]
head = lines[0]
body, tables = [], []
for l in lines[1:]:
    (tables if l.startswith("|") else body).append(l)
out = [head, ""]
for par in body:
    if re.match(r"^\*\*|^الجدول|^جدول", par.strip()):
        out.append(par.strip())
        continue
    for s in sentences(par):
        out.append("- " + s)
if tables:
    out.append("")
    out.extend(tables)
md = md[:i] + "\n".join(out) + "\n" + md[j:].lstrip("\n")
changed.append(("الحركة الملاحية والتكدس", f"{len(body)} فقرة → نقاط"))

# ---------------------------------------------------------------- 5) الخلفية القائمة → نقاط
i, j = section(md, "الخلفية القائمة")
seg = md[i:j]
lines = [l for l in seg.split("\n") if l.strip()]
head = lines[0]
out = [head, ""]
for par in lines[1:]:
    for s in sentences(par):
        out.append("- " + s)
md = md[:i] + "\n".join(out) + "\n" + md[j:].lstrip("\n")
changed.append(("الخلفية القائمة", f"{len(lines)-1} فقرة → نقاط"))

SRC.write_text(md, encoding="utf-8")

print("== ما نُفِّذ ==")
for k, v in changed:
    print(f"  · {k}: {v}")
print(f"\nعدد النقاط في المصدر بعد التحويل: {len(re.findall(r'^\\s*- ', md, re.M))}")
print(f"عدد النقاط الفرعية: {len(re.findall(r'^  - ', md, re.M))}")
print(f"النسخة الاحتياطية: {BAK}")
print(f"سجل القسم المسحوب: {AUD}")