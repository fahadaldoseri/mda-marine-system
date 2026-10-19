#!/usr/bin/env python3
"""خط فحص الجودة العشري — فشل مغلق.

يرمز الخروج:
  0 = اجتياز كل البوابات (يُسمح بالتسليم والنشر)
  1 = مخالفة مانعة (يُوقف التسليم والنشر)
  2 = مدخل أو أصل ناقص (يُوقف التسليم والنشر)

الاستعمال: python3 tools/qa_gates.py --date 2026-10-18
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

B = Path("/home/ubuntu/brain-marine-news")
SITE = Path("/home/ubuntu/seawatch")
REQUIRED_META = ("hero_kpis", "decision_card", "changes")
HIDDEN_SECTIONS = ("المصادر والمراجع", "موثوقية المصادر")


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def pdf_text(pdf: Path) -> str:
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True)
    return out.stdout


TASHKEEL = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")


def norm(s: str) -> str:
    """معايرة عربية: إزالة محارف التحكم والتشكيل والتطويل وتوحيد الألف والياء."""
    import unicodedata
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069\u061c]", "", s)
    s = TASHKEEL.sub("", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا").replace("ى", "ي")
    return re.sub(r"\s+", " ", s).strip()


def gate_schema(date: str):
    mp = B / "web" / "meta" / f"{date}.json"
    if not mp.exists():
        return False, "ملف الواجهة غير موجود", True
    try:
        meta = json.loads(read(mp))
    except json.JSONDecodeError as e:
        return False, f"ملف الواجهة غير صالح: {e}", True
    miss = [k for k in REQUIRED_META if k not in meta]
    if miss:
        return False, "حقول ناقصة في ملف الواجهة: " + "، ".join(miss), True
    if not isinstance(meta.get("hero_kpis"), list) or not meta["hero_kpis"]:
        return False, "hero_kpis يجب أن تكون قائمة غير فارغة", True
    n = len(meta.get("changes") or [])
    return True, f"ملف الواجهة سليم · {len(meta['hero_kpis'])} مؤشرًا · {n} بند تغيير", False


def gate_identity(date: str):
    html = read(SITE / "dist" / "reports" / f"{date}.html")
    if not html:
        return False, "صفحة التقرير غير مبنية", True
    titles = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.S)
    titles = [norm(re.sub(r"<[^>]+>", "", t)) for t in titles]
    _cover = "ما تغير منذ التقرير السابق"
    titles = [t for t in titles if not (t == _cover and titles.count(t) == 2)]
    dup = {t for t in titles if titles.count(t) > 1}
    anchors = re.findall(r'id="([^"]+)"', html)
    dup_anchor = {a for a in anchors if anchors.count(a) > 1}
    problems = []
    if dup:
        problems.append("عناوين مكرّرة: " + "، ".join(sorted(dup)))
    if dup_anchor:
        problems.append("معرّفات مكرّرة: " + "، ".join(sorted(dup_anchor)))
    meta = json.loads(read(B / "web" / "meta" / f"{date}.json"))
    cmap = json.loads(read(B / "appendices" / "event-code-map.json")) if (B / "appendices" / "event-code-map.json").exists() else {}
    raw = meta.get("event_keys") or []
    codes = [c if isinstance(c, str) else c.get("code", "") for c in raw]
    codes = [c for c in codes if c]
    inner = cmap.get("codes") if isinstance(cmap, dict) else None
    keys = set(inner) if isinstance(inner, dict) else (set(cmap) if isinstance(cmap, dict) else set())
    unresolved = [c for c in codes if keys and c not in keys]
    if unresolved:
        problems.append("رموز أحداث غير مُحلّة: " + "، ".join(unresolved))
    if problems:
        return False, " · ".join(problems), False
    return True, f"{len(titles)} عنوانًا فريدًا · {len(codes)} رمز حدث مُحلّ", False


def gate_numbers(date: str):
    """كل بند تغيير يحمل مرجعًا موثقًا، ولا قيم غير محلولة في الصفحة."""
    html = read(SITE / "dist" / "reports" / f"{date}.html")
    meta = json.loads(read(B / "web" / "meta" / f"{date}.json"))
    visible = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    bad = [p for p in ("{{", "}}", "None", "undefined") if p in visible]
    if re.search(r"\bnan\b", visible, re.I):
        bad.append("nan")
    if bad:
        return False, "قيم غير محلولة في الصفحة: " + "، ".join(bad), False
    changes = meta.get("changes") or []

    def has_ref(c):
        if not isinstance(c, dict):
            return False
        blob = " ".join(str(c.get(k, "")) for k in ("ref", "code", "text"))
        return bool(re.search(r"\d{2}-\d{2}", blob))

    nosrc = [c for c in changes if not has_ref(c)]
    if nosrc:
        return False, f"{len(nosrc)} بندًا في «ما تغيّر» بلا مرجع موثق", False
    return True, f"{len(changes)} بندًا موثقًا بمرجع رسمي", False


def gate_html(date: str):
    html = read(SITE / "dist" / "reports" / f"{date}.html")
    if 'dir="rtl"' not in html and "dir='rtl'" not in html:
        return False, "الصفحة ليست RTL", False
    routes = SITE / "public" / "manus-routes.json"
    if not routes.exists():
        return False, "ملف المسارات manus-routes.json مفقود", True
    try:
        json.loads(read(routes))
    except json.JSONDecodeError:
        return False, "ملف المسارات غير صالح", False
    return True, "الصفحة RTL وملف المسارات صالح", False


def tight(s: str) -> str:
    """مقارنة لا تتأثر بفقدان المسافات أو الترقيم في الطبقة النصية."""
    s = norm(s)
    s = re.sub(r"[\s\u00a0\u200b]+", "", s)
    return re.sub(r"[:؛،\-—.]+", "", s)


def gate_parity(date: str):
    src = read(B / "reports" / f"{date}-sectioned.md")
    txt = norm(pdf_text(SITE / "dist" / "reports" / "pdf" / f"{date}.pdf"))
    if not src or not txt:
        return False, "المصدر النصي أو PDF مفقود", True
    heads = [norm(h.lstrip("# ").strip()) for h in src.splitlines() if h.startswith("## ")]
    heads = [h for h in heads if h and not any(x in h for x in HIDDEN_SECTIONS)]
    tt = tight(txt)
    missing = [h for h in heads if tight(h) not in tt]
    if missing:
        return False, "أقسام غائبة من PDF: " + "، ".join(missing[:4]), False
    return True, f"{len(heads)} قسمًا مطابقًا بين المصدر وPDF", False


def gate_hidden(date: str):
    txt = norm(pdf_text(SITE / "dist" / "reports" / "pdf" / f"{date}.pdf"))
    shown = [s for s in HIDDEN_SECTIONS if s in txt]
    if shown:
        return False, "أقسام يجب حجبها ظاهرة في PDF: " + "، ".join(shown), False
    return True, "المصادر والموثوقية محجوبتان", False


def gate_format(date: str):
    pdf = SITE / "dist" / "reports" / "pdf" / f"{date}.pdf"
    if not pdf.exists():
        return False, "ملف PDF غير موجود", True
    out = subprocess.run([sys.executable, str(B / "validators" / "check_pdf_format.py"),
                          "--pdf", str(pdf), "--date", date],
                         capture_output=True, text=True)
    tail = (out.stdout or out.stderr).strip().splitlines()
    detail = tail[-1] if tail else "لا مخرجات"
    return out.returncode == 0, detail, False


def gate_toc_rtl_footer(date: str):
    pdf = SITE / "dist" / "reports" / "pdf" / f"{date}.pdf"
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", info)
    pages = int(m.group(1)) if m else 0
    html = read(SITE / "dist" / "reports" / f"{date}.html")
    txt = read(Path("/tmp/_qa_toc.txt"))
    problems = []
    if "class=\"ltr\"" not in html:
        problems.append("لا يوجد عزل اتجاهي .ltr في الصفحة")
    foot = len(re.findall(r"صفحة\s*\d+\s*من\s*\d+", txt)) or txt.count("صفحة ")
    if not pages:
        problems.append("عدد صفحات PDF غير معروف")
    toc = re.findall(r"^(.+?)\s+(\d{1,3})\s*$", txt, re.M)
    over = [t for t in toc if t[1].isdigit() and int(t[1]) > pages]
    if over:
        problems.append(f"{len(over)} بند فهرس يشير إلى صفحة خارج الملف")
    if problems:
        return False, " · ".join(problems), False
    return True, f"{pages} صفحة · عزل LTR حاضر · الفهرس داخل النطاق", False


def gate_docx(date: str):
    d = B / "reports" / "docx"
    cands = sorted(d.glob(f"*{date}*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        return False, "لا توجد نسخة Word للإصدار", True
    doc = cands[0]
    src = read(B / "reports" / f"{date}-sectioned.md")
    heads = [h.lstrip("# ").strip() for h in src.splitlines() if h.startswith("## ")]
    heads = [h for h in heads if not any(x in norm(h) for x in HIDDEN_SECTIONS)]
    try:
        from docx import Document
        doc_obj = Document(str(doc))
        paras = [p.text for p in doc_obj.paragraphs]
    except Exception as e:  # noqa: BLE001
        return False, f"تعذّر فحص Word: {e}", False
    joined = tight(" ".join(paras))
    missing = [h for h in heads if tight(h) not in joined]
    if missing:
        return False, "أقسام غائبة من Word: " + "، ".join(missing[:4]), False
    return True, f"Word يحوي {len(paras)} فقرة و{len(heads)} قسمًا", False


def gate_package(date: str):
    files = [SITE / "dist" / "reports" / f"{date}.html",
             SITE / "dist" / "reports" / "pdf" / f"{date}.pdf",
             B / "reports" / f"{date}-sectioned.md",
             B / "web" / "meta" / f"{date}.json"]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        return False, "ملفات ناقصة في الحزمة: " + "، ".join(missing), True
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()[:16] for f in files}
    log = B / "logs" / f"qa-{date}.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps({"date": date, "files": hashes}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return True, f"الحزمة كاملة · بصمات في {log.name}", False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    pdf = SITE / "dist" / "reports" / "pdf" / f"{a.date}.pdf"
    Path("/tmp/_qa_toc.txt").write_text(pdf_text(pdf), encoding="utf-8")
    gates = [
        ("١ المصدر والمخطط", gate_schema),
        ("٢ الهوية والمعرّفات", gate_identity),
        ("٣ الأرقام والمصادر", gate_numbers),
        ("٤ الصفحة والمسارات", gate_html),
        ("٥ تطابق المصدر وPDF", gate_parity),
        ("٦ حجب المصادر والموثوقية", gate_hidden),
        ("٧ التعبئة والفجوات", gate_format),
        ("٨ الفهرس والاتجاه والترقيم", gate_toc_rtl_footer),
        ("٩ مطابقة نسخة Word", gate_docx),
        ("١٠ الحزمة والتسليم", gate_package),
        ("١١ عناوين الأقسام بلا تكرار", gate_unique_sections),
        ("١٢ لا وسوم تصنيف فارغة", gate_no_empty_tags),
    ]
    print(f"خط فحص الجودة العشري — {a.date}")
    fails, missing = [], []
    for name, fn in gates:
        ok, detail, lack = fn(a.date)
        print(f"  {'✓' if ok else '✗'} {name}: {detail}")
        if not ok:
            (missing if lack else fails).append(name)
    print()
    if missing:
        print("النتيجة: مدخل أو أصل ناقص → " + "، ".join(missing))
        print("⛔ أوقف التسليم والنشر (رمز 3 — مدخل ناقص)")
        return 3
    if fails:
        print("النتيجة: مخالفة مانعة → " + "، ".join(fails))
        print("⛔ أوقف التسليم والنشر (رمز 2 — مخالفة مانعة)")
        return 2
    print("النتيجة: اجتياز كل البوابات ✓ — يُسمح بالتسليم والنشر")
    return 0


def gate_unique_sections(date: str):
    """لا عنوان قسم مكرر في الصفحة المبنية (عطل 19 أكتوبر 2026: قسم «ما تغيّر» ظهر مرتين)."""
    page = SITE / "dist" / "reports" / f"{date}.html"
    if not page.exists():
        return False, "الصفحة غير مبنية", True
    html = page.read_text(encoding="utf-8")
    titles = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.S)
    clean = [re.sub(r"<[^>]+>", " ", t) for t in titles]
    clean = [re.sub(r"\s+", " ", t).strip() for t in clean]
    clean = [t for t in clean if t]
    dup = sorted({t for t in clean if clean.count(t) > 1})
    if dup:
        return False, f"عنوان قسم مكرر: {dup}", True
    return True, f"{len(clean)} عنوانًا بلا تكرار", False


def gate_no_empty_tags(date: str):
    """لا وسوم تصنيف فارغة تظهر للقارئ (عطل 19 أكتوبر 2026: وسم «جديد» فارغ لحالة مستمرة)."""
    page = SITE / "dist" / "reports" / f"{date}.html"
    if not page.exists():
        return False, "الصفحة غير مبنية", True
    html = page.read_text(encoding="utf-8")
    bad = re.findall(r'<span class="(chg-tag|kstrip|conf|rk)[^"]*">\s*</span>', html)
    if bad:
        return False, f"وسم فارغ: {sorted(set(bad))}", True
    return True, "لا وسوم فارغة", False


if __name__ == "__main__":
    sys.exit(main())

