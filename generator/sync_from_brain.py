#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تحديث الموقع الدائم من مخرجات Brain اليومية.

الاستخدام:
  python3 generator/sync_from_brain.py --date 2026-10-12 [--brain /home/ubuntu/brain-marine-news]

ما يفعله بالترتيب:
1. ينسخ تقرير اليوم وملف واجهته من مساحة Brain إلى مصادر الموقع.
2. يحدّث دفتر الأحداث التراكمي إن وُجد أحدث منه.
3. يعيد بناء الموقع كاملًا (dist/) عبر build_site.py.
4. يطبع ملخصًا للنتيجة وحالة الروابط الداخلية.

لا ينشر ولا يرفع: النشر يبقى خطوة منفصلة عبر مشروع الاستضافة.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent


def copy_sources(date_iso: str, brain: Path) -> list:
    log = []
    src_md = brain / "reports" / f"{date_iso}-sectioned.md"
    src_meta = brain / "web" / "meta" / f"{date_iso}.json"
    dst_md = SITE / "sources" / "reports" / f"{date_iso}-sectioned.md"
    dst_meta = SITE / "sources" / "meta" / f"{date_iso}.json"

    if src_md.exists():
        shutil.copy2(src_md, dst_md)
        log.append(f"نُسخ التقرير: {dst_md.name} ({dst_md.stat().st_size} بايت)")
    else:
        log.append(f"تحذير: تقرير اليوم غير موجود: {src_md}")

    if src_meta.exists():
        try:
            json.loads(src_meta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log.append(f"خطأ: ملف الواجهة ليس JSON صالحًا ({e}) — لم يُنسخ")
            return log
        shutil.copy2(src_meta, dst_meta)
        log.append(f"نُسخ ملف الواجهة: {dst_meta.name}")
    else:
        log.append(f"تحذير: ملف واجهة اليوم غير موجود: {src_meta}")

    ledger_candidates = sorted((brain / "cumulative-2026").glob("event-ledger*.json"))
    if ledger_candidates:
        newest = max(ledger_candidates, key=lambda p: p.stat().st_mtime)
        shutil.copy2(newest, SITE / "sources" / "ledger.json")
        log.append(f"حُدّث دفتر الأحداث: {newest.name}")

    cum_md = sorted((brain / "cumulative-2026").glob("*تراكمي*.md"))
    if cum_md:
        newest = max(cum_md, key=lambda p: p.stat().st_mtime)
        shutil.copy2(newest, SITE / "sources" / "reports" / "cumulative.md")
        log.append(f"حُدّث السجل التراكمي: {newest.name}")
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="تاريخ التقرير YYYY-MM-DD")
    ap.add_argument("--brain", default="/home/ubuntu/brain-marine-news")
    ap.add_argument("--skip-build", action="store_true")
    a = ap.parse_args()

    brain = Path(a.brain).resolve()
    for line in copy_sources(a.date, brain):
        print(line)

    if a.skip_build:
        return 0
    r = subprocess.run([sys.executable, str(HERE / "build_site.py"), "--check"],
                       cwd=str(SITE), capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip(), file=sys.stderr)
        return r.returncode
    pages = sorted((SITE / "dist").rglob("*.html"))
    print(f"جاهز للنشر: {len(pages)} صفحة · " + " · ".join(p.name for p in pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
