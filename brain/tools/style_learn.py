#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تطوير ذاتي للقائمة السوداء — يقرأ سجل التعلم ويستخرج الكلمات التي صُحّحت،
فيضيفها كمرشحين (لا مانعين) حتى يعتمدها المستخدم.

الاستخدام:
  python3 tools/style_learn.py            # استخراج المرشحين من سجل التعلم
  python3 tools/style_learn.py --apply    # إضافة المرشحين إلى style-blacklist.json
القاعدة: ط10 في sections/75-style.md.
"""

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOG = BASE / "memory" / "learning-log.jsonl"
DB = BASE / "appendices" / "style-blacklist.json"

# صيغ تُستخرج من نص الدرس: «القديم» ← «الجديد» أو «القديم» → «الجديد» أو القديم > الجديد
PAIRS = [r"«([^»]{2,40})»\s*(?:←|->|→|>)\s*«([^»]{2,60})»",
         r"«([^»]{2,40})»\s*بدلًا? من\s*«([^»]{2,40})»",
         r"استبدال\s*«([^»]{2,40})»\s*بـ?«([^»]{2,60})»"]


def load_db():
    return json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else {
        "version": 1, "blocking": [], "patterns": [], "watch": [], "candidates": []}


def extract():
    if not LOG.exists():
        print("سجل التعلم غير موجود.")
        return []
    found = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("category") != "linguistic":
            continue
        if rec.get("status") == "rejected":
            continue
        text = " ".join(str(rec.get(k, "")) for k in ("lesson", "replacement", "evidence"))
        for pat in PAIRS:
            for old, new in re.findall(pat, text):
                old, new = old.strip(), new.strip()
                if 2 <= len(old) <= 40 and old != new:
                    found.append({"term": old, "replacement": new,
                                  "reason": f"من درس {rec.get('lesson_id','')} ({rec.get('origin','')})",
                                  "source": "tools/style_learn.py"})
    # إزالة التكرار
    uniq, seen = [], set()
    for f in found:
        if f["term"] not in seen:
            seen.add(f["term"])
            uniq.append(f)
    return uniq


def main():
    apply_ = "--apply" in sys.argv
    cands = extract()
    db = load_db()
    known = {i["term"] for i in db.get("blocking", [])} | {i["term"] for i in db.get("watch", [])}
    known |= {c["term"] for c in db.get("candidates", [])}
    new = [c for c in cands if c["term"] not in known]

    print(f"دروس لغوية مستخرجة: {len(cands)} | مرشحون جدد: {len(new)}")
    for c in new:
        print(f"  ? {c['term']} → {c['replacement']}   [{c['reason']}]")

    if apply_ and new:
        db.setdefault("candidates", []).extend(new)
        db["updated"] = "2026-10-17"
        DB.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"أُضيف {len(new)} مرشحًا. للترقية إلى مانع: python3 validators/check_style.py --promote \"العبارة\"")
    elif new:
        print("للتطبيق: أضف --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
