#!/usr/bin/env python3
"""افحص ملف Python بحثًا عن تعريفات/كتل/استيرادات مكررة ونمط norm قبل splitlines."""
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


class Scanner(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scope: list[str] = ["<module>"]
        self.definitions: dict[tuple[str, str, str], list[int]] = defaultdict(list)
        self.imports: dict[tuple[str, str], list[int]] = defaultdict(list)
        self.blocks: dict[tuple[str, str, str], list[int]] = defaultdict(list)
        self.norm_calls: list[int] = []
        self.split_after_norm: list[tuple[int, str]] = []
        self.normalizer_names: set[str] = set()
        self.norm_assignments: dict[tuple[str, str], int] = {}

    @property
    def current_scope(self) -> str:
        return ".".join(self.scope)

    def _record_definition(self, kind: str, name: str, line: int) -> None:
        self.definitions[(self.current_scope, kind, name)].append(line)

    def _visit_nested(self, node: ast.AST, scope_name: str) -> None:
        self.scope.append(scope_name)
        for child in ast.iter_child_nodes(node):
            self.visit(child)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.normalizer_names.add(node.name) if "norm" in node.name.lower() else None
        self._record_definition("دالة", node.name, node.lineno)
        self._visit_nested(node, f"{node.name}@{node.lineno}")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.normalizer_names.add(node.name) if "norm" in node.name.lower() else None
        self._record_definition("دالة غير متزامنة", node.name, node.lineno)
        self._visit_nested(node, f"{node.name}@{node.lineno}")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._record_definition("صنف", node.name, node.lineno)
        self._visit_nested(node, f"{node.name}@{node.lineno}")

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            key = (self.current_scope, f"import {alias.name} as {alias.asname or ''}".strip())
            self.imports[key].append(node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = "." * node.level + (node.module or "")
        for alias in node.names:
            key = (self.current_scope, f"from {module} import {alias.name} as {alias.asname or ''}".strip())
            self.imports[key].append(node.lineno)

    def _record_block(self, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)):
            body = getattr(node, "body", [])
            orelse = getattr(node, "orelse", [])
            if len(body) < 2 and not orelse:
                return
            structural = ast.dump(node, annotate_fields=True, include_attributes=False)
            key = (self.current_scope, type(node).__name__, structural)
            self.blocks[key].append(getattr(node, "lineno", 0))

    def visit(self, node: ast.AST) -> Any:  # noqa: N802
        self._record_block(node)
        return super().visit(node)

    def _is_normalizer_call(self, node: ast.AST) -> bool:
        if not isinstance(node, ast.Call):
            return False
        fn = node.func
        if isinstance(fn, ast.Name):
            return fn.id in self.normalizer_names or fn.id in {"norm", "normalize", "normalise"}
        return isinstance(fn, ast.Attribute) and "norm" in fn.attr.lower()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if self._is_normalizer_call(node):
            self.norm_calls.append(node.lineno)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "splitlines":
            value = node.func.value
            if self._is_normalizer_call(value):
                self.split_after_norm.append((node.lineno, "استدعاء مباشر: norm(...).splitlines()"))
            elif isinstance(value, ast.Name):
                prior = self.norm_assignments.get((self.current_scope, value.id))
                if prior is not None and prior <= node.lineno:
                    self.split_after_norm.append((node.lineno, f"المتغير {value.id} طُبّع في السطر {prior} ثم قُسّم"))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        if self._is_normalizer_call(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.norm_assignments[(self.current_scope, target.id)] = node.lineno
        self.generic_visit(node)


def _line_end(node: ast.AST) -> int:
    return int(getattr(node, "end_lineno", getattr(node, "lineno", 0)))


def _textual_norm_warning(source: str) -> list[tuple[int, str]]:
    warnings: list[tuple[int, str]] = []
    for match in re.finditer(r"\b(?:norm|normalize|normalise)\s*\([^\n;]*\)\s*\.\s*splitlines\s*\(", source):
        warnings.append((source.count("\n", 0, match.start()) + 1, "نمط نصي: التطبيع يسبق splitlines"))
    return warnings


def scan(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source, filename=str(path))
    scanner = Scanner()
    scanner.visit(tree)
    definitions = []
    for (scope, kind, name), lines in sorted(scanner.definitions.items()):
        if len(lines) > 1:
            definitions.append({"scope": scope, "kind": kind, "name": name, "lines": sorted(lines), "actual": max(lines)})
    imports = []
    for (scope, statement), lines in sorted(scanner.imports.items()):
        if len(lines) > 1:
            imports.append({"scope": scope, "statement": statement, "lines": sorted(lines)})
    blocks = []
    for (scope, kind, structural), lines in sorted(scanner.blocks.items()):
        if len(lines) > 1:
            blocks.append({"scope": scope, "kind": kind, "lines": sorted(lines)})
    warnings = sorted(set(scanner.split_after_norm + _textual_norm_warning(source)))
    return {"definitions": definitions, "imports": imports, "blocks": blocks, "norm_before_splitlines": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        result = scan(args.file)
    except (OSError, SyntaxError) as exc:
        print(f"تعذر فحص {args.file}: {type(exc).__name__}: {exc}")
        return 2
    print(f"فحص التكرار البنيوي: {args.file}")
    defs = result["definitions"]
    if defs:
        print("تعريفات دوال/أصناف مكررة:")
        for item in defs:
            print(f"  - {item['kind']} {item['name']} في النطاق {item['scope']}: الأسطر {item['lines']}; التعريف الذي ينفذ فعليًا غالبًا: السطر {item['actual']} (الأخير في النطاق)")
    else:
        print("تعريفات دوال/أصناف مكررة: لا يوجد")
    imports = result["imports"]
    if imports:
        print("استيرادات مكررة:")
        for item in imports:
            print(f"  - {item['statement']} في {item['scope']}: الأسطر {item['lines']}")
    else:
        print("استيرادات مكررة: لا يوجد")
    blocks = result["blocks"]
    if blocks:
        print("كتل مكررة بنيويًا:")
        for item in blocks:
            print(f"  - {item['kind']} في {item['scope']}: بدايات الأسطر {item['lines']}")
    else:
        print("كتل مكررة بنيويًا: لا يوجد")
    warnings = result["norm_before_splitlines"]
    if warnings:
        print("تحذير نمطي: دالة تطبيع استُدعيت قبل تقسيم الأسطر:")
        for line, detail in warnings:
            print(f"  - السطر {line}: {detail}")
    else:
        print("فحص norm قبل splitlines: لا تحذير")
    return 2 if defs or imports or blocks or warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
