#!/usr/bin/env python3
"""One-shot heading normalization for task-level playbooks (B-layer step 1).

Canonical structure after normalization:
  #   <Task Title>          (one per file)
  ##  <Section>             (Ask First / Workflow / Defaults / Rules & Pitfalls /
                             Pre-Delivery Checks / Scope Boundaries / ...)
  ### <Subsection>          (previously ####)

Rules applied to every task playbook (excluding _overview.md):
  1. Demote-free promotion: `### ` -> `## `, `#### ` -> `### ` in files that
     have no `## ` headings (the 49 legacy split files).
  2. Unify Defaults heading: `## Defaults *(apply silently, disclose at
     delivery)*` -> `## Defaults` (annotation moved to body as bold note).
  3. Files already using `## ` (the 5 merged/new files) are left untouched
     except rule 2.

Idempotent: running twice yields no further changes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOKS = ROOT / "references" / "corporate-finance" / "playbooks"

DEFAULTS_ANNOTATED = re.compile(r"^(#+) Defaults \*\((.+?)\)\*\s*$")


def normalize(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)
    has_h2 = any(line.startswith("## ") for line in lines)
    changed = False
    out: list[str] = []

    for line in lines:
        original = line
        if not has_h2:
            if line.startswith("#### "):
                line = "### " + line[5:]
            elif line.startswith("### "):
                line = "## " + line[4:]
        match = DEFAULTS_ANNOTATED.match(line)
        if match:
            hashes, note = match.groups()
            line = f"{hashes} Defaults"
            out.append(line)
            out.append("")
            out.append(f"**{note.strip()}.**" if not note.strip().endswith(".") else f"**{note.strip()}**")
            changed = True
            continue
        if line != original:
            changed = True
        out.append(line)

    if changed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    changed_files = 0
    for path in sorted(PLAYBOOKS.rglob("*.md")):
        if path.name == "_overview.md":
            continue
        if normalize(path):
            changed_files += 1
            print(f"normalized: {path.relative_to(ROOT)}")
    print(f"total changed: {changed_files}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
