#!/usr/bin/env python3
"""نموذج الترجيح الكمّي لمصفوفة ACH — نسخة 3.
score_i = sum_j ( w_ij * s_ij ) حيث s: ++ = +2 .. -- = -2
w = وزن الدرجة × وزن القوة التشخيصية × (معامل R لأدلة المقام)
"""
import json, math
from pathlib import Path

GRADE = {"A/1": 1.00, "A/2": 0.90, "B/2": 0.70, "C/3": 0.45, "D/4": 0.20, "F/6": 0.05}
SIGN = {"++": 2, "+": 1, "0": 0, "-": -1, "--": -2}
HYP = ["H1 الأسطول", "H2 الخط", "H3 العلم", "H4 الانتماء"]

# id, نص مختصر, الدرجة, القوة التشخيصية, علامات H1..H4, معامل R؟
E = [
 ("E1","ثلاث إصابات لأسطول واحد في ثلاثة أشهر وصفر خارجه","B/2",1.5,["++","+","+","++"],None),
 ("E2","ثلاثة ضحايا يرفعون علم سنغافورة","A/1",1.0,["0","0","++","0"],None),
 ("E3","ضحايا بأعلام ومشغّلين متنوعين","C/3",1.5,["--","++","--","0"],None),
 ("E4","التقييم الرسمي: أربع ناقلات وأربع حاويات","A/2",1.0,["0","+","-","0"],None),
 ("E5","تنوع أنواع السفن المستهدفة","A/1",0.5,["0","+","0","+"],None),
 ("E6","التمركز داخل المضيق ومياه عُمان","A/1",1.5,["0","++","0","0"],None),
 ("E7","خطوط مغذية في الخليج","B/2",1.0,["+","++","0","0"],None),
 ("E8","إسناد أمريكي مباشر لإصابة GFS PRIDE","A/2",1.0,["++","0","0","+"],None),
 ("E9","رواية اللغم البحري الإيرانية","D/4",0.5,["0","0","0","0"],None),
 ("E10","إطفاء التتبّع قبل الإصابة والعبور المظلم","C/3",1.0,["+","+","0","0"],None),
 ("E11","الخطاب الإيراني يستهدف بالانتماء لا بالعلم","D/4",1.5,["+","+","-","++"],None),
 ("E12","لا إصابات مماثلة خارج المضيق في الفترة","B/2",1.5,["0","++","0","+"],None),
 ("E13","إعلان أدنوك الرسمي: 15 سفينة استُهدفت","A/1",2.0,["0","0","0","++"],None),
 ("E14","اختبار المقام: عدم تناسب إصابات أدنوك R 2.3–12.2","A/1",2.0,["0","0","0","++"],"R"),
 ("E15","ST1 مملوكة لـSAFEEN (ذراع أدنوك)","C/3",1.5,["0","0","0","++"],None),
 ("E16","CAMEROON PROSPERITY بإدارة أدنوك الفنية","B/2",1.0,["0","0","0","++"],None),
 ("E17","ON PEACE (ONEX دبي) وVALTHERA (ISM إماراتي)","C/3",1.0,["0","0","0","+"],None),
 ("E18","GFS: AD Ports تملك 80–81%","A/1",1.5,["++","+","0","++"],None),
 ("E19","توزيع الأعلام على عشرين ضحية","C/3",1.5,["0","+","--","0"],None),
 ("E20","المقام: 30.25–40 عبورًا يوميًا","B/2",1.0,["0","+","0","0"],None),
 ("E21","62.7% من عبور أغسطس مظلم (درجة ضعيفة)","D/4",1.0,["0","+","0","0"],None),
 ("E22","إيران أدرجت KITION M وEVER VICT في قائمة عدم الامتثال","C/3",1.0,["0","0","0","0"],None),
 ("E23","معيار «غير الممتثلة» الإيراني يستهدف المرتبط بأمريكا وإسرائيل","D/4",1.5,["0","+","-","++"],None),
]

def r_weight(r):
    """معامل R: زيادة مستقلة لا مضاعفة للتشخيصية (توصية التدقيق) — clamp(log2 R, 0, 2)."""
    return max(0.0, min(2.0, math.log2(r)))

# تعديلات التدقيق المستقل (16 أكتوبر 2026)
REVISED = {
 "E13": {"diag": 1.25},                    # حتى نشر الأسماء والتواريخ
 "E14": {"diag": 1.25},                    # فصل معامل R عن التشخيصية
 "E2":  {"signs": ["0","0","+","0"]},      # حالتان من الثلاث مرتبطتان بالإمارات
 "E3":  {"signs": ["-","++","--","0"]},    # التنوع لا ينفي استهداف جزء من أسطول مسمى
 "E8":  {"signs": ["+","0","0","+"]},      # إسناد إصابة ≠ إثبات معيار الأسطول
 "E19": {"signs": ["0","+","-","0"]},      # لا مقام عبور حسب العلم
 "E21": {"diag": 0.5},                     # مصدر ضعيف وقياس مظلم/غير مصنف
}

def run(r_low=2.3, drop_grades=(), drop_ids=(), equal_weights=False, revised=False, r_flag=True):
    rows, totals = [], [0.0]*4
    total_w = 0.0
    for eid, txt, g, diag, signs, rflag in E:
        if eid in drop_ids or g in drop_grades:
            continue
        if revised and eid in REVISED:
            diag = REVISED[eid].get("diag", diag)
            signs = REVISED[eid].get("signs", signs)
        w = 1.0 if equal_weights else GRADE[g]*diag
        if rflag == "R" and r_flag:
            w += r_weight(r_low)
        total_w += w
        sc = [w*SIGN[s] for s in signs]
        for i in range(4):
            totals[i] += sc[i]
        rows.append({"id": eid, "w": round(w, 3), "score": [round(x, 3) for x in sc]})
    out = []
    for i, h in enumerate(HYP):
        raw = totals[i]
        support = sum(r["score"][i] for r in rows if r["score"][i] > 0)
        neg = sum(r["w"] for r in rows if r["score"][i] < 0)
        purity = support/(support + neg)*100 if (support + neg) else 100.0
        coverage = (support/2)/total_w*100 if total_w else 0.0
        out.append({"hypothesis": h, "weighted_score": round(raw, 2),
                    "support_mass": round(support, 2), "contradiction_mass": round(neg, 2),
                    "purity_pct": round(purity, 1), "coverage_pct": round(coverage, 1)})
    out.sort(key=lambda d: -d["weighted_score"])
    return {"total_weight": round(total_w, 2), "ranking": out, "rows": rows}

res = {
  "model": "weighted ACH — score = Σ (وزن الدرجة × القوة التشخيصية + معامل R) × الإشارة",
  "grade_weights": GRADE, "sign_values": SIGN, "evidence_count": len(E),
  "v3": {
    "base": run(r_low=2.3),
    "sensitivity": {
      "R_مرتفع (12.2)": run(r_low=12.2),
      "بلا أدلة D/4": run(drop_grades=("D/4",)),
      "بلا C/3 وD/4": run(drop_grades=("C/3","D/4")),
      "أوزان متساوية": run(equal_weights=True),
      "بلا كتلة الانتماء (E13–E18)": run(drop_ids=("E13","E14","E15","E16","E17","E18")),
      "بلا معامل R": run(r_flag=False),
    },
  },
  "v31_revised": {
    "base": run(r_low=2.3, revised=True),
    "sensitivity": {
      "R_مرتفع (12.2)": run(r_low=12.2, revised=True),
      "بلا أدلة D/4": run(drop_grades=("D/4",), revised=True),
      "بلا C/3 وD/4": run(drop_grades=("C/3","D/4"), revised=True),
      "أوزان متساوية": run(equal_weights=True, revised=True),
      "أوزان متساوية بلا D/4": run(equal_weights=True, drop_grades=("D/4",), revised=True),
      "بلا كتلة الانتماء (E13–E18)": run(drop_ids=("E13","E14","E15","E16","E17","E18"), revised=True),
      "حذف GFS (E1·E18)": run(drop_ids=("E1","E18"), revised=True),
      "حذف الإسناد الأمريكي (E8)": run(drop_ids=("E8",), revised=True),
      "بلا معامل R": run(revised=True, r_flag=False),
    },
  },
}
Path("appendices/ach-v3-model.json").write_text(json.dumps(res, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def show(tag, r):
    print(f"===== {tag} — مجموع الأوزان {r['total_weight']} =====")
    for d in r["ranking"]:
        print(f"  {d['hypothesis']:14s} صافي {d['weighted_score']:7.2f} · تغطية {d['coverage_pct']:5.1f}% · نقاء {d['purity_pct']:5.1f}% · تناقض {d['contradiction_mass']:.2f}")

show("نسخة 3 الأساسية (R=2.3)", res["v3"]["base"])
print()
show("نسخة 3.1 بعد التدقيق (R=2.3)", res["v31_revised"]["base"])
print()
print("===== حساسية 3.1 =====")
for name, r in res["v31_revised"]["sensitivity"].items():
    print(f"  [{name}] " + " · ".join(f"{d['hypothesis'].split()[0]}={d['weighted_score']:.1f}" for d in r["ranking"]))
