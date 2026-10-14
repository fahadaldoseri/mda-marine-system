#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مدقق التقرير الصباحي — الإصدار 2.2 (يستبدل المدقق السابق المتجاوَز).

كل فحص يصرّح برقم القاعدة التي ينفّذها من `sections/`:
  ف1 — بنية ملف واجهة الإصدار 2.1 وحقوله الإلزامية
  ف2 — بوابة بساطة اللغة (تُشغَّل بأداة مستقلة ويُستدعى ناتجها هنا)
  ف4 — قائمة فحوص التحقق الكاملة (الأرقام الداخلية 1..10 داخل ف4)

الاستخدام:
  python3 validators/validate_report.py web/meta/<التاريخ>.json [--md reports/<التاريخ>-sectioned.md]
يعيد 0 عند النجاح، و2 عند مخالفة مانعة، و3 عند تحذيرات فقط.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = {
    "report_schema_version": str, "title": str, "subtitle": str, "date_label": str,
    "headline": str, "lede": str, "window": str, "generated_label": str,
    "threat_level": str, "sources_checked": int, "sources_cited": int,
    "description": str, "notice": str, "hero_kpis": list, "map": dict,
    "classification": str, "ledger_url": str, "decision_card": dict, "changes": list,
    "indicators": list, "hypotheses": list, "gaps": list, "event_keys": list,
    "timeline": list, "blocks": dict, "glossary": dict,
}
DECISION_FIELDS = ["changed", "risk", "risk_kind", "action", "watch", "basis"]
# delta اختياري: المولّد يرسمه فقط عند وجوده (web/build_report.py)
HERO_FIELDS = ["label", "value", "note", "accent"]
INDICATOR_FIELDS = ["name", "current", "previous", "trend", "delta", "meaning"]
HYPOTHESIS_FIELDS = ["statement", "support", "against", "likelihood"]
GAP_FIELDS = ["gap", "owner", "impact"]
EVENT_FIELDS = ["code", "title", "area", "status", "note"]
TIMELINE_FIELDS = ["date", "count", "kind", "label"]

INTERNAL = ["checked_sources", "cited_sources", "confirmed_attacks_24h", "new_ukmto_reports_24h",
            "new_warnings_24h", "new_advisories_24h", "decision_card", "hero_kpis",
            "event_keys", "ledger_url", "report_schema_version", "kpis",
            "JSON", "schema", "قاعدة رقم", "الفهرس"]

TERM_MAP = {
    "هجمات جديدة": "وقائع أمنية جديدة",
    "إشعارات استشارية": "نشرات استشارية",
    "تحذير هجومي": "تحذير أمني بحري",
    "أجسام مجهولة": "مقذوفات غير محددة المصدر",
    "الصورة الجغرافية": "التوزيع الجغرافي",
    "الاختناق": "التكدس الملاحي",
    "المراجعة المعارضة الذاتية": "اختبار الفرضية المضادة",
    "الجهة الفاعلة": "الطرف المسؤول",
    "إدخالات": "بنود",
    "القياس السابق": "تقرير أمس",
    "في القياس": "في تقرير أمس",
}

TEMP_URL = re.compile(r"https?://[^\s\"']*(manus\.computer|ngrok|localhost|127\.0\.0\.1)[^\s\"']*")
CODE_RE = re.compile(r"MN-\d{4}-\d{2}-\d{2}-\d{2}")
REGION = {"lat": (12.0, 32.0), "lon": (32.0, 65.0)}


def strings_of(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from strings_of(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from strings_of(v, f"{path}[{i}]")
    elif isinstance(value, str):
        yield path, value


def check_schema(d):
    """ف1 — البنية والحقول."""
    errs = []
    for key, typ in REQUIRED.items():
        if key not in d:
            errs.append(f"[ف1] حقل مفقود: {key}")
        elif not isinstance(d[key], typ):
            errs.append(f"[ف1] نوع خاطئ للحقل {key}: {type(d[key]).__name__} بدل {typ.__name__}")
    if d.get("report_schema_version") != "2.1":
        errs.append(f"[ف1] إصدار المخطط غير معتمد: {d.get('report_schema_version')}")
    obj = d.get("decision_card") or {}
    errs += [f"[ف1] decision_card ينقصه {f}" for f in DECISION_FIELDS if f not in obj]
    for name, fields in (("hero_kpis", HERO_FIELDS), ("indicators", INDICATOR_FIELDS),
                         ("hypotheses", HYPOTHESIS_FIELDS), ("gaps", GAP_FIELDS),
                         ("event_keys", EVENT_FIELDS), ("timeline", TIMELINE_FIELDS)):
        for i, item in enumerate(d.get(name) or []):
            if not isinstance(item, dict):
                errs.append(f"[ف1] {name}[{i}] ليس كائنًا")
                continue
            errs += [f"[ف1] {name}[{i}] ينقصه {f}" for f in fields if f not in item]
    for sec, ref in (d.get("blocks") or {}).items():
        if not isinstance(ref, str):
            continue
        for name in [n.strip() for n in ref.split("+") if n.strip()]:
            if name not in d:
                errs.append(f"[ف1] الكتلة «{sec}» تشير إلى حقل غير موجود: {name}")
    return errs


def check_time(d):
    """ف4.1 — التاريخ والوقت والنافذة."""
    errs, warns = [], []
    try:
        dt = datetime.fromisoformat(str(d["generated_label"]).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            errs.append("[ف4.1] وقت التوليد بلا منطقة زمنية")
        elif dt.utcoffset() != timezone.utc.utcoffset(None):
            errs.append("[ف4.1] وقت التوليد ليس بتوقيت غرينتش UTC")
    except Exception:
        errs.append(f"[ف4.1] وقت التوليد غير صالح: {d.get('generated_label')}")
    if not re.search(r"\d{4}", str(d.get("date_label", ""))):
        errs.append("[ف4.1] وسم التاريخ بلا سنة")
    if not re.search(r"UTC|غرينتش", str(d.get("window", "")) + str(d.get("lede", ""))):
        warns.append("[ف4.1] النافذة الزمنية لا تذكر UTC صراحة")
    return errs, warns


def check_hypotheses(d):
    """ف4.3 — مجموع الاحتمالات = 100% وصيغتها معيارية."""
    hs = d.get("hypotheses") or []
    if not hs:
        return ["[ف4.3] لا فرضيات"]
    total, bad = 0.0, []
    for h in hs:
        raw = str(h.get("likelihood", "")).strip()
        m = re.match(r"^(\d+(?:\.\d+)?)\s*%$", raw)
        if not m:
            bad.append(raw)
        else:
            total += float(m.group(1))
    errs = []
    if bad:
        errs.append(f"[ف4.3] صيغة احتمال غير معيارية (يجب نسبة مئوية): {bad}")
    if abs(total - 100.0) > 0.1:
        errs.append(f"[ف4.3] مجموع الاحتمالات {total} وليس 100")
    return errs


def check_events(d):
    """ف4.5 و ف4.7 — رموز الأحداث والخريطة وعدم المبالغة."""
    errs, warns = [], []
    keys = {e.get("code") for e in (d.get("event_keys") or [])}
    text_codes = {c for _, s in strings_of(d) for c in CODE_RE.findall(s)}
    unknown = sorted(text_codes - keys)
    if unknown:
        errs.append(f"[ف4.5] رموز أحداث في النص بلا سجل في event_keys: {unknown}")
    for i, e in enumerate(d.get("event_keys") or []):
        if not CODE_RE.fullmatch(str(e.get("code", ""))):
            errs.append(f"[ف4.5] صيغة رمز غير معيارية في event_keys[{i}]: {e.get('code')}")
    for p in (d.get("map") or {}).get("points") or []:
        if p.get("code") and p["code"] not in keys:
            errs.append(f"[ف4.5] نقطة خريطة برمز غير مسجّل: {p['code']}")
        lat, lon = p.get("lat"), p.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            errs.append(f"[ف4.5] إحداثيات غير رقمية في نقطة الخريطة: {p.get('label')}")
        elif not (REGION["lat"][0] <= lat <= REGION["lat"][1] and REGION["lon"][0] <= lon <= REGION["lon"][1]):
            warns.append(f"[ف4.2] نقطة خارج نطاق التغطية: {p.get('label')} ({lat},{lon})")
    attack = None
    for k in d.get("hero_kpis") or []:
        lab = str(k.get("label", ""))
        if "هجوم" in lab and "مؤكد" in lab:
            m = re.search(r"\d+", str(k.get("value", "")))
            attack = int(m.group()) if m else None
    # واقعة مصنفة هجومًا: هجوم أو إصابة أو استهداف أو اعتراض
    ATK = ("هجوم", "إصابة", "استهداف", "اعتراض", "إطلاق")
    confirmed = sum(1 for e in (d.get("event_keys") or [])
                    if any(w in str(e.get("title", "")) for w in ATK))
    if attack is not None and attack > confirmed:
        errs.append(f"[ف4.7] مؤشر الهجمات المؤكدة ({attack}) يتجاوز الوقائع المصنفة هجومًا ({confirmed})")
    return errs, warns


def check_timeline(d):
    """ف4.4 — الخط الزمني يغطي أيام النافذة بلا تكرار."""
    errs, warns = [], []
    tl = d.get("timeline") or []
    dates = [str(t.get("date", "")) for t in tl]
    if len(set(dates)) != len(dates):
        errs.append("[ف4.4] تكرار أيام في الخط الزمني")
    days = re.findall(r"\b(\d{1,2})\b", str(d.get("window", "")))
    if len(tl) < 2:
        warns.append(f"[ف4.4] الخط الزمني قصير: {len(tl)} يومًا")
    elif len(days) >= 2:
        expected = abs(int(days[0]) - int(days[1])) + 1
        if len(tl) < expected:
            warns.append(f"[ف4.4] الخط الزمني لا يغطي كل أيام النافذة ({len(tl)} من {expected})")
    return errs, warns


def check_reader_text(d):
    """ف4.8 و ف4.9 — نظافة النص الموجّه للقارئ."""
    errs, warns = [], []
    for path, s in strings_of(d):
        if path.startswith("blocks"):
            continue
        for term in INTERNAL:
            if term in s:
                errs.append(f"[ف4.8] عبارة داخلية «{term}» في {path}")
        for bad, good in TERM_MAP.items():
            if bad in s:
                warns.append(f"[ف4.9] استخدم «{good}» بدل «{bad}» في {path}")
    return errs, warns


def check_delivery(d):
    """ف4.10 — لا روابط مؤقتة، والتصنيف معلن، وحاجز النشر."""
    errs, warns = [], []
    url = str(d.get("ledger_url", ""))
    if TEMP_URL.search(url):
        errs.append(f"[ف4.10] رابط مؤقت في ledger_url: {url}")
    elif not url.startswith("/") and "seawatch" not in url:
        warns.append(f"[ف4.10] ledger_url ليس مسارًا نسبيًا ولا نطاق الموقع الدائم: {url}")
    if d.get("classification") not in ("عام", "مقيّد", "حساس"):
        errs.append(f"[ف4.10] تصنيف غير معتمد: {d.get('classification')}")
    elif d.get("classification") in ("مقيّد", "حساس"):
        warns.append("[ف4.10] إصدار مقيّد أو حساس: يُمنع نشره علنًا حسب س1")
    return errs, warns


def check_language(md_path):
    """ف2 — بوابة بساطة اللغة عبر أداتها."""
    if not md_path:
        return [], ["[ف2] لم يُمرَّر ملف التقرير النصي، فلم تُشغَّل بوابة اللغة"]
    tool = ROOT / "validators" / "check_language.py"
    if not tool.exists():
        return [], [f"[ف2] أداة بوابة اللغة غير موجودة: {tool}"]
    p = subprocess.run([sys.executable, str(tool), str(md_path)], capture_output=True, text=True)
    out = (p.stdout or "").strip().splitlines()
    if p.returncode == 0:
        return [], [f"[ف2] {out[-1] if out else 'مقبول'}"]
    return [f"[ف2] {line.strip('- ')}" for line in out if line.strip().startswith("-") or "رفض" in line], []


def main():
    ap = argparse.ArgumentParser(description="مدقق التقرير الصباحي — الإصدار 2.2")
    ap.add_argument("meta", help="ملف واجهة الإصدار 2.1")
    ap.add_argument("--md", default="", help="ملف التقرير النصي لتشغيل بوابة اللغة")
    a = ap.parse_args()

    path = Path(a.meta)
    if not path.exists():
        print(f"الملف غير موجود: {path}")
        return 2
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ف1] JSON غير صالح: {e}")
        return 2

    errors = check_schema(d) + check_hypotheses(d)
    warnings = []
    for fn in (check_time, check_events, check_timeline, check_reader_text, check_delivery):
        e, w = fn(d)
        errors += e
        warnings += w
    e, w = check_language(a.md)
    errors += e
    warnings += w

    print(f"الملف: {path} · الإصدار: {d.get('report_schema_version')} · التصنيف: {d.get('classification')}")
    print(f"الوقائع: {len(d.get('event_keys') or [])} · المؤشرات: {len(d.get('indicators') or [])} "
          f"· الفرضيات: {len(d.get('hypotheses') or [])} · المصادر: {d.get('sources_checked')} مفحوص / "
          f"{d.get('sources_cited')} مستشهد")
    if warnings:
        print(f"\nتحذيرات ({len(warnings)}):")
        for w in warnings:
            print("  -", w)
    if errors:
        print(f"\nمخالفات مانعة ({len(errors)}):")
        for e in errors:
            print("  -", e)
        print("\nالنتيجة: رفض التسليم حتى الإصلاح.")
        return 2
    print("\nالنتيجة: اجتاز كل الفحوص المانعة.")
    return 3 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
