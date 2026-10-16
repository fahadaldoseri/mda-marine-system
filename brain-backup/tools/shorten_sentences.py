#!/usr/bin/env python3
"""يقصّر الجمل الطويلة في تقرير Markdown عند حدود الفواصل، دون المساس بالجداول والاقتباسات."""
import re
import sys
from pathlib import Path

LIMIT = 28          # أقصى عدد كلمات للجملة بعد التقصير
MIN_PART = 8        # أدنى عدد كلمات لكل جزء ناتج


def split_segment(seg: str) -> list[str]:
    parts, guard = [seg.strip()], 0
    while guard < 8:
        guard += 1
        changed = False
        out = []
        for p in parts:
            words = p.split()
            if len(words) <= LIMIT:
                out.append(p)
                continue
            # ابحث عن فاصلة قريبة من منتصف الجملة
            cut = None
            start = max(MIN_PART, int(len(words) * 0.40))
            for i in range(start, len(words) - MIN_PART):
                if words[i].endswith("،") or words[i].endswith("؛"):
                    cut = i
                    if i >= len(words) * 0.55:
                        break
            if cut is None:
                out.append(p)
                continue
            first = " ".join(words[: cut + 1]).rstrip("،؛") + "."
            second = " ".join(words[cut + 1:]).strip()
            out.extend([first, second])
            changed = True
        parts = out
        if not changed:
            break
    return parts


def main() -> int:
    path = Path(sys.argv[1])
    lines = path.read_text(encoding="utf-8").splitlines()
    result, touched = [], 0
    for ln in lines:
        stripped = ln.lstrip()
        if stripped.startswith("|") or stripped.startswith(">") or stripped.startswith("#"):
            result.append(ln)
            continue
        if len(ln.split()) <= LIMIT:
            result.append(ln)
            continue
        segments = re.split(r"(?<=[.؟!])\s+", ln.strip())
        new_segments = []
        for s in segments:
            pieces = split_segment(s)
            if len(pieces) > 1:
                touched += 1
            new_segments.extend(pieces)
        result.append(" ".join(new_segments))
    path.write_text("\n".join(result) + "\n", encoding="utf-8")
    print(f"  ✔ جمل قُسّمت: {touched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())