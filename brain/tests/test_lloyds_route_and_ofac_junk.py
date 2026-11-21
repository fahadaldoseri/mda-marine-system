#!/usr/bin/env python3
"""مسار Lloyd's List الرسمي (36) وحارس أسماء السفن من آثار الجلب (21 نوفمبر 2026).

- 36: الموقع وكل تغذياته ترد 403 (Cloudflare). المسار البديل تغذية بودكاست الجهة نفسها
  (المؤلف Lloyd's List في دليل Apple id1388378983)، لا وسيط يتجاوز الحماية، وبحد 20 عنصرًا.
- «HTTP 403» و«HTTP 405» دخلت قائمة OFAC من سطر التغطية فأوقفت G054؛ لا تُقرأ أسماء سفن.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_feeds  # noqa: E402
from vessel_names import _plausible, extract  # noqa: E402

FAIL = []


def check(cond: bool, msg: str) -> None:
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAIL.append(msg)


routes = check_feeds.FALLBACK_ROUTES.get(36) or []
check(len(routes) == 1 and routes[0]["via"].startswith("official-"), "36 له مسار رسمي واحد موسوم official-")
check("jina.ai" not in routes[0]["url"] and "lloydslist.com" not in routes[0]["url"],
      "المسار لا يمر بوسيط نصي ولا بالنطاق المحجوب")
check(routes[0].get("max_items") == 20, "حد 20 عنصرًا للتغذية الأرشيفية")
for junk in ("HTTP 403", "HTTP 405", "ADVISORY 198-26"):
    check(not _plausible(junk), f"«{junk}» ليس اسم سفينة")
for name in ("AL DHANNAH", "FUJAIRAH ENERGY", "PETRO DOLPHIN"):
    check(_plausible(name), f"«{name}» يبقى اسم سفينة")
check(extract("تعذر جلب المصدر (HTTP 403) و(HTTP 405) ثم HTTP 403") == [], "سطر التغطية لا يُخرج أسماء")
if FAIL:
    raise SystemExit(1)
print("  ✔ المسار الرسمي وحارس الأسماء سليمان")
