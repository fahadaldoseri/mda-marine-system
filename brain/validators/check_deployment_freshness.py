#!/usr/bin/env python3
"""حارس حداثة النشر — يقيس أن المتن المخدوم هو البناء الحالي نفسه، لا بناء أقدم.

الخلل الذي يعالجه: خطوة النشر كانت تتحقق من رابط التقرير وحده؛ فإن لم يتغيّر ملف التقرير
في هذا البناء مرّت بوصف «ناجح» بينما الشجرة المخدومة أقدم من الشجرة المبنية.

المنطق: لكل ملف مسبار معلن، تُقارن بصمة الملف في `dist` المحلي ببصمة المتن المخدوم.
  كلها مطابقة            → 0 (البناء الحالي هو المخدوم)
  أي ملف غائب أو مختلف   → 2 (فشل مغلق: القناة تخدم بناءً أقدم)
  تعذّر القياس أو غياب dist → 1 (غير مستوفى، لا يُصدَّق كنجاح)

لا يُطبع أي سر. الوحدات: بايت.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

PROBE_FILES = [
    "index.html",
    "feed.xml",
    "sitemap.xml",
    "reports/index.html",
    "sources.html",
    "additions.html",
]
BASE_DEFAULT = "https://mda-bh.pages.dev"
MIN_HTML_BYTES = 3000


def site_root() -> Path:
    for key in ("SITE_DIR", "SITE"):
        value = os.environ.get(key)
        if value and (Path(value) / "dist").is_dir():
            return Path(value)
    for candidate in (Path.home() / "seawatch",):
        if (candidate / "dist").is_dir():
            return candidate
    return Path.home() / "seawatch"


def sha_file(path: Path) -> tuple[str, int] | None:
    if not path.is_file():
        return None
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def fetch(url: str, timeout: int = 45) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "seawatch-freshness/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:  # 404 وغيره
        return exc.code, b""
    except Exception:  # noqa: BLE001
        return 0, b""


def probe(root: Path, date: str, base: str, extra: list[str] | None = None) -> dict:
    dist = root / "dist"
    files = list(PROBE_FILES) + list(extra or []) + [f"reports/{date}.html"]
    rows, missing, stale, unmeasured = [], [], [], []
    for rel in files:
        local = sha_file(dist / rel)
        if local is None:
            unmeasured.append({"file": rel, "why": "غير موجود في dist"})
            continue
        status, body = fetch(f"{base}/{rel}")
        live_sha = hashlib.sha256(body).hexdigest() if body else ""
        row = {"file": rel, "local_sha256": local[0], "local_bytes": local[1],
               "status": status, "live_sha256": live_sha, "live_bytes": len(body)}
        if status != 200 or not body:
            row["verdict"] = "missing"
            missing.append(row)
        elif live_sha == local[0]:
            row["verdict"] = "match"
        else:
            row["verdict"] = "stale"
            stale.append(row)
        rows.append(row)
    return {"date": date, "base": base, "files": rows,
            "match": len([r for r in rows if r["verdict"] == "match"]),
            "missing": missing, "stale": stale, "unmeasured": unmeasured}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--base", default=BASE_DEFAULT)
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--json-out", default="")
    ap.add_argument("--wait-seconds", type=int, default=240,
                    help="مهلة انتشار محدودة: يُعاد القياس خلالها حتى يظهر البناء الحالي (ك-573)")
    ap.add_argument("--interval", type=int, default=20, help="الفاصل بين محاولات القياس، بالثواني")
    a = ap.parse_args(argv)

    root = site_root()
    if not (root / "dist").is_dir():
        print(f"   غير مستوفى: لا يوجد dist في {root}")
        return 1
    import time
    waited, attempt, result = 0, 1, probe(root, a.date, a.base, a.extra)
    while (result["stale"] or result["missing"]) and waited < a.wait_seconds:
        time.sleep(a.interval)
        waited += a.interval
        attempt += 1
        result = probe(root, a.date, a.base, a.extra)
    result["propagation_wait_seconds"] = waited
    result["attempts"] = attempt
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"   مطابق: {result['match']} · قديم: {len(result['stale'])} · غائب: {len(result['missing'])}"
          f" · غير مقيس: {len(result['unmeasured'])} · محاولات: {attempt} · انتظار: {waited}ث")
    for row in result["stale"][:5]:
        print(f"   ✘ قديم: {row['file']} · محلي {row['local_bytes']} بايت / حي {row['live_bytes']} بايت")
    for row in result["missing"][:5]:
        print(f"   ✘ غائب: {row['file']} · حالة {row['status']}")
    if result["match"] and not result["stale"] and not result["missing"]:
        print("   ✔ البناء الحالي هو المخدوم على القناة")
        return 0
    if result["stale"] or result["missing"]:
        print("   ✘ فشل مغلق: القناة تخدم بناءً أقدم من البناء الحالي")
        return 2
    print("   غير مستوفى: تعذّر قياس الملفات")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
