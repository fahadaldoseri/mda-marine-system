#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""دقّق تغطية الأسطح السبعة، مع إعادة استخدام بوابات المشروع عند توفرها."""
from __future__ import annotations
import argparse, hashlib, html, json, os, re, subprocess, sys, tempfile, traceback
from datetime import date
from pathlib import Path

HERE=Path(__file__).resolve(); SKILL=HERE.parents[1]
def infer(name, fallback):
    val=os.environ.get(name)
    if val and Path(val).is_dir(): return Path(val).resolve()
    for cand in (SKILL/"../../"/fallback, Path.home()/fallback):
        if cand.is_dir(): return cand.resolve()
    return Path(fallback).resolve()

def norm(t):
    t=re.sub(r"[\u0640\u200b-\u200f\u202a-\u202e\u2066-\u2069\u064b-\u0652\u0670]", "", t)
    t=re.sub(r"\s+([،.:؛؟!])", r"\1", t)
    return re.sub(r"[ \t]{2,}", " ", t)

def strip_html(raw):
    raw=re.sub(r"(?is)<(script|style|noscript|template)[^>]*>.*?</\1>", " ", raw)
    rows=[]
    for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>",raw):
        cells=[re.sub(r"(?s)<[^>]+>"," ",c) for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>",row)]
        rows.append(" | ".join(html.unescape(re.sub(r"\s+"," ",c)).strip() for c in cells if c.strip()))
    raw=re.sub(r"(?is)<(table|thead|tbody|tfoot)[^>]*>.*?</\1>"," ",raw)
    return html.unescape(re.sub(r"(?s)<[^>]+>","\n",raw))+"\n"+"\n".join(rows)

def flatten(x,out):
    if isinstance(x,str): out.append(x)
    elif isinstance(x,dict):
        for v in x.values(): flatten(v,out)
    elif isinstance(x,list):
        for v in x: flatten(v,out)

def run_gate(cmd, path):
    try:
        r=subprocess.run(cmd+[str(path)],capture_output=True,text=True,timeout=120)
        out=(r.stdout or "")+(r.stderr or "")
        keys=[ln.strip() for ln in out.splitlines() if any(k in ln for k in ("✗","✘","مخالفة","النتيجة:","مقبول"))]
        return r.returncode, keys[:6]
    except Exception as e: return 70,[f"تعذر تشغيل البوابة: {e}"]

def local_path(kind, brain, site, day, custom_pdf):
    if kind=="text":
        return next((p for p in (brain/f"reports/{day}-sectioned.md",site/f"sources/reports/{day}-sectioned.md") if p.exists()), brain/f"reports/{day}-sectioned.md")
    if kind=="json":
        return next((p for p in (brain/f"web/meta/{day}.json",site/f"sources/meta/{day}.json") if p.exists()), brain/f"web/meta/{day}.json")
    if kind=="report": return site/f"dist/reports/{day}.html"
    if kind=="additions": return site/"dist/additions.html"
    if kind=="sources": return site/"dist/sources.html"
    if kind=="home": return site/"dist/index.html"
    return Path(custom_pdf).expanduser().resolve() if custom_pdf else site/f"dist/reports/pdf/{day}.pdf"

def extract(kind,path):
    if not path.exists(): return None,"المصدر غير موجود"
    if kind=="text": text=norm(path.read_text(encoding="utf-8",errors="replace"))
    elif kind=="json":
        vals=[]; flatten(json.loads(path.read_text(encoding="utf-8")),vals); text="\n".join(vals)
    elif kind=="pdf":
        r=subprocess.run(["pdftotext","-layout",str(path),"-"],capture_output=True,text=True)
        if r.returncode: return None,"تعذر استخراج PDF"
        text=r.stdout
    else: text=strip_html(path.read_text(encoding="utf-8",errors="replace"))
    if len(text.strip())<20: return None,"النص المستخرج فارغ"
    return text,""

def pdf_link_proof(text, brain, site, day):
    md=next((p for p in (brain/f"reports/{day}-sectioned.md",site/f"sources/reports/{day}-sectioned.md") if p.exists()),None)
    src=md.read_text(encoding="utf-8") if md else ""
    codes=sorted(set(re.findall(r"MN-\d{4}-\d{2}-\d{2}-\d+",src)))
    prose=re.sub(r"\[([^\]]*)\]\([^)]*\)|https?://\S+"," ",src)
    toks=sorted({x.rstrip("./-") for x in re.findall(r"[A-Za-z][A-Za-z0-9._/-]{3,}",prose)})
    missc=[c for c in codes if c not in text]; misst=[t for t in toks if t not in text]
    ratio=1-len(misst)/max(1,len(toks)); ok=bool(src) and not missc and ratio>=.90
    return ok,f"إسناد PDF: رموز البلاغ {len(codes)-len(missc)}/{len(codes)} · اللاتينية {round(ratio*100)}% ({len(toks)-len(misst)}/{len(toks)})"

def main():
    ap=argparse.ArgumentParser(description="تغطية بوابة الأسلوب للأسطح السبعة")
    ap.add_argument("--date",default=date.today().isoformat()); ap.add_argument("--brain",default=str(infer("BRAIN_DIR","brain-marine-news"))); ap.add_argument("--site",default=str(infer("SITE_DIR","seawatch"))); ap.add_argument("--pdf",default=""); ap.add_argument("--json",action="store_true")
    a=ap.parse_args(); brain=Path(a.brain).expanduser().resolve(); site=Path(a.site).expanduser().resolve()
    gates=brain/"validators"; tmp=Path(tempfile.mkdtemp(prefix="surface-coverage-")); rows=[]; uncovered=blocked=0
    specs=[("المتن","text"),("ملف الواجهة","json"),("صفحة التقرير","report"),("صفحة إضافات","additions"),("صفحة المصادر","sources"),("الصفحة الرئيسية","home"),("PDF","pdf")]
    try:
        for idx,(label,kind) in enumerate(specs,1):
            p=local_path(kind,brain,site,a.date,a.pdf); text,err=extract(kind,p)
            if text is None:
                uncovered+=1; rows.append({"label":label,"path":str(p),"status":"غير مغطى","note":err,"style":"—","prose":"—"}); continue
            target=tmp/f"{idx}.txt"; target.write_text(text,encoding="utf-8")
            if kind=="pdf":
                linked,note=pdf_link_proof(text,brain,site,a.date); blocked += 0 if linked else 1
                rows.append({"label":label,"path":str(p),"status":"مغطى بالإسناد" if linked else "مانع","note":note,"style":"—","prose":"—","text_sha256":hashlib.sha256(text.encode()).hexdigest()[:16]})
                continue
            style_cmd=[sys.executable,str(gates/"check_style.py")] if (gates/"check_style.py").exists() else None
            prose_cmd=[sys.executable,str(gates/"check_prose_defects.py"),"--md"] if (gates/"check_prose_defects.py").exists() else None
            sc,so=run_gate(style_cmd,target) if style_cmd else (0,["بوابة الأسلوب غير متاحة، فُحصت قابلية الاستخراج"])
            pc,po=run_gate(prose_cmd,target) if prose_cmd else (0,["بوابة النثر غير متاحة، فُحصت قابلية الاستخراج"])
            ok=sc==0 and pc in (0,1); blocked += 0 if ok else 1
            rows.append({"label":label,"path":str(p),"status":"مغطى" if ok else "مانع","note":"","style":"مقبول" if sc==0 else f"منع ({sc})","prose":"مقبول" if pc==0 else ("تحذير (1)" if pc==1 else f"منع ({pc})"),"findings":(so+po)[:6],"text_sha256":hashlib.sha256(text.encode()).hexdigest()[:16]})
    finally:
        pass
    result={"date":a.date,"surfaces":7,"rows":rows,"uncovered":uncovered,"blocked":blocked,"status":"ok" if not (uncovered or blocked) else "failed"}
    if a.json: print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print(f"=== تغطية الأسطح السبعة — {a.date} ===")
        for r in rows: print(f"{r['label']:<20} {r['status']:<14} {r.get('style','—'):<10} {r.get('prose','—'):<10} {r.get('note','')}")
        print(f"الأسطح: 7 · مغطاة: {7-uncovered-blocked} · غير مغطاة: {uncovered} · مانعة: {blocked}")
    return 0 if not (uncovered or blocked) else 2
if __name__=="__main__":
    try: raise SystemExit(main())
    except SystemExit: raise
    except Exception: traceback.print_exc(); raise SystemExit(70)
