#!/usr/bin/env python3
"""Classify Python CLI tools without importing or executing them.

The classifier is deliberately conservative. It emits one of four Arabic
categories and a static-only safety decision. It never writes to the scanned
folder, imports a target module, or invokes a subprocess.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


CATEGORIES = ("قراءة فقط", "تكتب ملفات", "تتصل بالشبكة", "تنشر/ترسل/تنسخ")
WRITE_MODES = {"w", "a", "x", "+"}
WRITE_METHODS = {
    "write_text",
    "write_bytes",
    "unlink",
    "remove",
    "rmdir",
    "rmtree",
    "mkdir",
    "makedirs",
    "rename",
    "replace",
    "touch",
    "dump",
    "dumps_to_file",
}
PUBLISH_METHODS = {
    "copy",
    "copy2",
    "copyfile",
    "copytree",
    "move",
    "send",
    "send_message",
    "sendmail",
    "publish",
    "post",
    "put",
    "upload",
    "push",
    "deploy",
    "broadcast",
    "webhook",
}
NETWORK_METHODS = {
    "urlopen",
    "request",
    "connect",
}
NETWORK_MODULES = {
    "aiohttp",
    "boto3",
    "cloudflare",
    "ftplib",
    "grpc",
    "http",
    "httpx",
    "imaplib",
    "mcp",
    "paramiko",
    "playwright",
    "requests",
    "selenium",
    "smtplib",
    "socket",
    "telegram",
    "telnyx",
    "urllib",
    "urllib3",
    "websockets",
}
PUBLISH_MODULES = {
    "boto3",
    "ftplib",
    "git",
    "github",
    "paramiko",
    "shutil",
    "smtplib",
    "telegram",
}
WRITE_OPTION_TOKENS = {
    "apply",
    "commit",
    "copy",
    "create",
    "delete",
    "deploy",
    "execute",
    "fix",
    "force",
    "modify",
    "overwrite",
    "publish",
    "push",
    "remove",
    "repair",
    "replace",
    "rotate",
    "save",
    "send",
    "sync",
    "update",
    "upload",
    "write",
}


def dotted(node: ast.AST | None) -> str:
    """Return a dotted name for a Name/Attribute node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def root_module(name: str) -> str:
    return name.split(".", 1)[0]


def constant_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def option_name(value: str) -> str | None:
    if not value.startswith("--"):
        return None
    return value[2:].split("=", 1)[0].replace("-", "_").lower()


@dataclass
class Evidence:
    imports: set[str] = field(default_factory=set)
    write: list[str] = field(default_factory=list)
    network: list[str] = field(default_factory=list)
    publish: list[str] = field(default_factory=list)
    options: set[str] = field(default_factory=set)
    manual_argv: bool = False
    argparse: bool = False
    parse_args: bool = False
    syntax_error: str | None = None


class Analyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.e = Evidence()
        self._argv_aliases: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            module = root_module(alias.name)
            self.e.imports.add(module)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = root_module(node.module or "")
        self.e.imports.add(module)
        if module == "sys":
            for alias in node.names:
                if alias.name == "argv":
                    self._argv_aliases.add(alias.asname or alias.name)
                    self.e.manual_argv = True
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == "argv" and dotted(node.value) == "sys":
            self.e.manual_argv = True
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in self._argv_aliases:
            self.e.manual_argv = True

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            option = option_name(node.value)
            if option:
                self.e.options.add(option)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = dotted(node.func)
        short = name.rsplit(".", 1)[-1] if name else ""
        module = root_module(name)

        if module == "argparse" or name.endswith("ArgumentParser"):
            self.e.argparse = True
        if short in {"parse_args", "parse_known_args"}:
            self.e.parse_args = True

        if short == "open" or name in {"io.open", "builtins.open"}:
            mode = None
            if len(node.args) >= 2:
                mode = constant_string(node.args[1])
            for keyword in node.keywords:
                if keyword.arg == "mode":
                    mode = constant_string(keyword.value)
            if mode and any(marker in mode for marker in WRITE_MODES):
                self.e.write.append(f"{name or 'open'}(mode={mode!r})")

        if short in WRITE_METHODS or name in {"json.dump", "yaml.dump"}:
            self.e.write.append(name or short)
        publish_call = short in PUBLISH_METHODS and (
            module in PUBLISH_MODULES
            or short in {"publish", "send_message", "sendmail", "upload", "push", "deploy", "broadcast", "webhook"}
        )
        if publish_call or module in PUBLISH_MODULES:
            self.e.publish.append(name or short)
        network_call = short in NETWORK_METHODS and (module in NETWORK_MODULES or short == "urlopen")
        if network_call or module in NETWORK_MODULES:
            self.e.network.append(name or short)
        if module == "subprocess" or short in {"system", "popen"}:
            self.e.publish.append(name or short)
        if short in {"execute", "executemany", "executescript"}:
            sql = constant_string(node.args[0]) if node.args else None
            if sql and sql.lstrip().lower().startswith(
                ("insert", "update", "delete", "replace", "create", "drop", "alter")
            ):
                self.e.write.append(f"{short}(SQL mutation)")

        self.generic_visit(node)


def option_gate(evidence: Evidence) -> str | None:
    for option in sorted(evidence.options):
        if option in WRITE_OPTION_TOKENS:
            return f"--{option.replace('_', '-')}"
    return None


def analyze(path: Path) -> dict[str, object]:
    evidence = Evidence()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        analyzer = Analyzer()
        analyzer.visit(tree)
        evidence = analyzer.e
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        evidence.syntax_error = f"AST غير متاح: {type(exc).__name__}: {exc}"

    if evidence.publish or any(module in PUBLISH_MODULES for module in evidence.imports):
        category = "تنشر/ترسل/تنسخ"
    elif evidence.network or any(module in NETWORK_MODULES for module in evidence.imports):
        category = "تتصل بالشبكة"
    elif evidence.write:
        category = "تكتب ملفات"
    else:
        category = "قراءة فقط"

    gate = option_gate(evidence)
    write_without_gate = bool(evidence.write) and gate is None
    interface = (
        "sys.argv يدوي"
        if evidence.manual_argv
        else "argparse/parse_args"
        if evidence.argparse and evidence.parse_args
        else "واجهة غير مثبتة"
    )
    unsafe = bool(
        evidence.syntax_error
        or evidence.manual_argv
        or interface == "واجهة غير مثبتة"
        or category != "قراءة فقط"
        or write_without_gate
    )

    reasons: list[str] = []
    if evidence.syntax_error:
        reasons.append(evidence.syntax_error)
    if evidence.manual_argv:
        reasons.append("قراءة sys.argv يدوية")
    if evidence.write:
        reasons.append("كتابة: " + ", ".join(sorted(set(evidence.write))))
    if evidence.network:
        reasons.append("شبكة: " + ", ".join(sorted(set(evidence.network))))
    if evidence.publish:
        reasons.append("نشر/إرسال/نسخ: " + ", ".join(sorted(set(evidence.publish))))
    if gate:
        reasons.append(f"خيار تشغيل صريح: {gate}")
    if write_without_gate:
        reasons.append("كتابة بلا خيار تشغيل صريح")
    if not reasons:
        reasons.append("لا أثر محظور ظاهر في AST")
    reasons.append("استدلال ساكن لا قياس حي")

    return {
        "path": str(path),
        "category": category,
        "interface": interface,
        "reason": "; ".join(reasons),
        "unsafe": unsafe,
        "write_without_gate": write_without_gate,
    }


def iter_python_files(directory: Path) -> Iterable[Path]:
    excluded_dirs = {"__pycache__", "_oneoff", "archive", "archives", "logs", "backups"}
    yield from sorted(
        path
        for path in directory.rglob("*.py")
        if not excluded_dirs.intersection(path.parts) and path.is_file()
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="صنّف أدوات Python ساكنًا دون استيرادها أو تشغيلها أو الكتابة في مسارها."
    )
    parser.add_argument("directory", help="مسار مجلد الأدوات المراد قراءته ساكنًا")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    directory = Path(args.directory).expanduser()
    if not directory.is_dir():
        parser.error(f"المجلد غير موجود أو ليس مجلدًا: {directory}")

    print("النطاق: ملفات Python؛ استبعاد _oneoff و__pycache__ والأرشيفات والسجلات والنسخ الاحتياطية (استدلال ساكن).")
    records = [analyze(path) for path in iter_python_files(directory)]
    print("المسار | الفئة | عقد الواجهة | الحكم | دليل ساكن")
    print("--- | --- | --- | --- | ---")
    for record in records:
        decision = "غير آمنة للفحص" if record["unsafe"] else "آمنة ساكنًا للفحص الحي"
        print(
            f"{record['path']} | {record['category']} | {record['interface']} | "
            f"{decision} | {record['reason']}"
        )

    counts = {category: 0 for category in CATEGORIES}
    for record in records:
        counts[record["category"]] += 1
    print("\nالملخص الساكن (لا يعني قياسًا حيًا):")
    print("؛ ".join(f"{category}: {counts[category]}" for category in CATEGORIES))
    unsafe_count = sum(1 for record in records if record["unsafe"])
    write_gate_count = sum(1 for record in records if record["write_without_gate"])
    print(f"غير آمنة للفحص: {unsafe_count}; كتابة بلا خيار صريح: {write_gate_count}")

    return 1 if unsafe_count or write_gate_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
