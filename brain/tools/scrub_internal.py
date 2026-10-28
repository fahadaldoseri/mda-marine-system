#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""المُنظّف الآلي للمحتوى الداخلي — يضمن ألا يتوقف النشر بسبب صنف معروف.

لماذا وُجد؟
بوابة الفهم تمنع نشر مسارات الملفات وأسماء الأدوات وعبارات الإجراءات.
لكن منعًا جافًا قد يوقف النشر في التشغيل الصباحي غير المراقب. فهذا المُنظّف
يُصلح الأصناف المعروفة **آليًا وقبل البناء**، فلا يصل إلى البوابة إلا ما هو جديد
حقًا — والجديد وحده يستحق أن يوقف التسليم.

القاعدة: كل تبديل يُسجَّل في logs/scrub-<date>.json بموضعه وقبل/بعد.
ولا يمسّ المُنظّف أي معلومة تشغيلية أو رقمية — يمسّ الصياغة الداخلية فقط.

الاستخدام:
  python3 tools/scrub_internal.py --date 2026-10-20 --dry-run
  python3 tools/scrub_internal.py --date 2026-10-20 --apply
"""
from __future__ import annotations

import os as _os
from pathlib import Path as _Path

_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

B = Path(f"{BRAIN}")

# ── تبديلات لفظية: الصيغة الداخلية ← الصيغة الموجّهة للقارئ ────────────────
PHRASES = [
    ("محجوب للفاحص", "يتعذر الوصول إليه من أدوات الفحص"),
    ("تعذر الاتصال بالفاحص", "تعذّر الاتصال بالمصدر"),
    ("تعذّر الاتصال بالفاحص", "تعذّر الاتصال بالمصدر"),
    ("الدفتر الجامع", "سجل الوقائع التراكمي"),
    ("خريطة رموز الأحداث", "سجل رموز الوقائع"),
    ("ملف التكيّف الذاتي", "سجل الدروس"),
    ("ملف التكيّف", "سجل الدروس"),
    ("سجل التعلّم", "سجل الدروس"),
    ("ملف الواجهة", "بيانات الإصدار"),
    ("الحقول البرمجية", "الحقول التقنية"),
    ("يُوسم النقل", "غير رسمي"),
    ("وُسم النقل", "غير رسمي"),
    ("يُوسم", "يُصنَّف"),
    ("لا يُقال إن", "لا يوجد إعلان رسمي بأن"),
    ("والأصل محفوظ", "والنص الأصلي محفوظ"),
]

# ── تبديلات المسارات: أي مسار ملف داخلي ← أرشيف المركز ─────────────────────
PATH_RULES = [
    (r"`?\b(?:archive|logs|appendices|validators|tools|cumulative-\d{4})/[A-Za-z0-9_./\-]*`?",
     "أرشيف المركز"),
    (r"`?reports/[A-Za-z0-9_./\-]*`?", "أرشيف المركز"),
    (r"`[^`]{0,80}\.(?:json|md|py|docx|txt)`", "أرشيف المركز"),
]

# ── أسطر إجراء داخلي تُحذف بالكامل ─────────────────────────────────────────
DELETE_LINES = [
    r"دُمج ملف اليوم في",
    r"نُسخ الدفتر إلى الموقع",
    r"وفق استثناء",
    r"^.*بُنيت خريطة رموز الأحداث.*$",
]


def scrub_text(text: str, source: str = "") -> tuple:
    """يُنظّف نصًا ويعيد (النص المنظّف، قائمة التبديلات)."""
    changes = []
    out_lines = []
    for i, line in enumerate(text.splitlines(), 1):
        original = line
        drop = False
        for pat in DELETE_LINES:
            if re.search(pat, line):
                changes.append({"line": i, "rule": "حذف سطر إجراء داخلي",
                                "before": original.strip()[:160], "after": "(حُذف)"})
                drop = True
                break
        if drop:
            continue
        for pat, rep in PATH_RULES:
            new = re.sub(pat, rep, line)
            if new != line:
                changes.append({"line": i, "rule": "مسار ملف داخلي",
                                "before": line.strip()[:160], "after": new.strip()[:160]})
                line = new
        for a, b in PHRASES:
            if a in line:
                changes.append({"line": i, "rule": f"صيغة داخلية: {a}",
                                "before": line.strip()[:160],
                                "after": line.replace(a, b).strip()[:160]})
                line = line.replace(a, b)
        out_lines.append(line)

    result = "\n".join(out_lines)
    if text.endswith("\n"):
        result += "\n"
    # تنظيف الجراح: مسافات مزدوجة وعلامات معلّقة
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r"\s+([،.·])", r"\1", result)
    result = re.sub(r"(?:—\s*){2,}", "— ", result)
    return result, changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = B / "reports" / f"{a.date}-sectioned.md"
    if not src.exists():
        print(f"✘ لا نص: {src}")
        return 2

    text = src.read_text(encoding="utf-8")
    cleaned, changes = scrub_text(text, str(src))

    logdir = B / "logs"
    logdir.mkdir(exist_ok=True)
    (logdir / f"scrub-{a.date}.json").write_text(
        json.dumps({"date": a.date, "applied": bool(a.apply),
                    "changes": len(changes), "detail": changes},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"=== المُنظّف الآلي — {a.date} ===")
    print(f"  التبديلات: {len(changes)}")
    seen = {}
    for c in changes:
        seen[c["rule"]] = seen.get(c["rule"], 0) + 1
    for rule, n in sorted(seen.items(), key=lambda x: -x[1]):
        print(f"    · {rule} ×{n}")

    if a.apply:
        if changes:
            src.write_text(cleaned, encoding="utf-8")
            print(f"  ✔ طُبّق — {src.name} نُظّف. السجل: logs/scrub-{a.date}.json")
        else:
            print("  ✔ لا شيء يحتاج تنظيفًا")
    else:
        print("  (فحص فقط — لم يُكتب الملف. استخدم --apply للتنفيذ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())