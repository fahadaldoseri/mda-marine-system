#!/usr/bin/env python3
"""تحويل المسارات المطلقة المثبّتة إلى مسارات محمولة (تعمل من أي جهاز).

القاعدة:
- الجذر الافتراضي يُستنتج من موقع الملف نفسه: BRAIN = جذر شجرة النظام، SITE = جذر شجرة الموقع.
- يمكن تجاوزهما بمتغيّري البيئة BRAIN_DIR و SITE_DIR.
- كل نص حرفي يبدأ بالمسار المطلق يُحوَّل إلى f-string يستعمل {BRAIN} أو {SITE}.

الاستخدام:
    python3 tools/portable_paths.py            # معاينة فقط (dry-run)
    python3 tools/portable_paths.py --apply    # التنفيذ
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

HOME = Path("/home/ubuntu")
TREES = {
    "BRAIN": HOME / "brain-marine-news",
    "SITE": HOME / "seawatch",
}
SKIP_PARTS = {"brain-backup", "__pycache__", "_oneoff", "legacy-local-server", "legacy-2026-10", "shots"}
SKIP_FILES = {"portable_paths.py"}
MARK = "# ── مسارات النظام: محمولة"

TREE_DIRNAMES = {"BRAIN": ("brain-marine-news", "brain"), "SITE": ("seawatch", "site")}

HELPER = """
def _tree(_env, _base, *_names):
    \"\"\"جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق.\"\"\"
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
"""


def build_header(own: str, other: str | None, used: set[str], depth: int) -> str:
    """ترويسة المسارات: الجذر المحلّي من موقع الملف، والمجاورة من متغيّر أو مجلد شقيق."""
    lines = [
        f"{MARK} (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──",
        "import os as _os",
        "from pathlib import Path as _Path",
        f"_ROOT = _Path(__file__).resolve().parents[{depth}]",
    ]
    if own in used:
        lines.append(f'{own} = _Path(_os.environ.get("{own}_DIR") or _ROOT)')
    if other and other in used:
        lines += HELPER.rstrip("\n").split("\n")
        lines.append(f'{other} = _tree("{other}_DIR", _ROOT, "{TREE_DIRNAMES[other][0]}", "{TREE_DIRNAMES[other][1]}")')
    return "\n".join(lines) + "\n"


def depth_from(root: Path, path: Path) -> int:
    """عدد مستويات المجلدات بين الجذر والملف."""
    rel = path.resolve().relative_to(root.resolve())
    return max(len(rel.parts) - 1, 0)


def default_expr(var: str, depth: int) -> str:
    literal = TREES[var].as_posix()
    parents = "_Path(__file__).resolve().parents[{d}]".format(d=depth)
    return (
        f'{var} = _Path(_os.environ.get("{var}_DIR") or {parents})\n'
        f'# الافتراضي عند التشغيل من خارج الشجرة: {literal}'
    )


def insert_line(text: str, var: str, depth: int) -> int | None:
    """سطر الإدراج بعد الترويسة والوثيقة ومستوردات __future__."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    line = 0
    if text.startswith("#!"):
        line = 1
    body = tree.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        line = max(line, body[0].end_lineno or line)
    for node in body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            line = max(line, node.end_lineno or line)
    return line


def transform_literals(text: str, used: set[str]) -> tuple[str, list[str], int]:
    """تحويل النصوص الحرفية الحاوية للمسار إلى f-strings."""
    skipped: list[str] = []
    out_lines = []
    changed = 0
    for raw in text.splitlines(keepends=True):
        stripped = raw.lstrip()
        if stripped.startswith("#"):
            out_lines.append(raw)
            continue
        new = raw
        for var, root in TREES.items():
            lit = root.as_posix()
            # نصوص مفردة أو مزدوجة على سطر واحد
            for q in ('"', "'"):
                pattern = re.compile(r"(?P<pfx>[fF]?)" + q + r"(?P<body>[^" + q + r"\n]*)" + q)

                def repl(m: re.Match) -> str:
                    nonlocal changed
                    body = m.group("body")
                    if lit not in body:
                        return m.group(0)
                    if "{" in body or "}" in body:
                        skipped.append(f"{q}{body}{q} (يحوي أقواسًا معقوفة)")
                        return m.group(0)
                    used.add(var)
                    changed += 1
                    return "f" + q + body.replace(lit, "{" + var + "}") + q

                new = pattern.sub(repl, new)
        out_lines.append(new)
    return "".join(out_lines), skipped, changed


def process(path: Path, apply: bool) -> dict:
    text = path.read_text(encoding="utf-8")
    if MARK in text:
        return {"file": path, "status": "مُحوَّل سابقًا", "changed": 0, "skipped": []}
    used: set[str] = set()
    new_text, skipped, changed = transform_literals(text, used)
    if not used:
        return {"file": path, "status": "لا مسار مطلق", "changed": 0, "skipped": skipped}
    own = "BRAIN" if TREES["BRAIN"].resolve() in path.resolve().parents else "SITE"
    other = "SITE" if own == "BRAIN" else "BRAIN"
    depth = depth_from(TREES[own], path)
    ln = insert_line(new_text, own, depth)
    if ln is None:
        return {"file": path, "status": "فشل التحليل", "changed": 0, "skipped": skipped}
    lines = new_text.splitlines(keepends=True)
    lines[ln:ln] = build_header(own, other, used, depth).splitlines(keepends=True)
    new_text = "".join(lines)
    try:
        ast.parse(new_text)
    except SyntaxError as exc:
        return {"file": path, "status": f"خطأ صياغة بعد التحويل: {exc}", "changed": 0, "skipped": skipped}
    if apply:
        path.write_text(new_text, encoding="utf-8")
    return {"file": path, "status": "جاهز", "changed": changed, "skipped": skipped}


def main() -> int:
    apply = "--apply" in sys.argv
    files: list[Path] = []
    for root in TREES.values():
        for p in root.rglob("*.py"):
            if any(part in SKIP_PARTS for part in p.parts) or p.name in SKIP_FILES:
                continue
            if "/home/ubuntu/brain-marine-news" in p.read_text(encoding="utf-8", errors="ignore") \
                    or "/home/ubuntu/seawatch" in p.read_text(encoding="utf-8", errors="ignore"):
                files.append(p)
    files.sort()
    total_changed = 0
    problems: list[str] = []
    skipped_all: list[str] = []
    for p in files:
        res = process(p, apply)
        total_changed += res["changed"]
        skipped_all += [f"{p.relative_to(HOME)} :: {s}" for s in res["skipped"]]
        if res["status"] not in ("جاهز", "مُحوَّل سابقًا", "لا مسار مطلق"):
            problems.append(f"{p.relative_to(HOME)} — {res['status']}")
        elif res["changed"]:
            print(f"  {'✎' if apply else '·'} {p.relative_to(HOME)} — {res['changed']} نصًّا")
    print(f"\nالملفات المفحوصة: {len(files)} · النصوص المحوَّلة: {total_changed} · الوضع: "
          f"{'تنفيذ' if apply else 'معاينة'}")
    if problems:
        print("\nمشكلات:")
        for x in problems:
            print("  ✘", x)
    if skipped_all:
        print(f"\nنصوص تُركت بلا تحويل ({len(skipped_all)}):")
        for x in skipped_all[:10]:
            print("  ⚠", x)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
