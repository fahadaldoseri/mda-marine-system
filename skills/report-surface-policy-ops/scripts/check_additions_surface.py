#!/usr/bin/env python3
"""بوابة سطح الإضافات وسياسة النقل المؤرخة، قراءة فقط."""
from __future__ import annotations
import argparse, html, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve()
SKILL = HERE.parents[1]
def infer(name, fallback):
    val = os.environ.get(name)
    if val and Path(val).is_dir(): return Path(val).resolve()
    for cand in (SKILL / "../../" / fallback, Path.home() / fallback):
        if cand.is_dir(): return cand.resolve()
    return Path(fallback).resolve()


def load_policy(brain: Path, site: Path) -> dict:
    for p in (brain/"appendices/report-sections-policy.json", site/"sources/report-sections-policy.json", brain/"sources/report-sections-policy.json"):
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    raise SystemExit("لم تُعثر سياسة الأقسام")

def headings(path: Path) -> list[str]:
    if not path.is_file(): return []
    text=path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower()==".md":
        return [re.sub(r"\s+#+$", "", x).strip() for x in re.findall(r"^##\s+(.+?)\s*$", text, re.M)]
    return [html.unescape(re.sub(r"<[^>]+>", "", x).strip()) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", text, re.S|re.I)]

def contains(title: str, candidates: list[str]) -> bool:
    return any(title in x or x in title for x in candidates)

def pdf_text(path: Path) -> str:
    if not path.is_file(): return ""
    r=subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
    return r.stdout if r.returncode==0 else ""


BIDI = re.compile(r"[\u202a-\u202e\u2066-\u2069\u200e\u200f]")
TASHKEEL = re.compile(r"[\u064b-\u0652\u0640]")


def norm(s: str) -> str:
    """تطبيع نصّ عربي/لاتيني: بلا محارف اتجاه ولا تشكيل، ومسافات موحّدة."""
    s = BIDI.sub("", s or "")
    s = TASHKEEL.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def violating_pages(text: str, titles: list[str], min_index_hits: int = 3) -> dict:
    """يرجع {العنوان: [صفحات مخالفة]} — مطابقة سطريّة لعناوين الأقسام فقط.

    القواعد: تُطابق العناوين كأسطر مستقلة (لا داخل جملة) · تُستثنى صفحات الفهرس ·
    وما يقع عند ملحق «إضافات» أو بعده مسموح.
    """
    raw = (text or "").split("\f")
    if not raw:
        return {}
    # التقسيم إلى أسطر قبل التطبيع: التطبيع يدمج المسافات ومنها فاصل السطر
    lines = [[norm(l) for l in p.splitlines() if norm(l)] for p in raw]

    def is_heading(line: str, title: str) -> bool:
        if not line or not title:
            return False
        bare = re.sub(r"^[\d\s.\-–—·]*", "", line)
        bare = re.sub(r"[\s:·\-–—.]+$", "", bare)
        return bare == title or line == title

    titles = [x for x in titles if norm(x)]
    hits = {x: [] for x in titles}
    index_pages = set()
    for i, ls in enumerate(lines):
        n = sum(1 for x in titles if any(is_heading(l, norm(x)) for l in ls))
        if n >= min_index_hits:
            index_pages.add(i + 1)
    annex = None
    for i, ls in enumerate(lines):
        if i + 1 in index_pages:
            continue
        for j, l in enumerate(ls):
            if is_heading(l, "إضافات"):
                annex = (i + 1, j)
                break
        if annex:
            break
    for i, ls in enumerate(lines):
        for x in titles:
            nx = norm(x)
            for j, l in enumerate(ls):
                if not is_heading(l, nx):
                    continue
                if (i + 1) in index_pages:
                    continue
                if annex and ((i + 1) > annex[0] or ((i + 1) == annex[0] and j > annex[1])):
                    continue
                hits[x].append(i + 1)
                break
    return {x: sorted(set(v)) for x, v in hits.items() if v}


def report_date(a, site, brain):
    if a.date: return a.date
    candidates=sorted((site/"sources/reports").glob("*-sectioned.md")) or sorted((brain/"reports").glob("*-sectioned.md"))
    return candidates[-1].name.replace("-sectioned.md", "") if candidates else ""

def emit(errors, warnings, notes, add_n, req_n):
    print(f"سطح إضافات: {add_n} عنوانًا · المطلوب نقلُه: {req_n}")
    for n in notes: print("  · "+n)
    for w in warnings: print("  ! "+w)
    if errors:
        for e in errors: print("  × "+e)
        print("النتيجة: مخالف — البوابة مغلقة")
        return 2
    print("  ✓ النقل مثبت: المتن محفوظ، الإضافات مكتملة، والعناوين المنقولة غائبة عن السطح القديم")
    if warnings:
        print("النتيجة: مطابق للويب فقط مع تحذيرات طباعة؛ شغّل --strict-print قبل التسليم")
    else:
        print("النتيجة: مطابق")
    return 0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--brain", default=str(infer("BRAIN_DIR", "brain-marine-news")))
    ap.add_argument("--site", default=str(infer("SITE_DIR", "seawatch")))
    ap.add_argument("--pdf", default="")
    ap.add_argument("--strict-print", action="store_true", help="اجعل غياب أو مخالفة PDF مانعًا")
    a=ap.parse_args(); brain=Path(a.brain).expanduser().resolve(); site=Path(a.site).expanduser().resolve(); dist=site/"dist"
    pol=load_policy(brain, site); day=report_date(a,site,brain)
    adds=list(pol.get("required_in_additions") or pol.get("additions_sections") or [])
    req=list(pol.get("required_in_report") or [])
    required_md=list(pol.get("required_in_md") or [])
    hidden=set(pol.get("hidden_sections") or [])
    effective=str(pol.get("additions_effective_from") or "")
    moved=set(adds); errors=[]; warnings=[]; notes=[]
    if not adds: errors.append("السياسة بلا required_in_additions")
    clash=sorted(set(req)&hidden)
    if clash: errors.append("تناقض في السياسة، مطلوب في التقرير ومخفى معًا: "+" · ".join(clash))
    md=site/"sources/reports"/f"{day}-sectioned.md"
    if not md.is_file(): md=brain/"reports"/f"{day}-sectioned.md"
    src_h=headings(md)
    for title in required_md:
        if not contains(title, src_h): errors.append(f"المتن لا يحفظ required_in_md: «{title}»")
    add_file=dist/"additions.html"; add_h=headings(add_file)
    report=dist/"reports"/f"{day}.html"; report_h=headings(report)
    if effective and day < effective:
        notes.append(f"الإصدار {day} أقدم من سريان النقل {effective}؛ لا يُعاد تشكيل الأرشيف رجعيًا")
    else:
        if not add_file.is_file(): errors.append(f"صفحة الإضافات غير مبنية: {add_file}")
        for title in adds:
            n=sum(1 for h in add_h if title in h or h in title)
            if n==0: errors.append(f"عنوان منقول غائب عن الإضافات: «{title}»")
            elif n>1: errors.append(f"عنوان منقول مكرر {n} مرات في الإضافات: «{title}»")
            if contains(title, report_h): errors.append(f"عنوان منقول ما زال ظاهرًا في التقرير: «{title}»")
        if not report.is_file(): errors.append(f"صفحة التقرير غير مبنية: {report}")
        else:
            for title in req:
                if not contains(title, report_h): errors.append(f"عنوان مطلوب في التقرير غائب: «{title}»")
    extra=[h for h in add_h if not any(t in h or h in t for t in adds)]
    if extra: warnings.append("عناوين إضافية خارج السياسة: "+" · ".join(extra[:4]))
    pdf=Path(a.pdf).expanduser().resolve() if a.pdf else dist/"reports/pdf"/f"{day}.pdf"
    if pdf.is_file():
        text=pdf_text(pdf)
        if not text:
            (errors if a.strict_print else warnings).append("تعذر استخراج PDF")
        else:
            bad = violating_pages(text, adds)
            if bad:
                detail = " · ".join(f"«{k}» ص{','.join(map(str, v))}" for k, v in bad.items())
                (errors if a.strict_print else warnings).append(
                    f"قسم منقول ظاهر في متن التقرير المطبوع: {detail}")
            else:
                npg = len([p for p in text.split("\f") if p.strip()])
                notes.append(f"لا قسم منقول في متن التقرير المطبوع (فُحص {npg} صفحة، باستثناء الفهرس والملحق)")
            notes.append(f"طباعة مفحوصة من {pdf.name} وفق السياسة")
    else:
        (errors if a.strict_print else warnings).append(f"PDF غير موجود للفحص: {pdf}")
    return emit(errors,warnings,notes,len(add_h),len(adds))
if __name__ == "__main__": raise SystemExit(main())
