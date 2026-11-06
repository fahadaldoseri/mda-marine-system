#!/usr/bin/env python3
"""استخرج عقد أداة CLI دون تشغيلها؛ استخدم --help فقط كمسار آمن احتياطي."""
from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass
class ArgSpec:
    names: list[str]
    kind: str
    required: bool
    takes_value: bool
    line: int


@dataclass
class Contract:
    tool: str
    source: str | None
    source_method: str
    accepted_options: list[str]
    accepted_positionals: list[str]
    required_arguments: list[str]
    arguments: list[dict[str, Any]]
    declared_exit_codes: list[int]
    warnings: list[str]
    help_probe: dict[str, Any] | None = None


_BOOLEAN_ACTIONS = {"store_true", "store_false", "count", "help", "version"}


def _literal(node: ast.AST | None) -> Any:
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _names_from_targets(target: ast.AST) -> Iterable[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _names_from_targets(elt)


class _ArgparseCollector(ast.NodeVisitor):
    """Collect add_argument calls; a method named add_argument is sufficient."""

    def __init__(self) -> None:
        self.specs: list[ArgSpec] = []
        self.has_parser = False

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Name) and node.func.id == "ArgumentParser":
            self.has_parser = True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            raw = [_literal(arg) for arg in node.args]
            names = [x for x in raw if isinstance(x, str)]
            options = [x for x in names if x.startswith("-")]
            positionals = [x for x in names if not x.startswith("-")]
            required = _literal(next((v for k, v in ((kw.arg, kw.value) for kw in node.keywords) if k == "required"), None)) is True
            action = _literal(next((v for k, v in ((kw.arg, kw.value) for kw in node.keywords) if k == "action"), None))
            nargs = _literal(next((v for k, v in ((kw.arg, kw.value) for kw in node.keywords) if k == "nargs"), None))
            takes_value = not (action in _BOOLEAN_ACTIONS or nargs == 0)
            if positionals and not options and nargs not in ("?", "*", "..."):
                required = True
            if options or positionals:
                self.specs.append(ArgSpec(options or positionals, "option" if options else "positional", required, takes_value, getattr(node, "lineno", 0)))
        self.generic_visit(node)


def _extract_exit_codes(text: str) -> list[int]:
    codes: set[int] = set()
    patterns = (
        r"\breturn\s+(\d+)\b",
        r"\b(?:SystemExit|exit)\s*\(\s*(\d+)\s*\)",
        r"(?:رمز\s+الخروج|exit\s+code|exit_code)\D{0,24}(\d+)",
    )
    for pattern in patterns:
        codes.update(int(m.group(1)) for m in re.finditer(pattern, text, re.IGNORECASE))
    return sorted(codes)


def _parse_help(text: str) -> tuple[list[str], list[str]]:
    options: set[str] = set()
    positionals: list[str] = []
    for line in text.splitlines():
        for match in re.finditer(r"(?<!\w)(--[A-Za-z][A-Za-z0-9_-]*|-[A-Za-z])(?!\w)", line):
            options.add(match.group(1))
        if line.lower().startswith("usage:"):
            # لا تعتبر metavars مثل PDF وDATE وسائط موضعية؛ فهي تأتي بعد خيار.
            usage = line.split(":", 1)[1]
            try:
                tokens = shlex.split(usage)
            except ValueError:
                tokens = usage.split()
            skip_value = False
            for token in tokens:
                if skip_value:
                    skip_value = False
                    if not token.startswith("-") and not token.startswith("["):
                        continue
                if token.startswith("--") or (token.startswith("-") and not token.startswith("[")):
                    name = token.split("=", 1)[0]
                    if re.fullmatch(r"--[A-Za-z][A-Za-z0-9_-]*|-[A-Za-z]", name):
                        options.add(name)
                    if "=" not in token:
                        skip_value = True
                    continue
                if re.fullmatch(r"[A-Z][A-Z0-9_-]{1,}", token) and token not in positionals:
                    positionals.append(token)
    return sorted(options), positionals


def _script_path(command: Sequence[str]) -> tuple[str | None, int | None]:
    for idx, token in enumerate(command):
        if token.endswith(".py") and Path(token).is_file():
            return token, idx
    if command and Path(command[0]).is_file() and not command[0].endswith((".py", ".sh")):
        return command[0], 0
    return None, None


def _tool_command(tool: str) -> list[str]:
    parts = shlex.split(tool)
    if not parts:
        return []
    if len(parts) == 1 and parts[0].endswith(".py"):
        return [sys.executable, parts[0]]
    return parts


def _probe_help(tool: str, timeout: float) -> tuple[dict[str, Any], str]:
    command = _tool_command(tool)
    if not command:
        return {"attempted": False, "error": "أداة فارغة"}, ""
    try:
        result = subprocess.run(command + ["--help"], capture_output=True, text=True, timeout=timeout, check=False)
        output = (result.stdout or "") + (result.stderr or "")
        return {"attempted": True, "returncode": result.returncode, "timeout_seconds": timeout}, output
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") if isinstance(exc.stdout, str) else "") + ((exc.stderr or "") if isinstance(exc.stderr, str) else "")
        return {"attempted": True, "returncode": None, "timeout_seconds": timeout, "timed_out": True}, output
    except OSError as exc:
        return {"attempted": True, "returncode": None, "error": f"{type(exc).__name__}: {exc}"}, ""


def inspect_tool(tool: str, timeout: float = 2.0, force_help: bool = False) -> Contract:
    """Return a contract without invoking the tool's normal operation."""
    source_path = Path(tool).expanduser()
    if not source_path.is_file():
        located = shutil.which(tool)
        if located:
            source_path = Path(located)
    source: str | None = None
    specs: list[ArgSpec] = []
    method = "help"
    warnings: list[str] = []
    if source_path.is_file() and source_path.suffix == ".py":
        try:
            source = source_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(source_path))
            collector = _ArgparseCollector()
            collector.visit(tree)
            specs = collector.specs
            method = "ast:add_argument"
            if not specs and not collector.has_parser:
                warnings.append("لم يُعثر على argparse/add_argument في AST")
        except (OSError, SyntaxError) as exc:
            warnings.append(f"تعذر تحليل المصدر بنيويًا: {type(exc).__name__}: {exc}")
            method = "help"
    help_probe: dict[str, Any] | None = None
    help_output = ""
    if force_help or not specs:
        help_probe, help_output = _probe_help(tool, timeout)
        help_options, help_positionals = _parse_help(help_output)
        if help_options:
            existing = {name for spec in specs for name in spec.names}
            specs.extend(ArgSpec([name], "option", False, True, 0) for name in help_options if name not in existing)
        if help_positionals and not any(spec.kind == "positional" for spec in specs):
            specs.extend(ArgSpec([name], "positional", True, True, 0) for name in help_positionals)
        if help_probe.get("timed_out"):
            warnings.append("انتهت مهلة --help؛ لم تُعتبر الأداة مُشغّلة")
        elif help_probe.get("error"):
            warnings.append(f"تعذر استدعاء --help الآمن: {help_probe['error']}")
    options = sorted({name for spec in specs if spec.kind == "option" for name in spec.names})
    positionals = [name for spec in specs if spec.kind == "positional" for name in spec.names]
    required: list[str] = []
    for spec in specs:
        if spec.required:
            required.extend(spec.names)
    if specs and any(spec.kind == "option" for spec in specs):
        options = sorted(set(options) | {"-h", "--help"})
    exit_codes = _extract_exit_codes(source or "")
    if help_output:
        exit_codes = sorted(set(exit_codes) | set(_extract_exit_codes(help_output)))
    return Contract(str(tool), str(source_path) if source_path.is_file() else None, method, options, positionals, sorted(set(required)), [asdict(spec) for spec in specs], exit_codes, warnings, help_probe)


def command_arguments(command: Sequence[str]) -> tuple[str, list[str]]:
    """Return the executable/tool token and arguments after a Python script if present."""
    tool_path, index = _script_path(command)
    if index is not None and tool_path is not None:
        return tool_path, list(command[index + 1 :])
    if not command:
        return "", []
    return command[0], list(command[1:])


def inspect_command(command: Sequence[str], timeout: float = 2.0, tool_override: str | None = None) -> tuple[Contract, list[str]]:
    tool, passed = command_arguments(command)
    if tool_override:
        tool = tool_override
    return inspect_tool(tool, timeout=timeout), passed


def unknown_arguments(contract: Contract, passed_args: Sequence[str]) -> list[str]:
    accepted = set(contract.accepted_options)
    unknown: list[str] = []
    for arg in passed_args:
        if not arg.startswith("-") or arg == "-":
            continue
        name = arg.split("=", 1)[0]
        if name == "--":
            continue
        if name.startswith("--"):
            if name not in accepted:
                unknown.append(name)
        elif len(name) == 2 and name not in accepted:
            unknown.append(name)
    return sorted(set(unknown))


def contract_dict(contract: Contract) -> dict[str, Any]:
    return asdict(contract)


def _split_wrapper_args(argv: Sequence[str]) -> tuple[list[str], list[str]]:
    if "--" in argv:
        idx = list(argv).index("--")
        return list(argv[:idx]), list(argv[idx + 1 :])
    return list(argv), []


def main(argv: Sequence[str] | None = None) -> int:
    own, passed = _split_wrapper_args(list(argv if argv is not None else sys.argv[1:]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True, help="مسار الأداة أو اسم الأمر؛ لا تُشغّل العملية العادية")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--probe-help", action="store_true", help="نفّذ --help فقط كمسار آمن قصير")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(own)
    contract = inspect_tool(args.tool, timeout=args.timeout, force_help=args.probe_help)
    unknown = unknown_arguments(contract, passed)
    payload = contract_dict(contract)
    payload["passed_arguments"] = passed
    payload["unknown_arguments"] = unknown
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"عقد الأداة: {contract.tool}")
    print(f"مصدر العقد: {contract.source_method}")
    print("الخيارات المقبولة: " + (", ".join(contract.accepted_options) if contract.accepted_options else "(لم تُستخرج)"))
    print("الوسائط الموضعية: " + (", ".join(contract.accepted_positionals) if contract.accepted_positionals else "(لا يوجد/لم تُستخرج)"))
    print("الوسائط الإلزامية: " + (", ".join(contract.required_arguments) if contract.required_arguments else "(لم تُعلن)"))
    print("أكواد الخروج المعلنة: " + (", ".join(map(str, contract.declared_exit_codes)) if contract.declared_exit_codes else "(لم تُعلن)"))
    if contract.help_probe:
        print(f"فحص --help الآمن: {contract.help_probe}")
    for warning in contract.warnings:
        print("تحذير: " + warning)
    if unknown:
        print("تحذير: وسائط لا يعرفها العقد: " + ", ".join(unknown))
    else:
        print("تحقق الوسائط: لا توجد وسائط غير معروفة")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
