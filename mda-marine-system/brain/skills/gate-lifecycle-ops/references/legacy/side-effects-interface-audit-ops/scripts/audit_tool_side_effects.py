#!/usr/bin/env python3
"""Static audit of a Python tool's file side effects and CLI surface.

The target is read as text and parsed with AST; it is never imported or run.
Exit 1 means at least one write is not visibly guarded by a write-control option.
Exit 2 means the audit input cannot be read or parsed.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

WRITE_METHODS = {
    "write_text", "write_bytes", "mkdir", "touch", "unlink", "rmdir",
    "rename", "write", "writelines",
}
OS_WRITE_FUNCTIONS = {"makedirs", "mkdir", "remove", "unlink", "rename", "replace", "rmdir"}
COPY_FUNCTIONS = {"copy", "copy2", "copyfile", "copytree", "move"}
WRITE_FLAGS = {
    "--apply", "--write", "--in-place", "--dry-run", "--check", "--plan",
    "--read-only", "--no-write",
}


def dotted(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return type(node).__name__


def constant_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def option_name(node: ast.AST) -> str | None:
    value = constant_string(node)
    return value if value and value.startswith("--") else None


def is_write_mode(mode: str | None) -> bool:
    return bool(mode and any(flag in mode for flag in "wax+"))


def likely_path_receiver(node: ast.AST) -> bool:
    """Avoid counting str.replace(); accept Path-like expressions conservatively."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return True
    if isinstance(node, ast.Call):
        return dotted(node.func).split(".")[-1] in {"Path", "PurePath"}
    if isinstance(node, ast.Name):
        lowered = node.id.lower()
        return node.id.isupper() or any(token in lowered for token in ("path", "file", "out", "dir", "dest"))
    if isinstance(node, ast.Attribute):
        return likely_path_receiver(node.value)
    return False


class StaticAudit(ast.NodeVisitor):
    def __init__(self) -> None:
        self.uses_argparse = False
        self.uses_manual_argv = False
        self.parser_has_default_help = False
        self.parser_has_parse = False
        self.uses_parse_known_args = False
        self.parse_lines: list[int] = []
        self.gate_dests: set[str] = set()
        self.options: list[str] = []
        self.writes: list[dict[str, object]] = []
        self._guards: list[bool] = []

    def visit_Import(self, node: ast.Import) -> None:
        if any(alias.name == "argparse" for alias in node.names):
            self.uses_argparse = True
        if any(alias.name == "sys" for alias in node.names):
            # A separate visit of sys.argv below identifies actual use.
            pass
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "argparse":
            self.uses_argparse = True
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == "argv" and isinstance(node.value, ast.Name) and node.value.id == "sys":
            self.uses_manual_argv = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
        full = dotted(node.func)
        if name == "ArgumentParser" or full.endswith(".ArgumentParser"):
            self.uses_argparse = True
            add_help = next((kw.value for kw in node.keywords if kw.arg == "add_help"), None)
            self.parser_has_default_help = add_help is None or add_help.value is True if isinstance(add_help, ast.Constant) else add_help is None
        if name in {"parse_args", "parse_known_args"}:
            self.parser_has_parse = True
            self.uses_parse_known_args = name == "parse_known_args"
            if hasattr(node, "lineno"):
                self.parse_lines.append(node.lineno)
        if name == "add_argument":
            flags = [option_name(arg) for arg in node.args]
            flags = [flag for flag in flags if flag]
            self.options.extend(flags)
            if any(flag in WRITE_FLAGS for flag in flags):
                dest = next((kw.value.value for kw in node.keywords if kw.arg == "dest" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)), None)
                self.gate_dests.add(dest or flags[0][2:].replace("-", "_"))
        record = self._write_record(node, name, full)
        if record is not None:
            self.writes.append(record)
        self.generic_visit(node)

    def _write_record(self, node: ast.Call, name: str, full: str) -> dict[str, object] | None:
        target: ast.AST | None = None
        kind = ""
        if name in WRITE_METHODS:
            target = node.func.value if isinstance(node.func, ast.Attribute) else None
            kind = f".{name}()"
        elif name == "replace":
            if not isinstance(node.func, ast.Attribute) or not likely_path_receiver(node.func.value):
                return None
            target = node.func.value
            kind = ".replace()"
        elif name == "open":
            mode_node = node.args[1] if len(node.args) > 1 else next((kw.value for kw in node.keywords if kw.arg == "mode"), None)
            mode = constant_string(mode_node)
            if not is_write_mode(mode):
                return None
            target = node.args[0] if node.args else None
            kind = f"open(mode={mode!r})"
        elif name in OS_WRITE_FUNCTIONS:
            target = node.args[-1] if name in {"rename", "replace"} and node.args else (node.args[0] if node.args else None)
            kind = f"{full}()"
        elif name in COPY_FUNCTIONS:
            target = node.args[-1] if node.args else None
            kind = f"{full}()"
        else:
            return None
        if name in {"write", "writelines"} and isinstance(target, ast.Name) and target.id in {"stdout", "stderr"}:
            return None
        return {
            "line": getattr(node, "lineno", 0),
            "kind": kind,
            "target": dotted(target) if target is not None else "مسار غير مستنتج",
            "guarded": bool(self._guards),
        }

    def _gate_in_test(self, test: ast.AST) -> bool:
        text = dotted(test)
        if any(flag in text for flag in WRITE_FLAGS):
            return True
        for item in ast.walk(test):
            if isinstance(item, ast.Name) and item.id in self.gate_dests:
                return True
            if isinstance(item, ast.Attribute) and item.attr in self.gate_dests:
                return True
        return False

    def visit_If(self, node: ast.If) -> None:
        guarded = self._gate_in_test(node.test)
        self._guards.append(guarded or bool(self._guards))
        for child in node.body:
            self.visit(child)
        self._guards.pop()
        self._guards.append(guarded or bool(self._guards))
        for child in node.orelse:
            self.visit(child)
        self._guards.pop()


def help_verdict(audit: StaticAudit) -> tuple[str, str]:
    if not audit.uses_argparse:
        if audit.uses_manual_argv:
            return "لا", "لا يوجد محلّل --help؛ ستُعامل الكلمة كوسيط يدوي أو مسار."
        return "لا", "لم تُكتشف واجهة argparse أو معالج --help."
    if not audit.parser_has_default_help:
        return "لا", "ArgumentParser معطّل فيه help أو لم يُثبت افتراضيه."
    if not audit.parser_has_parse:
        return "لا", "لم تُكتشف نقطة parse_args/parse_known_args."
    first_write = min((int(item["line"]) for item in audit.writes), default=None)
    first_parse = min(audit.parse_lines, default=None)
    if first_write is not None and first_parse is not None and first_write < first_parse:
        return "لا", f"توجد كتابة في السطر {first_write} قبل تحليل الوسائط في السطر {first_parse}."
    return "نعم", "استدلال ساكن: help افتراضي وparse_args قبل أول كتابة مكتشفة؛ لا يشغّل السكربت."


def unknown_argument_verdict(audit: StaticAudit) -> tuple[str, str]:
    if not audit.uses_argparse or not audit.parser_has_parse:
        return "لا", "لا يوجد parse_args يثبت رفض الوسيط غير المعروف."
    if audit.uses_parse_known_args:
        return "لا", "استُخدم parse_known_args؛ قبول الوسيط غير المعروف غير مرفوض ساكنًا."
    return "نعم", "parse_args يرفض الوسيط غير المعروف افتراضيًا (رمز 2)."


def run(path: Path) -> int:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        print(f"خطأ في قراءة/تحليل الأداة: {type(exc).__name__}: {exc}")
        return 2
    audit = StaticAudit()
    audit.visit(tree)
    help_ok, help_note = help_verdict(audit)
    unknown_ok, unknown_note = unknown_argument_verdict(audit)
    unguarded = [item for item in audit.writes if not item["guarded"]]
    print(f"الأداة: {path}")
    print(f"argparse؟ {'نعم' if audit.uses_argparse else 'لا'}")
    print(f"sys.argv يدويًا؟ {'نعم' if audit.uses_manual_argv else 'لا'}")
    print(f"تكتب ملفات/تغيّر مسارات؟ {'نعم' if audit.writes else 'لا'}")
    if audit.options:
        print("الخيارات المكتشفة: " + ", ".join(sorted(set(audit.options))))
    if audit.writes:
        print("مسارات/عمليات الكتابة المكتشفة:")
        for item in audit.writes:
            guard = "محروسة بخيار صريح" if item["guarded"] else "بلا خيار صريح"
            print(f"  السطر {item['line']}: {item['kind']} ← {item['target']} [{guard}]")
    print(f"--help آمن؟ {help_ok} ({help_note})")
    print(f"المعطى غير المعروف يخرج 2 بلا تنفيذ؟ {unknown_ok} ({unknown_note})")
    print(f"كتابة بلا خيار صريح؟ {'نعم' if unguarded else 'لا'}")
    if unguarded:
        print("النتيجة: منع الاعتماد — أصلح الكتابة أو ضعها خلف خيار صريح ثم أعد القياس.")
        return 1
    print("النتيجة: لا كتابة غير محروسة مكتشفة ساكنًا؛ أكمل اختبار القراءة فقط والمخرج الحرفي.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="فحص ساكن لآثار أداة Python وواجهة CLI")
    parser.add_argument("tool", type=Path, help="مسار ملف Python المراد قراءته ساكنًا")
    args = parser.parse_args()
    if not args.tool.is_file():
        print(f"الملف غير موجود أو ليس ملفًا عاديًا: {args.tool}")
        return 2
    return run(args.tool)


if __name__ == "__main__":
    raise SystemExit(main())
