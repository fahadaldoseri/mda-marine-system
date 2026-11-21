#!/usr/bin/env python3
"""رقم الحادث ورقم البلاغ — طبقة هوية فوق رمز الواقعة الثابت (قرار فهد 21 نوفمبر 2026).

المشكلة: رمز الواقعة `MN-YYYY-MM-DD-NN` يُعطى لكل بلاغ أو خبر، فالحادث الواحد الذي
تنقله عدة مصادر أو تُحدِّثه الجهة نفسها بعد أيام يأخذ عدة رموز بلا رقم يجمعها.

الصيغة المعتمدة (الصيغة أ):
  · رقم الحادث  `YY-NNNN`   آخر رقمين من السنة ثم تسلسل سنوي، والسنة سنة أول بلاغ (مثال 26-0417).
  · رقم البلاغ  `YY-NNNN/k` البلاغ رقم k عن الحادث نفسه، بترتيب ورود البلاغات (مثال 26-0417/1).
  الصيغة المختصرة باقتراح فهد 21 نوفمبر 2026 (بدل H-YYYY-NNNN).

القواعد:
  1. رمز الواقعة القديم لا يُمس ولا يتغير معناه (القاعدة 3 في CLAUDE.md)؛ الرقم الجديد
     يُحفظ في سجل مستقل `appendices/incident-id-map.json` يربط كل رمز قديم برقمه.
  2. البلاغ يدخل تحت حادث سابق فقط عبر علاقة مثبتة بالدليل في الدفتر:
     `update_of` أو `parent_id` أو `duplicate_of` (عقد `appendices/event-link-contract.md`).
     لا تجميع بالتشابه هنا.
  3. السجل تراكمي لا يُعاد ترقيمه: الرقم الذي صدر لا يتغير. إذا ظهر لاحقًا رابط يخالف
     رقمًا صادرًا يُبلَّغ عنه تحذيرًا (رمز 3) ولا يُعدَّل بصمت.
  4. سجلات «لا واقعة» (`NI-` أو `no_incident`) لا تأخذ رقم حادث.

الاستعمال:
  python3 tools/assign_incident_ids.py --apply   يعيّن الأرقام للرموز الجديدة ثم يفحص
  python3 tools/assign_incident_ids.py --check   يفحص فقط

رمز الخروج: 0 سليم · 3 سليم مع تحذير · 2 مخالفة مانعة.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])
REGISTRY_REL = Path("appendices") / "incident-id-map.json"
DAILY_REL = Path("cumulative-2026") / "daily"
LINK_FIELDS = ("update_of", "parent_id", "duplicate_of")
INCIDENT_RE = re.compile(r"^(\d{2})-(\d{4})$")
REPORT_RE = re.compile(r"^(\d{2}-\d{4})/([1-9]\d*)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# أول تقرير يعرض الرقم في بطاقة الواقعة؛ الصفحات الأقدم المنشورة لا تتغير.
DISPLAY_FROM = "2026-11-21"

FORMAT_NOTE = (
    "رقم الحادث YY-NNNN (آخر رقمين من السنة ثم تسلسل سنوي) بسنة أول بلاغ؛ ورقم البلاغ YY-NNNN/k بترتيب ورود "
    "البلاغات عن الحادث نفسه. يُربط البلاغ بحادث سابق فقط بعلاقة مثبتة في الدفتر "
    "(update_of أو parent_id أو duplicate_of). الأرقام الصادرة لا يُعاد ترقيمها. قرار فهد 21 نوفمبر 2026."
)


class IncidentIdError(ValueError):
    """مخالفة مانعة في الدفتر أو السجل."""


def is_no_incident(row: dict[str, Any]) -> bool:
    code = str(row.get("code") or "")
    return (
        row.get("no_incident") is True
        or row.get("class") == "no_incident"
        or row.get("event_kind") == "no_incident"
        or code.startswith("NI-")
    )


def load_rows(daily_dir: Path) -> list[dict[str, Any]]:
    """صفوف الدفتر مرتبة كما في عقد الربط: التاريخ ثم اسم ملف اليوم ثم ترتيب الصف."""
    ordered: list[tuple[str, str, int, dict[str, Any]]] = []
    seen: set[str] = set()
    for path in sorted(daily_dir.glob("*.json")):
        if not DATE_RE.match(path.stem):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IncidentIdError(f"تعذرت قراءة {path.name}: {exc}") from exc
        rows = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise IncidentIdError(f"جذر {path.name} ليس قائمة سجلات")
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                raise IncidentIdError(f"{path.name}: السجل {idx} ليس كائنًا")
            code = row.get("code")
            if not isinstance(code, str) or not code.strip():
                raise IncidentIdError(f"{path.name}: السجل {idx} بلا code")
            if code in seen:
                raise IncidentIdError(f"رمز مكرر في الدفتر: {code}")
            seen.add(code)
            date = str(row.get("date") or path.stem)[:10]
            ordered.append((date, path.name, idx, row))
    ordered.sort(key=lambda t: (t[0], t[1], t[2]))
    return [dict(t[3], _date=t[0]) for t in ordered]


def link_target(row: dict[str, Any]) -> str | None:
    targets = [row[f] for f in LINK_FIELDS if isinstance(row.get(f), str) and row[f].strip()]
    if not targets:
        return None
    # عقد الربط يمنع أكثر من حقل؛ وإن امتلأ أكثر من حقل بالهدف نفسه فلا لبس.
    if len(set(targets)) > 1:
        raise IncidentIdError(f"{row['code']}: حقول علاقة متعارضة {sorted(set(targets))}")
    return targets[0]


def root_of(code: str, by_code: dict[str, dict[str, Any]]) -> str:
    seen: set[str] = set()
    current = code
    while True:
        if current in seen:
            raise IncidentIdError(f"دورة في حقول العلاقة عند {code}")
        seen.add(current)
        target = link_target(by_code[current])
        if not target or target not in by_code or is_no_incident(by_code[target]):
            return current
        current = target


def empty_registry() -> dict[str, Any]:
    return {"version": 1, "format_ar": FORMAT_NOTE, "display_from": DISPLAY_FROM, "codes": {}}


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_registry()
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IncidentIdError(f"تعذرت قراءة السجل {path}: {exc}") from exc
    if not isinstance(reg, dict) or not isinstance(reg.get("codes"), dict):
        raise IncidentIdError("السجل يجب أن يكون كائنًا فيه codes")
    return reg


def _incident_serials(codes: dict[str, Any]) -> dict[str, int]:
    top: dict[str, int] = {}
    for entry in codes.values():
        m = INCIDENT_RE.match(str(entry.get("incident_id", "")))
        if m:
            top[m.group(1)] = max(top.get(m.group(1), 0), int(m.group(2)))
    return top


def assign(rows: list[dict[str, Any]], registry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """يعيّن أرقامًا للرموز التي لا رقم لها فقط؛ يعيد السجل الجديد وقائمة المضاف."""
    codes: dict[str, Any] = {k: dict(v) for k, v in registry["codes"].items()}
    by_code = {r["code"]: r for r in rows}
    serials = _incident_serials(codes)
    suffixes: dict[str, int] = {}
    for entry in codes.values():
        m = REPORT_RE.match(str(entry.get("report_id", "")))
        if m:
            suffixes[m.group(1)] = max(suffixes.get(m.group(1), 0), int(m.group(2)))
    added: list[str] = []
    for row in rows:
        code = row["code"]
        if is_no_incident(row) or code in codes:
            continue
        root = root_of(code, by_code)
        if root != code and root in codes:
            incident = codes[root]["incident_id"]
        else:
            year = row["_date"][2:4]
            serials[year] = serials.get(year, 0) + 1
            if serials[year] > 9999:
                raise IncidentIdError(f"تجاوز التسلسل السنوي 9999 في {year}")
            incident = f"{year}-{serials[year]:04d}"
        suffixes[incident] = suffixes.get(incident, 0) + 1
        codes[code] = {"incident_id": incident, "report_id": f"{incident}/{suffixes[incident]}"}
        added.append(code)
    out = dict(registry)
    out["format_ar"] = FORMAT_NOTE
    out.setdefault("display_from", DISPLAY_FROM)
    out["codes"] = {k: codes[k] for k in sorted(codes)}
    return out, added


def check(rows: list[dict[str, Any]], registry: dict[str, Any]) -> tuple[list[str], list[str]]:
    """يعيد (مخالفات مانعة، تحذيرات)."""
    errors: list[str] = []
    warnings: list[str] = []
    codes = registry.get("codes", {})
    by_code = {r["code"]: r for r in rows}
    material = [r for r in rows if not is_no_incident(r)]
    report_ids: dict[str, str] = {}
    if not DATE_RE.match(str(registry.get("display_from") or "")):
        errors.append("display_from مفقود أو بصيغة غير تاريخ")
    for code, entry in codes.items():
        inc = str(entry.get("incident_id", ""))
        rep = str(entry.get("report_id", ""))
        if not INCIDENT_RE.match(inc):
            errors.append(f"{code}: رقم حادث بصيغة غير معتمدة «{inc}»")
            continue
        m = REPORT_RE.match(rep)
        if not m or m.group(1) != inc:
            errors.append(f"{code}: رقم البلاغ «{rep}» لا يتبع رقم الحادث «{inc}»")
        if rep in report_ids:
            errors.append(f"رقم بلاغ مكرر {rep}: {report_ids[rep]} و{code}")
        report_ids[rep] = code
        if code not in by_code:
            errors.append(f"{code}: في السجل ولا يوجد في الدفتر (لا يُحذف رمز صدر له رقم)")
        elif is_no_incident(by_code[code]):
            errors.append(f"{code}: سجل «لا واقعة» لا يأخذ رقم حادث")
    for row in material:
        code = row["code"]
        if code not in codes:
            errors.append(f"{code}: واقعة بلا رقم حادث (شغّل --apply)")
            continue
        try:
            root = root_of(code, by_code)
        except IncidentIdError as exc:
            errors.append(str(exc))
            continue
        if root != code and root in codes and codes[root]["incident_id"] != codes[code]["incident_id"]:
            warnings.append(
                f"{code}: مرتبط بالدليل بـ{root} ({codes[root]['incident_id']}) لكن رقمه الصادر "
                f"{codes[code]['incident_id']}؛ لا يُعاد ترقيم رقم صادر، والقرار لصاحب المشروع"
            )
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="رقم الحادث ورقم البلاغ")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true", help="عيّن أرقامًا للرموز الجديدة ثم افحص")
    mode.add_argument("--check", action="store_true", help="افحص فقط")
    parser.add_argument("--root", type=Path, default=BRAIN)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    reg_path = root / REGISTRY_REL
    try:
        rows = load_rows(root / DAILY_REL)
        registry = load_registry(reg_path)
        if args.apply:
            registry, added = assign(rows, registry)
            if added:
                reg_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = reg_path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(registry, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                tmp.replace(reg_path)
            print(f"أُضيف رقم لـ {len(added)} رمزًا")
        errors, warnings = check(rows, registry)
    except IncidentIdError as exc:
        print(f"فشل مغلق: {exc}", file=sys.stderr)
        return 2
    incidents = {e["incident_id"] for e in registry["codes"].values()}
    print(f"البلاغات المرقّمة: {len(registry['codes'])} · الحوادث: {len(incidents)}")
    for w in warnings:
        print(f"تحذير: {w}")
    for e in errors:
        print(f"مخالفة: {e}", file=sys.stderr)
    if errors:
        return 2
    return 3 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
