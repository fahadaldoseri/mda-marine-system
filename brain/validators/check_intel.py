#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة التحقق من قسم «قراءة الموقف وتحليل المؤشرات» — تنفّذ القاعدة ف5 وقواعد ح1–ح12.

الاستخدام:
    python3 validators/check_intel.py reports/<التاريخ>-sectioned.md [web/meta/<التاريخ>.json]

الرمز الخارج: 0 = مجتاز (قد توجد تحذيرات) · 1 = فشل يمنع التسليم.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TITLE = "قراءة الموقف وتحليل المؤشرات"

LEXICON = [
    "فرصة تكاد تكون معدومة",
    "مستبعد جدًا",
    "ضعيف الاحتمال",
    "غير مُرجَّح",
    "يُرجَّح ألّا",
    "فرصة متكافئة",
    "يُرجَّح جدًا",
    "يُرجَّح",
    "شبه مؤكد",
]

VAGUE = ["قد", "ربما", "يحتمل", "يشير إلى", "من المحتمل", "أظن", "لعل"]
AR = "\u0621-\u064A"

def _word(text: str, w: str) -> bool:
    """يبحث عن الكلمة ككلمة مستقلة، لا داخل كلمة أخرى (مثل «قد» داخل «التقدير»)."""
    return re.search(rf"(?<![{AR}]){re.escape(w)}(?![{AR}])", text) is not None

FIELD_LEAK = ["intel_analysis", "blocks_map", "hero_kpis", "meta[", "block_data", "source_reliability"]

errors: list[str] = []
blocking: list[str] = []
warns: list[str] = []


def read_section(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    parts = re.split(r"^##\s+", text, flags=re.M)
    for p in parts:
        first = p.split("\n", 1)[0].strip()
        if first.startswith(TITLE):
            return p
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="بوابة قراءة الموقف وتحليل المؤشرات")
    ap.add_argument("md", help="مسار تقرير Markdown")
    ap.add_argument("meta", nargs="?", help="مسار ملف الواجهة JSON (اختياري)")
    a = ap.parse_args()
    md = Path(a.md)
    meta_path = Path(a.meta) if a.meta else None
    if not md.exists():
        print(f"✘ الملف غير موجود: {md}")
        return 1

    sec = read_section(md)
    if not sec:
        _pol = {}
        try:
            import json as _json
            from pathlib import Path as _P
            _f = _P(__file__).resolve().parents[1] / 'appendices' / 'report-sections-policy.json'
            _pol = _json.loads(_f.read_text(encoding='utf-8'))
        except Exception:
            _pol = {}
        if TITLE in set(_pol.get('internal_only') or []):
            print(f"↷ مُتجاوز بحسب سياسة الأقسام: «{TITLE}» غير منشور (يُدوَّن داخليًا).")
            return 0
        print(f"✘ فشل (ف5/ح1): لا قسم بعنوان «{TITLE}» في {md.name}")
        return 1

    body = sec.split("\n", 1)[1] if "\n" in sec else ""
    
    # ── قرار المالك: الفقرات السردية محذوفة بقرار موثّق في السياسة ──
    _pol = {}
    try:
        import json as _json
        _pol = _json.loads((Path(__file__).resolve().parents[1] / "appendices" /
                            "report-sections-policy.json").read_text(encoding="utf-8"))
    except Exception:
        _pol = {}
    _narr = bool(_pol.get("intel_narrative_removed"))
    if _narr:
        print("  · ح1/ح2/ح3/ح5: الفقرات السردية محذوفة بقرار المالك — يُشترط ما بقي:")
    paras = [p for p in re.split(r"\n\s*\n", body) if len(p.strip()) > 40 and not p.strip().startswith("|")]

    print(f"===== بوابة قراءة الموقف وتحليل المؤشرات — {md.name} =====")

    # ح1 — الحد الأدنى ثلاث فقرات
    if len(paras) < 3 and not _narr:
        errors.append(f"ح1: فقرات القسم {len(paras)} والصقب الأدنى 3")
    else:
        print(f"  ✔ ح1: فقرات القسم = {len(paras)}")

    # ح2 — لغة عدم اليقين
    hits = [t for t in LEXICON if t in body]
    if not hits and not _narr:
        errors.append("ح2: لا عبارة احتمالية معتمدة من سلّم ICD 203")
    else:
        print(f"  ✔ ح2: عبارات الاحتمال المعتمدة = {len(hits)} → {', '.join(hits[:4])}")
    if not re.search(r"[（(]\s*\d{1,2}\s*[–\-]\s*\d{1,2}\s*%", body):
        warns.append("ح2: لا نطاق مئوي بصيغة «العبارة (55–80%)»")

    vague = sorted({v for v in VAGUE if _word(body, v)})
    if vague:
        errors.append("ح2: عبارات مبهمة ممنوعة → " + " · ".join(vague))
    else:
        print("  ✔ ح2: لا عبارات مبهمة في القسم")

    # ح3 — درجة الثقة
    if "درجة الثقة" not in body and not _narr:
        errors.append("ح3: لا سطر «درجة الثقة»")
    else:
        print("  ✔ ح3: درجة الثقة معلنة")

    # ح4 — سند المصدر بدرجته
    grade = re.search(r"\b[ABCDEF]\s*/\s*[1-6]\b|\b[ABCDEF][1-6]\b", body)
    if not grade and not (re.search(r"(?:موثوقية|الموثوقية)\s*[:：]?\s*[ABCDEF]\b", body)
                          and re.search(r"(?:مصداقية|المصداقية)\s*[:：]?\s*[1-6]\b", body)):
        warns.append("ح4: لا درجة مصدر A–F / 1–6 ظاهرة في القسم")

    # ح5 — الأساليب الأربعة
    checks = {
        "الافتراضات": ("افتراض", "الافتراضات"),
        "مؤشرات التغيّر": ("مؤشر", "مؤشرات"),
        "الفرضيات": ("فرضية", "الفرضيات", "الفرضية", "المتنافسة"),
        "تقييم دقة الأمس": ("تحقق", "لم يتحقق", "لم يتم التأكيد بعد"),
    }
    NARRATIVE_STYLES = {"الافتراضات", "الفرضيات", "تقييم دقة الأمس"}
    for label, keys in checks.items():
        if _narr and label in NARRATIVE_STYLES:
            print(f"  · ح5: {label} — محذوف بقرار المالك")
            continue
        if not any(k in body for k in keys):
            errors.append(f"ح5: الأسلوب «{label}» غير ظاهر في القسم")
        else:
            print(f"  ✔ ح5: {label}")

    # ح6 — عدد المؤشرات
    ind_rows = [ln for ln in body.split("\n") if ln.strip().startswith("|") and "مؤشر" in ln]
    print(f"  · ح6: صفوف المؤشرات = {len(ind_rows)}")

    # ح11 — المراجعة النظيرة
    if "المراجعة النظيرة" not in body:
        warns.append("ح11: لا سطر مراجعة نظيرة أسفل القسم")

    # تنظيف النص من أسماء الحقول البرمجية
    leaked = [f for f in FIELD_LEAK if f in body]
    if leaked:
        errors.append("ح1/ك1: تسرب أسماء حقول برمجية → " + " · ".join(leaked))

    # ── ما يجب أن يبقى داخل القسم بعد إزالة الفقرات السردية ──
    if _narr:
        if not any(k in body for k in ("علامات الإنذار المبكر", "مؤشرات الإنذار", "مؤشرات تحذير مبكر")):
            errors.append("بقاء-1: «علامات الإنذار المبكر» غير ظاهرة بعد الحذف الجزئي (تُقبل الصيغة القديمة أيضًا)")
        else:
            print("  ✔ بقاء-1: علامات الإنذار المبكر")
        if not re.search(r"EST-\d{4}-\d{2}-\d{2}-\d{2}", body):
            errors.append("بقاء-2: جدول رموز التقدير EST غير ظاهر بعد الحذف الجزئي")
        else:
            print("  ✔ بقاء-2: جدول رموز التقدير EST")
        # ك-196: تعارض مع G035 (منع ذكر العمل الداخلي في المتن). السجل صار في الواجهة.
        _mp = meta_path
        _meta_rev = ""
        if _mp is not None and _mp.is_file():
            _meta_rev = str((json.loads(_mp.read_text(encoding="utf-8")).get("intel_analysis") or {}).get("internal_review", "") or "")
        if not _meta_rev:
            warns.append("بقاء-3: سجل المراجعة الداخلية غير ظاهر في الواجهة")
        else:
            print("  ✔ بقاء-3: سجل المراجعة الداخلية في الواجهة")

    # ح12 — وسم الأسلوب في ملف الواجهة
    if meta_path and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            blk = meta.get("intel_analysis") or {}
            method = (blk.get("method") or "").strip()
            if not method:
                errors.append("ح12: لا وسم أسلوب تحليلي (intel_analysis.method)")
            else:
                print(f"  ✔ ح12: وسم الأسلوب = {method}")
            inds = blk.get("indicators") or []
            if not (3 <= len(inds) <= 5):
                warns.append(f"ح6: عدد مؤشرات التحذير المبكر في ملف الواجهة = {len(inds)} (المعتمد 3–5)")
            # ك-: خريطة بلا نقاط = تسليم بلا خريطة. تُمنع مبكرًا بدل أن تفشل بوابة الطباعة متأخرة.
            evs = [e for e in (meta.get("event_keys") or []) if (e.get("area") or "").strip()]
            _mp = meta.get("map") or {}
            mpts = _mp.get("points") or []
            off_map = _mp.get("off_map") or []
            _excl = {"خارج القطاعات", "المنطقة كاملة"}
            need = [e for e in evs if (e.get("area") or "").strip() not in _excl]
            drawn = {p.get("code") for p in mpts}
            missing = [e.get("code") for e in need if e.get("code") not in drawn]
            if need and missing:
                blocking.append("ح13: وقائع بمنطقة بلا نقطة على الخريطة ({} من {}): {}".format(
                    len(missing), len(need), "، ".join(str(x) for x in missing[:4])))
            elif need and len(mpts) + len(off_map) < len(need):
                blocking.append("ح13: نقاط الخريطة ({}) + خارج النطاق ({}) أقل من الوقائع ذات المنطقة ({})".format(
                    len(mpts), len(off_map), len(need)))
            else:
                print(f"  ✔ ح13: نقاط الخريطة = {len(mpts)} من {len(need)} واقعة بمنطقة · خارج النطاق {len(off_map)}")
            for _p in mpts:
                if _p.get("precision") not in ("exact", "approximate"):
                    blocking.append(f"ح13: نقطة بلا تصنيف دقة معتمد: {_p.get('code')}")
                elif _p.get("precision") == "approximate" and not (_p.get("basis") or "").strip():
                    blocking.append(f"ح13: موضع تقريبي بلا أساس مكتوب: {_p.get('code')}")
        # تضييق مقصود (2026-10-28): أعطال القراءة/التحليل المتوقعة فقط — ما عداها يظهر ولا يُبتلع.
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError) as e:
            errors.append(f"تعذر قراءة ملف الواجهة: {e}")
    else:
        warns.append("لم يُمرَّر ملف الواجهة — لم يُفحص وسم الأسلوب (ح12)")

    print()
    for w in warns:
        print(f"  ⚠ {w}")
        if errors or blocking:
            for b in blocking:
                print(f"  ✘ {b}")
            for e in errors:
                print(f"  ✘ {e}")
            print(f"\nالنتيجة: فشل — {len(errors) + len(blocking)} خطأ ({len(blocking)} مانع) · {len(warns)} تحذير")
            return 2 if blocking else 1
    print(f"\nالنتيجة: مجتاز — 0 خطأ · {len(warns)} تحذير")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)
