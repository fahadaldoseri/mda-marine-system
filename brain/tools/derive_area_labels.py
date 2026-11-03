#!/usr/bin/env python3
"""اشتقاق وسم «الموقع» في دفتر الأحداث من سجل المناطق البحرية الحاكم.

القاعدة: الوسم يحمل اسم المنطقة البحرية نفسها، أو «الموقع الدقيق - المنطقة البحرية»
عندما يذكر المصدر موقعًا ساحليًا. لا تخمين: كل تحويل مسنود إلى جدول معلن في
appendices/area-registry.json أو إلى اسم مسطح بحري مذكور نصًّا.

الاستعمال:
  python3 tools/derive_area_labels.py --report /tmp/area-relabel.tsv        # قياس فقط
  python3 tools/derive_area_labels.py --apply --backup-stamp 20261103       # تطبيق
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "cumulative-2026" / "daily"
REGISTRY = ROOT / "appendices" / "zone-registry.json"


def norm(text: str) -> str:
    """تطبيع عربي/لاتيني للمطابقة: بلا تشكيل، بألف وياء موحدتين."""
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("ـ", "")
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ئ", "ي"), ("ؤ", "و")):
        t = t.replace(a, b)
    t = t.replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", t).strip().lower()


def stems(text: str) -> list[str]:
    """صيغ مطابقة: الاسم كما هو، وبلا «ال» التعريف، وبلا حروف الجر الملتصقة.

    عربيًّا تُكتب «للإمارات» و«بالبحرين»، والمطابقة الحرفية تفشل معها؛
    فنطابق الجذع بلا سابقة مكوّنة من حرف أو حرفين ثم «ال».
    """
    base = norm(text)
    out = [base]
    stripped = re.sub(r"^[وفبكل]{0,2}ال", "", base)
    if stripped and stripped != base:
        out.append(stripped)
    return out


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def sea_terms(reg: dict) -> list[tuple[str, str]]:
    """أزواج (اسم مطابق مُطبَّع، الاسم الحاكم بالعربية)، الأطول أولًا."""
    out: list[tuple[str, str]] = []
    for a in reg["areas"]:
        for term in (a["ar"], a["en"]):
            out.append((norm(term), a["ar"]))
        # مرادفات شائعة في المصادر
    extra = {
        "خليج عمان": "خليج عُمان",
        "بحر عمان": "خليج عُمان",
        "gulf of oman": "خليج عُمان",
        "arabian gulf": "الخليج العربي",
        "persian gulf": "الخليج العربي",
        "red sea": "البحر الأحمر",
        "arabian sea": "بحر العرب",
        "gulf of aden": "خليج عدن",
        "horn of africa": "القرن الأفريقي",
        "indian ocean": "المحيط الهندي",
        "black sea": "البحر الأسود",
        "bab-el-mandeb": "باب المندب",
        "bab el mandeb": "باب المندب",
    }
    for k, v in extra.items():
        out.append((norm(k), v))
    seen = set()
    uniq = []
    for term, name in sorted(out, key=lambda x: -len(x[0])):
        if term in seen or not term:
            continue
        seen.add(term)
        uniq.append((term, name))
    return uniq


def find_seas(text: str, terms: list[tuple[str, str]]) -> list[str]:
    t = norm(text)
    found: list[str] = []
    for term, name in terms:
        if term in t and name not in found:
            found.append(name)
    return found


def find_place(text: str, reg: dict) -> tuple[str, str] | None:
    t = norm(text)
    for row in reg["place_area"]:
        for m in row["match"]:
            if any(v in t for v in stems(m)):
                return row["place"], row["area"]
    return None


def find_country(text: str, reg: dict) -> tuple[str, str] | None:
    t = norm(text)
    for row in reg["country_area"]:
        for m in row["match"]:
            if any(v in t for v in stems(m)):
                return row["country"], row["area"]
    return None


def scope_value(raw: str, reg: dict) -> str | None:
    """قيم النطاق المحفوظة كما هي: «المنطقة كاملة» · «سياق إقليمي» · «غير مكانية»."""
    r = norm(raw)
    for keep in ("المنطقة كاملة", "سياق إقليمي", "غير مكانية"):
        if norm(keep) == r:
            return keep
    return None


def conformant(raw: str, reg: dict) -> bool:
    """هل القيمة مطابقة لصيغة السجل؟ يمنع إعادة تحويل قيمة سليمة (ثبات الأداة)."""
    names = {a["ar"] for a in reg["areas"]}
    parts = [p.strip() for p in raw.split("·") if p.strip()]
    if not parts:
        return False
    for part in parts:
        if part in names:
            continue
        if " - " in part:
            left, _, right = part.rpartition(" - ")
            if left.strip() and right.strip() in names:
                continue
        return False
    return True


def sector_of(area_name: str, reg: dict) -> str | None:
    for a in reg["areas"]:
        if a["ar"] == area_name:
            return a.get("sector")
    return None


def sector_label(sid: str | None, reg: dict) -> str:
    if not sid:
        return ""
    for s in reg["zones"]:
        if s["id"] == sid:
            return f"{sid} — {s['ar']}"
    return sid


def is_no_incident(row: dict) -> bool:
    """صفوف ليست وقائع: «لا واقعة» · وإسقاط المادة بلا واقعة."""
    code = str(row.get("code") or "")
    title = str(row.get("title") or "")
    desc = str(row.get("source_description") or "")
    if code.startswith("NI-") or "لا واقعة" in title or "لا واقعة" in desc:
        return True
    if code.startswith("COVER-") and not str(row.get("area") or "").strip():
        return True
    return False


def derive(row: dict, reg: dict, terms: list[tuple[str, str]]) -> tuple[str | None, str, str | None]:
    """يعيد (القيمة الجديدة أو None للإزالة، رمز القاعدة، معرّف القطاع)."""
    if is_no_incident(row):
        return None, "R5:صف «لا واقعة» بلا قيمة موقع", None
    raw = str(row.get("area") or "").strip()
    location = str(row.get("location") or "").strip()
    title = str(row.get("title") or "").strip()
    excerpt = str(row.get("source_excerpt") or "")[:300]

    # R0: قيمة نطاق معلنة تُحفظ كما هي (ليست موقعًا).
    kept = scope_value(raw, reg)
    if kept:
        return kept, "R0:قيمة نطاق محفوظة", None

    # R0ب: قيمة مطابقة للصيغة تُحفظ كما هي (ثبات الأداة).
    if conformant(raw, reg):
        return raw, "R0ب:قيمة مطابقة محفوظة", sector_of(raw.split("·")[0].split(" - ")[-1].strip(), reg)

    # R1: اسم مسطح بحري مذكور نصًّا (في وسم المصدر نفسه أولًا)
    for source, tag in ((raw, "R1"), (location, "R1"), (title, "R1"), (excerpt, "R1")):
        seas = find_seas(source, terms)
        if seas:
            pos = norm(source)
            seas = sorted(seas, key=lambda n: pos.find(norm(n)))
            value = " · ".join(seas)
            sid = sector_of(seas[0], reg) if len(seas) == 1 else None
            return value, f"{tag}:اسم مسطح بحري في {tag[-2:] if tag else ''}{'وسم المصدر' if source is raw else 'نص الواقعة'}", sid

    # R2: موقع دقيق ساحلي ← «الموقع - المنطقة البحرية»
    for source in (raw, location, title, excerpt):
        hit = find_place(source, reg)
        if hit:
            place, area = hit
            return f"{place} - {area}", "R2:قاعدة الساحل (موقع دقيق)", sector_of(area, reg)

    # R3: دولة فقط ← «الدولة - المنطقة البحرية»
    for source in (raw, location, title, excerpt):
        hit = find_country(source, reg)
        if hit:
            country, area = hit
            return f"{country} - {area}", "R3:جدول الدولة", sector_of(area, reg)

    # R4: لا مسطح بحري ولا موقع ساحلي
    return reg["non_spatial_value"], "R4:غير مكانية (بلا مسطح بحري)", None


def walk_rows(obj, out: list[dict]) -> None:
    if isinstance(obj, dict):
        if isinstance(obj.get("area"), str) and obj["area"].strip():
            out.append(obj)
        for v in obj.values():
            walk_rows(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_rows(v, out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="كتابة القيم الجديدة في الدفتر")
    ap.add_argument("--report", default="", help="مسار تقرير TSV")
    ap.add_argument("--backup-stamp", default="", help="وسم النسخة الاحتياطية قبل التطبيق")
    args = ap.parse_args()

    reg = load_registry()
    terms = sea_terms(reg)
    files = sorted(LEDGER.glob("*.json"))
    rows_report: list[tuple[str, str, str, str, str, str]] = []
    changed = unchanged = 0
    pairs: dict[tuple[str, str], int] = {}
    unresolved: list[str] = []
    touched_files: list[pathlib.Path] = []

    targets: list[pathlib.Path] = list(files) + sorted((ROOT / "web" / "meta").glob("*.json"))
    for f in targets:
        data = json.loads(f.read_text(encoding="utf-8"))
        out: list[dict] = []
        walk_rows(data, out)
        dirty = False
        for row in out:
            before = str(row.get("area") or "").strip()
            value, rule, sid = derive(row, reg, terms)
            if value is None:
                if "area" in row:
                    if args.apply:
                        row.pop("area", None)
                        dirty = True
                    changed += 1
                    rows_report.append((f.stem, str(row.get("code") or ""), before, "(بلا قيمة)", rule, ""))
                    pairs[(before, "(بلا قيمة)")] = pairs.get((before, "(بلا قيمة)"), 0) + 1
                else:
                    unchanged += 1
                continue
            if value == before and (row.get("sector_id") or "") == (sid or ""):
                unchanged += 1
                continue
            if value == before:
                if args.apply and (row.get("sector_id") or "") != (sid or ""):
                    row["sector_id"] = sid or ""
                    row["sector"] = sector_label(sid, reg)
                    dirty = True
                unchanged += 1
                continue
            changed += 1
            rows_report.append((f.stem, str(row.get("code") or ""), before, value, rule, sid or ""))
            pairs[(before, value)] = pairs.get((before, value), 0) + 1
            if rule.startswith("R4") and before != reg["non_spatial_value"]:
                unresolved.append(f"{f.stem} · {row.get('code')} · «{before}»")
            if args.apply:
                row["area"] = value
                row["sector_id"] = sid or ""
                row["sector"] = sector_label(sid, reg)
                dirty = True
        if args.apply and dirty:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            touched_files.append(f)

    if args.report:
        p = pathlib.Path(args.report)
        p.write_text(
            "التاريخ\tالشفرة\tقبل\tبعد\tالقاعدة\tالقطاع\n"
            + "\n".join("\t".join(r) for r in rows_report)
            + "\n",
            encoding="utf-8",
        )

    print(f"   ملفات الدفتر: {len(files)} · صفوف لها قيمة موقع: {len(rows_report) + unchanged}")
    print(f"   يتغيّر: {changed} · بلا تغيير: {unchanged} · أزواج تحويل مختلفة: {len(pairs)}")
    print("   ══ أكبر عشرة تحويلات ══")
    for (b, a), c in sorted(pairs.items(), key=lambda x: -x[1])[:10]:
        print(f"   {c:>4} × «{b[:46]}» ← «{a[:46]}»")
    print(f"   ══ صفوف بقيت «غير مكانية» بلا دليل مكاني: {len(unresolved)} ══")
    for u in unresolved[:12]:
        print(f"      {u}")
    if args.apply:
        print(f"   طُبِّق على {len(touched_files)} ملفًا")
    else:
        print("   (قياس فقط — بلا كتابة)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
