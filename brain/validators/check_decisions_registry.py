#!/usr/bin/env python3
"""حارس دفتر القرارات — يمنع أن يُكتب «منفَّذ» بلا دليل، وأن يضيع قرار.

يفشل مغلقًا (رمز 2) إذا:
  1) غاب `decisions/registry.json` أو تعذّرت قراءته.
  2) نقص عدد القرارات عن الحد المعلن في العقد نفسه.
  3) تكرّر معرّف قرار، أو نقص قرار من السلسلة D-01…D-16.
  4) كانت حالة قرار خارج القيم الأربع المعلنة.
  5) كانت حالة قرار «منفَّذ» أو «منفَّذ جزئيًّا» بلا دليل، أو بلا ملف حاكم.
  6) أشار دليل من نوع «file» إلى ملف غير موجود.
  7) كان قرار غير منفَّذ بلا خطوة تالية معلنة.

الاستعمال: python3 validators/check_decisions_registry.py [--root .] [--summary]
رمز الخروج: 0 سليم · 2 خلل.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

OK_LINE = "✔ دفتر القرارات: 16 قرارًا بحالة ودليل · صفر «منفَّذ» بلا سند"
REQUIRED_IDS = [f"D-{n:02d}" for n in range(1, 17)]
DONE = {"منفَّذ", "منفَّذ جزئيًّا"}


def check(root: Path) -> list[str]:
    errs: list[str] = []
    path = root / "decisions" / "registry.json"
    if not path.is_file():
        return [f"دفتر القرارات غير موجود: {path}"]
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"دفتر القرارات غير قابل للقراءة: {exc}"]

    allowed = set(reg.get("status_values_ar") or [])
    if allowed != {"منفَّذ", "منفَّذ جزئيًّا", "يحتاج تحققًا", "يحتاج قرارًا"}:
        errs.append(f"قيم الحالة المعلنة غير مطابقة: {sorted(allowed)}")

    items = reg.get("decisions") or []
    if len(items) < len(REQUIRED_IDS):
        errs.append(f"عدد القرارات {len(items)} أقل من {len(REQUIRED_IDS)}")

    ids = [str(d.get("id")) for d in items]
    for d in set(ids):
        if ids.count(d) > 1:
            errs.append(f"معرّف قرار مكرر: {d}")
    for missing in [i for i in REQUIRED_IDS if i not in ids]:
        errs.append(f"قرار غائب من الدفتر: {missing}")

    counts: dict[str, int] = {}
    for d in items:
        did = d.get("id")
        st = d.get("status")
        counts[st] = counts.get(st, 0) + 1
        if st not in allowed:
            errs.append(f"{did}: حالة غير معلنة {st!r}")
            continue
        if not str(d.get("title_ar", "")).strip():
            errs.append(f"{did}: بلا عنوان")
        if st in DONE:
            ev = d.get("evidence") or []
            # EVIDENCE_SHAPE_V1: دليل بشكل غير قائمة عناصر kind/ref يُمنع ولا يُسقط الحارس
            if not isinstance(ev, list) or any(not isinstance(x, dict) for x in ev):
                errs.append(f"{did}: صيغة الدليل يجب أن تكون قائمة عناصر kind/ref")
                continue
            if not ev:
                errs.append(f"{did}: حالة «{st}» بلا دليل")
            if not str(d.get("governing_file", "")).strip():
                errs.append(f"{did}: حالة «{st}» بلا ملف حاكم")
            for e in ev:
                if not e.get("kind") or not e.get("ref"):
                    errs.append(f"{did}: دليل ناقص (kind/ref)")
                    continue
                if e.get("kind") == "file" and not (root / str(e["ref"])).exists():
                    errs.append(f"{did}: دليل ملف غير موجود: {e['ref']}")
        else:
            if not str(d.get("next_action_ar", "")).strip():
                errs.append(f"{did}: قرار غير منفَّذ بلا خطوة تالية")

    declared = reg.get("counts") or {}
    for k, v in declared.items():
        actual = counts.get(k, 0)
        if actual != v:
            errs.append(f"عدّاد «{k}» معلن {v} والواقع {actual}")

    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس دفتر القرارات")
    ap.add_argument("--root", default=".", help="جذر المشروع")
    ap.add_argument("--summary", action="store_true", help="طباعة سطر واحد فقط")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    errs = check(root)
    if errs:
        print("✘ دفتر القرارات: خلل يمنع الاعتماد")
        for e in errs:
            print(f"   - {e}")
        return 2

    if args.summary:
        print(OK_LINE)
        return 0

    reg = json.loads((root / "decisions" / "registry.json").read_text(encoding="utf-8"))
    print(OK_LINE)
    print(f"   القياس الأخير: {reg.get('last_measured')} · القرارات: {len(reg['decisions'])}")
    print("   التوزيع: " + " · ".join(f"{k} {v}" for k, v in reg.get("counts", {}).items()))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
