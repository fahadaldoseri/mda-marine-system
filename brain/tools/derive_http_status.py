#!/usr/bin/env python3
"""اشتقاق http_status لمصادر سجل «لا واقعة» من ملف حالة التغذيات لليوم نفسه.

قرار المالك (2026-11-17): سجل 2026-11-12 كُتب بلا http_status، فيُشتق من
``feeds/feeds-{date}.status.json`` الذي سجّل نتيجة الجلب الفعلية ذلك اليوم.
القاعدة: ok=true ⇒ 200 · ok=false ⇒ رمز HTTP المذكور في block_reason إن وُجد، وإلا 0.
كل قيمة مشتقة تُوسم ``http_status_derived: true`` مع ``http_status_basis``.
القيمة الموجودة لا تُمس. مصدر لا يطابق عنصرًا في ملف الحالة = فشل مغلق بلا كتابة.
بلا ``--apply`` معاينة فقط.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rows(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("events", "items", "rows"):
            if isinstance(value.get(key), list):
                return value[key]
    raise ValueError("بنية دفتر غير معروفة")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--date", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    status_rel = f"feeds/feeds-{args.date}.status.json"
    daily_path = args.root / "cumulative-2026" / "daily" / f"{args.date}.json"
    try:
        status = json.loads((args.root / status_rel).read_text(encoding="utf-8"))
        value = json.loads(daily_path.read_text(encoding="utf-8"))
        rows = _rows(value)
    except (OSError, ValueError) as exc:
        print(f"✘ {exc}")
        return 2
    feeds = status.get("checked_feeds") or []
    by_url: dict[str, dict] = {}
    for feed in feeds:
        for key in ("primary_url", "fetched_url"):
            if feed.get(key):
                by_url[feed[key]] = feed
    changes, unmatched = [], []
    for r_index, row in enumerate(rows, 1):
        for s_index, source in enumerate(row.get("sources_checked") or [], 1):
            if not isinstance(source, dict) or source.get("http_status") is not None:
                continue
            feed = by_url.get(source.get("url") or "")
            if feed is None:
                unmatched.append(f"#{r_index}.sources_checked[{s_index}] {source.get('url')}")
                continue
            reason = str(feed.get("block_reason") or "")
            if feed.get("ok") is True:
                code = 200
            else:
                found = re.search(r"HTTP (\d{3})", reason)
                code = int(found.group(1)) if found else 0
            changes.append((source, code, feed, reason))
    if unmatched:
        print("✘ فشل مغلق: مصادر بلا عنصر مطابق في " + status_rel + ":")
        for item in unmatched:
            print("  " + item)
        return 2
    for source, code, feed, reason in changes:
        print(f"  {source.get('url')} ⇐ {code} (ok={feed.get('ok')} · رقم {feed.get('num')})")
    if not args.apply:
        print(f"معاينة: {len(changes)} قيمة تُشتق. أضف --apply للكتابة.")
        return 0
    for source, code, feed, reason in changes:
        source["http_status"] = code
        source["http_status_derived"] = True
        source["http_status_basis"] = (
            f"مشتق بقرار المالك 2026-11-17 من {status_rel} "
            f"(رقم {feed.get('num')} · ok={str(feed.get('ok')).lower()})")
        if reason and not source.get("block_reason"):
            source["block_reason"] = reason
    daily_path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✔ كُتبت {len(changes)} قيمة مشتقة في {daily_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
