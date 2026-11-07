#!/usr/bin/env python3
"""تشغيل runbook.py run بأمان لتاريخ واحد، مع منع التوازي وقراءة سجل المنع."""
from __future__ import annotations

import argparse
import datetime as _dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STEP_RE = re.compile(r"▶\s*([A-Za-z0-9_-]+)\s+—")
PID_RE = re.compile(r"(?:pid|PID)\s*[:=]\s*(\d+)")
SECRET_RE = re.compile(
    r"(?i)(\b(?:bot[_-]?token|telegram[_-]?token|api[_-]?key|secret|password|authorization)\b\s*[:=]\s*)\S+"
)


def _redact(text: str) -> str:
    """أخفِ القيم الشبيهة بالأسرار قبل طباعتها؛ لا تغيّر أسماء الخطوات العربية."""
    return SECRET_RE.sub(r"\1[مخفي]", text)


def _date_arg(value: str) -> str:
    if not DATE_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("يجب أن يكون التاريخ بصيغة YYYY-MM-DD")
    try:
        _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("التاريخ غير صالح") from exc
    return value


def _proc_cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (FileNotFoundError, PermissionError, OSError):
        return []
    return [p.decode("utf-8", "replace") for p in raw.split(b"\0") if p]


def _proc_cwd(pid: int) -> str | None:
    try:
        return os.path.realpath(f"/proc/{pid}/cwd")
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _arg_value(args: list[str], name: str) -> str | None:
    for i, arg in enumerate(args):
        if arg == name and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return None


def _running_processes(brain: Path, date: str) -> list[str]:
    """ابحث في /proc عن runbook.py أو سائق آخر لنفس الجذر والتاريخ."""
    hits: list[str] = []
    current = os.getpid()
    brain_s = str(brain)
    try:
        pids: Iterable[str] = (p for p in os.listdir("/proc") if p.isdigit())
    except OSError:
        return hits
    for raw_pid in pids:
        pid = int(raw_pid)
        if pid == current:
            continue
        cmd = _proc_cmdline(pid)
        if not cmd:
            continue
        joined = " ".join(cmd)
        if not ("runbook.py" in joined or "runbook_driver.py" in joined):
            continue
        if _arg_value(cmd, "--date") != date:
            continue
        root_arg = _arg_value(cmd, "--root") or _arg_value(cmd, "--brain")
        cwd = _proc_cwd(pid)
        same_root = root_arg and os.path.realpath(root_arg) == brain_s
        same_root = bool(same_root or cwd == brain_s)
        if same_root:
            hits.append(f"عملية قائمة PID={pid}")
    return hits


def _project_lock_markers(brain: Path, date: str) -> list[str]:
    """اقرأ مؤشرات القفل/العملية الموجودة مسبقًا دون إنشاء أي ملف في المشروع."""
    candidates = [
        brain / ".runbook.lock",
        brain / f".runbook-{date}.lock",
        brain / "runbook" / f"{date}.lock",
        brain / "runbook" / f".{date}.lock",
        brain / "logs" / "runbook" / f"{date}.lock",
        brain / "logs" / "runbook" / f"{date}.pid",
        brain / "logs" / "runbook" / f"{date}.run.lock",
        brain / "logs" / "runbook" / date / ".lock",
    ]
    active: list[str] = []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:4096]
        except OSError:
            active.append(str(path))
            continue
        pid_match = PID_RE.search(text)
        if pid_match:
            pid = int(pid_match.group(1))
            if _proc_cmdline(pid):
                active.append(str(path))
            # مؤشر قديم بلا عملية حية لا يحجب القفل الذري للسائق.
        else:
            # محتوى قفل غير قابل للإسناد: فشل مغلق بدل التخمين بأنه قديم.
            active.append(str(path))
    return active


def _lock_path(brain: Path, date: str) -> Path:
    skill_root = Path(__file__).resolve().parents[1]
    lock_dir = skill_root / ".locks"
    lock_dir.mkdir(mode=0o700, exist_ok=True)
    digest = hashlib.sha256(f"{brain}\0{date}".encode("utf-8")).hexdigest()[:24]
    return lock_dir / f"{digest}.lock"


def _acquire_lock(path: Path, brain: Path, date: str):
    handle = path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(
        json.dumps(
            {
                "pid": os.getpid(),
                "brain": str(brain),
                "date": date,
                "started_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            },
            ensure_ascii=True,
        )
        + "\n"
    )
    handle.flush()
    return handle


def _latest_step_from_ledger(brain: Path, date: str) -> str | None:
    path = brain / "logs" / "runbook" / f"{date}.jsonl"
    latest: dict[str, dict] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("step"):
            latest[str(item["step"])] = item
    for item in reversed(latest.values()):
        if item.get("status") in {"failed", "waiting_agent"}:
            return str(item.get("step"))
    return None


def _tail_log(brain: Path, date: str, step: str, count: int = 40) -> str | None:
    path = brain / "logs" / "runbook" / date / f"{step}.log"
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"تعذّر قراءة السجل: {exc.__class__.__name__}"
    return "\n".join(lines[-count:]) if lines else "(السجل فارغ)"


def _print_result(brain: Path, date: str, returncode: int, output: str) -> None:
    if output:
        rendered = _redact(output)
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    step_match = STEP_RE.search(output)
    step = step_match.group(1) if step_match else _latest_step_from_ledger(brain, date)
    if returncode == 0:
        print("الخطوة التالية: لا توجد؛ اكتمل التشغيل وفق السجل.")
    elif returncode == 10:
        print(f"الخطوة التالية المطلوبة: {step or 'خطوة agent غير معروفة'}.")
        print("نفّذ الـ prompt المطبوع وحده، ثم complete للخطوة نفسها، ثم أعد run.")
    elif returncode == 2:
        print(f"الخطوة المانعة: {step or 'غير محددة'}.")
        if step:
            tail = _tail_log(brain, date, step)
            if tail is None:
                print("سجل الخطوة: غير موجود؛ لا تخمّن السبب.")
            else:
                print(f"آخر 40 سطرًا من logs/runbook/{date}/{step}.log:")
                print(_redact(tail))
        print("فشل مغلق: توقف؛ لا نشر ولا Telegram ولا نسخة احتياطية.")
    else:
        print(f"كود غير معياري: {returncode}. اقرأ المخرج الحرفي وسجل الخطوة قبل أي تخمين.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain", required=True, type=Path, help="جذر مشروع مركز الوعي بالمجال البحري")
    parser.add_argument("--date", required=True, type=_date_arg)
    args = parser.parse_args()
    brain = args.brain.expanduser().resolve()
    date = args.date
    if not brain.is_dir():
        print("✘ منع مغلق: جذر المشروع غير موجود.", file=sys.stderr)
        return 2
    if not (brain / "runbook" / "runbook.json").is_file() or not (brain / "tools" / "runbook.py").is_file():
        print("✘ منع مغلق: المانيفست أو محرّك الكتيب غير موجود.", file=sys.stderr)
        return 2

    process_hits = _running_processes(brain, date)
    marker_hits = _project_lock_markers(brain, date)
    if process_hits or marker_hits:
        print("✘ منع مغلق: يوجد تشغيل أو قفل قائم لنفس التاريخ؛ لم يُشغّل runbook.", file=sys.stderr)
        for hit in process_hits:
            print(f"  {hit}", file=sys.stderr)
        for hit in marker_hits:
            print(f"  مؤشر قفل: {Path(hit).name}", file=sys.stderr)
        return 2

    lock_path = _lock_path(brain, date)
    handle = _acquire_lock(lock_path, brain, date)
    if handle is None:
        print("✘ منع مغلق: سائق آخر يمسك قفل التاريخ؛ لم يُشغّل runbook.", file=sys.stderr)
        return 2
    try:
        # أعد الفحص بعد القفل الذري لالتقاط عملية بدأت بين الفحص الأول والقفل.
        process_hits = _running_processes(brain, date)
        if process_hits:
            print("✘ منع مغلق: ظهرت عملية لنفس التاريخ بعد أخذ القفل؛ لم يُشغّل runbook.", file=sys.stderr)
            for hit in process_hits:
                print(f"  {hit}", file=sys.stderr)
            return 2
        completed = subprocess.run(
            [sys.executable, "tools/runbook.py", "run", "--date", date, "--root", str(brain)],
            cwd=str(brain),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        _print_result(brain, date, completed.returncode, output)
        return completed.returncode if completed.returncode >= 0 else 1
    except OSError as exc:
        print(f"✘ عطل تشغيل: {exc.__class__.__name__}: {_redact(str(exc))}", file=sys.stderr)
        return 2
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            # لا نُحوّل نجاح التشغيل إلى نجاح كاذب؛ يبقى القفل في الدليل ليُفحص لاحقًا.
            pass


if __name__ == "__main__":
    raise SystemExit(main())
