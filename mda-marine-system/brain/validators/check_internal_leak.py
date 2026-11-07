#!/usr/bin/env python3
"""بوابة مانعة لتسرب عمل التحرير الداخلي إلى التقرير أو واجهة الموقع."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INTERNAL_PATTERNS = [
    (re.compile(r"المراجعة\s+الداخلية"), "عبارة عمل داخلي: المراجعة الداخلية"),
    (re.compile(r"الخط\s+اليومي"), "عبارة عمل داخلي: الخط اليومي"),
    # «التشغيل» وحدها ترد في عنوان قسم مشروع («التوجيهات التشغيلية») وفي سطر المصادر المُولَّد،
    # فلا تُعد تسرّبًا إلا في تركيب يدل على عمل داخلي (تصحيح ك-136).
    (re.compile(r"خط\s+التشغيل|التشغيل\s+اليومي|عملية\s+التشغيل|التشغيل\s+الآلي"), "عبارة عمل داخلي: التشغيل"),
    (re.compile(r"الوكيل"), "عبارة عمل داخلي: الوكيل"),
    (re.compile(r"المولّد|المولد"), "عبارة عمل داخلي: المولّد"),
    (re.compile(r"المخزون"), "عبارة عمل داخلي: المخزون"),
    (re.compile(r"المستودع"), "عبارة عمل داخلي: المستودع"),
    (re.compile(r"سجل\s+الدروس"), "عبارة عمل داخلي: سجل الدروس"),
    (re.compile(r"(?:^|[\s`(])tools/[^\s`),؛]+"), "اسم أداة داخلي: tools/…"),
    (re.compile(r"(?:^|[\s`(])validators/[^\s`),؛]+"), "اسم مدقق داخلي: validators/…"),
    (re.compile(r"(?<![\w])(?:[A-Za-z0-9_-]+/)?[^\s`),؛]+\.py\b"), "امتداد بايثون داخلي: .py"),
    (re.compile(r"(?<![\w])(?:[A-Za-z0-9_-]+/)?[^\s`),؛]+\.json\b"), "امتداد بيانات داخلي: .json"),
]


def body_lines(text: str):
    """يعيد أسطر المتن، مع إسقاط front matter والكتل البرمجية."""
    lines = text.splitlines()
    in_front = bool(lines and lines[0].strip() == "---")
    in_fence = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if in_front:
            if number > 1 and stripped == "---":
                in_front = False
            continue
        if stripped.startswith("#"):
            continue  # العناوين ليست متنًا
        if stripped.startswith("- المصادر:") or stripped.startswith("- تشغيل منقوص مُفصح:"):
            continue  # أسطر مُولَّدة آليًا ومعتمدة في المتن
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence and stripped:
            yield number, line


def scan_text(text: str, source: str):
    findings = []
    for line_no, line in body_lines(text):
        for pattern, reason in INTERNAL_PATTERNS:
            for match in pattern.finditer(line):
                sample = match.group(0).strip(" `()؛،")
                findings.append({
                    "source": source,
                    "line": line_no,
                    "reason": reason,
                    "match": sample,
                    "text": line.strip(),
                })
    return findings


def scan_json(path: Path):
    # التحقق من JSON أولًا، ثم فحص تمثيله النصي كي يظهر موضع السطر للمراجع.
    raw = path.read_text(encoding="utf-8")
    json.loads(raw)
    return scan_text(raw, str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="بوابة التسرب الداخلي من التقرير")
    parser.add_argument("path", nargs="?", help="مسار التقرير")
    parser.add_argument("--md", dest="md", help="مسار تقرير Markdown")
    parser.add_argument("--meta", help="ملف واجهة JSON اختياري للفحص")
    args = parser.parse_args()
    chosen = args.md or args.path
    if not chosen and not args.meta:
        print("الاستخدام: check_internal_leak.py --md <التقرير> [--meta <الواجهة>]")
        return 2
    findings = []
    if chosen:
        path = Path(chosen)
        if not path.exists():
            print(f"الملف غير موجود: {path}")
            return 2
        findings.extend(scan_text(path.read_text(encoding="utf-8"), str(path)))
    if args.meta:
        meta = Path(args.meta)
        if not meta.exists():
            print(f"ملف الواجهة غير موجود: {meta}")
            return 2
        try:
            findings.extend(scan_json(meta))
        except json.JSONDecodeError as exc:
            print(f"ملف الواجهة JSON غير صالح: {exc}")
            return 2
    print("=== بوابة منع تسرب المحتوى الداخلي ===")
    for item in findings:
        print(f"✘ {item['source']} — السطر {item['line']} — {item['reason']} — «{item['match']}»")
        print(f"  النص: {item['text']}")
    if findings:
        print(f"النتيجة: مانع — رُصد {len(findings)} تسرب داخلي.")
        return 2
    print("✔ النتيجة: سليم — لم يُرصد تسرب داخلي في الملفات المفحوصة.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
