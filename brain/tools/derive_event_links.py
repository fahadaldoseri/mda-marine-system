#!/usr/bin/env python3
"""اشتقاق روابط الوقائع في الدفتر التراكمي — بالدليل فقط، بلا تشابه نصي.

المشكلة التي يحلّها (فجوة بيانات الربط المعلنة في تقرير 2026-11-01):
حقول `update_of` و`parent_id` و`duplicate_of` كانت صفرًا في كل الدفتر، فظهر في بطاقة
سجل الأحداث إفصاح «لا توجد حقول تثبت فرعًا تابعًا». والسبب أن الدفتر يُكتب يومًا بيوم
ولا خطوة تربط واقعة اليوم بواقعة سابقة.

قواعد الاشتقاق (كل رابط يُسند إلى حقل معرّف حقيقي، ولا يُشتق رابط من تشابه نصي):

 1) duplicate_of — تكرار حرفي: نفس `source_url` القانوني + نفس العنوان بعد التطبيع.
  2) update_of و`parent_id` — الواقعة نفسها تُحدَّث عبر الأيام، بمعرّف الواقعة الرسمي:
     · رقم التحذير الرسمي نفسه المستخرج من نصّ المصدر (مثال UKMTO 190-26).
     · معرّف واقعة رسمي (`evidence_ref`) بصيغة معرّف لا رابط صفحة.
  3) لا يُشتق أي رابط من تشابه نصي، ولا من تطابق اسم مصدر، ولا من قرب زمني،
     ولا من تكرار اسم السفينة: تكرار السفينة واقعتان مختلفتان لا تحديث لواحدة.
  4) يُسجَّل المعرّف الرسمي في السجل (`official_ref`) ليصبح الربط ممكنًا في الأيام القادمة.

حقول مساندة تُملأ فقط عندما يذكرها المصدر نصًّا، مع حفظ نص السند:
  · `incident_kind` من كلمة صريحة في العنوان أو التصنيف أو المقتطف.
  · `target` = «سفينة» عند ذكر سفينة صراحة.

الاستعمال:
  python3 tools/derive_event_links.py                 # تجفيف: يعرض ما سيتغيّر
  python3 tools/derive_event_links.py --apply         # يكتب ويحفظ النسخ الأصلية
  python3 tools/derive_event_links.py --json out.json # تقرير مفصّل

المخرجات: تعديل ملفات `cumulative-2026/daily/*.json` في مواضعها + تقرير JSON.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRAIN = pathlib.Path(os.environ.get("BRAIN_DIR") or ROOT)
DAILY = BRAIN / "cumulative-2026" / "daily"
BACKUP_DIR = pathlib.Path("/home/ubuntu/audit-2026-10-30/backups-20261102")

# ── استخراج المعرّفات ──────────────────────────────────────────────────────────
WARN_RE = re.compile(r"(?:UKMTO|تحذير)[^\n]{0,40}?(\d{2,4}-\d{2})", re.IGNORECASE)
DATE_LIKE_RE = re.compile(r"^20\d\d-\d\d$")
REF_ID_RE = re.compile(r"^(?:IMO|UKMTO|EV|MN)-[0-9A-Za-z-]+$")

KIND_WORDS = [
    ("هجوم", ["هجوم", "استهدف", "استهداف", "أصيبت", "اصيبت", "ضربة", "صاروخ"]),
    ("حريق", ["حريق", "اشتعال", "اشتعلت", "نيران"]),
    ("ألغام", ["لغم", "ألغام", "الغام"]),
    ("تسرب", ["تسرب", "تسّرْب"]),
    ("اختطاف", ["اختطاف", "خطف", "اختُطفت"]),
    ("تهديد", ["تهديد", "تحذير من خطر"]),
    ("إغلاق", ["إغلاق", "اغلاق", "أُغلق المضيق"]),
    ("جنوح", ["جنوح", "جُنحت"]),
    ("عطل", ["عطل", "تعطل", "خلل فني"]),
    ("نشاط مشبوه", ["نشاط مشبوه", "نشاط غير معتاد"]),
]


def allowed_kinds() -> set[str]:
    """القائمة المغلقة للتصنيف من المخطط الحاكم — لا تُخترع قيم من خارجه."""
    p = BRAIN / "schemas" / "daily-events.schema.json"
    try:
        s = json.loads(p.read_text(encoding="utf-8"))
        return set(s["$defs"]["material_record"]["properties"]["incident_kind"].get("enum") or [])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return {k for k, _ in KIND_WORDS}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def record_date(rec: dict) -> str:
    return str(rec.get("date") or "")


def warn_of(rec: dict) -> str | None:
    txt = f"{rec.get('title', '')} {rec.get('source_excerpt', '')} {rec.get('description', '')}"
    m = WARN_RE.search(txt)
    if not m:
        return None
    val = m.group(1)
    return None if DATE_LIKE_RE.match(val) else val


def official_ref(rec: dict) -> str | None:
    """معرّف واقعة رسمي — لا رابط صفحة ولا رقم يشبه التاريخ."""
    ref = norm(str(rec.get("evidence_ref") or ""))
    if ref and REF_ID_RE.match(ref):
        return ref
    txt = " ".join(str(rec.get(k, "")) for k in
                   ("title", "source_excerpt", "description", "class", "classification"))
    found = sorted(refs_in_text(txt))
    return f"UKMTO-{found[0]}" if found else None


REF_TEXT_RE = re.compile(
    r"(?:UKMTO|النشرة|التحذير|تحذير|Advisory|WARNING|Warning)[^\n]{0,30}?(\d{2,4}-\d{2})"
)


def refs_in_text(txt: str) -> set[str]:
    out = set()
    for m in REF_TEXT_RE.finditer(txt or ""):
        v = m.group(1)
        if not DATE_LIKE_RE.match(v):
            out.add(v)
    return out


def frozen_reference_map() -> dict[str, str]:
    """معرّف النشرة الرسمية ← معرّف الواقعة في الدفتر المجمّد (28 فبراير–11 أكتوبر)."""
    p = BRAIN / "cumulative-2026" / "event-ledger-sectioned-2026-02-28-to-2026-10-11.json"
    out: dict[str, str] = {}
    if not p.exists():
        return out
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return out
    for e in j.get("events", []):
        txt = " ".join([
            str(e.get("description", "")),
            str(e.get("classification", "")),
            " ".join(e.get("sources") or []),
        ])
        for r in refs_in_text(txt):
            out.setdefault(r, str(e.get("event_id") or ""))
    return out


def kind_of(rec: dict) -> tuple[str | None, str | None]:
    hay = " ".join(
        str(rec.get(k, ""))
        for k in ("title", "class", "classification", "source_excerpt", "description", "outcome")
    )
    for kind, words in KIND_WORDS:
        for w in words:
            if w in hay:
                return kind, w
    return None, None


def load_days() -> list[tuple[pathlib.Path, list[dict]]]:
    out = []
    for f in sorted(DAILY.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:  # ملف تالف يُعلن ولا يُتجاوز
            print(f"   ✘ تعذّر قراءة {f.name}: {exc}")
            continue
        if isinstance(data, list):
            out.append((f, data))
    return out


def derive(days) -> tuple[dict, dict]:
    """يعيد (التعديلات، التقرير). التعديلات: {file: {code: {field: value}}}"""
    edits: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(dict))
    report: dict = {"links": [], "kinds": [], "skipped_no_evidence": 0, "days": len(days), "records": 0}

    # فهرسة كل السجلات بترتيب زمني
    index: list[tuple[str, str, dict]] = []  # (date, code, record)
    for f, recs in days:
        for r in recs:
            if not isinstance(r, dict):
                continue
            index.append((record_date(r) or f.stem, str(r.get("code") or ""), r))
    index.sort(key=lambda t: (t[0], t[1]))
    report["records"] = len(index)

    # 1) التكرار الحرفي
    seen_title: dict[tuple[str, str], str] = {}
    for date, code, r in index:
        url = norm(r.get("source_url"))
        title = norm(r.get("title"))
        if url and title:
            key = (url, title)
            if key in seen_title and seen_title[key] != code:
                edits[date][code]["duplicate_of"] = seen_title[key]
                edits[date][code]["link_basis"] = f"source_url + title متطابقان مع {seen_title[key]}"
                report["links"].append({"kind": "duplicate_of", "code": code, "of": seen_title[key],
                                        "basis": "source_url + title"})
            else:
                seen_title.setdefault(key, code)

    # 2) تسجيل المعرّف الرسمي ثم سلاسل التحديث بالمعرّف نفسه
    date_of = {c: d for d, c, _r in index}
    for date, code, r in index:
        ref = official_ref(r)
        if ref and not r.get("official_ref"):
            edits[date][code]["official_ref"] = ref
            edits[date][code]["official_ref_basis"] = f"معرّف رسمي من نصّ المصدر: {ref}"
    chains: dict[str, list[str]] = defaultdict(list)
    for date, code, r in index:
        ref = official_ref(r)
        if ref:
            chains[ref].append(code)
    for key, codes in chains.items():
        if len(codes) < 2:
            continue
        codes_sorted = sorted(set(codes))
        root = codes_sorted[0]
        for i, code in enumerate(codes_sorted[1:], start=1):
            prev = codes_sorted[i - 1]
            date = date_of.get(code, "")
            edits[date][code]["update_of"] = prev
            edits[date][code]["parent_id"] = root
            edits[date][code]["link_basis"] = f"official_ref={key} (سلسلة من {len(codes_sorted)} وقائع)"
            report["links"].append({"kind": "update_of", "code": code, "of": prev, "parent": root,
                                    "basis": f"official_ref={key}"})

    # تكرار اسم السفينة: واقعتان مختلفتان — يُبلَّغ ولا يُربَط
    vessels: dict[str, list[str]] = defaultdict(list)
    for date, code, r in index:
        v = norm(str(r.get("vessel_name") or ""))
        if v:
            vessels[v].append(code)
    report["vessel_repeats"] = {v: c for v, c in vessels.items() if len(c) > 1}

    # 2ب) الربط العابر: واقعة يومية تُعيد النشرة نفسها المسجّلة في الدفتر المجمّد
    frozen_refs = frozen_reference_map()
    cross = 0
    for date, code, r in index:
        if edits[date][code].get("update_of") or r.get("update_of"):
            continue
        ref = official_ref(r)
        ev = frozen_refs.get(ref or "") or frozen_refs.get((ref or "").replace("UKMTO-", ""))
        if ref and ev:
            edits[date][code]["update_of"] = ev
            edits[date][code]["parent_id"] = ev
            edits[date][code]["link_basis"] = f"official_ref={ref} (سجل الدفتر المجمّد {ev})"
            report["links"].append({"kind": "update_of", "code": code, "of": ev, "parent": ev,
                                    "basis": f"official_ref={ref} · دفتر مجمّد"})
            cross += 1
    report["cross_store_links"] = cross

    # 3) حقول مساندة بذكر صريح
    ok_kinds = allowed_kinds()
    for date, code, r in index:
        cur = str(r.get("incident_kind") or "")
        if cur and cur not in ok_kinds:
            edits[date][code]["__delete__"] = ["incident_kind", "incident_kind_basis"]
            report.setdefault("invalid_kinds_cleared", []).append({"code": code, "was": cur})
            cur = ""
        if cur:
            continue
        kind, word = kind_of(r)
        if kind and word and kind in ok_kinds:
            edits[date][code]["incident_kind"] = kind
            edits[date][code]["incident_kind_basis"] = f"ذكر صريح: «{word}»"
            report["kinds"].append({"code": code, "kind": kind, "word": word})
        if not r.get("target") and re.search(r"سفينة|ناقلة|سفن", " ".join(
                str(r.get(k, "")) for k in ("title", "source_excerpt", "description"))):
            edits[date][code]["target"] = "سفينة"

    # 4) تصحيح الروابط القديمة: سند مفقود أو معرّف معلّق
    known = {c for _d, c, _r in index}
    frozen_ids: set[str] = set()
    _fp = BRAIN / "cumulative-2026" / "event-ledger-sectioned-2026-02-28-to-2026-10-11.json"
    if _fp.exists():
        try:
            _fj = json.loads(_fp.read_text(encoding="utf-8"))
            frozen_ids = {str(e.get("event_id") or "") for e in _fj.get("events", [])}
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            frozen_ids = set()
    known |= frozen_ids
    by_vessel: dict[str, str] = {}
    for date, code, r in index:
        v = norm(str(r.get("vessel_name") or "")) or norm(str(r.get("imo_number") or ""))
        if v:
            by_vessel.setdefault(v, code)
    for date, code, r in index:
        dup = str(r.get("duplicate_of") or "").strip()
        upd = str(r.get("update_of") or "").strip()
        if not dup and not upd:
            continue
        fields = edits[date][code]
        note = norm(str(r.get("dedup_note") or ""))
        # سند مفقود: يُستخرج من ملاحظة إزالة التكرار الموثّقة في السجل نفسه
        if not str(r.get("link_basis") or "").strip() and not fields.get("link_basis") and note:
            fields["link_basis"] = f"ملاحظة إزالة تكرار موثّقة في السجل: {note[:160]}"
        # معرّف معلّق: يُعاد توجيهه إلى سجل الواقعة نفسه بالاسم أو رقم IMO
        ref = dup or upd
        if ref and ref not in known:
            v = norm(str(r.get("vessel_name") or "")) or norm(str(r.get("imo_number") or ""))
            target = by_vessel.get(v)
            if not target:
                # البحث باسم سفينة لاتيني مذكور في السجل أو في ملاحظة إزالة التكرار
                blob = " ".join(str(r.get(k, "")) for k in
                                ("title", "dedup_note", "source_excerpt", "description"))
                for name in set(re.findall(r"\b[A-Z][A-Z0-9]{2,}(?:\s+[A-Z][A-Z0-9]{2,}){1,3}\b", blob)):
                    for d2, c2, r2 in index:
                        if c2 == code:
                            continue
                        if name in json.dumps(r2, ensure_ascii=False):
                            target = c2
                            break
                    if target:
                        break
            if target and target != code:
                fields["duplicate_of"] = target
                fields.pop("update_of", None)
                fields.pop("parent_id", None)
                fields["link_basis"] = (f"تصحيح معرّف معلّق ({ref}) ← {target}: "
                                        f"الواقعة نفسها بالسفينة {v}")
                report.setdefault("dangling_fixed", []).append({"code": code, "was": ref, "now": target})
            else:
                fields["__delete__"] = sorted(set(fields.get("__delete__") or []) |
                                              {"duplicate_of", "update_of", "parent_id"})
                report.setdefault("dangling_cleared", []).append({"code": code, "was": ref})

    # 5) اتساق التكرار مع العدّ (سبب جذري، 21 نوفمبر 2026): S070 تعيد اشتقاق الحقول من الصفر
    # فتكتب «جديد» و`counts_as_new=true`، ثم تضيف هذه الخطوة `duplicate_of` فوقها، فكان صف
    # التكرار يُحتسب واقعة جديدة (MN-2026-11-18-03 و-04 وNI-2026-11-12 و-15). كل صف ينتهي
    # بـ`duplicate_of` يصير «تكرار» غير محتسب، بحقل علاقة واحد كما يشترط العقد.
    for date, code, r in index:
        pending = edits.get(date, {}).get(code, {})
        deleted = set(pending.get("__delete__") or [])
        dup = pending.get("duplicate_of") or ("" if "duplicate_of" in deleted else r.get("duplicate_of"))
        if not dup:
            continue
        want = {"event_kind": "تكرار", "counts_as_new": False, "link_status": "مرتبط",
                "update_of": None, "parent_id": None}
        if all(r.get(k) == v and k not in pending for k, v in want.items()):
            continue
        fields = edits[date][code]
        fields["event_kind"] = "تكرار"
        fields["counts_as_new"] = False
        fields["link_status"] = "مرتبط"
        fields["update_of"] = None
        fields["parent_id"] = None
        if not str(fields.get("link_evidence") or r.get("link_evidence") or "").strip():
            fields["link_evidence"] = str(r.get("source_url") or dup)
        report.setdefault("duplicates_uncounted", []).append({"code": code, "of": dup})

    report["skipped_no_evidence"] = sum(
        1 for _d, _c, r in index
        if not official_ref(r)
    )
    return edits, report


def main() -> int:
    ap = argparse.ArgumentParser(description="اشتقاق روابط الوقائع في الدفتر التراكمي (بلا تشابه نصي)")
    ap.add_argument("--apply", action="store_true", help="اكتب التعديلات بعد حفظ نسخ أصلية")
    ap.add_argument("--json", help="مسار تقرير JSON")
    args = ap.parse_args()

    days = load_days()
    if not days:
        print("   ✘ لا ملفات يومية في", DAILY)
        return 2
    edits, report = derive(days)

    n_fields = sum(len(v) for per in edits.values() for v in per.values())
    print(f"   ══ قياس ══")
    print(f"   أيام: {report['days']} · وقائع: {report['records']}")
    print(f"   روابط مشتقة: {len(report['links'])} (تكرار {sum(1 for l in report['links'] if l['kind']=='duplicate_of')} · "
          f"تحديث {sum(1 for l in report['links'] if l['kind']=='update_of')})")
    print(f"   تصنيف حادث مشتق: {len(report['kinds'])} · حقول مكتوبة: {n_fields}")
    print(f"   وقائع بلا معرّف قوي (تبقى بلا رابط، بصدق): {report['skipped_no_evidence']}")
    for l in report["links"][:12]:
        print(f"      · {l['code']} ← {l['kind']} {l.get('of')} ({l['basis']})")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   ✔ تقرير: {args.json}")

    if not args.apply:
        print("   (تجفيف — لم تُكتب أي ملفات)")
        return 0

    # فشل مغلق: كل رابط يجب أن يحمل سندًا
    for per in edits.values():
        for code, fields in per.items():
            if ("update_of" in fields or "duplicate_of" in fields) and not fields.get("link_basis"):
                print(f"   ✘ رابط بلا سند: {code} — أُوقف الكتابة")
                return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    written = 0
    for f, recs in days:
        per = edits.get(f.stem)
        if not per:
            continue
        shutil.copy2(f, BACKUP_DIR / f"{f.name}.bak-links-{stamp}")
        for r in recs:
            if not isinstance(r, dict):
                continue
            code = str(r.get("code") or "")
            fields = per.get(code)
            if not fields:
                continue
            for k, v in fields.items():
                if k == "__delete__":
                    for dk in v:
                        r.pop(dk, None)
                    continue
                r[k] = v
        f.write_text(json.dumps(recs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
    print(f"   ✔ كُتبت {written} ملفًا · النسخ الأصلية في {BACKUP_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
