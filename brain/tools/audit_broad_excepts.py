#!/usr/bin/env python3
"""حصر الاستثناءات العامة التي تبتلع الخطأ — البند (د) من مراجعة 23 أكتوبر.

القاعدة: أي `except` عام (بلا نوع، أو `except Exception`) يبتلع خطأً يخصّ حكم البوابة
ويُخرج رمز نجاح أو تحذير = ثغرة فشل مفتوح. المطلوب: إما إعادة رفع الاستثناء،
أو الخروج برمز الانهيار 70 عبر `_guard`.

يكافئ قاعدتي ruff: S110 (try-except-pass) و S112 (try-except-continue).

الاستخدام:
  python3 tools/audit_broad_excepts.py                 # تقرير كامل (رمز 1 إن وُجدت مخالفة)
  python3 tools/audit_broad_excepts.py --only-gate     # ما تستدعيه البوابة فقط
  python3 tools/audit_broad_excepts.py --json          # مخرَج JSON
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("validators", "tools")
SAFE_MARKERS = ("_guard", "raise", "sys.exit(70)", "CRASH")


def swallowed(node: ast.Try) -> bool:
    """هل كل معالجات الاستثناء تبتلع الخطأ (pass أو متابعة بلا إعادة رفع)؟"""
    if not node.handlers:
        return False
    for h in node.handlers:
        broad = h.type is None or (
            isinstance(h.type, ast.Name) and h.type.id in ("Exception", "BaseException")
        )
        if not broad:
            return False
        body = h.body
        if any(isinstance(x, ast.Raise) for x in body):
            return False
        if len(body) == 1 and isinstance(body[0], (ast.Pass, ast.Continue)):
            continue
        # جسم فيه طباعة أو تعيين ثم متابعة بلا رفع = ابتلاع
        if all(isinstance(x, (ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Continue,
                              ast.Pass, ast.Break)) for x in body):
            continue
        return False
    return True


def scan_file(p: Path) -> list[dict]:
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [{"file": str(p), "line": e.lineno or 0, "kind": "خطأ صياغة", "text": str(e)}]
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Try) and swallowed(n):
            seg = ast.get_source_segment(p.read_text(encoding="utf-8"), n) or ""
            out.append({"file": str(p.relative_to(B)), "line": n.lineno,
                        "kind": "except يبتلع الخطأ", "text": seg.splitlines()[0].strip()})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows: list[dict] = []
    for d in SCAN_DIRS:
        for p in sorted((B / d).glob("*.py")):
            rows += scan_file(p)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        if not rows:
            print("  ✓ لا استثناء عام يبتلع الخطأ في validators و tools")
        else:
            print(f"  · استثناءات عامة تبتلع الخطأ: {len(rows)}")
            for r in rows:
                print(f"    - {r['file']}:{r['line']} — {r['text'][:80]}")
    return 1 if rows else 0


if __name__ == "__main__":
    sys.path.insert(0, str(B / "validators"))
    from _guard import run

    run(main)
