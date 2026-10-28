#!/usr/bin/env python3
"""اتساق سجل الأقسام (runbook/runbook.json) مع نص التقرير وسياسة الأقسام — بديل اختبارات tests/sections/test_*.sh
(كانت تتحقق بـ grep عن جملة ثابتة ومن مسار /home/ubuntu).

يفحص لتاريخ D (الافتراضي: أحدث reports/*-sectioned.md):
  1) كل قسم له `heading` في السجل يظهر في النص عنوانًا `## ...` (أو أحد أسمائه البديلة `aliases`).
  2) كل عنوان `##` في النص مسجَّل في السجل — لا قسم خارج السجل.
  3) كل قسم في `required_in_md` من سياسة الأقسام له قسم في السجل.
  4) كل عنوان في hidden_sections/internal_only معروف للسجل أو بديل له.
الاستعمال: python3 tests/test_sections_registry_vs_report.py [YYYY-MM-DD] [--selftest]    رمز 0 سليم · 2 خلل
"""
import json
import os
import re
import sys
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)


def names(sec):
    return [n for n in [sec.get("heading")] + list(sec.get("aliases", [])) if n]


def check(manifest, policy, md_text):
    errs = []
    secs = manifest["sections"]
    known = {n for s in secs for n in names(s)}
    retired = set(manifest.get("retired_headings", []))  # عناوين قديمة ما زالت في السياسة فقط
    heads = re.findall(r"^##\s+(.+?)\s*$", md_text, flags=re.M)
    for s in secs:
        if s.get("heading") and not any(n in heads for n in names(s)):
            errs.append(f"قسم السجل «{s['id']}» (العنوان «{s['heading']}») غائب عن نص التقرير")
    for h in heads:
        if h not in known:
            errs.append(f"عنوان في التقرير غير مسجَّل في السجل: «{h}»")
    for req in policy.get("required_in_md", []):
        if not any(n.startswith(req) or req in n for n in known):
            errs.append(f"قسم مطلوب في السياسة بلا قسم في السجل: «{req}»")
    for key in ("hidden_sections", "internal_only"):
        for h in policy.get(key, []):
            if h not in known and h not in retired and not any(h in n or n in h for n in known):
                errs.append(f"{key}: «{h}» لا يطابق أي قسم أو اسم بديل في السجل")
    return errs


def selftest():
    man = {"sections": [{"id": "a", "heading": "الخلاصة"}, {"id": "b", "heading": "الخلفية", "aliases": ["الخلفية العامة"]}]}
    pol = {"required_in_md": ["الخلاصة"], "hidden_sections": ["الخلفية العامة"], "internal_only": []}
    good = "## الخلاصة\nx\n## الخلفية العامة\ny\n"
    cases = [("سليم", check(man, pol, good) == []),
             ("قسم غائب يُكشف", bool(check(man, pol, "## الخلاصة\n"))),
             ("قسم خارج السجل يُكشف", bool(check(man, pol, good + "## جديد\n"))),
             ("سياسة بلا قسم تُكشف", bool(check(man, dict(pol, required_in_md=["غير موجود"]), good)))]
    bad = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(("  ✔ " if ok else "  ✘ ") + n)
    return 0 if not bad else 2


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--selftest" in sys.argv:
        return selftest()
    manifest = json.loads((B / "runbook" / "runbook.json").read_text(encoding="utf-8"))
    policy = json.loads((B / "appendices" / "report-sections-policy.json").read_text(encoding="utf-8"))
    if args:
        md = B / "reports" / f"{args[0]}-sectioned.md"
    else:
        found = sorted((B / "reports").glob("*-sectioned.md"))
        if not found:
            print("✘ لا تقرير للفحص")
            return 2
        md = found[-1]
    if not md.is_file():
        print(f"✘ غير موجود: {md}")
        return 2
    errs = check(manifest, policy, md.read_text(encoding="utf-8"))
    for e in errs:
        print("✘", e)
    if not errs:
        print(f"✔ السجل متسق مع {md.name} ({len(manifest['sections'])} قسمًا)")
    return 2 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
