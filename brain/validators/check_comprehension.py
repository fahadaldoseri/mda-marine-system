#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة الفهم — تقيس فهم القارئ، لا شكل الكتابة.

لماذا وُجدت؟
كل البوابات السابقة تقيس شكل الكتابة: الطول والأرقام والنقاط والرموز وقائمة
أسود معروفة. ولا واحدة تسأل: **هل يفهم القارئ هذه الجملة؟** ولذلك مرّت مصطلحات
حاجبة ورموز بلا تعريف ومسارات ملفات داخلية إلى النص المنشور.

الفحوص الخمسة:
  ف1 — رمز أو اختصار بلا تعريف داخل النص (A–F / 1–6 · EST- · DTG · ICD …).
  ف2 — اصطلاح مجرّد أو إداري يحجب المعنى (خط أساس · وقت القطع · فجوة التبليغ …).
  ف3 — محتوى داخلي منشور: مسارات ملفات وأسماء أدوات وعبارات إجراءات.
  ف4 — التباس دلالي: «قُطر» سفينة السحب مع «قطر» الدولة في السطر نفسه.
  ف5 — تعارض بين أرقام بطاقة الملخص وأرقام المتن.

الترقية المرحلية (appendices/comprehension-stages.json):
  مرحلة 0 تحذيري · 1 يمنع ف3 · 2 يمنع ف3+ف4+ف5 · 3 يضيف ف1 · 4 يمنع الكل
  ولا تُرقّى مرحلة إلا إذا اجتازت آخر تقريرين متاحين فحوصها الجديدة، بعد
  تطبيق المُنظّف الآلي tools/scrub_internal.py — فلا يوقف النشر إلا ما هو جديد.

رموز الخروج: 0 مكتمل · 1 تحذير · 2 مانع

الاستخدام:
  python3 validators/check_comprehension.py --date 2026-10-20
  python3 validators/check_comprehension.py --date 2026-10-20 --json
  python3 validators/check_comprehension.py --status
  python3 validators/check_comprehension.py --promote
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
STAGES_FILE = B / "appendices" / "comprehension-stages.json"
MAX_STAGE = 4

# ── ف1: الرموز التي لا يجوز أن تمرّ بلا تعريف ───────────────────────────────
REQUIRED_SYMBOLS = {
    "A–F / 1–6": ["موثوقية المصدر", "درجة موثوقية", "مصداقية المعلومة", "درجة المصدر"],
    "EST-": ["رمز التقدير", "رموز التقديرات", "تقدير تحليلي مرقّم"],
    "DTG": ["صيغة الوقت العسكرية", "يوم/ساعة/دقيقة", "صيغة DTG"],
    "ICD": ["سلم الاحتمالات", "درجات الاحتمال", "نطاق الاحتمال"],
    "NAVAREA": ["منطقة التحذيرات الملاحية", "مناطق التحذيرات الملاحية"],
    "AIS": ["تتبّع السفن", "نظام تتبّع السفن", "بيانات التتبّع", "نظام التعريف الآلي"],
    "IMO": ["المنظمة البحرية الدولية"],
    "ACH": ["تحليل الفرضيات المتنافسة", "الفرضيات المتنافسة"],
    "MN-": ["رمز الواقعة", "رموز الوقائع", "رمز الحدث"],
    # المصطلحات المتحقَّق منها في كشف 20 أكتوبر 2026 — تعريفها في بنك التعريفات المعياري
    "UKMTO": ["مركز التجارة البحرية البريطاني"],
    "JMIC": ["مركز المعلومات البحرية المشترك"],
    "CMF": ["القوات البحرية المشتركة"],
    "NCAGS": ["التعاون والتوجيه للملاحة"],
    "BMP": ["أفضل الممارسات الإدارية"],
    "MMSI": ["تسع خانات"],
    "MSI": ["معلومات السلامة البحرية"],
    "STS": ["نقل الحمولة بين سفينتين"],
    "CENTCOM": ["القيادة المركزية"],
    "FZE": ["منطقة حرة بالإمارات", "مساهم واحد"],
    "BNA": ["وكالة أنباء البحرين"],
    "IRNA": ["وكالة الأنباء الإيرانية"],
    "PGSA": ["هيئة مضيق الخليج"],
    "WARNING": ["تصنيف نوع البلاغ"],
    "RPG": ["قاذف"],
    "VHF": ["نطاق تردد لاسلكي"],
    "GNSS": ["النظام العالمي للملاحة"],
    "IMF": ["صندوق النقد الدولي"],
    "AFP": ["وكالة فرانس برس"],
    "DOC": ["شهادة الامتثال"],
    "ISM": ["إدارة السلامة", "مدير السلامة"],
    "MPA": ["هيئة الموانئ"],
    "OFAC": ["قائمة العقوبات", "قائمة الحظر", "فحص العقوبات"],
    "IMB": ["مكتب القرصنة"],
    "SPAR": ["تمرين مكافحة القرصنة"],
    "CRITICAL": ["سلّم JMIC", "مستوى تهديد في سلّم"],
    "SEVERE": ["سلّم JMIC", "مستوى تهديد في سلّم"],
    "SUBSTANTIAL": ["سلّم JMIC", "مستوى تهديد في سلّم"],
    "SIGNIFICANT": ["سلّم JMIC", "مستوى تهديد في سلّم"],
    "MODERATE": ["سلّم JMIC", "مستوى تهديد في سلّم"],
}

# ── ف2: اصطلاحات تحجب المعنى ───────────────────────────────────────────────
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
    "وقت القطع": "وقت إقفال المعلومات",
}

# ── ف3: محتوى داخلي لا يُنشر ───────────────────────────────────────────────
INTERNAL_PATTERNS = [
    (r"`[^`]*\b(?:archive|logs|appendices|cumulative-\d{4}|tools|validators)\b[^`]*`",
     "مسار ملف داخلي"),
    (r"(?<![A-Za-z0-9_/])(?:archive|logs|appendices|cumulative-\d{4})/[A-Za-z0-9_./\-]+",
     "مسار ملف داخلي"),
    (r"\.(?:json|md|docx|py)\b", "امتداد ملف داخلي"),
    (r"(?:محجوب للفاحص|تعذر الاتصال بالفاحص|الدفتر الجامع|خريطة رموز الأحداث|"
     r"يُوسم النقل|وُسم النقل|لا يُقال إن|ملف الواجهة|الحقول البرمجية|"
     r"وفق استثناء|سجل التعلّم|ملف التكيّف)",
     "عبارة إجراء داخلي"),
]

DUAL_FORMS = {
    "تحذيران": "تحذير", "تحذيرين": "تحذير",
    "حادثتان": "حادثة", "حادثتين": "حادثة",
    "واقعتان": "واقعة", "واقعتين": "واقعة",
    "سفينتان": "سفينة", "سفينتين": "سفينة",
    "عبورتان": "عبور", "عبورتين": "عبور",
}


# ── التحميل والفحوص ────────────────────────────────────────────────────────
def load_stages() -> dict:
    if STAGES_FILE.exists():
        return json.loads(STAGES_FILE.read_text(encoding="utf-8"))
    return {"stage": 0, "blocking": {"0": []}, "stage_names": {"0": "تحذيري"}}


def save_stages(cfg: dict) -> None:
    cfg["updated"] = __import__("datetime").date.today().isoformat()
    STAGES_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")


def strip_markup(text: str) -> str:
    t = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    return t


def scrub(text: str) -> str:
    """يطبّق المُنظّف الآلي إن وُجد — حتى تُقاس الحالة التي ستُنشر فعلًا."""
    try:
        sys.path.insert(0, str(B / "tools"))
        from scrub_internal import scrub_text
        return scrub_text(text)[0]
    except Exception:
        return text


def glossary_text(meta: str) -> str:
    """قاموس الرموز والمصطلحات المنشور في ملف الواجهة — يراه القارئ مع المتن."""
    if not meta:
        return ""
    try:
        g = json.loads(meta).get("glossary") or {}
        return "\n".join(f"{k}: {v}" for k, v in g.items())
    except Exception:
        return ""


def check_symbols(text: str) -> list:
    found = []
    for sym, keys in REQUIRED_SYMBOLS.items():
        probe = sym.replace("–", "-")
        present = (probe in text) or (sym in text)
        if not present and sym.startswith("A–F"):
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
            out.append({"label": label, "sample": m.group(0).strip()[:90]})
    return out


def check_tug_confusion(text: str) -> list:
    out = []
    for ln in text.splitlines():
        if "دولة قطر" in ln:
            continue
        tug = bool(re.search(r"قُطر|خرطوم|سحب", ln))
        country = bool(re.search(r"قطري|قبالة قطر|قطر\)|\(قطر", ln))
        if tug and country:
            out.append({"sample": ln.strip()[:150],
                        "why": "«قُطر» سفينة سحب و«قطر» الدولة في السطر نفسه"})
    return out


def check_summary_numbers(md: str, meta: str) -> list:
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
    warn_bullets = len(re.findall(r"^-\s+\*\*\d+/\d+\*\*", md, flags=re.M))
    for word, base in DUAL_FORMS.items():
        if word not in scope:
            continue
        if base == "تحذير" and warn_bullets and warn_bullets != 2:
            out.append({"kind": "تعارض عدد في الملخص", "term": word,
                        "hint": f"الملخص يقول «{word}» والمتن يسرد {warn_bullets} تحذيرات"})
        elif word not in md and card and word in card:
            out.append({"kind": "عدد مزدوج في الملخص لا نظير له في المتن",
                        "term": word, "hint": f"راجع عدد «{base}»"})
    return out


def run_checks(md: str, meta: str = "") -> dict:
    body = strip_markup(md)
    return {
        # ف1 يفحص المتن + قاموس الرموز المنشور في ملف الواجهة، لأن القارئ يراهما معًا
        "ف1": check_symbols(body + "\n" + glossary_text(meta)),
        "ف2": check_ambiguous(body),
        "ف3": check_internal(md),
        "ف4": check_tug_confusion(body),
        "ف5": check_summary_numbers(body, meta),
    }


def read_report(date: str) -> tuple:
    md_p = B / "reports" / f"{date}-sectioned.md"
    meta_p = B / "web" / "meta" / f"{date}.json"
    md = md_p.read_text(encoding="utf-8") if md_p.exists() else ""
    meta = meta_p.read_text(encoding="utf-8") if meta_p.exists() else ""
    return md, meta


def available_dates(limit: int = 2) -> list:
    d = B / "reports"
    if not d.exists():
        return []
    dates = sorted({p.name[:10] for p in d.glob("*-sectioned.md")}, reverse=True)
    return dates[:limit]


# ── الأوامر ────────────────────────────────────────────────────────────────
def cmd_status(cfg: dict) -> int:
    stage = int(cfg.get("stage", 0))
    names = cfg.get("stage_names", {})
    blocking = cfg.get("blocking", {}).get(str(stage), [])
    print(f"=== بوابة الفهم — الحالة ===")
    print(f"  المرحلة الحالية: {stage} — {names.get(str(stage), '')}")
    print(f"  المانع الآن: {'، '.join(blocking) if blocking else 'لا شيء (تحذيري بالكامل)'}")
    print(f"  المرحلة التالية: {stage + 1} — {names.get(str(stage + 1), 'مكتمل')}")
    if stage < MAX_STAGE:
        nxt = cfg.get("blocking", {}).get(str(stage + 1), [])
        print(f"  ستُصبح مانعة: {'، '.join(nxt)}")
    print("  ── ما ترصده البوابة في آخر إصدارين ──")
    for date in available_dates(2):
        md, meta = read_report(date)
        res = run_checks(scrub(md), meta)
        counts = " · ".join(f"{k}={len(v)}" for k, v in res.items())
        print(f"    {date}: {counts}")
    return 0


def cmd_promote(cfg: dict) -> int:
    stage = int(cfg.get("stage", 0))
    if stage >= MAX_STAGE:
        print("المرحلة النهائية مُفعّلة بالفعل (4).")
        return 0
    target = stage + 1
    new_blocking = cfg.get("blocking", {}).get(str(target), [])
    names = cfg.get("stage_names", {})
    dates = available_dates(2)
    print(f"=== طلب ترقية: {stage} ← {target} ({names.get(str(target), '')}) ===")
    print(f"  شرط الترقية: أن تكون {new_blocking} نظيفة في آخر {len(dates)} إصدار، بعد التنظيف الآلي")

    if not dates:
        print("  ✘ لا إصدارات متاحة للتحقق — الترقية مرفوضة")
        return 2

    problems = []
    for date in dates:
        md, meta = read_report(date)
        res = run_checks(scrub(md), meta)
        for chk in new_blocking:
            if res.get(chk):
                problems.append((date, chk, res[chk]))
        counts = " · ".join(f"{k}={len(res[k])}" for k in new_blocking)
        print(f"    {date}: {counts}")

    if problems:
        print("  ✘ الترقية مرفوضة — الشرط المُسبق غير محقق:")
        for date, chk, items in problems:
            print(f"    {date} · {chk}: {len(items)} بندًا يحتاج إصلاحًا")
            for it in items[:4]:
                s = it.get("sample") or it.get("term") or it.get("symbol") or ""
                print(f"       - {s}")
        print("  الإجراء: أصلح البنود أعلاه ثم أعد الطلب.")
        return 2

    cfg["stage"] = target
    cfg.setdefault("history", []).append({
        "date": __import__("datetime").date.today().isoformat(),
        "from": stage, "to": target, "by": "صاحب القرار",
        "evidence": f"اجتازت {new_blocking} في آخر {len(dates)} إصدار بعد التنظيف الآلي",
    })
    save_stages(cfg)
    print(f"  ✔ رُقّيت إلى المرحلة {target} — المانع الآن: {'، '.join(new_blocking)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--md", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--promote", action="store_true")
    a = ap.parse_args()

    cfg = load_stages()
    if a.status:
        return cmd_status(cfg)
    if a.promote:
        return cmd_promote(cfg)

    if a.md:
        md = Path(a.md).read_text(encoding="utf-8")
        meta, label = "", Path(a.md).name
    elif a.date:
        md, meta = read_report(a.date)
        label = a.date
    else:
        print("مرّر --date أو --md أو --status أو --promote")
        return 2

    if not md:
        print(f"✘ لا نص للفحص: {label}")
        return 2

    res = run_checks(md, meta)
    stage = int(cfg.get("stage", 0))
    blocking = cfg.get("blocking", {}).get(str(stage), [])
    names = cfg.get("check_names", {})

    if a.json:
        print(json.dumps({"date": label, "stage": stage, "blocking": blocking,
                          "results": res}, ensure_ascii=False, indent=2))
    else:
        print(f"=== بوابة الفهم — {label} — المرحلة {stage} ===")
        for chk in ("ف1", "ف2", "ف3", "ف4", "ف5"):
            items = res[chk]
            mark = "✘ مانع" if chk in blocking else ("· تحذير" if items else "✔ نظيف")
            print(f"  {chk} {names.get(chk, '')}: {len(items)} — {mark}")
            for it in items[:6]:
                s = (it.get("sample") or it.get("term") or it.get("symbol") or "")
                extra = f" → {it['replacement']}" if it.get("replacement") else ""
                hint = f" ({it['hint']})" if it.get("hint") else ""
                print(f"       {s}{extra}{hint}")

    blocking_hits = sum(len(res[c]) for c in blocking)
    total = sum(len(v) for v in res.values())
    if blocking_hits:
        print(f"  النتيجة: مانع — {blocking_hits} بندًا في الفحوص المانعة (المرحلة {stage})")
        return 2
    if total:
        print(f"  النتيجة: تحذير — {total} بندًا في فحوص لم تُرقَّ بعد إلى مانعة")
        return 1
    print("  النتيجة: مكتمل — لا رمز بلا تعريف ولا اصطلاح حاجب ولا محتوى داخلي")
    return 0


if __name__ == "__main__":
    sys.exit(main())
