#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوابة «الأسلوب الكتابي للتقارير العملياتية» — تمنع التسليم عند ورود لفظ ممنوع.

الاستخدام:
  python3 validators/check_style.py <ملف التقرير>          # فحص مانع
  python3 validators/check_style.py <ملف> --json            # مخرجات JSON
  python3 validators/check_style.py --list                  # عرض القائمة السوداء
  python3 validators/check_style.py --add "عبارة" --reason "السبب" --replacement "البديل"
  python3 validators/check_style.py --suggest <ملف>         # كشف عبارات جديدة مرشحة للإدراج
  python3 validators/check_style.py --promote "عبارة"       # ترقية مرشح إلى مانع

القاعدة: ط10 في sections/75-style.md — رمز الخروج 0 عند القبول، و2 عند المنع.
التطوير: كل تصحيح لغوي مسجّل في memory/learning-log.jsonl يُضاف تلقائيًا كمرشح
عبر tools/style_learn.py، ثم يُرقّى بأمر --promote بعد موافقة المستخدم.
"""

import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "appendices" / "style-blacklist.json"

MAX_WORDS = 20          # حد الجملة المعتمد (مع استثناء معلّل)
HARD_WORDS = 35         # إطالة غير مقبولة مطلقًا
EXCUSE = "استثناء-طول"  # تعليق معلّل في النص: <!-- استثناء-طول: السبب -->

PROB = ["مؤكد", "مرجّح", "ممكن", "غير حاسم"]
CONF = ["ثقة عالية", "ثقة متوسطة", "ثقة منخفضة", "بثقة عالية", "بثقة متوسطة", "بثقة منخفضة"]


def load_db():
    if not DB.exists():
        print(f"ملف القائمة السوداء غير موجود: {DB}")
        sys.exit(2)
    return json.loads(DB.read_text(encoding="utf-8"))


def save_db(db):
    DB.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_text(text):
    t = re.sub(r"\|.*?\|", " ", text)                      # خلايا الجداول تُبقى للفحص أدناه
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#*_>`]+", " ", t)
    return t


def sentences(text):
    """جمل المتن فقط — تُستثنى أسطر الجداول والقوائم المرقّمة (تُفحص في القائمة السوداء)."""
    lines = []
    for ln in clean_text(text).splitlines():
        t = ln.strip()
        if not t or t.startswith("|") or t.startswith("-") or t.startswith(">"):
            continue
        if t.count("|") >= 2 or set(t) <= set("-— "):
            continue
        lines.append(t)
    raw = []
    for ln in lines:                      # كل سطر وحدة مستقلة — يمنع دمج بنود القوائم
        raw.extend(re.split(r"(?<=[.!؟:؛])\s+", ln))
    out = []
    for s in raw:
        s = s.strip()
        if len(re.findall(r"[\u0600-\u06FF]{2,}", s)) >= 3:
            out.append(s)
    return out


def words(s):
    return re.findall(r"[\u0600-\u06FF]{2,}", s)


def scan(path):
    text = Path(path).read_text(encoding="utf-8")
    db = load_db()
    findings = {"blocked": [], "warn": [], "long": [], "watch": []}

    flat = clean_text(text)
    flat_collapsed = re.sub(r"\s+", " ", flat)

    # 1) القائمة السوداء اللفظية — مانعة
    for item in db.get("blocking", []):
        term = item["term"]
        if term in flat_collapsed:
            findings["blocked"].append({
                "type": "blacklist", "term": term,
                "reason": item.get("reason", ""),
                "replacement": item.get("replacement", ""),
                "count": flat_collapsed.count(term),
            })

    # 2) الأنماط
    for pat in db.get("patterns", []):
        if pat["id"] == "mixed_prob_conf":
            for s in sentences(text):
                if any(p in s for p in PROB) and any(c in s for c in CONF):
                    findings["blocked"].append({
                        "type": "pattern", "term": "جمع الاحتمال بالثقة في جملة واحدة",
                        "reason": pat["reason"], "replacement": pat["replacement"],
                        "sample": s[:160],
                    })
            continue
        if pat["id"] == "separated_clock":
            hits = [m.group(0) for m in re.finditer(pat["regex"], flat_collapsed)]
            hits = [h for h in hits if not re.search(r"\d{6}Z", h)]
            if hits:
                findings["warn"].append({
                    "type": "pattern", "term": "ساعة منفصلة بلا DTG",
                    "reason": pat["reason"], "replacement": pat["replacement"],
                    "sample": "، ".join(sorted(set(hits))[:8]),
                })
            continue
        hits = re.findall(pat["regex"], flat_collapsed)
        if hits:
            bucket = "blocked" if pat.get("blocking") else "warn"
            sample = hits[0] if isinstance(hits[0], str) else " ".join(hits[0])
            findings[bucket].append({
                "type": "pattern", "term": pat["id"],
                "reason": pat["reason"], "replacement": pat["replacement"],
                "count": len(hits), "sample": sample[:120],
            })

    # 3) طول الجملة
    excused = EXCUSE in text
    for s in sentences(text):
        n = len(words(s))
        if n > HARD_WORDS:
            findings["blocked"].append({
                "type": "length", "term": f"جملة {n} كلمة (الحد الأقصى {HARD_WORDS})",
                "reason": "إطالة غير مقبولة؛ تُقسم الجملة",
                "replacement": "جملتان قصيرتان", "sample": s[:160],
            })
        elif n > MAX_WORDS:
            findings["long"].append({"words": n, "sample": s[:160]})
    if excused and findings["long"]:
        findings["warn"].append({
            "type": "length", "term": f"{len(findings['long'])} جملة بين 21 و{HARD_WORDS} كلمة",
            "reason": "معلَّلة بتعليق استثناء-طول في النص — تُراجع يدويًا",
            "replacement": "—", "sample": "",
        })

    # 4) قائمة الرصد (تنبيه فقط)
    for item in db.get("watch", []):
        if item["term"] in flat_collapsed:
            findings["watch"].append({"term": item["term"], "replacement": item["replacement"]})

    return findings


def report(path, findings, as_json=False):
    if as_json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
        return
    print(f"=== بوابة الأسلوب: {Path(path).name} ===")
    if findings["blocked"]:
        print(f"منع التسليم — {len(findings['blocked'])} مخالفة مانعة:")
        for f in findings["blocked"]:
            line = f"  ✗ [{f['type']}] {f['term']}"
            if f.get("count"):
                line += f" ×{f['count']}"
            print(line)
            print(f"      السبب: {f['reason']}")
            print(f"      البديل: {f['replacement']}")
            if f.get("sample"):
                print(f"      السياق: {f['sample']}")
    if findings["long"]:
        print(f"تنبيه — {len(findings['long'])} جملة تجاوزت {MAX_WORDS} كلمة (تحتاج تعليلًا أو تقصيرًا):")
        for x in findings["long"][:10]:
            print(f"  · {x['words']} كلمة: {x['sample']}")
    for f in findings["warn"]:
        print(f"  ! {f['term']} — {f['reason']}")
    if findings["watch"]:
        print("مرشحة للتبسيط: " + "، ".join(f"{w['term']} → {w['replacement']}" for w in findings["watch"]))
    if not findings["blocked"]:
        print("مقبول: لا لفظ ممنوع في القائمة السوداء.")


def suggest(path):
    """كشف عبارات جديدة مرشحة: كلمات ثقيلة/مبهمة أو صيغ مطلقة متكررة."""
    text = Path(path).read_text(encoding="utf-8")
    db = load_db()
    known = {i["term"] for i in db.get("blocking", [])} | {i["term"] for i in db.get("watch", [])}
    seeds = ["سياق", "تجدر", "حيال", "إزاء", "بيد أن", "على ضوء", "تكمن", "يساور", "يعتري",
             "بصورة", "إلى حد كبير", "بشكل واضح", "من المرجح جدًا", "ربما", "قد يكون",
             "لا يمكن الجزم", "غير معروف", "مجهول", "بلا شك", "بالفعل", "عمليًا"]
    out = []
    for s in seeds:
        if s in text and s not in known:
            out.append({"term": s, "reason": "مرشّح آلي — يُراجع قبل الترقية",
                        "replacement": "", "count": text.count(s)})
    if out:
        print("مرشحون للإدراج في القائمة السوداء (يُراجعون ثم يُرقّون بـ--promote):")
        for o in out:
            print(f"  · {o['term']} ×{o['count']}")
    else:
        print("لا مرشحين جددًا.")
    return out


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--add")
    ap.add_argument("--reason", default="")
    ap.add_argument("--replacement", default="")
    ap.add_argument("--suggest")
    ap.add_argument("--promote")
    a = ap.parse_args()

    if a.list:
        db = load_db()
        print(f"مانع ({len(db.get('blocking', []))}):")
        for i in db.get("blocking", []):
            print(f"  ✗ {i['term']} → {i.get('replacement','')}")
        print(f"رصد ({len(db.get('watch', []))}):")
        for i in db.get("watch", []):
            print(f"  · {i['term']} → {i.get('replacement','')}")
        if db.get("candidates"):
            print(f"مرشحون ({len(db['candidates'])}):")
            for i in db["candidates"]:
                print(f"  ? {i['term']} — {i.get('reason','')}")
        return 0

    if a.add:
        db = load_db()
        if any(i["term"] == a.add for i in db["blocking"]):
            print("العبارة موجودة أصلًا.")
            return 0
        db["blocking"].append({"term": a.add, "reason": a.reason or "إدراج يدوي",
                               "replacement": a.replacement or "—",
                               "source": "إدراج يدوي 2026-10-17"})
        db["candidates"] = [c for c in db.get("candidates", []) if c["term"] != a.add]
        db["updated"] = "2026-10-17"
        save_db(db)
        print(f"أُدرجت مانعة: {a.add}")
        return 0

    if a.promote:
        db = load_db()
        found = [c for c in db.get("candidates", []) if c["term"] == a.promote]
        if not found:
            print("لا مرشح بهذا النص.")
            return 2
        c = found[0]
        db["blocking"].append({"term": c["term"], "reason": c.get("reason", "مرقّى من المرشحين"),
                               "replacement": c.get("replacement") or "—", "source": "ترقية مرشح 2026-10-17"})
        db["candidates"] = [x for x in db["candidates"] if x["term"] != a.promote]
        save_db(db)
        print(f"رُقّيت إلى مانعة: {a.promote}")
        return 0

    if a.suggest:
        suggest(a.suggest)
        return 0

    if not a.file or not Path(a.file).exists():
        print("الاستخدام: check_style.py <ملف التقرير> [--json] | --list | --add ... | --suggest <ملف> | --promote ...")
        return 2

    f = scan(a.file)
    report(a.file, f, as_json=a.json)
    return 2 if f["blocked"] else 0


if __name__ == "__main__":
    sys.exit(main())
