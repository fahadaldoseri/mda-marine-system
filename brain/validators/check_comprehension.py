#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة الفهم — تسدّ الفجوة التي لم تكن أي بوابة سابقة تقيسها.

لماذا وُجدت هذه البوابة؟
كل البوابات السابقة تقيس **شكل الكتابة**: طول الجملة، والأرقام، والنقاط،
والرموز، والقائمة السوداء اللفظية. ولا واحدة منها تسأل السؤال الوحيد المهم:
**هل يفهم القارئ هذه الجملة؟** ولذلك مرّت مصطلحات مبهمة ورموز بلا تعريف
ومسارات ملفات داخلية، وهي كلها شكلها سليم وطولها مقبول.

ما تقيسه هذه البوابة:
  ف1 — رمز أو اختصار بلا تعريف داخل النص (A–F / 1–6 · EST- · DTG · ICD …).
  ف2 — اصطلاح مجرّد أو إداري يحجب المعنى عن القارئ (خط أساس · نافذة · وقت القطع …).
  ف3 — محتوى داخلي منشور: مسارات ملفات وأسماء أدوات وعبارات إجراءات.
  ف4 — التباس دلالي: «قُطر» (سفينة سحب) مع «قطر» (الدولة) في السطر نفسه.
  ف5 — رقم في بطاقة الملخص لا أثر له في المتن.

رموز الخروج: 0 = مكتمل · 1 = تحذيرات · 2 = مانع (محتوى داخلي منشور)

الاستخدام:
  python3 validators/check_comprehension.py --date 2026-10-20
  python3 validators/check_comprehension.py --md reports/2026-10-20-sectioned.md
  python3 validators/check_comprehension.py --date 2026-10-20 --json
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
from pathlib import Path

B = Path(f"{BRAIN}")

# ── ف1: الرموز التي لا يجوز أن تمرّ بلا تعريف ───────────────────────────────
# المفتاح: الرمز كما يظهر · القيمة: عبارات تدل على أن تعريفه موجود في النص
REQUIRED_SYMBOLS = {
    "A–F / 1–6": ["موثوقية المصدر", "درجة موثوقية", "مصداقية المعلومة", "درجة المصدر"],
    "EST-": ["رمز التقدير", "رموز التقديرات", "تقدير تحليلي مرقّم"],
    "DTG": ["صيغة الوقت العسكرية", "يوم/ساعة/دقيقة", "صيغة DTG"],
    "ICD": ["سلم الاحتمالات", "درجات الاحتمال", "نطاق الاحتمال"],
    "NAVAREA": ["منطقة التحذيرات الملاحية", "مناطق التحذيرات الملاحية"],
    "AIS": ["تتبّع السفن", "نظام تتبّع السفن", "بيانات التتبّع"],
    "IMO": ["المنظمة البحرية الدولية"],
    "ACH": ["تحليل الفرضيات المتنافسة", "الفرضيات المتنافسة"],
}

# ── ف2: اصطلاحات تحجب المعنى (تُبلَّغ للتعديل؛ تُرقّى بأمر صاحب القرار) ───────
AMBIGUOUS = {
    "خط أساس": "المعدل الطبيعي قبل الأزمة",
    "وقت القطع": "وقت إقفال المعلومات",
    "فجوة التبليغ": "وقائع لا تُبلَّغ ولا تُسجَّل",
    "القراءة التشغيلية": "الأثر على الملاحة",
    "يُقرأ للاتجاه": "يُستدل به على الاتجاه العام",
    "العدّ الرسمي": "العدد المسجَّل رسميًا",
    "المراجعة النظيرة": "المراجعة الداخلية",
    "المرجع الساري": "النص الرسمي النافذ",
    "الجهة القادرة على الحسم": "الجهة التي تستطيع الحسم",
    "خرطوم عائم": "خرطوم عائم (خرطوم تحميل طافٍ)",
    "شبه غاطسة": "منصة شبه غاطسة",
    "إطفاء أنظمة التتبّع": "إطفاء أجهزة تتبّع السفن (AIS)",
    "مسار الفصل الملاحي": "ممرات الفصل الملاحي الرسمية",
    "غير حاسم": "لم يُحسم بعد",
    "الإسناد": "المصدر",
}

# ── ف3: محتوى داخلي لا يُنشر (يُنفّذ القاعدتين 14 و19 في sections/60-validation) ─
INTERNAL_PATTERNS = [
    (r"`[^`]*\b(?:archive|logs|appendices|cumulative-\d{4}|tools|validators)\b[^`]*`",
     "مسار ملف داخلي بين علامتي اقتباس"),
    (r"(?<![A-Za-z0-9_/])(?:archive|logs|appendices|cumulative-\d{4})/[A-Za-z0-9_./\-]+",
     "مسار ملف داخلي"),
    (r"\.(?:json|md|docx|py)\b", "امتداد ملف داخلي"),
    (r"(?:محجوب للفاحص|تعذر الاتصال بالفاحص|الدفتر الجامع|خريطة رموز الأحداث|"
     r"يُوسم النقل|وُسم النقل|لا يُقال إن|ملف الواجهة|الحقول البرمجية|"
     r"وفق استثناء|سجل التعلّم|ملف التكيّف)",
     "عبارة إجراء داخلي"),
]

# ── ف5: كلمات العدد المزدوجة في الملخص ──────────────────────────────────────
DUAL_FORMS = {
    "تحذيران": "تحذير", "تحذيرين": "تحذير",
    "حادثتان": "حادثة", "حادثتين": "حادثة",
    "واقعتان": "واقعة", "واقعتين": "واقعة",
    "سفينتان": "سفينة", "سفينتين": "سفينة",
    "عبورتان": "عبور", "عبورتين": "عبور",
}


def strip_markup(text: str) -> str:
    t = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    return t


def load_texts(date: str, md_path: str) -> dict:
    out = {}
    if md_path:
        p = Path(md_path)
        if p.exists():
            out["md"] = p.read_text(encoding="utf-8")
    elif date:
        p = B / "reports" / f"{date}-sectioned.md"
        if p.exists():
            out["md"] = p.read_text(encoding="utf-8")
    if date:
        m = B / "web" / "meta" / f"{date}.json"
        if m.exists():
            out["meta"] = m.read_text(encoding="utf-8")
    return out


def check_symbols(text: str) -> list:
    """ف1: رمز حاضر في النص بلا تعريف في أي موضع منه."""
    found = []
    for sym, keys in REQUIRED_SYMBOLS.items():
        probe = sym.replace("–", "-")
        present = (probe in text) or (sym in text)
        if not present:
            # أنماط بديلة لدرجات الموثوقية مثل A/2 و C/3
            if sym.startswith("A–F"):
                present = bool(re.search(r"\b[A-F]/\d\b", text))
            if not present:
                continue
        if not any(k in text for k in keys):
            found.append({"symbol": sym, "hint": keys[0]})
    return found


def check_ambiguous(text: str) -> list:
    return [{"term": t, "replacement": r, "count": text.count(t)}
            for t, r in AMBIGUOUS.items() if t in text]


def check_internal(text: str) -> list:
    out = []
    for pat, label in INTERNAL_PATTERNS:
        for m in re.finditer(pat, text):
            frag = m.group(0).strip()
            out.append({"label": label, "sample": frag[:90]})
    return out


def check_tug_confusion(text: str) -> list:
    """ف4: سطر يجمع «قُطر» سفينة السحب مع «قطر» الدولة."""
    out = []
    for ln in text.splitlines():
        if "دولة قطر" in ln:
            continue
        tug_context = bool(re.search(r"قُطر|خرطوم|سحب", ln))
        country_context = bool(re.search(r"قطري|قبالة قطر|قطر\)|\(قطر", ln))
        if tug_context and country_context:
            out.append({"sample": ln.strip()[:150],
                        "why": "«قُطر» سفينة سحب و«قطر» الدولة في السطر نفسه"})
    return out


def check_summary_numbers(md: str, meta: str) -> list:
    """ف5: رقم في بطاقة الملخص لا أثر له في المتن."""
    out = []
    card = ""
    if meta:
        try:
            data = json.loads(meta)
            card = " ".join(json.dumps(data.get(k, ""), ensure_ascii=False)
                            for k in ("hero_kpis", "decision_card", "summary"))
        except json.JSONDecodeError:
            card = ""
    scope = (card + " " + md).strip()

    # عدد بنود التحذيرات الجديدة المسرودة في المتن
    warn_bullets = len(re.findall(r"^-\s+\*\*\d+/\d+\*\*", md, flags=re.M))

    for word, base in DUAL_FORMS.items():
        if word not in scope:
            continue
        if base == "تحذير" and warn_bullets and warn_bullets != 2:
            out.append({"kind": "تعارض عدد في الملخص",
                        "term": word,
                        "hint": f"الملخص يقول «{word}» والمتن يسرد {warn_bullets} تحذيرات"})
        elif word not in md and card and word in card:
            out.append({"kind": "عدد مزدوج في الملخص لا نظير له في المتن",
                        "term": word, "hint": f"راجع عدد «{base}»"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--md", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    texts = load_texts(a.date, a.md)
    if "md" not in texts:
        print("✘ لا نص للفحص — مرّر --date أو --md")
        return 2

    raw = texts["md"]
    body = strip_markup(raw)
    meta = texts.get("meta", "")

    symbols = check_symbols(body)
    ambiguous = check_ambiguous(body)
    internal = check_internal(raw)
    tug = check_tug_confusion(body)
    numbers = check_summary_numbers(body, meta)

    label = a.date or Path(a.md).name
    result = {
        "date": label,
        "undefined_symbols": symbols,
        "ambiguous_terms": ambiguous,
        "internal_content": internal,
        "tug_confusion": tug,
        "summary_numbers": numbers,
    }

    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"=== بوابة الفهم — {label} ===")
        print(f"  ف1 رموز بلا تعريف: {len(symbols)}")
        for s in symbols:
            print(f"     ✗ {s['symbol']} — يُضاف تعريفه (مثال: {s['hint']})")
        print(f"  ف2 اصطلاحات تحجب المعنى: {len(ambiguous)}")
        for s in ambiguous[:12]:
            print(f"     · {s['term']} ×{s['count']} → {s['replacement']}")
        print(f"  ف3 محتوى داخلي منشور: {len(internal)}")
        for s in internal[:12]:
            print(f"     ✗ {s['label']}: {s['sample']}")
        print(f"  ف4 التباس «قُطر/قطر»: {len(tug)}")
        for s in tug[:6]:
            print(f"     ✗ {s['sample']}")
        print(f"  ف5 أرقام الملخص: {len(numbers)}")
        for s in numbers:
            print(f"     ✗ {s['term']} — {s['hint']}")

    if internal:
        print("  النتيجة: مانع — محتوى داخلي في نص منشور")
        return 2
    if symbols or tug or numbers:
        print("  النتيجة: تحذير — بنود تحتاج معالجة قبل النشر")
        return 1
    print("  النتيجة: مكتمل — لا رمز بلا تعريف ولا اصطلاح حاجب ولا محتوى داخلي")
    return 0


if __name__ == "__main__":
    sys.exit(main())
