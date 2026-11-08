#!/usr/bin/env python3
"""يجعل رابط القرّاء الرسمي هو القناة الأساسية المعلَنة (Cloudflare Pages).

- make_tg_digest: يفضّل عنوان القناة الأساسية من المانيفست على base_url في site.json.
- sources/site.json: يُحدَّث base_url إلى عنوان القناة الأساسية (قرار المالك: القناة
  الأساسية هي رابط القرّاء، وManus مرآة اختيارية).
"""
from __future__ import annotations

import json
import pathlib

B = pathlib.Path(__file__).resolve().parent.parent.parent
DIGEST = B / "tools" / "make_tg_digest.py"
MANIFEST = B / "runbook" / "runbook.json"

OLD_FN = '''def site_base_url():
    for cand in (os.environ.get("SITE_DIR"), B.parent / "seawatch", B.parent / "site"):
        if cand and (Path(cand) / "sources" / "site.json").is_file():
            return json.loads((Path(cand) / "sources" / "site.json").read_text(encoding="utf-8")).get("base_url", "")
    return ""'''

NEW_FN = '''def primary_channel_url():
    """عنوان القناة الأساسية من المانيفست — رابط القرّاء الرسمي."""
    try:
        doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    for ch in doc.get("publish_channels") or []:
        if ch.get("primary") and ch.get("enabled"):
            return str(ch.get("base_url") or ch.get("url") or "").rstrip("/")
    return ""


def site_base_url():
    primary = primary_channel_url()
    if primary:
        return primary
    for cand in (os.environ.get("SITE_DIR"), B.parent / "seawatch", B.parent / "site"):
        if cand and (Path(cand) / "sources" / "site.json").is_file():
            return json.loads((Path(cand) / "sources" / "site.json").read_text(encoding="utf-8")).get("base_url", "")
    return ""'''


def main() -> int:
    t = DIGEST.read_text(encoding="utf-8")
    if "primary_channel_url" not in t:
        if OLD_FN not in t:
            print("   ✘ لم يُعثر على دالة رابط الموقع")
            return 2
        t = t.replace(OLD_FN, NEW_FN, 1)
        if "MANIFEST = " not in t:
            t = t.replace('B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)',
                          'B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)\n'
                          'MANIFEST = B / "runbook" / "runbook.json"', 1)
        DIGEST.write_text(t, encoding="utf-8")
        print("   ✔ مولّد الملخص: يفضّل القناة الأساسية")
    else:
        print("   = مولّد الملخص مطبَّق مسبقًا")

    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    primary = ""
    for ch in doc.get("publish_channels") or []:
        if ch.get("primary") and ch.get("enabled"):
            primary = str(ch.get("base_url") or ch.get("url") or "").rstrip("/")
            break
    if not primary:
        print("   ✘ لا قناة أساسية معلَنة")
        return 2

    for p in (pathlib.Path("/home/ubuntu/seawatch/sources/site.json"),
              B.parent / "site" / "sources" / "site.json"):
        if not p.is_file():
            print(f"   - غير موجود: {p}")
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        old = data.get("base_url")
        if old == primary:
            print(f"   = {p} مضبوط مسبقًا على {primary}")
            continue
        data["base_url"] = primary
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"   ✔ {p}: {old} → {primary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())