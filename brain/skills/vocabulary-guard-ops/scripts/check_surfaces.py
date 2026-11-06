#!/usr/bin/env python3
"""مسح كل سطح يُقرأه القارئ بحثًا عن ألفاظ المنع، مع تطبيع النص المشتق.

خرائط الأسطح تُقرأ من ملف JSON:
[
  {"label": "المتن",        "path": "brain/reports/2026-10-27-sectioned.md", "kind": "text"},
  {"label": "الواجهة",      "path": "brain/web/meta/2026-10-27.json",        "kind": "json"},
  {"label": "ملخص مشتق",    "path": "brain/logs/tg-digest-2026-10-27.html",  "kind": "html",
   "derive": ["brain/tools/make_tg_digest.py", "--date", "2026-10-27"]},
  {"label": "صفحة الإصدار", "path": "site/dist/reports/2026-10-27.html",     "kind": "html"},
  {"label": "PDF",          "path": "site/dist/reports/pdf/2026-10-27.pdf",  "kind": "pdf",
   "attest": "brain/reports/2026-10-27-sectioned.md"}
]

قواعد:
  · السطح ذو "derive" يُبنى من مصدره **قبل** الفحص (لا يُحكم على نسخة قديمة).
  · النص المشتق (html/pdf) يُطبَّع: NFKC + إزالة الكشيدة وعلامات الاتجاه والحركات + تصحيح مواضع الترقيم.
  · "kind": "pdf" + "attest" يُقاس بالإسناد (رموز البلاغ والمصطلحات اللاتينية)، لا بتشابه النص العربي.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

MARKS = "\u0640\u200b-\u200f\u202a-\u202e\u2066-\u2069\u064b-\u0652\u0670"


def norm_derived(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(f"[{MARKS}]", "", t)
    t = re.sub(r"\s+([،.:؛؟!])", r"\1", t)
    return re.sub(r"[ \t]{2,}", " ", t)


def strip_html(t: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"&nbsp;?", " ", t)


def beacons(src: str) -> list[str]:
    """إشارات لاتينية لا يمسّها استخراج PDF: رموز البلاغ والمصطلحات الأجنبية."""
    prose = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", src)
    prose = re.sub(r"https?://\S+", " ", prose)
    return sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9._/-]{3,}", prose)))


def surface_text(s: dict, tmp: Path) -> tuple[str, str]:
    p = Path(s["path"])
    if s.get("derive"):
        tool = Path(s["derive"][0])
        if tool.exists():
            subprocess.run([sys.executable, str(tool), *s["derive"][1:]], capture_output=True, text=True)
    kind = s.get("kind", "text")
    if kind == "pdf":
        out = tmp / "pdf.txt"
        r = subprocess.run(["pdftotext", "-layout", str(p), str(out)], capture_output=True, text=True)
        if r.returncode != 0:
            return "", "تعذّر استخراج PDF"
        return out.read_text(encoding="utf-8", errors="replace"), ""
    if not p.exists():
        return "", "الملف غير موجود"
    raw = p.read_text(encoding="utf-8", errors="replace")
    if kind == "html":
        return norm_derived(strip_html(raw)), ""
    if kind == "text":
        return norm_derived(raw), ""
    return raw, ""


def main() -> int:
    ap = argparse.ArgumentParser(description="فحص ألفاظ المنع على كل الأسطح")
    ap.add_argument("--registry", required=True, help="السجل الحاكم")
    ap.add_argument("--surfaces", required=True, help="ملف JSON بوصف الأسطح")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    reg = json.loads(Path(a.registry).read_text(encoding="utf-8"))
    entries = reg.get("entries", reg) if isinstance(reg, dict) else reg
    banned = [str(e["term"]) for e in entries if e.get("status") == "approved"
              and all(str(p).strip() for p in (e.get("plain") or [None]))]
    sur = json.loads(Path(a.surfaces).read_text(encoding="utf-8"))
    rows, blocked = [], 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for s in sur:
            text, err = surface_text(s, tmp)
            if s.get("kind") == "pdf":
                src = Path(s["attest"]) if s.get("attest") else None
                if src and src.exists() and text:
                    toks = beacons(src.read_text(encoding="utf-8"))
                    miss = [t for t in toks if t not in text]
                    ok = (len(miss) / max(1, len(toks))) <= 0.15
                    rows.append({"label": s["label"], "status": "مغطى بالإسناد" if ok else "غير مُسند",
                                 "hits": miss[:5], "note": f"مفقود {len(miss)}/{len(toks)}"})
                    blocked += 0 if ok else 1
                else:
                    rows.append({"label": s["label"], "status": "غير مغطى", "hits": [], "note": err})
                    blocked += 1
                continue
            if err:
                rows.append({"label": s["label"], "status": "غير مغطى", "hits": [], "note": err})
                blocked += 1
                continue
            hits = [b for b in banned if b in text]
            rows.append({"label": s["label"], "status": "مانع" if hits else "مغطى",
                         "hits": hits, "note": ""})
            blocked += 1 if hits else 0
    res = {"surfaces": len(rows), "blocked": blocked, "rows": rows}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"  {r['label']:<28} {r['status']:<14} {r['hits']}")
        print(f"── الأسطح: {len(rows)} · مانعة: {blocked}")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
