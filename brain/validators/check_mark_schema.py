#!/usr/bin/env python3
"""بوابة مخطط العلامة اليومية — شكل ثابت مُتحقَّق (ع-1 · قرار 2026-10-23).

العلامة كانت تتغيّر من يوم لآخر، فلا يمكن بناء أي قياس عليها. هنا يُتحقق أن كل حقل
معتمد في templates/mark-schema.json موجود بنوعه الصحيح، وأن أرقام المصادر الثلاثة صحيحة
ومتطابقة مع بيانات التشغيل.

الاستخدام: python3 validators/check_mark_schema.py --date 2026-10-23
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((B / "templates" / "mark-schema.json").read_text(encoding="utf-8"))


def _type_ok(value, spec: str) -> bool:
    if spec == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if spec == "str":
        return isinstance(value, str)
    if spec == "bool":
        return isinstance(value, bool)
    if spec == "obj":
        return isinstance(value, dict)
    if spec.startswith("enum:"):
        return value in spec.split(":", 1)[1].split("|")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    p = B / "logs" / f"pipeline-{a.date}.json"
    if not p.exists():
        print(f"  ✘ لا علامة: {p}")
        return 2
    mark = json.loads(p.read_text(encoding="utf-8"))
    bad: list[str] = []
    gate_json = B / "logs" / f"gate-{a.date}" / "gate.json"
    pre_gate = (mark.get("gate_state") == "not_run" and not gate_json.exists()
                and mark.get("written_stage") != "final")

    for k, spec in SCHEMA["required"].items():
        if k == "final_gate" and pre_gate and k not in mark:
            continue  # مرحلة الخط اليومي: البوابة لم تُشغَّل بعد، والحقل المعلن هو gate_state
        if k not in mark:
            bad.append(f"حقل مفقود: {k}")
        elif not _type_ok(mark[k], spec):
            bad.append(f"نوع خاطئ: {k} = {mark[k]!r} (المطلوب {spec})")
    for k, spec in SCHEMA["required_in_sources"].items():
        v = (mark.get("sources") or {}).get(k)
        if not _type_ok(v, spec):
            bad.append(f"sources.{k} = {v!r} (المطلوب {spec})")
    if "final_gate" in mark:
        for k, spec in SCHEMA["required_in_final_gate"].items():
            v = (mark.get("final_gate") or {}).get(k)
            if not _type_ok(v, spec):
                bad.append(f"final_gate.{k} = {v!r} (المطلوب {spec})")
    elif mark.get("written_stage") == "final" or gate_json.exists():
        bad.append("final_gate مفقود مع أن العلامة نهائية أو بوابة التسليم شُغِّلت")
    else:
        print("  · العلامة في مرحلة الخط اليومي: بوابة التسليم لم تُشغَّل بعد، فلا يُشترط final_gate")

    # تطابق أرقام المصادر مع بيانات التشغيل (لا ادعاء أكبر مما حدث)
    sys.path.insert(0, str(B / "tools"))
    from source_counts import counts
    c = counts(a.date)
    for k in ("approved", "checked", "ok"):
        if (mark.get("sources") or {}).get(k) != c[k]:
            bad.append(f"sources.{k} = {(mark.get('sources') or {}).get(k)} والواقع {c[k]}")

    if bad:
        for x in bad:
            print(f"  ✘ {x}")
        print(f"النتيجة: مخطط العلامة مخالف ({len(bad)}) — مانع")
        return 2
    gate_txt = (mark.get("final_gate") or {}).get("status") or mark.get("gate_state") or "لم تُشغَّل بعد"
    print(f"  ✓ مخطط العلامة v{mark['schema_version']} مطابق · المصادر {c['approved']}/{c['checked']}/{c['ok']} · "
          f"البوابة {gate_txt}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _guard import run
    run(main)