#!/usr/bin/env python3
"""قسّم ملفات التدقيق على وكلاء بملكية أولية غير متداخلة.

Input: UTF-8 file, one path per line; blank lines and lines beginning with # are ignored.
Output: deterministic JSON on stdout. The script never reads or writes the listed files.
Exit codes: 0 success · 2 invalid input.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def read_paths(manifest: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        item = raw.strip()
        if not item or item.startswith("#"):
            continue
        if item in seen:
            raise ValueError(f"مسار مكرر في السطر {number}: {item}")
        seen.add(item)
        paths.append(item)
    if not paths:
        raise ValueError("قائمة الملفات فارغة")
    return paths


def parse_agents(raw: str) -> list[str]:
    agents = [part.strip() for part in raw.split(",")]
    if not agents or any(not agent for agent in agents):
        raise ValueError("يجب تقديم أسماء وكلاء مفصولة بفواصل دون قيم فارغة")
    invalid = [name for name in agents if not re.fullmatch(r"[A-Za-z0-9_.-]+", name)]
    if invalid:
        raise ValueError("اسم وكيل غير صالح: " + ", ".join(invalid))
    if len(set(agents)) != len(agents):
        raise ValueError("اسم وكيل مكرر")
    return agents


def assign(paths: list[str], agents: list[str]) -> dict[str, list[str]]:
    assignments = {agent: [] for agent in agents}
    for index, path in enumerate(paths):
        assignments[agents[index % len(agents)]].append(path)
    return assignments


def main() -> int:
    parser = argparse.ArgumentParser(description="توزيع ملفات التدقيق دون تكرار الملكية")
    parser.add_argument("--files", required=True, type=Path, help="قائمة UTF-8، مسار واحد في كل سطر")
    parser.add_argument("--agents", required=True, help="أسماء وكلاء ASCII مفصولة بفواصل")
    args = parser.parse_args()

    try:
        paths = read_paths(args.files)
        agents = parse_agents(args.agents)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"✘ تعذر توزيع الملفات: {exc}", file=sys.stderr)
        return 2

    assignments = assign(paths, agents)
    assigned = [path for owned in assignments.values() for path in owned]
    if len(assigned) != len(paths) or len(set(assigned)) != len(paths):
        print("✘ خرق داخلي: التوزيع لم يحفظ التفرد والتغطية", file=sys.stderr)
        return 2

    print(json.dumps({
        "assignments": assignments,
        "file_count": len(paths),
        "unique_assignments": len(set(assigned)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
