#!/usr/bin/env python3
"""عقود تمنع عودة عطلَي المراجعة الثانية في G040."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _main_guard(tree: ast.Module) -> ast.If:
    for node in tree.body:
        if isinstance(node, ast.If) and "__main__" in ast.dump(node.test):
            return node
    raise AssertionError("لا توجد كتلة تنفيذ __main__")


def _calls_guard_run(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    guard = _main_guard(tree)
    imports_run = any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").endswith("_guard")
        and any(alias.name == "run" for alias in node.names)
        for node in ast.walk(guard)
    )
    return imports_run and any(
        isinstance(node, ast.Call) and getattr(node.func, "id", "") == "run"
        for node in ast.walk(guard)
    )


def test_skills_parity_uses_fail_closed_guard() -> None:
    assert _calls_guard_run(ROOT / "validators" / "check_skills_parity.py")


def test_browser_measure_does_not_swallow_broad_close_errors() -> None:
    tree = ast.parse((ROOT / "tools" / "browser_measure.py").read_text(encoding="utf-8"))
    measure = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "measure")
    broad = []
    for node in ast.walk(measure):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            broad.append(node.lineno)
        elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
            broad.append(node.lineno)
        elif isinstance(node.type, ast.Attribute) and node.type.attr in {"Exception", "BaseException"}:
            broad.append(node.lineno)
    assert not broad, f"معالجات عامة داخل measure: {broad}"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
