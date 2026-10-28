#!/usr/bin/env python3
"""إعادة بناء فهرس الأعطال من سجل Markdown دون تعديل سجل المصدر."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import tempfile
from pathlib import Path


class IndexError(RuntimeError):
    """خطأ يمنع إعلان فهرس ناقص أو غير قابل للقراءة."""


def resolve_arg(value: str, brain: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else brain / path


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def parse_rows(text: str) -> list[dict]:
    rows: list[dict] = []
    pattern = re.compile(r"^(?:ع|ك|ث|م|ز)-\d{2,3}$")
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not pattern.fullmatch(cells[0]):
            continue
        if len(cells) >= 7 and re.fullmatch(r"\d{4}-\d{2}-\d{2}|—|-", cells[1]):
            row = {
                "id": cells[0],
                "date": "" if cells[1] in {"—", "-"} else cells[1],
                "axis": cells[2],
                "symptom": cells[3],
                "cause": cells[4],
                "fix_status": cells[5],
                "status_tail": cells[6],
            }
        elif len(cells) >= 6:
            row = {
                "id": cells[0],
                "date": "",
                "surface": cells[1],
                "symptom": cells[2],
                "cause": cells[3],
                "fix_status": cells[4],
                "status_tail": cells[5],
            }
        else:
            continue
        row["source_line"] = line_no
        status_text = " ".join(str(row.get(k, "")) for k in ("fix_status", "status_tail"))
        row["closed"] = "مغلق" in status_text or "مُغلق" in status_text
        rows.append(row)
    if not rows:
        raise IndexError("لم تُستخرج أي صفوف أعطال من سجل Markdown")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="إعادة بناء فهرس الأعطال")
    ap.add_argument("--brain", required=True, help="جذر المشروع")
    ap.add_argument("--frozen", help="ملف CSS المقفل (اختياري)؛ الافتراضي templates/approved-pdf/print-css-frozen.css")
    ap.add_argument("--profile", help="profile المقفل (اختياري)؛ الافتراضي templates/approved-pdf/print-profile.json")
    ap.add_argument("--fault-log", help="سجل Markdown؛ الافتراضي audit/سجل-الأعطال-والثغرات.md")
    ap.add_argument("--out", help="فهرس JSONL؛ الافتراضي audit/faults-index.jsonl")
    ap.add_argument("--json-out", help="نسخة JSON؛ الافتراضي audit/فهرس-الأعطال.json")
    args = ap.parse_args()

    brain = Path(args.brain).expanduser().resolve()
    frozen = resolve_arg(args.frozen or "templates/approved-pdf/print-css-frozen.css", brain)
    profile = resolve_arg(args.profile or "templates/approved-pdf/print-profile.json", brain)
    if not brain.is_dir():
        raise IndexError(f"جذر المشروع غير موجود: {brain}")
    # فهرس الأعطال لا يُمنع بغياب القفل: يُذكر النقص في المخرج ويُبنى الفهرس (كي لا تُفقد حلقة التعلم)
    for label, path in (("ملف القفل", frozen), ("profile", profile)):
        if not path.is_file():
            print(f"تنبيه: {label} غير موجود ({path}) — بُني الفهرس بلا سياق إصدار")
    fault_log = resolve_arg(args.fault_log or "audit/سجل-الأعطال-والثغرات.md", brain)
    out = resolve_arg(args.out or "audit/faults-index.jsonl", brain)
    json_out = resolve_arg(args.json_out or "audit/فهرس-الأعطال.json", brain)
    if not fault_log.is_file():
        raise IndexError(f"سجل الأعطال غير موجود: {fault_log}")

    rows = parse_rows(fault_log.read_text(encoding="utf-8", errors="replace"))
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    for row in rows:
        row["indexed_utc"] = generated
    jsonl = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    atomic_write(out, jsonl)
    atomic_write(json_out, json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(f"أُعيد بناء فهرس الأعطال: {len(rows)} صفًا")
    print(f"JSONL: {out}")
    print(f"JSON: {json_out}")
    print("النتيجة: فهرس قابل للقراءة ✓")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IndexError as exc:
        print(f"مانع: {exc}")
        raise SystemExit(2)
