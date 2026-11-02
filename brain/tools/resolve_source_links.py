#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حلّ روابط المصادر في دفتر اليوم — ملاحظة المالك 2026-11-02.

الغرض: كل واقعة تُعرض في بطاقة «سجل الأحداث» يجب أن يكون **اسم مصدرها رابطًا**
يُدخل القارئ إلى مادة المصدر نفسها. الأداة تُثري الدفتر بحقلين:

- `source_url`: رابط مادة المصدر (وثيقة رسمية محلولة إن وُجد رابط مختصر في المقتطف،
  وإلا صفحة الجهة المصدر عند إمكان تحديدها من اسم المصدر).
- `source_url_kind`: `official-product` أو `account` أو يُترك غائبًا إن تعذّر.

قواعد السلامة:
- لا تُختلق روابط: تُحلّ الروابط المختصرة الموجودة نصًّا في المقتطف، أو تُستخدم صفحة
  الجهة المعروفة من جدول صريح، وإلا يبقى الحقل غائبًا وتُخفى الصفوف التابعة في البطاقة.
- لا كتابة إن لم يتغيّر شيء (تشغيل متكرّر آمن).
- الفشل مغلق: أي خطأ كتابة يُرجع رمزًا غير صفري.

الاستعمال:
  python3 tools/resolve_source_links.py --date 2026-11-02
  python3 tools/resolve_source_links.py --date 2026-11-02 --brain "$BRAIN_DIR" --site "$SITE_DIR"
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHORT_RE = re.compile(r"https?://(?:t\.co|bit\.ly|lnkd\.in|tinyurl\.com|goo\.gl|ow\.ly|"
                      r"buff\.ly|is\.gd|cutt\.ly|rb\.gy)/\S+")
# جدول صريح لا تخمين: اسم الجهة في الدفتر ↦ صفحتها الرسمية.
ACCOUNTS = {
    "UK_MTO": "https://x.com/UK_MTO",
    "UKMTO": "https://www.ukmto.org/",
    "JMIC": "https://www.jmic.jo/",
    "IMO": "https://www.imo.org/",
}


def _resolve_short(url: str, timeout: int = 25) -> str:
    """يحلّ الرابط المختصر إلى عنوانه النهائي؛ ويعيد نصًّا فارغًا عند التعذّر."""
    try:
        out = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{url_effective}",
                              "-L", "--max-time", str(timeout), url],
                             capture_output=True, text=True)
        final = (out.stdout or "").strip()
        return final if final.startswith("http") else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _account_for(source: str) -> str:
    for key, url in ACCOUNTS.items():
        if key in source:
            return url
    return ""


def _targets(brain: Path, site: Path, date: str) -> list[Path]:
    out = [brain / "cumulative-2026" / "daily" / f"{date}.json"]
    for candidate in (site / "sources" / "daily-events" / f"{date}.json",
                      brain / "web" / "daily-events" / f"{date}.json"):
        out.append(candidate)
    return out


def enrich(path: Path, cache: dict[str, str]) -> tuple[int, int, bool]:
    if not path.is_file():
        return 0, 0, False
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("events")
    if not isinstance(rows, list):
        return 0, 0, False
    official = account = 0
    changed = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("source_url") or "").startswith("http"):
            official += int(row.get("source_url_kind") == "official-product")
            account += int(row.get("source_url_kind") == "account")
            continue
        short = SHORT_RE.search(str(row.get("source_excerpt") or ""))
        target = kind = ""
        if short:
            key = short.group(0)
            if key not in cache:
                cache[key] = _resolve_short(key)
            if cache[key]:
                target, kind = cache[key], "official-product"
        if not target:
            fallback = _account_for(str(row.get("source") or ""))
            if fallback:
                target, kind = fallback, "account"
        if target:
            row["source_url"] = target
            row["source_url_kind"] = kind
            changed = True
            official += int(kind == "official-product")
            account += int(kind == "account")
    if changed:
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return official, account, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="حلّ روابط المصادر في دفتر اليوم", allow_abbrev=False)
    parser.add_argument("--date", required=True)
    parser.add_argument("--brain", default=str(ROOT))
    parser.add_argument("--site", default=str(ROOT.parent / "seawatch"))
    args = parser.parse_args()
    brain, site = Path(args.brain), Path(args.site)
    cache: dict[str, str] = {}
    found = False
    for path in _targets(brain, site, args.date):
        if not path.is_file():
            continue
        found = True
        official, account, changed = enrich(path, cache)
        rel = path.name if path.parent.name == "daily-events" else str(path.relative_to(brain))
        print(f"  {rel}: رسمي {official} · حساب {account} · كُتب {'نعم' if changed else 'لا (محدَّث)'}")
    if not found:
        print(f"✘ منع: لا دفتر وقائع لهذا التاريخ: {args.date}")
        return 2
    print(f"روابط المصادر — {args.date}: تمّ الحل بلا اختلاق روابط (فشل مغلق عند التعذّر).")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validators"))
    try:
        from _guard import run
    except ImportError:
        sys.exit(main())
    run(main)
