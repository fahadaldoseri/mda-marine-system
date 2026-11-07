#!/usr/bin/env python3
"""اختبار مقترن لتصنيف المسارات: كل حالة تحمل صنفًا متوقعًا، وأي اختلاف يفشل مغلقًا.

الغاية: إثبات أن قائمة التجاهُل تلتقط المولَّد فعلًا، ولا تتسرّب إلى شيفرة أو بيانات حقيقية.

الاستعمال:
  check_classification_matrix.py --matrix matrix.json [--brain DIR]

مصفوفة مثال:
{
  "spec": "/home/ubuntu/brain-marine-news/appendices/code-paths.json",
  "cases": [
    {"path": "brain/tools/__pycache__/x.cpython-312.pyc", "expect": "generated", "why": "مولَّد"},
    {"path": "brain/validators/check_style.py",          "expect": "code",      "why": "شيفرة"},
    {"path": "brain/web/meta/2026-11-04.json",           "expect": "data",      "why": "بيانات"}
  ]
}

رموز الخروج: 0 مطابق · 2 اختلاف حالة · 70 تعذّر القياس (فشل مغلق).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_generated_boundary import load_classifier  # noqa: E402

ALLOWED = {"code", "data", "generated", "none"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--brain", default=None, help="جذر الدماغ لاستعمال مكتبة المشروع")
    a = ap.parse_args()

    mpath = Path(a.matrix)
    if not mpath.is_file():
        print(f"✘ تعذّر القياس (فشل مغلق 70): لا مصفوفة في {mpath}")
        return 70
    m = json.loads(mpath.read_text(encoding="utf-8"))
    spec_path = Path(m.get("spec") or "")
    if not spec_path.is_file():
        print(f"✘ تعذّر القياس (فشل مغلق 70): لا مواصفة في {spec_path}")
        return 70
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    brain = Path(a.brain).resolve() if a.brain else spec_path.parent.parent
    classify, _ignored, engine = load_classifier(brain)
    print(f"   المواصفة: {spec_path}")
    print(f"   محرّك التصنيف: {engine}")

    failures = []
    for case in m.get("cases", []):
        rel = case["path"]
        expect = case["expect"]
        if expect not in ALLOWED:
            failures.append(f"{rel}: صنف متوقع غير معروف «{expect}»")
            continue
        got = classify(rel, spec) or "none"
        mark = "✔" if got == expect else "✘"
        print(f"   {mark} {rel} ⇒ {got} (المتوقع {expect})")
        if got != expect:
            failures.append(f"{rel}: {got} ≠ {expect} — {case.get('why', '')}")

    if failures:
        print(f"✘ فشلت المصفوفة: {len(failures)} حالة")
        for f in failures:
            print(f"   · {f}")
        return 2
    print(f"✔ اجتازت المصفوفة: {len(m.get('cases', []))} حالة بلا اختلاف")
    return 0


if __name__ == "__main__":
    sys.exit(main())