#!/usr/bin/env python3
"""حصر الاستثناءات العامة التي تبتلع الخطأ — البند (د) من مراجعة 23 أكتوبر، ومُوسَّع بأمر فهد 2026-10-24 (البند 7).

القاعدة: أي `except` عام (بلا نوع، أو `Exception`/`BaseException` ولو داخل نوع مركّب) يبتلع خطأً
يخصّ حكم البوابة = ثغرة فشل مفتوح. المطلوب: إعادة رفع الاستثناء، أو الخروج برمز الانهيار 70.

قواعد الحكم (مطبَّقة حرفيًّا، ومُختبرة في tests/test_audit_broad_excepts.py):
  (أ) `except Exception: return ...` يُعدّ ابتلاعًا.
  (ب) `sys.exit(70)` (أي خروج بغير صفر) لا يُعدّ ابتلاعًا.
  (ج) الأنواع المركّبة تُكتشف: `except (Exception, OSError)` عام، و`except (ValueError, KeyError)` ضيّق.
  (د) `--only-gate` يفحص ما تستدعيه البوابة والكتيب والاختبارات فعلًا.
  (هـ) `--json` يعيد رمزًا غير صفري عند وجود مخالفة غير مصنّفة.
  (و) المسح تعاودي في كل المجلدات المصرّح بها.

الاستخدام:
  python3 tools/audit_broad_excepts.py                 # تقرير كامل (رمز 1 إن وُجد غير مصنّف)
  python3 tools/audit_broad_excepts.py --only-gate     # ما تستدعيه البوابة فقط
  python3 tools/audit_broad_excepts.py --json          # مخرَج JSON (رمز 1 عند وجود غير مصنّف)
  python3 tools/audit_broad_excepts.py --baseline      # إعادة توليد خط الأساس من المسح الحيّ
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("validators", "tools", "webdev")
SKIP_PARTS = ("__pycache__", "/.git/", "/archive/", "/backups/", "/_oneoff", "/.venv/", "/node_modules/")
BROAD_NAMES = ("Exception", "BaseException")
NOT_SWALLOW_CALLS = ("fail", "_fail", "die", "crash", "boom", "abort")
GATE_SOURCES = ("tools/final_gate.sh", "runbook/runbook.json", "tests/run_checks.sh",
                "tools/daily_pipeline.sh", "tools/rebuild_report.sh")


def broad_type(t: ast.AST | None) -> bool:
    """(ج) النوع عام: بلا نوع، أو Exception/BaseException ولو داخل نوع مركّب."""
    if t is None:
        return True
    if isinstance(t, ast.Tuple):
        return any(broad_type(e) for e in t.elts)
    if isinstance(t, ast.Name):
        return t.id in BROAD_NAMES
    if isinstance(t, ast.Attribute):
        return t.attr in BROAD_NAMES
    return False


def exits_nonzero(node: ast.AST) -> bool:
    """(ب) خروج بغير صفر لا يُعدّ ابتلاعًا."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = getattr(f, "attr", None) or getattr(f, "id", None)
            if name == "exit":
                arg = n.args[0] if n.args else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int) and arg.value != 0:
                    return True
                if arg is None:
                    return False
            if name in NOT_SWALLOW_CALLS:
                return True
    return False


def handler_swallows(h: ast.ExceptHandler) -> bool:
    if not broad_type(h.type):
        return False
    if any(isinstance(x, ast.Raise) for x in ast.walk(h)):
        return False
    if exits_nonzero(h):
        return False
    return True


def swallowed(node: ast.Try) -> bool:
    """كل المعالجات عامة وتبتلع الخطأ (بما فيه return بلا رفع)."""
    if not node.handlers:
        return False
    return all(handler_swallows(h) for h in node.handlers)


def handler_kind(node: ast.Try) -> str:
    """ما يفعله المعالج عند الابتلاع: إرجاع قيمة (خطر حكم) · متابعة · طباعة فقط."""
    kinds = set()
    for h in node.handlers:
        for x in ast.walk(h):
            if isinstance(x, ast.Return):
                kinds.add("إرجاع قيمة")
            elif isinstance(x, ast.Continue):
                kinds.add("متابعة")
            elif isinstance(x, ast.Break):
                kinds.add("قطع")
            elif isinstance(x, ast.Pass):
                kinds.add("تجاهل")
    if "إرجاع قيمة" in kinds:
        return "إرجاع قيمة"
    return " · ".join(sorted(kinds)) or "تجاهل"


GATE_FUNCS = ("main", "check", "validate", "run", "verify", "gate", "judge", "report")


def category_of(row: dict) -> str:
    """تصنيف الموقع: منطق البوابة (يجب تضييقه) أو تنظيف ثانوي."""
    in_validator = row["file"].startswith("validators/")
    judgment = row.get("handler_kind") == "إرجاع قيمة" or any(
        k in (row.get("func") or "").lower() for k in GATE_FUNCS)
    return "منطق البوابة" if (in_validator and judgment) else "تنظيف ثانوي"


def site_key(row: dict) -> str:
    """مفتاح الموقع: الملف + الدالة الحاضنة + بصمة كتلة try (لا رقم السطر — يتزحزح)."""
    snip = re.sub(r"\s+", " ", (row.get("snippet") or "")).strip()
    return f"{row.get('file')}::{row.get('func') or '<module>'}::{snip[:40]}::{row.get('fingerprint') or ''}"


def enclosing_funcs(tree: ast.AST) -> list[tuple[str, int, int]]:
    return [(n.name, n.lineno, getattr(n, "end_lineno", n.lineno))
            for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def scan_file(p: Path) -> list[dict]:
    src = p.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"file": str(p), "line": e.lineno or 0, "kind": "خطأ صياغة", "text": str(e)}]
    funcs = enclosing_funcs(tree)

    def enclosing(line: int) -> str:
        name = ""
        for fname, a, b in funcs:
            if a <= line <= b:
                name = fname
        return name or "<module>"

    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Try) and swallowed(n):
            seg = ast.get_source_segment(src, n) or ""
            first = next((l.strip() for l in seg.splitlines()[1:] if l.strip()), "")
            out.append({"file": str(p.relative_to(B)), "line": n.lineno,
                        "kind": "except يبتلع الخطأ", "text": seg.splitlines()[0].strip(),
                        "snippet": first, "func": enclosing(n.lineno),
                        "handler_kind": handler_kind(n),
                        "fingerprint": hashlib.sha1(re.sub(r"\s+", " ", seg).encode()).hexdigest()[:8]})
    return out


def gate_files() -> set[str]:
    """الملفات التي تستدعيها البوابة أو الكتيب أو الاختبارات فعلًا (البند د)."""
    refs: set[str] = set()
    for rel in GATE_SOURCES:
        f = B / rel
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"([A-Za-z0-9_./-]+\.py)", text):
            cand = m.group(1)
            for d in SCAN_DIRS:
                if cand.startswith(f"{d}/"):
                    refs.add(cand)
    return refs


def scan_all(only_gate: bool) -> list[dict]:
    rows: list[dict] = []
    wanted = gate_files() if only_gate else None
    for d in SCAN_DIRS:
        root = B / d
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.py")):          # (و) مسح تعاودي
            s = str(p)
            if any(x in s for x in SKIP_PARTS):
                continue
            rel = str(p.relative_to(B))
            if wanted is not None and rel not in wanted:
                continue
            try:
                rows += scan_file(p)
            except Exception as exc:                   # noqa: BLE001 — يُرفع كخطأ أداة لا يُبتلع
                rows.append({"file": rel, "line": 0, "kind": "تعذّر المسح", "text": f"{type(exc).__name__}: {exc}"})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--only-gate", action="store_true")   # (د)
    ap.add_argument("--baseline", action="store_true")
    a = ap.parse_args()

    rows = scan_all(a.only_gate)
    base_f = B / "appendices" / "broad-excepts-baseline.json"
    base = json.loads(base_f.read_text(encoding="utf-8")) if base_f.exists() else {"accepted": []}
    accepted = base.get("accepted") or []

    if a.baseline:
        out = []
        for r in rows:
            prev = next((e for e in accepted if site_key(e) == site_key(r)), {})
            out.append({"file": r["file"], "func": r.get("func"), "fingerprint": r.get("fingerprint"),
                        "line_at_generation": r.get("line"), "snippet": r.get("snippet"),
                        "handler_kind": r.get("handler_kind"),
                        "category": category_of(r), "reason": prev.get("reason", "")})
        base["accepted"] = out
        base_f.write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"  ✔ أُعيد توليد خط الأساس: {len(out)} موقعًا")
        return 0

    known = {site_key(r) for r in accepted if r.get("fingerprint")}
    fresh = [r for r in rows if site_key(r) not in known]
    gate_swallow = [e for e in accepted if e.get("category") == "منطق البوابة"]
    if a.json:
        print(json.dumps({"total": len(rows), "unclassified": fresh,
                          "accepted_gate_logic": gate_swallow}, ensure_ascii=False, indent=1))
        # المواقع المصنفة المقبولة تُعرض للتتبع، لكنها ليست مخالفة جديدة؛
        # لا يُمنع التشغيل إلا عند ظهور موقع غير مصنف فعليًا.
        return 1 if fresh else 0        # (هـ)
    print(f"  · استثناءات عامة تبتلع الخطأ: {len(rows)} — غير مصنّفة: {len(fresh)}")
    if gate_swallow:
        print(f"  ✘ استثناءات داخل منطق البوابة (يجب تضييقها): {len(gate_swallow)}")
    for r in fresh:
        print(f"    - {r['file']}:{r.get('line')} — {r.get('func')} — {r['text'][:70]}")
    if not rows:
        print("  ✓ لا استثناء عام يبتلع الخطأ")
    return 1 if (fresh or gate_swallow) else 0


if __name__ == "__main__":
    sys.path.insert(0, str(B / "validators"))
    from _guard import run

    run(main)
