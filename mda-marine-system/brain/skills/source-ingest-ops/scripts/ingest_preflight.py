#!/usr/bin/env python3
"""Read-only preflight for a dated feed-ingestion run."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--brain', required=True)
    ap.add_argument('--date', required=True)
    a = ap.parse_args()
    b, d = Path(a.brain), a.date
    paths = {
        'feed_json': b/'feeds'/f'feeds-{d}.json',
        'feed_md': b/'feeds'/f'feeds-{d}.md',
        'feed_status': b/'feeds'/f'feeds-{d}.status.json',
        'sources': b/'sections'/'10-sources.md',
        'report': b/'reports'/f'{d}-sectioned.md',
    }
    missing=[]
    for label, p in paths.items():
        ok=p.is_file() and p.stat().st_size>0
        print(f'{label}: {"present" if ok else "MISSING"} {p}')
        if not ok: missing.append(label)
    status_path=paths['feed_status']
    if status_path.is_file():
        try:
            data=json.loads(status_path.read_text())
            state=data.get('status', data.get('overall', data.get('state', 'unknown')))
            print(f'feed_state={state}')
        except Exception as exc:
            print(f'feed_state=unreadable:{type(exc).__name__}')
            missing.append('valid_feed_status')
    print(f'preflight_missing={len(missing)}')
    return 1 if missing else 0

if __name__ == '__main__':
    raise SystemExit(main())
