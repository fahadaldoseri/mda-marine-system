#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حارس تغيّر PDF — يُعلن صراحةً إن لم يتغيّر الملف بعد تعديل.

الأساس (ك-44): عُدّل القاموس في بيانات Brain ولم يتغير PDF، لأن التصدير يقرأ من
مصادر الموقع وتسلسل المزامنة لم يُنفَّذ، فمرّت دورة كاملة بإنذار كاذب بالإصلاح.

الاستخدام:
  python3 tools/pdf_change_guard.py --date 2026-10-20 --snapshot   # قبل التعديل
  python3 tools/pdf_change_guard.py --date 2026-10-20 --verify     # بعد إعادة البناء
الرمز: 0 تغيّر · 1 جديد بلا بصمة سابقة · 2 لم يتغيّر (مانع)
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, datetime
import os
from pathlib import Path

B = Path(__file__).resolve().parent.parent
S = Path(os.environ.get("SITE_DIR") or B.parent / "seawatch")
sys.path.insert(0, str(B / "validators"))
from check_pdf_format import page_metrics  # noqa: E402
SNAP = B / "logs" / ".pdf-snapshot"
PDF = S / "dist" / "reports" / "pdf"


def digest(p: Path) -> dict:
    """بصمة **المحتوى** لا بصمة الملف.

    عطل ك-49: تصديران متتاليان بلا أي تعديل أنتجا بصمتين ملفيتين مختلفتين (الحجم
    نفسه 1,109,917 بايت) لأن PDF غير حتمي. فالبصمة الملفية تُعلن «تغيّر» دائمًا
    ولا ترصد الفقد أبدًا. البصمة الصحيحة = نص المستخرج + عدد الصفحات + تعبئة كل صفحة.
    """
    txt = subprocess.run(["pdftotext", "-layout", str(p), "-"],
                         capture_output=True, text=True, timeout=300).stdout
    norm = re.sub(r"\s+", " ", txt).strip()
    pages = 0
    fills: list[float] = []
    try:
        fills, _ = page_metrics(p)
        pages = len(fills)
    except Exception:
        pass
    h = hashlib.sha256()
    h.update(norm.encode("utf-8"))
    tail = f"|pages={pages}|" + ",".join(f"{round(f)}" for f in fills)
    h.update(tail.encode("utf-8"))
    return {"sha256": h.hexdigest(), "chars": len(norm), "pages": pages,
            "last_fill": round(fills[-1]) if fills else 0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true")
    g.add_argument("--verify", action="store_true")
    a = ap.parse_args()

    pdf = PDF / f"{a.date}.pdf"
    if not pdf.exists():
        print(f"✘ لا ملف PDF: {pdf}"); return 2
    SNAP.mkdir(parents=True, exist_ok=True)
    f = SNAP / f"{a.date}.json"
    cur = digest(pdf)
    cur["mtime"] = datetime.datetime.fromtimestamp(pdf.stat().st_mtime, datetime.UTC) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")

    if a.snapshot:
        f.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✔ بُصمة المحتوى قبل التعديل: {cur['sha256'][:12]} · "
              f"{cur['chars']:,} حرفًا · {cur['pages']} صفحة")
        return 0

    if not f.exists():
        print("! لا بصمة سابقة — لا يمكن الحكم على التغيّر · تحذير")
        return 1
    old = json.loads(f.read_text(encoding="utf-8"))
    if old.get("sha256") == cur["sha256"]:
        print("  ✘ لم يتغيّر PDF بعد التعديل — الدورة لم تصل إلى المخرج، لا تعتبر الإصلاح ناجحًا")
        print(f"     البصمة نفسها: {cur['sha256'][:12]} · {cur['chars']:,} حرفًا · "
              f"{cur['pages']} صفحة")
        print("     السبب المتوقع: تعديل لم يُمَرَّ عبر merge_glossary ← sync_from_brain ← build_site")
        return 2
    print(f"  ✔ تغيّر محتوى PDF: {old['sha256'][:12]} → {cur['sha256'][:12]}")
    print(f"     الحروف: {old.get('chars',0):,} → {cur['chars']:,} · "
          f"الصفحات: {old.get('pages',0)} → {cur['pages']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
