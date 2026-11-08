#!/usr/bin/env python3
"""حارس سياسة التسليم المتصل — قرار المالك «أ» (دائم، لكل المراحل والدفعات والجولات).

يفشل مغلقًا (رمز 2) إذا:
  1) غاب عقد السياسة أو تعذّر قراءته.
  2) لم يكن الوضع «A» أو لم تكن السياسة دائمة وشاملة.
  3) نقص عنصر من سلسلة التسليم الثمانية أو اختل ترتيبها.
  4) نقص حارس من الحراس الستة الممنوعة.
  5) غابت خطوات التسليم الفعلية عن المانيفست (فالسياسة بلا خطواتٍ وعدٌ لا يُنفَّذ).

الاستعمال:
  python3 validators/check_delivery_policy.py [--root .] [--summary]

رمز الخروج: 0 سليم · 2 خلل.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

OK_LINE = "✔ سياسة التسليم المتصل: الوضع أ · سلسلة ثمانية عناصر · ستة حراس · خطوات المانيفست حاضرة"

REQUIRED_SEQUENCE = ["branch", "pr", "merge", "push", "publish", "live_verify", "telegram", "report"]
REQUIRED_FORBIDDEN = [
    "force_push",
    "direct_push_main",
    "merge_without_step",
    "publish_without_step",
    "telegram_outside_step",
    "silent_close",
]
# القائمة مرجعها المانيفست نفسه؛ هذا السطر للتوافق الخلفي فقط
REQUIRED_MANIFEST_STEPS = ["D005", "D010", "D030", "D033", "D035", "D040", "D070", "D071"]


def manifest_deliver_steps(manifest: dict) -> list[str]:
    """خطوات التسليم الفعلية = كل خطوة في طور deliver بالمانيفست (لا قائمة ثابتة)."""
    return sorted(s["id"] for s in manifest.get("steps", []) if str(s.get("phase")) == "deliver")

def check(root: Path) -> list[str]:
    errs: list[str] = []
    policy_path = root / "runbook" / "delivery-policy.json"
    manifest_path = root / "runbook" / "runbook.json"

    if not policy_path.is_file():
        return [f"عقد السياسة غير موجود: {policy_path}"]
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"عقد السياسة غير قابل للقراءة: {exc}"]

    if str(policy.get("mode", "")).strip().upper() != "A":
        errs.append(f"الوضع ليس «أ»: {policy.get('mode')!r}")

    decision = policy.get("decision") or {}
    if decision.get("permanent") is not True:
        errs.append("السياسة غير موسومة بأنها دائمة (permanent != true)")
    if str(decision.get("scope", "")).strip() != "all":
        errs.append(f"نطاق السياسة ليس شاملًا: {decision.get('scope')!r}")
    if not decision.get("decided_by"):
        errs.append("مصدر القرار غير مذكور (decided_by)")

    seq = policy.get("sequence") or []
    missing = [s for s in REQUIRED_SEQUENCE if s not in seq]
    if missing:
        errs.append("عناصر ناقصة في سلسلة التسليم: " + " · ".join(missing))
    else:
        order = [seq.index(s) for s in REQUIRED_SEQUENCE]
        if order != sorted(order):
            errs.append("ترتيب سلسلة التسليم غير صحيح")
    if len(seq) != len(REQUIRED_SEQUENCE):
        errs.append(f"عدد عناصر السلسلة {len(seq)} والمتوقع {len(REQUIRED_SEQUENCE)}")

    forbidden = policy.get("forbidden") or []
    lost = [g for g in REQUIRED_FORBIDDEN if g not in forbidden]
    if lost:
        errs.append("حراس ممنوعة ساقطة: " + " · ".join(lost))

    if not policy.get("report_fields_ar"):
        errs.append("حقول تقرير التسليم غير معرَّفة")

    if not manifest_path.is_file():
        errs.append(f"المانيفست غير موجود: {manifest_path}")
        return errs
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errs.append(f"المانيفست غير قابل للقراءة: {exc}")
        return errs

    ids = {str(s.get("id")) for s in manifest.get("steps", [])}
    absent = [sid for sid in REQUIRED_MANIFEST_STEPS if sid not in ids]
    if absent:
        errs.append("خطوات تسليم غائبة عن المانيفست: " + " · ".join(absent))

    declared = policy.get("manifest_delivery_steps") or []
    drift = sorted(set(declared) - ids)
    if drift:
        errs.append("السياسة تعلن خطوات غير موجودة في المانيفست: " + " · ".join(drift))

    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="حارس سياسة التسليم المتصل (الوضع أ)")
    ap.add_argument("--root", default=".", help="جذر المشروع")
    ap.add_argument("--summary", action="store_true", help="طباعة ملخص قصير فقط")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    errs = check(root)

    if errs:
        print("✘ سياسة التسليم المتصل: خلل يمنع التسليم")
        for e in errs:
            print(f"   - {e}")
        return 2

    if args.summary:
        print(OK_LINE)
        return 0

    policy = json.loads((root / "runbook" / "delivery-policy.json").read_text(encoding="utf-8"))
    print(OK_LINE)
    print(f"   النطاق: {policy['decision'].get('scope')} · دائمة: {policy['decision'].get('permanent')} · القرار: {policy['decision'].get('decided_at')}")
    print("   السلسلة: " + " ← ".join(policy["sequence"]))
    print("   الممنوعات: " + " · ".join(policy["forbidden"]))
    print("   خطوات المانيفست: " + " · ".join(policy["manifest_delivery_steps"]))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
