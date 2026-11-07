#!/usr/bin/env python3
"""Read-only inventory of runbook steps, tools, validators, and skill names."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain', required=True)
    ap.add_argument('--skills', required=True)
    args = ap.parse_args()
    brain, skills = Path(args.brain), Path(args.skills)
    manifest = json.loads((brain/'runbook'/'runbook.json').read_text())
    steps = manifest.get('steps', [])
    tool_files = [p for p in (brain/'tools').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    validator_files = [p for p in (brain/'validators').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.json'}]
    skill_names = sorted(p.name for p in skills.iterdir() if (p/'SKILL.md').is_file())
    print(f'steps={len(steps)}')
    print('step_prefixes=' + ','.join(sorted({s.get("id", "")[:1] for s in steps})))
    print(f'tools={len(tool_files)} validators={len(validator_files)} skills={len(skill_names)}')
    for s in steps:
        print(f'STEP\t{s.get("id")}\t{s.get("title", "")}')
    for p in sorted(tool_files):
        print(f'TOOL\t{p.relative_to(brain)}')
    for p in sorted(validator_files):
        print(f'VALIDATOR\t{p.relative_to(brain)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
