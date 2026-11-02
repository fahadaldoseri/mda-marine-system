#!/usr/bin/env python3
"""خط فحص الجودة العشري — فشل مغلق.

يرمز الخروج:
  0 = اجتياز كل البوابات (يُسمح بالتسليم والنشر)
  1 = مخالفة مانعة (يُوقف التسليم والنشر)
  2 = مدخل أو أصل ناقص (يُوقف التسليم والنشر)

الاستعمال: python3 tools/qa_gates.py --date 2026-10-18
"""
from __future__ import annotations
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
SITE = _tree("SITE_DIR", _ROOT, "seawatch", "site")

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

B = Path(f"{BRAIN}")
SITE = Path(f"{SITE}")
REQUIRED_META = ("hero_kpis", "decision_card", "changes")
HIDDEN_SECTIONS = ("المصادر والمراجع", "موثوقية المصادر")
try:  # سياسة الأقسام: مصدر واحد يقرأه المولّد والبوابات (ك-86/ك-91)
    import json as _json
    _pol = _json.loads((B / "appendices" / "report-sections-policy.json").read_text(encoding="utf-8"))
    HIDDEN_SECTIONS = tuple(HIDDEN_SECTIONS) + tuple(_pol.get("hidden_sections", []))
    _norm_hidden = lambda arr: tuple(norm(x) for x in arr)  # توحيد التطبيع قبل المقارنة
except Exception:
    pass


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
    # لا تُحتسب سمات data-*-id؛ تُقرأ سمات id الحقيقية فقط.
    anchors = re.findall(r'(?<![\w-])id="([^"]+)"', html)
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
    if print_pipeline_disabled() and not txt:
        return True, "PDF مستثنى — الطباعة معطّلة بطلب المالك في المانيفست", False
    if not src or not txt:
        return False, "المصدر النصي أو PDF مفقود", True
    heads = [norm(h.lstrip("# ").strip()) for h in src.splitlines() if h.startswith("## ")]
    _H = tuple(norm(x) for x in HIDDEN_SECTIONS)
    heads = [h for h in heads if h and not any(x in h for x in _H)]
    tt = tight(txt)
    def _seen_pdf(hh):
        k = tight(hh)
        return k in tt or k[:10] in tt
    missing = [h for h in heads if not _seen_pdf(h)]
    if missing:
        return False, "أقسام غائبة من PDF: " + "، ".join(missing[:4]), False
    return True, f"{len(heads)} قسمًا مطابقًا بين المصدر وPDF", False


# ── قياس الحجب: ما يراه القارئ في المتن، لا ما يمكن عدّه في الملف ──────────
# عطل 2026-10-28: القياس القديم كان يعدّ سطر الفهرس (‏«.10 الوقائع الجديدة ص 6») وإحالة
# داخل المتن إظهارًا للقسم، فيمنع تسليمًا سليمًا. القاعدة الآن:
#   1) يُقاس المتن وحده — الملحق (المجموعة المنقولة) هو موضعها المعتمد.
#   2) سطر الفهرس (يحمل «ص» ورقم صفحة) ليس إظهارًا للقسم.
#   3) يُعدّ القسم ظاهرًا فقط إذا جاء عنوانًا قائمًا بذاته، لا إحالة داخل جملة.
APPENDIX_MARKERS = ("المجموعة المنقولة من التقرير اليومي", "ملحق إضافات")
_INDEX_LINE = re.compile(r"ص\s*[0-9]+")


def _is_index_line(line: str) -> bool:
    """سطر فهرس: يحمل رقم صفحة أو نقاط قيادة — ليس عنوانًا في المتن."""
    return bool(_INDEX_LINE.search(line)) or "..." in line or "…" in line


def _body_before_appendix(txt: str) -> str:
    """المتن حتى بداية الملحق؛ وما بعده لا يُحسب إظهارًا."""
    marks = [txt.find(m) for m in APPENDIX_MARKERS]
    marks = [m for m in marks if m > 0]
    return txt[:min(marks)] if marks else txt


def _heading_shown(text: str, title: str) -> bool:
    """يظهر القسم فقط إن كان عنوانًا قائمًا بذاته في المتن."""
    t = norm(title).strip()
    for line in text.splitlines():
        if _is_index_line(line):
            continue
        n = norm(line).strip()
        if not n or not n.startswith(t):
            continue
        if len(n[len(t):].strip()) <= 8:
            return True
    return False


def gate_hidden(date: str):
    raw = pdf_text(SITE / "dist" / "reports" / "pdf" / f"{date}.pdf")
    body = _body_before_appendix(raw)
    shown = [s for s in HIDDEN_SECTIONS if _heading_shown(body, s)]
    if shown:
        return False, "أقسام يجب حجبها ظاهرة في متن PDF: " + "، ".join(shown), False
    return True, "الأقسام المنقولة محجوبة عن المتن وموضعها المعتمد الملحق", False


def print_pipeline_disabled() -> bool:
    """هل خط الطباعة معطّل بطلب المالك في المانيفست؟ (يُعاد التسليح تلقائيًا عند تفعيله)"""
    try:
        rb = json.loads(read(B / "runbook" / "runbook.json"))
    except (json.JSONDecodeError, AttributeError):
        return False
    if isinstance(rb.get("print"), dict) and rb["print"].get("disabled") is True:
        return True
    for step in rb.get("steps", []):
        if step.get("id") == "B020":
            return step.get("disabled") is True
    return False


def gate_format(date: str):
    pdf = SITE / "dist" / "reports" / "pdf" / f"{date}.pdf"
    # ملف فارغ (0 بايت) أثرُ تصديرٍ مبتور: يُعامل معاملة «لم يُنتَج» ولا يُقبل كدليل على مخرج سليم.
    produced = pdf.exists() and pdf.stat().st_size > 0
    if not produced and print_pipeline_disabled():
        return True, "التعبئة والفجوات مستثناة — الطباعة معطّلة بطلب المالك", False
    if not produced:
        return False, "ملف PDF غير موجود", True
    out = subprocess.run([sys.executable, str(B / "validators" / "check_pdf_format.py"),
                          "--pdf", str(pdf), "--date", date],
                         capture_output=True, text=True)
    text = (out.stdout or out.stderr).strip()
    lines = text.splitlines()
    detail = lines[-1] if lines else "لا مخرجات"
    if out.returncode == 0:
        return True, detail, False
    violations = [ln.strip() for ln in lines if ln.strip().startswith("✗")]
    style_only = bool(violations) and all("نمط الطباعة" in ln for ln in violations)
    if style_only and print_pipeline_disabled():
        return True, ("الطباعة معطّلة بطلب المالك — بند «نمط الطباعة» غير مانع · "
                      "يُعاد تسليحه تلقائيًا عند تفعيل الطباعة · " + detail), False
    return False, detail, False


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
    if not pages and print_pipeline_disabled():
        if problems:
            return False, " · ".join(problems), False
        return True, "الفهرس والاتجاه مستثنيان من قياس PDF — الطباعة معطّلة بطلب المالك", False
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
    if not cands and print_pipeline_disabled():
        return True, "نسخة Word مستثناة — الطباعة معطّلة بطلب المالك في المانيفست", False
    if not cands:
        return False, "لا توجد نسخة Word للإصدار", True
    doc = cands[0]
    src = read(B / "reports" / f"{date}-sectioned.md")
    heads = [h.lstrip("# ").strip() for h in src.splitlines() if h.startswith("## ")]
    heads = [h for h in heads if not any(x in norm(h) for x in tuple(norm(y) for y in HIDDEN_SECTIONS))]
    try:
        from docx import Document
        doc_obj = Document(str(doc))
        paras = [p.text for p in doc_obj.paragraphs]
    except Exception as e:  # noqa: BLE001
        return False, f"تعذّر فحص Word: {e}", False
    joined = tight(" ".join(paras))
    def _seen_docx(hh):
        k = tight(hh)
        return k in joined or k[:10] in joined
    missing = [h for h in heads if not _seen_docx(h)]
    if missing:
        return False, "أقسام غائبة من Word: " + "، ".join(missing[:4]), False
    return True, f"Word يحوي {len(paras)} فقرة و{len(heads)} قسمًا", False


def gate_package(date: str):
    files = [SITE / "dist" / "reports" / f"{date}.html",
             B / "reports" / f"{date}-sectioned.md",
             B / "web" / "meta" / f"{date}.json"]
    if not print_pipeline_disabled():
        files.insert(1, SITE / "dist" / "reports" / "pdf" / f"{date}.pdf")
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        return False, "ملفات ناقصة في الحزمة: " + "، ".join(missing), True
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()[:16] for f in files}
    log = B / "logs" / f"qa-{date}.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps({"date": date, "files": hashes}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return True, f"الحزمة كاملة · بصمات في {log.name}", False


def gate_site_output(date: str):
    """فحص مخرجات كل صفحات الموقع: أقواس كود التنسيق · قاعدة الاتجاه · نجوم خام ·
    مستويات ثقة معرّبة · وسوم اتجاه مقطّعة · حاويات جداول قابلة للتركيز."""
    pages = sorted((SITE / "dist").rglob("*.html"))
    if not pages:
        return False, "لا صفحات مبنية في dist", True
    prob = []
    for pg in pages:
        h = read(pg)
        css = "\n".join(m.group(1) for m in re.finditer(r"<style[^>]*>(.*?)</style>", h, re.S))
        depth = 0
        stray = 0
        for ch in css:
            if ch == "{":
                depth += 1
            elif ch == "}":
                if depth == 0:
                    stray += 1
                else:
                    depth -= 1
        if stray:
            prob.append(f"{pg.name}: قوس زائد في كود التنسيق ({stray})")
        if not re.search(r"\.ltr\s*\{", css):
            prob.append(f"{pg.name}: قاعدة .ltr للإحداثيات غائبة")
        if re.search(r"</span>([/\-.:])<span class=\"ltr\">", h):
            prob.append(f"{pg.name}: وسم اتجاه مقطّع")
        body = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", h.split("<body", 1)[-1], flags=re.S)
        if "**" in body:
            prob.append(f"{pg.name}: علامات نجوم ظاهرة ({body.count('**')})")
        for w in ("high", "medium", "low"):
            if f"<td>{w}</td>" in h:
                prob.append(f"{pg.name}: مستوى ثقة بالإنجليزية ({w})")
        for m in re.finditer(r'<div class="(?:tbl-wrap|tbl-scroll)"[^>]*>\s*<table', h):
            if "tabindex=" not in m.group(0):
                prob.append(f"{pg.name}: حاوية جدول غير قابلة للتركيز")
                break
    if prob:
        return False, " · ".join(prob[:4]) + (f" · +{len(prob) - 4}" if len(prob) > 4 else ""), False
    return True, f"{len(pages)} صفحة سليمة: أقواس · اتجاه · نجوم · ثقة · جداول", False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    pdf = SITE / "dist" / "reports" / "pdf" / f"{a.date}.pdf"
    Path("/tmp/_qa_toc.txt").write_text(pdf_text(pdf), encoding="utf-8")
    gates = [
        ("1 المصدر والمخطط", gate_schema),
        ("2 الهوية والمعرّفات", gate_identity),
        ("3 الأرقام والمصادر", gate_numbers),
        ("4 الصفحة والمسارات", gate_html),
        ("5 تطابق المصدر وPDF", gate_parity),
        ("6 حجب المصادر والموثوقية", gate_hidden),
        ("7 التعبئة والفجوات", gate_format),
        ("8 الفهرس والاتجاه والترقيم", gate_toc_rtl_footer),
        ("9 مطابقة نسخة Word", gate_docx),
        ("10 الحزمة والتسليم", gate_package),
        ("11 عناوين الأقسام بلا تكرار", gate_unique_sections),
        ("12 لا وسوم تصنيف فارغة", gate_no_empty_tags),
        ("13 مخرجات الموقع (اتجاه وأقواس وجداول)", gate_site_output),
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
