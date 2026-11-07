#!/usr/bin/env python3
"""فحص صلابة البوابات والحراس — عشر فئات خلل تُنتج بوابات نائمة أو منهارة أو مُنذرة كاذبة.

الاستخدام:
    python3 gate_audit.py --root /path/to/project [--manifest runbook/runbook.json] [--json]

رمز الخروج: 0 إن لم توجد بنود · 1 إن وُجدت بنود تحتاج قرارًا (ليست فشلًا نهائيًا).
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sys
import tokenize
from collections import defaultdict

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build", ".history"}
SCAN_DIRS = ("validators", "tools", "generator", "tests", "runbook", "scripts")
CODE_EXT = {".py", ".sh"}
SECRET_RE = re.compile(r"(TOKEN|SECRET|API_KEY|PASSWORD)\s*[:=]", re.I)
NARROWING_TOKENS = ("exclude", "allow", "whitelist", "doc", "ignore", "pattern", "regex")
FIXTURE_SECRET_TOKENS = ("tok-", "tok_", "dummy", "example", "placeholder", "changeme", "test-")
UA_TOKENS = ("User-Agent", "user_agent", "user-agent", "-A ", "--user-agent")
# API clients and Playwright already provide a protocol/session context.  This
# category is reserved for shell HTTP probes that impersonate no client.
DYNAMIC_HINTS = ("curl ",)
LOOP_CAP_TOKENS = ("MAX_", "_MAX", "max_iter", "limit", "cap", "budget", "attempts", "range(")
# بعض الحراس رقيقة فوق مولّد/دالة تحقق تحمل اسمًا مختلفًا. لا نعدّها «بلا اختبار»
# إذا كان الاختبار يمرّر المسار المعياري نفسه بموجب وسالب؛ هذا ربط صريح لا إعفاء عام.
RELATED_TESTS = {
    "check_reference_generated.py": ("tests/test_reference_generator.py",),
}
OPERATIONAL_WRITE_TOKENS = ("logs/", "memory/", "audit/", "evidence", ".jsonl", "QUEUE", "DECISIONS")
VERDICT_WRITE_TOKENS = ("verdict", "status", "result", "outcome", "decision", "level", "finding")
TIME_PROVENANCE_TOKENS = (
    '"date"', "'date'", "args.date", "a.date", "TODAY", "DATE", "retrieved_at",
    "timestamp", "generated_at", "utcnow", "now()",
)


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


def _string_lines(text: str) -> set[int]:
    """Return source lines inside string literals (including embedded JS)."""
    out: set[int] = set()
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for tok in tokens:
            if tok.type != tokenize.STRING:
                continue
            out.update(range(tok.start[0], tok.end[0] + 1))
    except (IndentationError, SyntaxError, tokenize.TokenError):
        return set()
    return out


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
    # Unit tests are consumers of a guard, not guards themselves.  Requiring
    # every test filename in the runbook produced 11 structural false alarms.
    for p in iter_files(root, ("validators",)):
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
        if "tests" in p.parts:
            continue
        if p.suffix != ".py":
            continue
        lines = read(p).splitlines()
        string_lines = _string_lines("\n".join(lines))
        for i, ln in enumerate(lines):
            if i + 1 in string_lines or "SystemExit(main())" in ln:
                continue
            if re.search(r"(sys\.exit\(\s*[1-9]|raise SystemExit\()", ln):
                window = "\n".join(lines[max(0, i - 4): i + 1])
                # A non-zero SystemExit with a literal/f-string reason is an
                # announced contract failure, not a silent failure.
                if re.search(r"raise SystemExit\(\s*[furbFUR]?['\"]", window):
                    continue
                if not re.search(r"(print|log|logger|stderr|echo)", window):
                    out.append(f"{p.relative_to(root)}:{i + 1}")
    return out


def check_unbounded_loops(root: pathlib.Path):
    """فئة 7: حلقة تحويل قد لا تتقارب (while بلا سقف قريب)."""
    out = []
    for p in iter_files(root, ("tools", "generator", "validators")):
        if p.suffix != ".py":
            continue
        text = read(p)
        lines = text.splitlines()
        string_lines = _string_lines(text)
        for i, ln in enumerate(lines):
            if i + 1 in string_lines:
                continue
            if re.match(r"\s*while\s", ln) and "while True" not in ln:
                window = "\n".join(lines[i: i + 14])
                condition = re.sub(r"^\s*while\s+|:\s*$", "", ln).strip()
                provably_bounded = (
                    re.search(r"(?:<|<=|>)\s*len\(", condition)
                    or re.search(r"(?:<|<=)\s*(?:end|stop|finish)\b", condition)
                    or re.search(r"\b(?:in|is not None|is None)\b", condition)
                    or re.search(r"\blen\([^)]*\)\s*>\s*\d+", condition)
                    or re.search(r"\b(?:queue|stack|body)\b", condition)
                    or ".pop(" in window
                    or ".popleft(" in window
                    or re.search(r"\b(?:changed|done)\s*=\s*False", window)
                )
                if not provably_bounded and not any(t in window for t in LOOP_CAP_TOKENS):
                    out.append(f"{p.relative_to(root)}:{i + 1}")
    return out


def check_secret_false_positives(root: pathlib.Path):
    """فئة 6: أنماط تُنذر كاذبة لأنها لا تُضيّق التوثيق أو المرجع الداخلي."""
    out = []
    for p in iter_files(root, ("validators", "tools", "tests")):
        if p.suffix != ".py":
            continue
        # هذا الاختبار يحتوي عمدًا على قيمة حقيقية/وهمية لإثبات الحساسية؛
        # لا يصح أن يفحص الفاحص نص اختبار الفاحص نفسه.
        if "tests" in p.parts and "gate_audit" in p.stem:
            continue
        t = read(p)
        matches = []
        for m in SECRET_RE.finditer(t):
            line = t[m.start(): t.find("\n", m.start()) if t.find("\n", m.start()) >= 0 else len(t)]
            if any(tok.lower() in line.lower() for tok in FIXTURE_SECRET_TOKENS):
                continue
            matches.append(m)
        if matches and not any(tok in t.lower() for tok in NARROWING_TOKENS):
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
    test_files = list(iter_files(root, ("tests",)))
    tests_text = "\n".join(read(p) for p in test_files)
    test_names = {p.name for p in test_files}
    out = []
    for p in iter_files(root, ("validators",)):
        if p.suffix != ".py" or p.name == "__init__.py":
            continue
        semantic = p.stem.removeprefix("check_")
        aliases = {p.name, p.stem, semantic, f"test_{semantic}.py", f"test_{semantic}"}
        related = []
        for rel in RELATED_TESTS.get(p.name, ()):
            test_path = root / rel
            if test_path.is_file():
                text = read(test_path)
                # عقد موجب/سالب: الاختبار يجب أن يستدعي دالة التحقق المعيارية
                # ويثبت مساري الاجتياز والمنع، لا أن يذكر اسم الحارس فقط.
                has_pass = "== 0" in text or bool(re.search(r"cmd_check\([^\n]*\),\s*0\)", text))
                has_block = "== 2" in text or bool(re.search(r"cmd_check\([^\n]*\),\s*2\)", text))
                if "cmd_check" in text and has_pass and has_block:
                    related.append(rel)
        if not (aliases & test_names or any(alias in tests_text for alias in aliases) or related):
            out.append(str(p.relative_to(root)))
    return out


def check_verdict_freshness(root: pathlib.Path):
    """فئة 2: أدوات تكتب أحكامًا/سجلات بلا زمن مخزَّن (فتُقرأ قديمة لاحقًا)."""
    out = []
    for p in iter_files(root, ("tools", "validators")):
        if p.suffix != ".py":
            continue
        t = read(p)
        lines = t.splitlines()
        contexts = []
        for i, line in enumerate(lines):
            if not any(x in line for x in ("write_text", "json.dump", "open(")):
                continue
            context = " ".join(lines[max(0, i - 3): min(len(lines), i + 4)])
            if any(tok.lower() in context.lower() for tok in OPERATIONAL_WRITE_TOKENS):
                contexts.append(context)
        writes_log = bool(contexts) and any(
            tok.lower() in t.lower() for tok in VERDICT_WRITE_TOKENS
        )
        # Date-scoped evidence and records carrying source retrieval time are
        # not stale verdicts.  The old check treated every generated JSON/MD
        # artifact as a reusable verdict and produced 89 structural alarms.
        has_provenance = any(
            any(tok.lower() in (c + " " + t).lower() for tok in TIME_PROVENANCE_TOKENS)
            for c in contexts
        )
        if writes_log and not has_provenance and "_oneoff" not in str(p):
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
