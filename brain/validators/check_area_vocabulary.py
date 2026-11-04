#!/usr/bin/env python3
"""حارس مفردات حقل «الموقع» — يفشل مغلقًا على أي قيمة خارج سجل المناطق.

المصدر الحاكم: appendices/zone-registry.json (areas · area_value_format · area_rules).
القيم المسموحة: أسماء المناطق المسجَّلة · «غير مكانية» · «المنطقة كاملة» · «سياق إقليمي»
· صيغة «الموقع الدقيق - المنطقة البحرية» · وسرد عدة مناطق مفصولة بـ«·».
ويمنع أن يحمل صف «لا واقعة مسجّلة» قيمة موقع.

الخروج: 0 مطابق · 2 مخالف (يمنع التسليم).
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "appendices" / "zone-registry.json"
LEDGER = ROOT / "cumulative-2026" / "daily"
META = ROOT / "web" / "meta"

SCOPE = ("المنطقة كاملة", "سياق إقليمي")


def load_allowed() -> tuple[set[str], str]:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    names = {a["ar"] for a in reg.get("areas", [])}
    return names, reg.get("non_spatial_value", "غير مكانية")


def parts_ok(raw: str, names: set[str], non_spatial: str) -> tuple[bool, str]:
    raw = raw.strip()
    if not raw:
        return False, "قيمة فارغة"
    for part in [p.strip() for p in raw.split("·") if p.strip()]:
        if part in names or part == non_spatial or part in SCOPE:
            continue
        if " - " in part:
            left, _, right = part.rpartition(" - ")
            if left.strip() and right.strip() in names:
                continue
            return False, f"صيغة غير مطابقة: «{part}»"
        return False, f"قيمة خارج السجل: «{part}»"
    return True, ""


def is_no_incident(row: dict) -> bool:
    code = str(row.get("code") or "")
    title = str(row.get("title") or "")
    desc = str(row.get("source_description") or "")
    if code.startswith("NI-") or "لا واقعة" in title or "لا واقعة" in desc:
        return True
    if code.startswith("COVER-") and not str(row.get("area") or "").strip():
        return True
    return False


def walk_rows(obj, out: list[dict]) -> None:
    if isinstance(obj, dict):
        if "area" in obj or "code" in obj:
            out.append(obj)
        for v in obj.values():
            walk_rows(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_rows(v, out)


def main() -> int:
    names, non_spatial = load_allowed()
    bad: list[str] = []
    checked = 0

    for f in sorted(LEDGER.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        rows: list[dict] = []
        walk_rows(data, rows)
        for row in rows:
            if not str(row.get("code") or ""):
                continue
            if is_no_incident(row):
                if str(row.get("area") or "").strip():
                    bad.append(f"{f.name} · {row.get('code')} · صف «لا واقعة» يحمل قيمة موقع «{row['area']}»")
                continue
            checked += 1
            if "area" not in row:
                bad.append(f"{f.name} · {row.get('code')} · بلا قيمة موقع")
                continue
            ok, why = parts_ok(str(row["area"]), names, non_spatial)
            if not ok:
                bad.append(f"{f.name} · {row.get('code')} · {why}")

    for f in sorted(META.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for ev in (data.get("event_keys") or []):
            if not isinstance(ev, dict):
                continue
            checked += 1
            if "area" not in ev:
                bad.append(f"meta/{f.name} · {ev.get('code')} · بلا قيمة موقع")
                continue
            ok, why = parts_ok(str(ev["area"]), names, non_spatial)
            if not ok:
                bad.append(f"meta/{f.name} · {ev.get('code')} · {why}")

    print(f"   حارس مفردات الموقع — المناطق المسجَّلة: {len(names)} · صفوف مفحوصة: {checked}")
    if bad:
        print(f"   ✘ مخالفات: {len(bad)}")
        for b in bad[:25]:
            print(f"      {b}")
        return 2
    print("   ✔ كل قيم الموقع داخل السجل الحاكم وبالصيغة المعتمدة")
    return 0


if __name__ == "__main__":
    # ك-133: كل مدقق يمرّ عبر الحارس الموحّد — الانهيار يخرج بالرمز 70 ويمنع التسليم.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
