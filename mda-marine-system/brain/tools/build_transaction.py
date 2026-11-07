#!/usr/bin/env python3
"""معاملة بناء واحدة: سجّل بصمة النص، ابنِ HTML، ثم تحقّق قبل تحرير القفل."""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from build_lock import BuildLock, BuildLockBusy, default_lock_path


@dataclass
class BuildResult:
    returncode: int
    output: str


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stamp_path(brain: Path, date: str) -> Path:
    return brain / "logs" / f"gate-{date}" / f".text-hash-{date}.json"


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_stamp(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_atomic(
    brain: Path,
    site: Path,
    date: str,
    *,
    build_fn: Callable[[], int],
    lock_timeout: float = 0.0,
) -> BuildResult:
    """نفّذ العملية تحت قفل واحد ولا تسمح بخروج ناجح مع نص متغيّر."""
    brain, site = Path(brain).resolve(), Path(site).resolve()
    report = brain / "reports" / f"{date}-sectioned.md"
    artifact = site / "dist" / "reports" / f"{date}.html"
    lock = BuildLock(default_lock_path(brain), stale_after=3600)
    lines: list[str] = []
    try:
        lock.acquire(timeout=lock_timeout)
    except BuildLockBusy as exc:
        return BuildResult(73, f"✘ رُفض البناء الثاني — {exc}\n")

    try:
        if not report.is_file() or report.stat().st_size == 0:
            return BuildResult(2, f"✘ لا نص نهائي صالح للبناء: {report}\n")
        before = _sha(report)
        stamp = _stamp_path(brain, date)
        recorded = {
            "date": date,
            "md": str(report.relative_to(brain)),
            "sha256": before,
            "mtime": report.stat().st_mtime,
            "recorded_utc": _utc_now(),
            "transaction": "hash-record-build-verify-v1",
            "lock": str(lock.path),
        }
        _write_stamp(stamp, recorded)
        lines.append(f"✔ [1/3] سُجّلت بصمة النص النهائي: {before[:16]}")

        rc = int(build_fn())
        if rc != 0:
            lines.append(f"✘ [2/3] فشل البناء: rc={rc}")
            return BuildResult(rc, "\n".join(lines) + "\n")
        lines.append("✔ [2/3] اكتمل البناء داخل القفل")

        after = _sha(report)
        if after != before:
            lines.append(f"✘ [3/3] نص التقرير تغيّر بعد تسجيل البصمة: {before[:16]} → {after[:16]}")
            lines.append("✘ النص المبني ليس النص النهائي — منع (المعاملة الذرية)")
            return BuildResult(70, "\n".join(lines) + "\n")
        if not artifact.is_file() or artifact.stat().st_size == 0:
            lines.append(f"✘ [3/3] مخرج HTML مفقود أو فارغ: {artifact}")
            return BuildResult(70, "\n".join(lines) + "\n")

        recorded.update({
            "verified_utc": _utc_now(),
            "artifact": str(artifact.relative_to(site)),
            "artifact_sha256": _sha(artifact),
            "artifact_bytes": artifact.stat().st_size,
        })
        _write_stamp(stamp, recorded)
        lines.append(f"✔ [3/3] تطابقت البصمة: {after[:16]} · HTML={artifact.stat().st_size} بايت")
        return BuildResult(0, "\n".join(lines) + "\n")
    finally:
        lock.release()


def _run_site_build(brain: Path, site: Path, date: str, timeout: int) -> int:
    env = dict(os.environ)
    env.update({
        "BRAIN_DIR": str(brain),
        "SITE_DIR": str(site),
        "MARINE_BUILD_LOCK_HELD": "1",
        "MARINE_BUILD_LOCK_PATH": str(default_lock_path(brain)),
    })
    cmd = [sys.executable, str(site / "generator" / "build_site.py"), "--site-root", str(site)]
    try:
        p = subprocess.run(cmd, cwd=site, env=env, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"✘ تجاوز البناء المهلة: {timeout} ثانية")
        return 124
    if p.stdout:
        print(p.stdout, end="")
    if p.stderr:
        print(p.stderr, end="", file=sys.stderr)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="hash → build → verify تحت قفل بناء واحد")
    ap.add_argument("--date", required=True)
    ap.add_argument("--brain", default=os.environ.get("BRAIN_DIR", os.getcwd()))
    ap.add_argument("--site", default=os.environ.get("SITE_DIR"))
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--lock-timeout", type=float, default=0.0)
    a = ap.parse_args()
    brain = Path(a.brain).resolve()
    site = Path(a.site or (brain.parent / "seawatch")).resolve()
    result = run_atomic(
        brain,
        site,
        a.date,
        build_fn=lambda: _run_site_build(brain, site, a.date, a.timeout),
        lock_timeout=a.lock_timeout,
    )
    print(result.output, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
