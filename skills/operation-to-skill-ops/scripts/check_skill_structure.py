#!/usr/bin/env python3
"""فحص بنيوي لمهارة قبل تسليمها.

يفحص ما لا يُرى بالنظر: ترتيب الأقسام، والأسطر المكررة، ووسوم TODO الباقية،
وصحة الواجهة (name/description)، وعدد الأسطر، والملفات غير المسموحة.

استعمال:
  check_skill_structure.py --path /home/ubuntu/skills/<skill-name> [--json]

رمز الخروج: 0 سليم · 2 عطل. لا يحتاج أي مكتبة خارجية.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

MAX_LINES = 500
MIN_DESC = 40
MAX_DESC = 1024
FORBIDDEN_FILES = ("README.md", "CHANGELOG.md", "CONTRIBUTING.md", "TODO.md")

# ترتيب الأقسام المعتمد: الغاية ← القواعد ← طريقة التنفيذ ← ما يجب ألا يحدث ← الأدوات
GROUP_PATTERNS = {
    "purpose": r"^##\s*(الغاية|الهدف|Purpose|الغرض)",
    "rule": r"^##\s*(القاعدة|Rule)",
    "workflow": r"^##\s*(طريقة التنفيذ|خطوات التنفيذ|Workflow|Steps)",
    "forbidden": r"^##\s*(ما يجب ألا يحدث|الممنوعات|Forbidden|Do not)",
    "tools": r"^##\s*(الأدوات|Tools|الملفات المرفقة)",
}


def parse_frontmatter(text: str):
    """يعيد قاموس الواجهة أو None."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    data = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def section_positions(lines):
    """يعيد لكل مجموعة أول موضع قسم يخصّها، أو None."""
    found = {}
    for index, line in enumerate(lines):
        for group, pattern in GROUP_PATTERNS.items():
            if re.match(pattern, line.strip()) and group not in found:
                found[group] = index
    return found


def rule_sections_without_body(lines):
    """أقسام «قاعدة» بلا متن تحتها."""
    empty = []
    indexes = [i for i, ln in enumerate(lines) if re.match(GROUP_PATTERNS["rule"], ln.strip())]
    for i in indexes:
        body = []
        for line in lines[i + 1:]:
            if line.strip().startswith("## "):
                break
            if line.strip():
                body.append(line)
        if not body:
            empty.append(lines[i].strip())
    return empty


def duplicate_lines(lines):
    """أسطر محتوى مكررة حرفيًا (تُهمل الأسطر الفارغة والفواصل)."""
    seen = {}
    for line in lines:
        key = line.strip()
        if len(key) < 12:
            continue
        if set(key) <= {"-", "|", " ", "="}:
            continue
        seen[key] = seen.get(key, 0) + 1
    return [f"{count}× {key[:90]}" for key, count in seen.items() if count > 1]


def main() -> int:
    parser = argparse.ArgumentParser(description="فحص بنيوي لمهارة")
    parser.add_argument("--path", required=True, help="مجلد المهارة")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = pathlib.Path(args.path).expanduser().resolve()
    problems = []
    notes = []

    if not root.is_dir():
        print(f"✘ مجلد غير موجود: {root}", file=sys.stderr)
        return 2

    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        print(f"✘ لا يوجد SKILL.md في: {root}", file=sys.stderr)
        return 2

    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 1) الواجهة
    front = parse_frontmatter(text)
    if front is None:
        problems.append("الواجهة (frontmatter) مفقودة أو غير مغلقة")
    else:
        name = front.get("name", "")
        description = front.get("description", "")
        if not name:
            problems.append("حقل name مفقود في الواجهة")
        else:
            if name != root.name:
                problems.append(f"name «{name}» لا يطابق اسم المجلد «{root.name}»")
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
                problems.append(f"name «{name}» ليس بصيغة kebab-case")
        if not description:
            problems.append("حقل description مفقود في الواجهة")
        elif "[TODO" in description:
            problems.append("description ما زال يحمل قالب TODO")
        elif not (MIN_DESC <= len(description) <= MAX_DESC):
            problems.append(f"طول description {len(description)} خارج المدى {MIN_DESC}–{MAX_DESC}")
        notes.append(f"name={name or '—'} · description={len(front.get('description',''))} حرفًا")

    # 2) وسوم TODO باقية
    todo_hits = [i + 1 for i, line in enumerate(lines) if "[TODO" in line]
    if todo_hits:
        problems.append(f"وسوم TODO باقية في الأسطر: {todo_hits[:6]}")

    # 3) عدد الأسطر
    if len(lines) > MAX_LINES:
        problems.append(f"عدد الأسطر {len(lines)} يتجاوز {MAX_LINES}")

    # 4) ترتيب الأقسام
    pos = section_positions(lines)
    if "rule" in pos and "workflow" in pos and pos["rule"] > pos["workflow"]:
        problems.append("قسم «القاعدة» يظهر بعد «طريقة التنفيذ»")
    if "workflow" in pos and "tools" in pos and pos["workflow"] > pos["tools"]:
        problems.append("قسم «طريقة التنفيذ» يظهر بعد «الأدوات»")
    if "rule" in pos and "tools" in pos and pos["rule"] > pos["tools"]:
        problems.append("قسم «القاعدة» يظهر بعد «الأدوات»")
    if "purpose" in pos and "rule" in pos and pos["purpose"] > pos["rule"]:
        problems.append("قسم «الغاية» يظهر بعد «القاعدة»")
    if "tools" in pos:
        after = [i for i in range(pos["tools"] + 1, len(lines))
                 if lines[i].strip().startswith("## ")]
        if after:
            problems.append("«الأدوات» ليس آخر الأقسام")
    notes.append("الأقسام المكتشفة: " + " · ".join(sorted(pos)) if pos else "لا أقسام قياسية")

    # 5) قواعد بلا متن
    empty_rules = rule_sections_without_body(lines)
    if empty_rules:
        problems.append(f"أقسام قاعدة بلا متن: {empty_rules[:4]}")

    # 6) أسطر مكررة
    dups = duplicate_lines(lines)
    if dups:
        problems.append(f"أسطر مكررة: {dups[:4]}")

    # 7) ملفات غير مسموحة
    for item in root.iterdir():
        if item.name in FORBIDDEN_FILES:
            problems.append(f"ملف غير مسموح: {item.name}")
        if item.suffix in (".bak", ".tmp", ".orig") or item.name.endswith("~"):
            problems.append(f"ملف مؤقت باقٍ: {item.name}")

    # 8) الأدوات المعلنة موجودة فعلًا
    declared = set(re.findall(r"`(scripts/[^`]+?\.py)`", text))
    for rel in sorted(declared):
        if not (root / rel).is_file():
            problems.append(f"أداة معلنة غير موجودة: {rel}")
    notes.append(f"أدوات معلنة: {len(declared)}")

    if args.json:
        print(json.dumps({"path": str(root), "lines": len(lines),
                          "problems": problems, "notes": notes},
                         ensure_ascii=False, indent=2))
    else:
        print(f"   فحص بنيوي: {root.name} · {len(lines)} سطرًا")
        for note in notes:
            print(f"   · {note}")
        if problems:
            print(f"   ✘ عيوب: {len(problems)}")
            for problem in problems:
                print(f"      - {problem}")
        else:
            print("   ✔ البنية سليمة: ترتيب صحيح · لا TODO · لا سطر مكرر · لا ملف ممنوع")

    return 0 if not problems else 2


if __name__ == "__main__":
    sys.exit(main())