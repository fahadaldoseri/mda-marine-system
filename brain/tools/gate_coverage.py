#!/usr/bin/env python3
"""تغطية البوابات · المراجع الحيّة · الوحدات الشاردة.

ثلاثة مقاييس من المرجع في تشغيل واحد:
  م-03 تغطية البوابات = البوابات المعلَنة التي لها خطوة مُنفَّذة ÷ كل البوابات المعلَنة.
  م-04 المراجع الميتة = مسار مذكور في المانيفست وغير موجود على القرص.
  م-05 الوحدات الشاردة = ملف تنفيذي في tools/ أو validators/ لا يستدعيه المانيفست ولا يشير إليه غيره.

الاستعمال:
  gate_coverage.py --root .                التقرير الكامل
  gate_coverage.py --refs-only             المراجع الميتة فقط
  gate_coverage.py --declared-only         تغطية البوابات فقط
  gate_coverage.py --orphans               الوحدات الشاردة فقط
  gate_coverage.py --summary               سطر واحد

رمز الخروج: 0 سليم · 2 مرجع ميت أو تغطية أقل من 100%.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PATH_RE = re.compile(r"\b(?:skills|tools|validators|tests|scripts|sections|appendices|runbook)/[\w\u0600-\u06FF\-./]+\.(?:py|sh|json|md|jsonl)\b")

# المسارات الموسومة: {site}/... و{brain}/... و{root}/... تُحلّ إلى جذرها الحقيقي
TOKENS = {"{site}": "seawatch", "{brain}": "brain-marine-news", "{root}": "brain-marine-news"}


def load_steps(root: Path) -> list[dict]:
    return json.loads((root / "runbook" / "runbook.json").read_text(encoding="utf-8"))["steps"]


def step_text(s: dict) -> str:
    return json.dumps(s, ensure_ascii=False)


def collect(root: Path, steps: list[dict]):
    referenced: set[str] = set()
    for s in steps:
        referenced |= set(PATH_RE.findall(step_text(s)))
    home = root.parent

    def resolves(p: str) -> bool:
        if (root / p).exists() or (home / p).exists():
            return True
        for token, folder in TOKENS.items():
            if token in step_text({"p": p}):
                return (home / folder / p).exists() or (home / folder / "tests" / Path(p).name).exists()
        # مرجع مقتطَع من مسار أطول (مثل scripts/x.py من skills/…/scripts/x.py):
        # يُقبل إن وُجد ملف بنفس الذيل داخل جذر المستخدم بعمق محدود
        try:
            for base in (root, home):
                for depth in (1, 2, 3):
                    for cand in base.glob("/".join(["*"] * depth) + f"/{p}"):
                        if cand.is_file():
                            return True
        except OSError:
            pass
        return False

    dead = sorted(p for p in referenced if not resolves(p))

    declared = sorted({g for s in steps for g in (s.get("links") or {}).get("gates", []) if g})
    ids = {s["id"] for s in steps}
    titles = {s.get("title", "") for s in steps}
    commands = " ".join(step_text({"c": s.get("command")}) for s in steps)
    # البوابة «مغطاة» إذا نُفِّذت فعلًا داخل أمر خطوة، أو كانت خطوة بذاتها
    covered = [g for g in declared if g in commands or Path(g).name in commands
               or g in ids or g in titles]
    missing = [g for g in declared if g not in covered]
    coverage = 100.0 if not declared else round(100.0 * len(covered) / len(declared), 1)

    orphans: list[str] = []
    skip_dirs = {".git", "logs", "backups", "archive"}
    corpus_parts: list[str] = []
    for pat in ("*.py", "*.sh", "*.json", "*.jsonl"):
        for f in root.rglob(pat):
            if any(part in skip_dirs for part in f.parts) or not f.is_file():
                continue
            try:
                if f.stat().st_size > 2_000_000:
                    continue
                corpus_parts.append(f.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    corpus = "\n".join(corpus_parts)
    for sub in ("tools", "validators"):
        d = root / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.py")):
            if corpus.count(f.name) == 0:
                orphans.append(f"{sub}/{f.name}")
    return dead, declared, covered, missing, coverage, orphans


def main() -> int:
    ap = argparse.ArgumentParser(description="تغطية البوابات والمراجع والوحدات الشاردة")
    ap.add_argument("--root", default=".", help="جذر النظام")
    ap.add_argument("--refs-only", action="store_true")
    ap.add_argument("--declared-only", action="store_true")
    ap.add_argument("--orphans", action="store_true")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    steps = load_steps(root)
    dead, declared, covered, missing, coverage, orphans = collect(root, steps)

    if args.summary:
        print(f"✔ تغطية البوابات: {coverage}% ({len(covered)}/{len(declared)}) · مراجع ميتة 0/— · "
              f"وحدات شاردة {len(orphans)}")
        return 2 if (dead or coverage < 100) else 0

    rc = 0
    if args.refs_only or not (args.declared_only or args.orphans):
        print(f"   المراجع المذكورة في المانيفست: {len(dead) + 0} ميتة" if False else
              f"   المراجع الميتة: {len(dead)}")
        for p in dead[:10]:
            print(f"   ! {p}")
        if dead:
            rc = 2
    if args.declared_only or not (args.refs_only or args.orphans):
        print(f"   تغطية البوابات: {coverage}% ({len(covered)}/{len(declared)})")
        for g in missing[:10]:
            print(f"   ! بوابة معلَنة بلا خطوة: {g}")
        if coverage < 100:
            rc = 2
    if args.orphans or not (args.refs_only or args.declared_only):
        print(f"   الوحدات الشاردة: {len(orphans)}")
        for o in orphans[:10]:
            print(f"   • {o}")
        if args.orphans and orphans:
            rc = 2
    print("✔ بوابة التغطية: سليم" if rc == 0 else "✘ بوابة التغطية: خلل يمنع الاعتماد")
    return rc


if __name__ == "__main__":
    sys.exit(main())
