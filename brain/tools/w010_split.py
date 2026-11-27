#!/usr/bin/env python3
"""تقسيم طلب W010 (كتابة التقرير اليومي) إلى خمس مجموعات أقسام لخفض حجم كل طلب إلى النموذج المجاني.

الوحدة بلا شبكة ولا حالة: دوال خالصة يستعملها `agent_write_llm.py`.
- المجموعات (قرار فهد 27 نوفمبر 2026، وثيقة التصميم platform-study-2026-11-27/تصميم-تقسيم-طلب-W010.md):
  أ الخلاصة ومستوى التهديد والتوجيهات، ب سجل الأحداث والتحذيرات وسجل IMO،
  ج قراءة الموقف والاحتمالات والحركة الملاحية، د التوزيع الجغرافي والمؤشرات وما لم يُحسم والمراقبة والخلفية،
  هـ المصادر والمراجع. (الرموز في الشيفرة: A..E.)
- ترتيب التوليد B ثم C ثم D ثم E ثم A، لأن الخلاصة والتوجيهات تُلخّص بقية الأقسام.
- سطرا العنوان الرئيسي والاقتباس يُركَّبان بالشيفرة من التاريخ (متطابقان في كل التقارير)، فلا يكتبهما النموذج.
- يبقى ملف التقرير الناتج واحدًا بترتيب الأقسام في المانيفست، فلا يتغير ما تتوقعه البوابات.
"""
from __future__ import annotations

import re

# كل مجموعة: معرّفات أقسام المانيفست، أرقام أمثلة 20-examples.md، أنواع ملفات القراءة التي تحتاجها.
# أنواع القراءة: feeds التغذيات، daily دفتر اليوم، meta ملف الواجهة، est سجل رموز التقدير.
GROUPS: dict[str, dict] = {
    "A": {"sections": ["summary", "threat-level", "directives"], "examples": [1, 4], "reads": []},
    "B": {"sections": ["new-incidents", "warnings", "imo-log"], "examples": [2, 12], "reads": ["feeds", "daily"]},
    "C": {"sections": ["intel-analysis", "attribution", "traffic"], "examples": [3, 5, 9, 10],
          "reads": ["feeds", "meta", "est"]},
    "D": {"sections": ["incident-map", "indicators", "open-questions", "monitoring", "background"],
          "examples": [7, 8], "reads": ["feeds", "meta"]},
    "E": {"sections": ["sources"], "examples": [11, 12], "reads": ["feeds"]},
}
ORDER = ["B", "C", "D", "E", "A"]

# كتل قالب write-report.md: تُحذف كتلة الإتمام من كل مجموعة (يحلّ محلها نطاق الطلب)،
# وتُحفظ كتلتا مستوى التهديد والتقديرات لمن تخصّه فقط.
DROP_BLOCKS = ("شروط الإتمام",)
ONLY_BLOCKS = {"قسم «مستوى التهديد»": {"A"}, "تسجيل التقديرات EST": {"A", "C"}}

PREAMBLE_TITLE = "# التقرير اليومي لأمن الملاحة"


def written_sections(manifest: dict) -> list[dict]:
    return [s for s in sorted(manifest.get("sections", []), key=lambda x: x["order"]) if s.get("heading")]


def supported(manifest: dict) -> bool:
    """التقسيم صالح فقط إن غطّت المجموعات كل الأقسام المكتوبة بالضبط (قسم جديد في المانيفست يُسقطه إلى الطلب الواحد)."""
    ids = [i for g in GROUPS.values() for i in g["sections"]]
    return sorted(ids) == sorted(s["id"] for s in written_sections(manifest)) and len(ids) == len(set(ids))


def preamble(date: str) -> str:
    y, mo, d = date.split("-")
    return f"{PREAMBLE_TITLE}\n> مركز الوعي بالمجال البحري — مملكة البحرين · {d}/{mo}/{y} · UTC\n"


def read_kind(rel: str) -> str:
    if rel.startswith("feeds/"):
        return "feeds"
    if rel.startswith("cumulative-2026/daily/"):
        return "daily"
    if rel.startswith("web/meta/"):
        return "meta"
    if rel.endswith("estimate-code-map.json"):
        return "est"
    return "other"


def examples_subset(text: str, nums: list[int]) -> str:
    """مقاطع 20-examples.md المرقمة `## N) ...` المطلوبة فقط، مع رأس الملف."""
    parts = re.split(r"(?m)^(?=## \d+\) )", text)
    keep = [p for p in parts[1:] if int(re.match(r"## (\d+)\)", p).group(1)) in nums]
    return (parts[0] + "".join(keep)).rstrip()


def sections_subset(rendered: str, orders: set[int]) -> str:
    """كتل `### N. ...` المطلوبة فقط من نص أقسام التقرير الذي يولّده المحرّك."""
    parts = re.split(r"(?m)^(?=### \d+\. )", rendered)
    keep = [p for p in parts[1:] if int(re.match(r"### (\d+)\.", p).group(1)) in orders]
    return "\n\n".join(p.strip() for p in keep)


def split_blocks(src: str) -> list[str]:
    """قالب البرومت إلى كتل تبدأ كل منها بسطر `## ` (الكتلة الأولى مقدمة القالب)."""
    return re.split(r"(?m)^(?=## )", src)


def block_title(block: str) -> str:
    return block[3:].split("\n", 1)[0].strip() if block.startswith("## ") else ""


def keep_block(block: str, group: str) -> bool:
    t = block_title(block)
    if any(t.startswith(d) for d in DROP_BLOCKS):
        return False
    for prefix, only in ONLY_BLOCKS.items():
        if t.startswith(prefix):
            return group in only
    return True


def _cands(cell: str) -> list[str]:
    return [c.strip() for c in re.split(r"[،؛/|]", cell) if len(c.strip()) >= 2] + ([cell.strip()] if cell.strip() else [])


def filter_lexicon(lex: str, corpus: str) -> str:
    """يحذف من جدول «أ) ألفاظ ومعانٍ» الصفوف التي لا يرد لفظها ولا معناها في مادة المجموعة. باقي الملف كما هو.

    الاستعمال مشروط بتفعيل صريح (W010_LEXICON=filtered) إلى أن تجتاز بوابة المعجم G044 على تشغيل حقيقي.
    """
    out, in_a = [], False
    for line in lex.split("\n"):
        if line.startswith("## "):
            in_a = line.startswith("## أ)")
        if in_a and line.startswith("|") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0] != "المعنى":
                if not any(t in corpus for t in _cands(cells[2]) + _cands(cells[0])):
                    continue
        out.append(line)
    return "\n".join(out)


# ───────────────────────── التجميع والتحقق ─────────────────────────

def parse_blocks(text: str) -> list[tuple[str, str]]:
    """كتل `## عنوان` من نص جزء: [(العنوان، الكتلة كاملة)]. ما قبل أول عنوان يُهمل."""
    out = []
    for b in re.split(r"(?m)^(?=## )", text):
        if b.startswith("## "):
            out.append((b[3:].split("\n", 1)[0].strip(), b.rstrip()))
    return out


def section_order(heading: str, sections: list[dict]) -> int | None:
    h = heading.strip().rstrip(":：").strip()
    for s in sections:
        if h == s["heading"] or h in (s.get("aliases") or []):
            return s["order"]
    return None


def missing_headings(part_text: str, group: str, manifest: dict) -> list[str]:
    """عناوين أقسام المجموعة الناقصة من الجزء (العنوان أو أحد مرادفاته)، أو بلا متن."""
    have = {}
    for h, b in parse_blocks(part_text):
        o = section_order(h, written_sections(manifest))
        if o is not None and len(b.split("\n", 1)[-1].strip()) >= 20:
            have[o] = True
    by_id = {s["id"]: s for s in written_sections(manifest)}
    return [by_id[i]["heading"] for i in GROUPS[group]["sections"] if by_id[i]["order"] not in have]


def assemble(date: str, parts: dict[str, str], manifest: dict) -> str:
    """يجمع الأجزاء الخمسة في تقرير واحد بترتيب أقسام المانيفست؛ العنوان الرئيسي والاقتباس من الشيفرة.

    عنوان بلا قسم معروف يلتحق بالكتلة السابقة في جزئه. ما كُتب خارج مجموعته يُهمل (لا يُكرَّر قسم)."""
    secs = written_sections(manifest)
    rows, seq = [], 0
    for g in ORDER:
        mine = {s["order"] for s in secs if s["id"] in GROUPS[g]["sections"]}
        cur = None
        for h, b in parse_blocks(parts.get(g, "")):
            o = section_order(h, secs)
            if o is None:
                if cur is not None:
                    rows[cur][2] += "\n\n" + b
                continue
            if o not in mine:
                cur = None
                continue
            rows.append([o, seq, b])
            cur = len(rows) - 1
            seq += 1
    rows.sort(key=lambda r: (r[0], r[1]))
    return preamble(date) + "\n" + "\n\n".join(r[2].rstrip() for r in rows) + "\n"


def blame(problems: str, manifest: dict) -> set[str]:
    """المجموعات التي يرد عنوان قسم من أقسامها (أو مرادفه) في نص رفض المحرّك. فارغ = تعذّر التحديد."""
    by_id = {s["id"]: s for s in written_sections(manifest)}
    out = set()
    for g, cfg in GROUPS.items():
        for i in cfg["sections"]:
            names = [by_id[i]["heading"], *(by_id[i].get("aliases") or [])]
            if any(n and n in problems for n in names):
                out.add(g)
    return out


def digest(parts: dict[str, str], manifest: dict, per_section: int = 200, cap: int = 2200) -> str:
    """موجز بقية الأقسام المكتوبة لمجموعة الخلاصة: العنوان وأول المتن لكل قسم، بسقف إجمالي."""
    secs = written_sections(manifest)
    rows = []
    for g in ORDER:
        if g == "A":
            continue
        for h, b in parse_blocks(parts.get(g, "")):
            o = section_order(h, secs)
            if o is not None:
                rows.append((o, h, " ".join(b.split("\n", 1)[-1].split())[:per_section]))
    rows.sort()
    txt = "\n".join(f"- {h}: {body}" for _, h, body in rows)
    return txt[:cap]
