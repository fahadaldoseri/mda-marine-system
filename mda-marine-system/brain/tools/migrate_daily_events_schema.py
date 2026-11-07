#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ترحيل دفتر الوقائع إلى مخطط `schemas/daily-events.schema.json` — تجفيف افتراضي.

ما ترحّله هذه الأداة (ولا شيء غيره):

1. `confidence` خارج القائمة المغلقة ← القيمة المطابقة مع حفظ الخام في `confidence_raw`.
   جدول التطبيع مكتوب أدناه، وأي قيمة لا يطابقها الجدول تُترك وتُبلَّغ بلا تعديل.

لا تُنشئ الأداة قيمة غير موجودة، ولا تُملأ حقول عرض ناقصة، ولا تُصحَّح أرقام IMO:
هذه كلها تُترك للباحث وللقرار. النسخة الأصلية لكل ملف مُعدَّل تُحفظ قبل الكتابة.

الاستعمال:
  python3 tools/migrate_daily_events_schema.py                 # تجفيف: يعرض ما سيتغيّر
  python3 tools/migrate_daily_events_schema.py --apply         # يكتب ويحفظ النسخ الأصلية
  python3 tools/migrate_daily_events_schema.py --date 2026-10-14 --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "cumulative-2026" / "daily"
BACKUP = ROOT / "backups" / "daily-events-pre-migration"
CONFIDENCE = ("عالية", "متوسطة", "منخفضة")

# جدول التطبيع: أي قيمة خام تحتوي اللفظ تُطبَّع إلى الفئة المغلقة المقابلة.
CONFIDENCE_RULES = (
    ("عالية", "عالية"),
    ("متوسطة", "متوسطة"),
    ("منخفضة", "منخفضة"),
)


def normalise_confidence(raw: str) -> str | None:
    text = (raw or "").strip()
    if text in CONFIDENCE:
        return None
    for token, target in CONFIDENCE_RULES:
        if token in text:
            return target
    return None


def rows_of(value):
    if isinstance(value, list):
        return value, "list"
    if isinstance(value, dict):
        for key in ("events", "items", "rows"):
            if isinstance(value.get(key), list):
                return value[key], key
    return None, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--date", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    targets = sorted(DAILY.glob(f"{args.date}.json")) if args.date else sorted(DAILY.glob("*.json"))
    if not targets:
        print("✘ لا ملفات مطابقة")
        return 2

    planned: list[dict] = []
    unmapped: list[str] = []
    for path in targets:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"✘ تعذر قراءة {path}: {exc}")
            return 2
        rows, container = rows_of(payload)
        if rows is None:
            print(f"✘ بنية غير معروفة في {path}")
            return 2
        changes = []
        for index, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                continue
            raw = str(row.get("confidence") or "").strip()
            if not raw or raw in CONFIDENCE:
                continue
            target = normalise_confidence(raw)
            if target is None:
                unmapped.append(f"{path.stem}#{index}: {raw}")
                continue
            changes.append({"index": index, "code": row.get("code"), "from": raw, "to": target})
            if args.apply:
                row["confidence"] = target
                row.setdefault("confidence_raw", raw)
        if changes:
            planned.append({"file": str(path), "container": container, "changes": changes,
                            "payload": payload if args.apply else None})
            if args.apply:
                BACKUP.mkdir(parents=True, exist_ok=True)
                backup_path = BACKUP / path.name
                if not backup_path.exists():
                    shutil.copy2(path, backup_path)
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                                encoding="utf-8")

    summary = {"applied": bool(args.apply), "files": len(planned),
               "records": sum(len(p["changes"]) for p in planned),
               "unmapped": unmapped,
               "changes": [{k: v for k, v in p.items() if k != "payload"} for p in planned]}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=1))
    else:
        mode = "تطبيق" if args.apply else "تجفيف"
        print(f"ترحيل مخطط الدفتر ({mode}): {summary['files']} ملفًا · {summary['records']} سجلًا")
        for item in summary["changes"]:
            for change in item["changes"]:
                print(f"  {'✎' if args.apply else '·'} {Path(item['file']).stem} "
                      f"#{change['index']} {change['code']}: «{change['from']}» → «{change['to']}»")
        if unmapped:
            print(f"  ✘ قيم بلا قاعدة تطبيع ({len(unmapped)}): " + " · ".join(unmapped))
            print("    النتيجة: منع — لا تُطبَّع قيمة بلا قاعدة مكتوبة")
            return 2
        if args.apply:
            print(f"  النسخ الأصلية محفوظة في {BACKUP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())