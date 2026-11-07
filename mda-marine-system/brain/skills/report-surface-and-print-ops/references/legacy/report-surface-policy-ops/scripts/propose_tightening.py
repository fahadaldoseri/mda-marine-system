#!/usr/bin/env python3
"""استخرج أصناف ثغرات الأسطح والسياسة والطباعة واقترح تشديدات."""
from __future__ import annotations
import argparse, json, os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
DEFAULT_BRAIN=Path(os.environ.get("BRAIN_DIR",str(SKILL/"../../brain-marine-news"))).resolve()
RULES=[
("سياسة التاريخ والنقل",("surface","policy","date","إضافات","نقل","سياسة","تاريخ"),"اجعل قرار النقل مؤرخًا ومصدره واحدًا، ولا تعِد تشكيل الأرشيف القديم.","غيّر effective_from واختبر إصدارًا قبله وبعده مع توقعين مختلفين."),
("اكتمال الإضافات",("addition","missing","coverage","إضافات","نقص","تغطية"),"طابق required_in_additions مرة واحدة، واحتفظ بكل required_in_md في المتن.","احذف عنوانًا من الإضافات أو المتن وتحقق من رمز 2."),
("السطح القديم",("report","hidden","old","تقرير","مخفي","قديم"),"ارفض ظهور القسم المنقول في صفحة التقرير أو في عناوين PDF بعد النقل.","أعد عنوانًا منقولًا إلى التقرير وتحقق من فشل البوابة."),
("الطباعة",("pdf","print","طباعة","PDF"),"أعد بناء PDF ثم أثبت الإسناد؛ لا تعامل PDF القديم كدليل نجاح.","قدّم PDF قديمًا أو عنوانًا منقولًا ظاهرًا وتحقق من المنع الصارم."),
("تغطية الأسطح",("style","surface","سطح","أسلوب"),"غطّ المتن والواجهة والتقرير والإضافات والمصادر والرئيسية وPDF بجدول واحد.","احذف سطحًا أو اتركه فارغًا وتحقق من أن العدّ يهبط إلى أقل من 7."),
]
def files(a):
    if a.fault_log:return [Path(x) for x in a.fault_log]
    return sorted((Path(a.brain)/"audit").glob("faults*.jsonl"))
def rows(paths):
    for p in paths:
        if not p.is_file():continue
        for line in p.read_text(encoding="utf-8",errors="replace").splitlines():
            try:
                x=json.loads(line)
                if isinstance(x,dict):yield x
            except json.JSONDecodeError:pass
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--brain",default=str(DEFAULT_BRAIN));ap.add_argument("--fault-log",action="append");ap.add_argument("--output",default=str(SKILL/"references/proposed-tightening.md"));a=ap.parse_args()
    rs=list(rows(files(a))); counts=Counter()
    for r in rs:
        text=" ".join(str(r.get(k,"")) for k in ("axis","surface","area","symptom","cause","fix_status","status_tail")).lower()
        for name,words,_,_ in RULES:
            if any(w.lower() in text for w in words):counts[name]+=1
    out=["# مخرج propose_tightening","",f"- وقت الاستخراج {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",f"- السجلات الصالحة {len(rs)}","","| الصنف | العدد | التشديد المقترح | الاختبار السلبي |","|---|---:|---|---|"]
    for name,_,hard,neg in RULES:out.append(f"| {name} | {counts[name]} | {hard} | {neg} |")
    out += ["","هذه خلاصة آلية؛ عدّل السياسة أو البوابة فقط بعد مراجعة السبب الجذري."]
    text="\n".join(out)+"\n";Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(text,encoding="utf-8");print(text,end="");return 0
if __name__=="__main__":raise SystemExit(main())
