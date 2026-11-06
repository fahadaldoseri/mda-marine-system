#!/usr/bin/env python3
"""فحص صلابة البوابات والحراس — عشر فئات خلل تُنتج بوابات نائمة أو منهارة أو مُنذرة كاذبة.

الاستخدام:
    python3 gate_audit.py --root /path/to/project [--manifest runbook/runbook.json] [--json]

رمز الخروج: 0 إن لم توجد بنود · 1 إن وُجدت بنود تحتاج قرارًا (ليست فشلًا نهائيًا).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import defaultdict

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build", ".history"}
SCAN_DIRS = ("validators", "tools", "generator", "tests", "runbook", "scripts")
CODE_EXT = {".py", ".sh"}
SECRET_RE = re.compile(r"(TOKEN|SECRET|API_KEY|PASSWORD)\s*[:=]", re.I)
NARROWING_TOKENS = ("exclude", "allow", "whitelist", "doc", "ignore", "pattern", "regex")
UA_TOKENS = ("User-Agent", "user_agent", "user-agent")
DYNAMIC_HINTS = ("requests.get(", "requests.post(", "curl ", "urllib.request", "httpx.")
LOOP_CAP_TOKENS = ("MAX_", "_MAX", "max_iter", "limit", "cap", "budget", "attempts", "range(")


def iter_files(root: pathlib.Path, dirs=SCAN_DIRS):
    for d in dirs:
        base = root / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.is_file() and not any(part in SKIP_DIRS for part in p.parts):
                yield p


def read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def check_duplicates(root: pathlib.Path):
    """فئة 1: نسخ متكرّرة من الأداة نفسها في أكثر من مجلد."""
    seen = defaultdict(list)
    for p in iter_files(root):
        if p.suffix in CODE_EXT and p.name not in {"__init__.py"}:
            seen[p.name].append(str(p.relative_to(root)))
    return {k: v for k, v in seen.items() if len(v) > 1}


def check_unlinked(root: pathlib.Path, manifest_text: str, index_text: str):
    """فئة 10: حارس أو اختبار لا يستدعيه المانيفست ولا الفهرس."""
    out = []
    for p in iter_files(root, ("validators", "tests")):
        if p.suffix != ".py" or p.name == "__init__.py":
            continue
        rel = str(p.relative_to(root))
        if p.name not in manifest_text and rel not in manifest_text and p.name not in index_text:
            out.append(rel)
    return out


def check_silent_exit(root: pathlib.Path):
    """فئة 3: خروج غير صفري بلا طباعة سبب قريب."""
    out = []
    for p in iter_files(root):
        if p.suffix != ".py":
            continue
        lines = read(p).splitlines()
        for i, ln in enumerate(lines):
            if re.search(r"(sys\.exit\(\s*[1-9]|raise SystemExit\()", ln):
                window = "\n".join(lines[max(0, i - 4): i + 1])
                if not re.search(r"(print|log|logger|stderr|echo)", window):
                    out.append(f"{p.relative_to(root)}:{i + 1}")
    return out


def check_unbounded_loops(root: pathlib.Path):
    """فئة 7: حلقة تحويل قد لا تتقارب (while بلا سقف قريب)."""
    out = []
    for p in iter_files(root, ("tools", "generator", "validators")):
        if p.suffix != ".py":
            continue
        lines = read(p).splitlines()
        for i, ln in enumerate(lines):
            if re.match(r"\s*while\s", ln) and "while True" not in ln:
                window = "\n".join(lines[i: i + 14])
                if not any(t in window for t in LOOP_CAP_TOKENS):
                    out.append(f"{p.relative_to(root)}:{i + 1}")
    return out


def check_secret_false_positives(root: pathlib.Path):
    """فئة 6: أنماط تُنذر كاذبة لأنها لا تُضيّق التوثيق أو المرجع الداخلي."""
    out = []
    for p in iter_files(root, ("validators", "tools", "tests")):
        if p.suffix != ".py":
            continue
        t = read(p)
        if SECRET_RE.search(t) and not any(tok in t.lower() for tok in NARROWING_TOKENS):
            out.append(str(p.relative_to(root)))
    return out


def check_static_verification(root: pathlib.Path):
    """فئة 8: تحقق من هدف ديناميكي بلا سياق مستخدم (يُنتج حكمًا كاذبًا)."""
    out = []
    for p in iter_files(root, ("tools", "validators")):
        if p.suffix != ".py":
            continue
        t = read(p)
        if any(h in t for h in DYNAMIC_HINTS) and not any(u.lower() in t.lower() for u in UA_TOKENS):
            out.append(str(p.relative_to(root)))
    return out


def check_negative_tests(root: pathlib.Path):
    """فئة 9: حارس بلا اختبار يقيسه (موجب أو سالب)."""
    tests_text = "\n".join(read(p) for p in iter_files(root, ("tests",)))
    out = []
    for p in iter_files(root, ("validators",)):
        if p.suffix != ".py" or p.name == "__init__.py":
            continue
        if p.name not in tests_text:
            out.append(str(p.relative_to(root)))
    return out


def check_verdict_freshness(root: pathlib.Path):
    """فئة 2: أدوات تكتب أحكامًا/سجلات بلا زمن مخزَّن (فتُقرأ قديمة لاحقًا)."""
    out = []
    for p in iter_files(root, ("tools", "validators")):
        if p.suffix != ".py":
            continue
        t = read(p)
        writes_log = re.search(r"(logs/|\.jsonl|\.json)", t) and re.search(r"(write_text|json\.dump|open\(.+w)", t)
        if writes_log and not re.search(r"(timestamp|generated_at|\"ts\"|time\.time|utcnow|now\()", t):
            out.append(str(p.relative_to(root)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="فحص صلابة البوابات والحراس")
    ap.add_argument("--root", required=True)
    ap.add_argument("--manifest", default="runbook/runbook.json")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    root = pathlib.Path(a.root).resolve()
    if not root.is_dir():
        print(f"   ✘ الجذر غير موجود: {root}")
        return 2

    man = root / a.manifest
    manifest_text = read(man) if man.is_file() else ""
    index_text = read(root / "INDEX.md")

    findings = {
        "1 · نسخ مكرّرة من أداة": check_duplicates(root),
        "2 · أحكام بلا زمن مخزَّن": check_verdict_freshness(root),
        "3 · خروج غير صفري بلا سبب": check_silent_exit(root),
        "6 · أنماط قابلة للإنذار الكاذب": check_secret_false_positives(root),
        "7 · حلقات بلا سقف": check_unbounded_loops(root),
        "8 · تحقق ساكن من هدف ديناميكي": check_static_verification(root),
        "9 · حارس بلا اختبار يقيسه": check_negative_tests(root),
        "10 · حارس غير مربوط": check_unlinked(root, manifest_text, index_text),
    }

    if a.json:
        print(json.dumps({k: (v if isinstance(v, list) else list(v)) for k, v in findings.items()},
                         ensure_ascii=False, indent=2))
    else:
        print(f"   ═══ فحص صلابة البوابات · {root} ═══")
        print(f"   المانيفست: {'مقروء' if manifest_text else 'غير موجود'} · INDEX: {'مقروء' if index_text else 'غير موجود'}")
        total = 0
        for k, v in findings.items():
            n = len(v)
            total += n
            mark = "✔" if n == 0 else "◐"
            print(f"   {mark} {k}: {n}")
            if n:
                if isinstance(v, dict):
                    for name, places in list(v.items())[:3]:
                        print(f"        · {name} ← {', '.join(places[:2])}")
                else:
                    for s in v[:3]:
                        print(f"        · {s}")
        print(f"   ── الإجمالي: {total} بندًا يحتاج قرارًا (0 = لا بنود) ──")
    return 0 if sum(len(v) for v in findings.values()) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())