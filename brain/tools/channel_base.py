#!/usr/bin/env python3
"""يطبع رابط القناة الأساسية المعلَنة في المانيفست (أو قناة بالاسم).

الغرض: لا تُثبَّت عناوين القنوات في أوامر الخطوات؛ تُقرأ من المانيفست وحده،
فتُطبَّق أي إضافة قناة مستقبلية بلا تعديل خطوة.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

MANIFEST = pathlib.Path(__file__).resolve().parent.parent / "runbook" / "runbook.json"


def channels(manifest: pathlib.Path) -> list[dict]:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return list(data.get("publish_channels") or [])


def base_of(channel: dict) -> str:
    return str(channel.get("base_url") or channel.get("url") or "").rstrip("/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="", help="اسم قناة محددة بدل الأساسية")
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--all", action="store_true", help="يطبع كل القنوات المعلَنة: name=base")
    a = ap.parse_args()

    chans = channels(pathlib.Path(a.manifest))
    if a.all:
        for c in chans:
            print(f"{c.get('name')}={base_of(c)}")
        return 0

    if a.name:
        for c in chans:
            if str(c.get("name")) == a.name:
                base = base_of(c)
                if not base:
                    print(f"✘ القناة {a.name} بلا base_url معلن", file=sys.stderr)
                    return 2
                print(base)
                return 0
        print(f"✘ القناة {a.name} غير معلنة في المانيفست", file=sys.stderr)
        return 2

    for c in chans:
        if c.get("primary") and c.get("enabled") and base_of(c):
            print(base_of(c))
            return 0
    print("✘ لا قناة أساسية مُفعَّلة بعنوان معلن", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())