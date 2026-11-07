#!/usr/bin/env python3
"""تشغيل بوابات المخرج وجمع دليل حي قابل للمراجعة."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


class EvidenceError(RuntimeError):
    """خطأ يمنع إصدار دليل ناقص أو مضلل."""


def resolve_arg(value: str, brain: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else brain / path


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.is_file() else "غير موجود"


def find_pdf(brain: Path, day: str) -> Path:
    candidates = [
        brain / "reports" / "pdf" / f"{day}.pdf",
        brain / "reports" / f"{day}.pdf",
        brain / "reports" / "docx" / f"التقرير-اليومي-{day}-طبق-الأصل.pdf",
        brain / "audit" / f"طباعة-{day}.pdf",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise EvidenceError("لم يُعثر على PDF؛ مرّر --pdf صراحة")


def discover_site(brain: Path, explicit: str | None) -> Path:
    if explicit:
        site = Path(explicit).expanduser()
        return site if site.is_absolute() else brain / site
    for candidate in (brain / "site", brain.parent / "seawatch", brain.parent / "site"):
        if candidate.is_dir():
            return candidate
    return brain / "site"


def run_gate(name: str, command: list[str], cwd: Path, env: dict[str, str]) -> dict:
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        status = "PASS" if proc.returncode == 0 else ("WARN" if proc.returncode == 1 else "FAIL")
        return {
            "name": name,
            "command": shlex.join(command),
            "return_code": proc.returncode,
            "status": status,
            "output": output,
        }
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        output += (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return {
            "name": name,
            "command": shlex.join(command),
            "return_code": 70,
            "status": "FAIL",
            "output": output + "\nانتهت المهلة بعد 1800 ثانية",
        }
    except OSError as exc:
        return {
            "name": name,
            "command": shlex.join(command),
            "return_code": 70,
            "status": "FAIL",
            "output": f"تعذر تشغيل البوابة: {type(exc).__name__}: {exc}",
        }


def compact(text: str, limit: int = 700) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else one_line[: limit - 1] + "…"


def main() -> int:
    ap = argparse.ArgumentParser(description="تشغيل أدلة المخرج المقفل")
    ap.add_argument("--brain", required=True, help="جذر المشروع")
    ap.add_argument("--frozen", required=True, help="ملف CSS المقفل")
    ap.add_argument("--profile", required=True, help="ملف profile المقفل")
    ap.add_argument("--date", required=True, help="تاريخ الإصدار YYYY-MM-DD")
    ap.add_argument("--pdf", help="PDF النهائي؛ يُكتشف إن غاب")
    ap.add_argument("--page", help="صفحة HTML المطبوعة لاختبار التأكيد الحي")
    ap.add_argument("--site", help="جذر الموقع لبوابة تغطية الأسطح")
    ap.add_argument("--out-dir", help="مجلد الأدلة؛ الافتراضي logs/approved-output-evidence-<date>")
    args = ap.parse_args()

    try:
        dt.date.fromisoformat(args.date)
    except ValueError as exc:
        raise EvidenceError(f"التاريخ يجب أن يكون YYYY-MM-DD: {args.date}") from exc
    brain = Path(args.brain).expanduser().resolve()
    frozen = resolve_arg(args.frozen, brain)
    profile = resolve_arg(args.profile, brain)
    if not brain.is_dir():
        raise EvidenceError(f"جذر المشروع غير موجود: {brain}")
    for required, label in ((frozen, "القفل"), (profile, "profile")):
        if not required.is_file():
            raise EvidenceError(f"{label} غير موجود: {required}")
    pdf = resolve_arg(args.pdf, brain) if args.pdf else find_pdf(brain, args.date)
    if not pdf.is_file():
        raise EvidenceError(f"PDF غير موجود: {pdf}")
    page = resolve_arg(args.page, brain) if args.page else None
    if page is not None and not page.is_file():
        raise EvidenceError(f"صفحة HTML غير موجودة: {page}")
    site = discover_site(brain, args.site)

    validators = brain / "validators"
    tools = brain / "tools"
    shape = validators / "check_pdf_format.py"
    quality = validators / "check_print_quality.py"
    coverage = tools / "audit_style_coverage.py"
    missing = [str(p) for p in (shape, quality, coverage) if not p.is_file()]
    if missing:
        raise EvidenceError("بوابات مفقودة: " + " · ".join(missing))

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else brain / "logs" / f"approved-output-evidence-{args.date}"
    if not out_dir.is_absolute():
        out_dir = brain / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["BRAIN_DIR"] = str(brain)
    env["SITE_DIR"] = str(site)
    env["SITE"] = str(site)

    commands = [
        ("PDF shape", [sys.executable, str(shape), "--pdf", str(pdf), "--date", args.date]),
        ("print quality", [sys.executable, str(quality), "--pdf", str(pdf), "--date", args.date]),
        ("surface coverage", [sys.executable, str(coverage), "--date", args.date, "--json"]),
    ]
    if page is not None:
        commands[1][1].extend(["--page", str(page)])

    results = [run_gate(name, command, brain, env) for name, command in commands]
    evidence = {
        "kind": "approved-output-change-evidence",
        "date": args.date,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "brain": str(brain),
        "site": str(site),
        "pdf": {"path": str(pdf), "sha16": sha16(pdf)},
        "frozen": {"path": str(frozen), "sha16": sha16(frozen)},
        "profile": {"path": str(profile), "sha16": sha16(profile)},
        "gates": results,
        "status": "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL",
    }
    json_path = out_dir / "evidence.json"
    table_path = out_dir / "evidence.txt"
    json_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    table_lines = [
        f"دليل المخرج المقفل — {args.date}",
        f"PDF: {pdf} · sha16={evidence['pdf']['sha16']}",
        f"CSS: {frozen} · sha16={evidence['frozen']['sha16']}",
        f"profile: {profile} · sha16={evidence['profile']['sha16']}",
        "",
        "command | output | status",
        "--- | --- | ---",
    ]
    for result in results:
        table_lines.append(
            f"{result['command']} | {compact(result['output']).replace('|', '\\|') or '—'} | "
            f"{result['status']} (rc={result['return_code']})"
        )
    table_lines += ["", "تفصيل المخرجات:"]
    for result in results:
        table_lines += [f"\n### {result['name']}\n```text", result["output"].rstrip(), "```"]
    table_path.write_text("\n".join(table_lines) + "\n", encoding="utf-8")

    print(f"دليل JSON: {json_path}")
    print(f"جدول الأدلة: {table_path}")
    print("command | output | status")
    for result in results:
        print(f"{result['command']} | {compact(result['output']) or '—'} | {result['status']} (rc={result['return_code']})")
    print(f"النتيجة: {evidence['status']}")
    return 0 if evidence["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceError as exc:
        print(f"مانع: {exc}")
        raise SystemExit(2)
