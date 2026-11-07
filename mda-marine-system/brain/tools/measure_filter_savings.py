#!/usr/bin/env python3
"""قياس الوفر المتوقع من ترشيح بنود التغذيات واستخلاص مقاطع الصفحات.

المدخل: feeds/feeds-YYYY-MM-DD.json + قائمة روابط (اختياري)
المخرج: أرقام مقيسة: حجم قبل/بعد لكل مرحلة، ونسبة الوفر.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent

# كلمات دالة لنطاق العمل: جغرافي + موضوعي + رسمي
GEO = [
    "هرمز", "hormuz", "خليج عمان", "gulf of oman", "بحر العرب", "arabian sea",
    "البحر الأحمر", "red sea", "باب المندب", "bab el mandeb", "bab-el-mandeb",
    "خليج عدن", "gulf of aden", "الخليج العربي", "persian gulf", "فجيرة", "fujairah",
    "المحيط الهندي", "indian ocean", "القرن الأفريقي", "horn of africa",
]
TOPIC = [
    "ناقلة", "tanker", "سفينة", "vessel", "ship", "حاويات", "container",
    "قرصنة", "piracy", "سطو", "robbery", "خطف", "hijack", "هجوم", "attack",
    "صاروخ", "missile", "مسيّرة", "مسيرة", "drone", "لغم", "mine",
    "ukmto", "navarea", "imo", "msci", "jmic", "centcom", "سنتكوم",
    "تكدس", "congestion", "رسو", "anchorage", "عبور", "transit", "إغلاق", "closure",
    "عقوبات", "sanction", "أسطول الظل", "shadow fleet", "مصادرة", "seizure",
    "حريق", "fire", "تسرب", "spill", "تلوث", "pollution", "إخلاء", "evacuat",
]
KEYWORDS = [k.lower() for k in GEO + TOPIC]

# كلمات تُستبعد دائمًا (ضجيج خارج النطاق)
NOISE = [
    "football", "رياضة", "كرة القدم", "طقس الغد", "horoscope", "سياحة", "tourism",
    "recipe", "وصفة", "صحة", "celebrity", "مشاهير",
]


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower()


def in_scope(text: str) -> bool:
    t = norm(text)
    if any(n in t for n in NOISE):
        return False
    return any(k in t for k in KEYWORDS)


def sz_bytes(s: str) -> int:
    return len(s.encode("utf-8"))


def analyse_feeds(day: str) -> dict:
    p = ROOT / f"feeds/feeds-{day}.json"
    if not p.exists():
        return {"error": f"لا يوجد {p}"}
    data = json.loads(p.read_text(encoding="utf-8"))
    channels = [c for c in data if c.get("items")]
    items = [it for c in channels for it in c["items"]]
    keep = [it for it in items if in_scope(json.dumps(it, ensure_ascii=False))]
    # تقدير حجم مخرَج الترشيح: سطر لكل بند + ترويسة المصدر
    lines: list[str] = []
    for c in channels:
        sel = [it for it in c["items"] if in_scope(json.dumps(it, ensure_ascii=False))]
        if not sel:
            continue
        lines.append(f"## {c.get('num')}. {c.get('name')}")
        for it in sel:
            lines.append(f"- {it.get('date','')} · {it.get('title','')}")
    filtered = "\n".join(lines) + "\n"
    return {
        "raw_bytes": p.stat().st_size,
        "channels": len(channels),
        "items": len(items),
        "items_bytes": sum(sz_bytes(json.dumps(i, ensure_ascii=False)) for i in items),
        "kept_items": len(keep),
        "kept_bytes_est": sz_bytes(filtered),
        "kept_channels": sum(1 for c in channels if any(
            in_scope(json.dumps(i, ensure_ascii=False)) for i in c["items"])),
    }


def strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<(nav|footer|aside|form)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", "\n", html)
    text = re.sub(r"&[a-z#0-9]+;", " ", text)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_matches(text: str, window: int = 400) -> str:
    """يستبقي المقاطع التي فيها كلمة دالة، بفترة سياق محدودة."""
    keep: list[str] = []
    for para in text.split("\n"):
        para = para.strip()
        if len(para) < 40:
            continue
        if in_scope(para):
            keep.append(para[:window])
    out: list[str] = []
    seen: set[str] = set()
    for para in keep:
        sig = para[:80]
        if sig in seen:
            continue
        seen.add(sig)
        out.append(para)
    return "\n".join(out)


def analyse_pages(urls: list[str]) -> list[dict]:
    rows: list[dict] = []
    for u in urls:
        try:
            raw = subprocess.run(
                ["curl", "-sL", "--max-time", "30", "-A", "Mozilla/5.0", u],
                capture_output=True, timeout=45,
            ).stdout
        except Exception as e:  # noqa: BLE001
            rows.append({"url": u, "error": str(e)})
            continue
        html = raw.decode("utf-8", "ignore")
        text = strip_html(html)
        ext = extract_matches(text)
        rows.append({
            "url": u,
            "html_bytes": len(raw),
            "text_bytes": sz_bytes(text),
            "extract_bytes": sz_bytes(ext),
            "ratio_text": round(100 * sz_bytes(text) / max(len(raw), 1), 1),
            "ratio_extract_of_text": round(100 * sz_bytes(ext) / max(sz_bytes(text), 1), 1),
            "ratio_extract_of_html": round(100 * sz_bytes(ext) / max(len(raw), 1), 1),
        })
    return rows


def main() -> int:
    day = sys.argv[1] if len(sys.argv) > 1 else "2026-10-14"
    print("=" * 68)
    print(f"قياس الوفر — يوم {day} (UTC)")
    print("=" * 68)

    f = analyse_feeds(day)
    print("\n[1] بنود التغذيات")
    if "error" in f:
        print("   ", f["error"])
    else:
        print(f"    · الحجم الخام: {f['raw_bytes']:,} بايت · قنوات: {f['channels']} · بنود: {f['items']:,}")
        print(f"    · بنود داخل النطاق: {f['kept_items']:,} من {f['items']:,} "
              f"({100*f['kept_items']/max(f['items'],1):.1f}%) في {f['kept_channels']} قناة")
        print(f"    · حجم مخرَج الترشيح المقاس: {f['kept_bytes_est']:,} بايت "
              f"({100*f['kept_bytes_est']/max(f['raw_bytes'],1):.1f}% من الخام)")
        dig = ROOT / f"feeds/feeds-{day}.md"
        if dig.exists():
            d = dig.stat().st_size
            print(f"    · الملخص الحالي (digest): {d:,} بايت → الوفر من الترشيح: "
                  f"{100*(d-f['kept_bytes_est'])/max(d,1):.1f}%")

    print("\n[2] الصفحات المجلوبة")
    urls = sys.argv[2:] or [
        "https://straits.live/briefs/2026-10-14",
        "https://combinedmaritimeforces.com/jmic/",
        "https://www.ukmto.org/recent-incidents",
    ]
    rows = analyse_pages(urls)
    tot_h = tot_t = tot_e = 0
    for r in rows:
        if "error" in r:
            print(f"    ✘ {r['url'][:52]} — {r['error']}")
            continue
        tot_h += r["html_bytes"]; tot_t += r["text_bytes"]; tot_e += r["extract_bytes"]
        print(f"    · {r['url'][:50]}")
        print(f"        HTML {r['html_bytes']:,} → نص {r['text_bytes']:,} ({r['ratio_text']}%) "
              f"→ مستخلص {r['extract_bytes']:,} ({r['ratio_extract_of_html']}% من HTML · "
              f"{r['ratio_extract_of_text']}% من النص)")
    if tot_h:
        print(f"\n    الإجمالي: HTML {tot_h:,} → نص {tot_t:,} → مستخلص {tot_e:,}")
        print(f"    نسبة المستخلص من HTML: {100*tot_e/tot_h:.1f}% · الوفر: {100-100*tot_e/tot_h:.1f}%")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())