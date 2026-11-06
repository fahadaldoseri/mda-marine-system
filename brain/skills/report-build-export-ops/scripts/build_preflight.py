#!/usr/bin/env python3
"""Read-only preflight for report/site build inputs."""
from __future__ import annotations
import argparse
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain', required=True)
    ap.add_argument('--site', required=True)
    ap.add_argument('--date', required=True)
    a = ap.parse_args()
    b, s, d = Path(a.brain), Path(a.site), a.date
    checks = {
        'report': b/'reports'/f'{d}-sectioned.md',
        'meta': b/'web'/'meta'/f'{d}.json',
        'runbook': b/'runbook'/'runbook.json',
        'site_generator': s/'generator',
        'pdf_profile': b/'templates'/'approved-pdf'/'print-profile.json',
        'print_css': b/'templates'/'approved-pdf'/'print-css-frozen.css',
    }
    missing = []
    for label, path in checks.items():
        ok = path.exists() and (path.is_file() and path.stat().st_size > 0 or path.is_dir())
        print(f'{label}: {"present" if ok else "MISSING"} {path}')
        if not ok: missing.append(label)
    print(f'preflight_missing={len(missing)}')
    return 1 if missing else 0

if __name__ == '__main__':
    raise SystemExit(main())
