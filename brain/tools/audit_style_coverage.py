#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""قياس تغطية بوابة الأسلوب على كل سطح يقرأه القارئ.

القاعدة (ط15): كل نص ثابت يظهر للقارئ يدخل في مدى بوابة الأسلوب. هذه الأداة تُثبت ذلك أو تعلن الثغر:
تُحوّل كل سطح إلى نص، وتُمرّره على بوابة الأسلوب وبوابة الألفاظ المصطنعة، وتعرض جدولًا:
السطح · المصدر · فُحص؟ · النتيجة.

الأسطح: المتن · ملف الواجهة (القاموس وبطاقة القرار) · رسالة تلغرام · صفحة التقرير ·
صفحة المصادر · الصفحة الرئيسية · PDF (قياس محدود: استخراج العربي يعكس الحروف).

رموز الخروج: 0 كل الأسطح مغطاة · 2 سطح غير مغطى أو مانع · 70 انهيار.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SITE = Path(os.environ.get("SITE") or os.environ.get("SITE_DIR") or (Path.home() / "seawatch"))
TODAY = date.today().isoformat()
TMP = Path(tempfile.gettempdir()) / "style-coverage"


def strip_html(raw: str) -> str:
    """يحوّل HTML إلى نص، ويحفظ كل صف جدول في سطر واحد بفواصل أنابيب.

    السبب: بوابة عيوب الصياغة تستثني أسطر الجداول من قياس «قالب الجملة المتكرر»،
    لأن تكرار الخلية بنية جدول لا قالب جملة. فلو سطّحنا الجدول إلى أسطر منفصلة
    لظهر كل مصدر بعينه كأنه «قالب جملة» — قياس خاطئ لا عيب في الصفحة.
    """
    raw = re.sub(r"(?is)<(script|style|noscript|template)[^>]*>.*?</\1>", " ", raw)
    rows = []
    for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", raw):
        cells = [re.sub(r"(?s)<[^>]+>", " ", c) for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row)]
        cells = [html.unescape(re.sub(r"\s+", " ", c)).strip() for c in cells]
        rows.append(" | ".join(c for c in cells if c))
    raw = re.sub(r"(?is)<(table|thead|tbody|tfoot)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", "\n", raw)
    return html.unescape(raw) + "\n" + "\n".join(rows)


def flatten_json(obj, out: list[str]) -> None:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            flatten_json(v, out)
    elif isinstance(obj, list):
        for v in obj:
            flatten_json(v, out)


def run_gate(cmd: list[str], text_file: Path) -> tuple[int, list[str]]:
    r = subprocess.run(cmd + [str(text_file)], capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    keys = [ln.strip() for ln in out.splitlines()
            if any(k in ln for k in ("✗", "✘", "مخالفة", "الألفاظ المصطنعة", "النتيجة:", "مقبول"))]
    return r.returncode, keys[:6]


def surfaces(day: str) -> list[dict]:
    return [
        {"label": "المتن (التقرير)", "kind": "text", "path": BASE / "reports" / f"{day}-sectioned.md"},
        {"label": "ملف الواجهة (القاموس وبطاقة القرار)", "kind": "json",
         "path": BASE / "web" / "meta" / f"{day}.json"},
        {"label": "رسالة تلغرام", "kind": "html", "path": BASE / "logs" / f"tg-digest-{day}.html"},
        {"label": "صفحة التقرير", "kind": "html", "path": SITE / "dist" / "reports" / f"{day}.html"},
        {"label": "صفحة المصادر", "kind": "html", "path": SITE / "dist" / "sources.html"},
        {"label": "الصفحة الرئيسية", "kind": "html", "path": SITE / "dist" / "index.html"},
        {"label": "PDF (قياس محدود)", "kind": "pdf", "path": SITE / "dist" / "reports" / "pdf" / f"{day}.pdf"},
    ]


def extract(s: dict, idx: int) -> tuple[Path | None, str]:
    p = s["path"]
    if not p.exists():
        return None, "المصدر غير موجود"
    tgt = TMP / f"{idx}.txt"
    if s["kind"] == "text":
        tgt.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    elif s["kind"] == "json":
        vals: list[str] = []
        flatten_json(json.loads(p.read_text(encoding="utf-8")), vals)
        tgt.write_text("\n".join(vals), encoding="utf-8")
    elif s["kind"] == "html":
        tgt.write_text(strip_html(p.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
    else:
        r = subprocess.run(["pdftotext", "-layout", str(p), str(tgt)], capture_output=True, text=True)
        if r.returncode != 0:
            return None, "تعذّر استخراج نص PDF (pdftotext)"
    if not tgt.exists() or tgt.stat().st_size < 20:
        return None, "النص المستخرج فارغ"
    return tgt, ""


def pdf_link_proof(pdf_text: str, day: str) -> tuple[bool, str]:
    """إثبات أن PDF بُني من نصِّ الإصدار نفسه — بمدخلات لاتينية لا يمسّها استخراج العربي.

    السبب: استخراج نص PDF العربي يعكس الحروف ويفصلها، فقياس الألفاظ العربية عليه غير صالح بنيويًا.
    البديل الصادق: رموز البلاغ `MN-YYYY-MM-DD-NN` والمصطلحات اللاتينية تُستخرج سليمة،
    فوجودها في PDF هو ما يثبت أنه من النص المعتمد نفسه الذي مرّ على البوابة.
    """
    md = BASE / "reports" / f"{day}-sectioned.md"
    src = md.read_text(encoding="utf-8") if md.exists() else ""
    if not src:
        return False, "نص الإصدار غير موجود — لا يمكن الإسناد"
    codes = sorted(set(re.findall(r"MN-\d{4}-\d{2}-\d{2}-\d+", src)))
    # الروابط لا تُطبع في PDF بنصها، فلا تُحسب مفقودة: تُستثنى أولًا.
    prose = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", src)
    prose = re.sub(r"https?://\S+", " ", prose)
    toks = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9._/-]{3,}", prose)))
    miss_codes = [c for c in codes if c not in pdf_text]
    miss_toks = [t for t in toks if t not in pdf_text]
    ratio = 1 - len(miss_toks) / max(1, len(toks))
    ok = not miss_codes and ratio >= 0.90
    note = (f"إسناد PDF: رموز البلاغ {len(codes) - len(miss_codes)}/{len(codes)} · "
            f"المصطلحات اللاتينية {round(ratio * 100)}% ({len(toks) - len(miss_toks)}/{len(toks)}) "
            f"· قياس الألفاظ العربية على PDF غير صالح بنيويًا (الاستخراج يعكس الحروف)")
    return ok, note


def main() -> int:
    ap = argparse.ArgumentParser(description="قياس تغطية بوابة الأسلوب لكل سطح")
    ap.add_argument("--date", default=TODAY)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)

    rows, blocked, uncovered = [], 0, 0
    for i, s in enumerate(surfaces(a.date), 1):
        tgt, err = extract(s, i)
        if tgt is None:
            uncovered += 1
            rows.append({"label": s["label"], "path": str(s["path"]), "status": "غير مغطى",
                         "note": err, "style": "—", "prose": "—"})
            continue
        sc, s_out = run_gate(["python3", str(BASE / "validators" / "check_style.py")], tgt)
        pc, p_out = run_gate(["python3", str(BASE / "validators" / "check_prose_defects.py"), "--md"], tgt)
        # بوابة المصطنعة تُرجع 1 للتحذير و2 للمنع (وهو سلوك البوابة نفسها في التسليم)
        if s["kind"] == "pdf":
            linked, note = pdf_link_proof(tgt.read_text(encoding="utf-8", errors="replace"), a.date)
            if not linked:
                blocked += 1
            rows.append({
                "label": s["label"], "path": str(s["path"]),
                "status": "مغطى بالإسناد" if linked else "مانع",
                "note": note,
                "style": "— (لا يُقاس على PDF)",
                "prose": "— (لا يُقاس على PDF)",
                "findings": [],
                "text_sha256": hashlib.sha256(tgt.read_bytes()).hexdigest()[:16],
            })
            continue
        ok = sc == 0 and pc in (0, 1)
        if not ok:
            blocked += 1
        note = ""
        rows.append({
            "label": s["label"], "path": str(s["path"]),
            "status": "مغطى" if ok else "مانع",
            "note": note,
            "style": "مقبول" if sc == 0 else f"منع ({sc})",
            "prose": "مقبول" if pc == 0 else ("تحذير (1)" if pc == 1 else f"منع ({pc})"),
            "findings": (s_out + p_out)[:6],
            "text_sha256": hashlib.sha256(tgt.read_bytes()).hexdigest()[:16],
        })

    if a.json:
        print(json.dumps({"date": a.date, "rows": rows}, ensure_ascii=False, indent=2))
    else:
        print(f"=== تغطية بوابة الأسلوب — {a.date} ===")
        print(f"{'السطح':<42} {'النتيجة':<14} {'الأسلوب':<10} {'المصطنعة':<10}")
        for r in rows:
            print(f"{r['label'][:41]:<42} {r['status']:<14} {r['style']:<10} {r['prose']:<10}  {r['note']}")
            for f in r.get("findings", [])[:3]:
                print(f"      · {f}")
        print(f"── الأسطح: {len(rows)} · مغطاة: {len(rows) - uncovered - blocked} · "
              f"غير مغطاة: {uncovered} · مانعة: {blocked}")
    return 2 if (uncovered or blocked) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(70)
