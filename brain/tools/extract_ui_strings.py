#!/usr/bin/env python3
"""يستخرج كل النصوص العربية الظاهرة للقارئ من شيفرة المولّد والقوالب (للقراءة فقط).

الاستعمال:  python3 extract_ui_strings.py <مجلد1> [<مجلد2> ...] > ui-strings.tsv
الناتج:     ملف|سطر|النص   (نصوص حرفية بالعربية داخل .py و.js و.html و.md و.json)
ثم يُشغَّل عليه style_metrics و check_orthography وقائمة اللفظ الموحّد.
"""
import ast
import os
import re
import sys

AR = re.compile(r"[؀-ۿ]")
EXT = {".py", ".js", ".mjs", ".html", ".htm", ".md", ".json", ".txt", ".css"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", "shots", "logs", "archive", "reports", "cumulative-2026", "feeds"}


def py_strings(path):
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except Exception:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and AR.search(node.value):
            out.append((node.lineno, node.value.strip().replace("\n", " ⏎ ")))
    return out


def text_strings(path):
    out = []
    for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        if AR.search(line):
            out.append((n, line.strip()))
    return out


def main():
    roots = sys.argv[1:]
    if not roots:
        print(__doc__)
        return 0
    count = 0
    for root in roots:
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in EXT:
                    continue
                p = os.path.join(d, f)
                items = py_strings(p) if ext == ".py" else text_strings(p)
                for n, s in items:
                    if len(s) >= 3:
                        print(f"{p}\t{n}\t{s[:400]}")
                        count += 1
    print(f"# المجموع: {count} نصًا", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
