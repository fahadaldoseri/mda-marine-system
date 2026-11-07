#!/usr/bin/env python3
"""قفل بناء single-flight مشترك بين مغلف البناء ومولّد الموقع."""
from __future__ import annotations

import datetime as _dt
import errno
import json
import os
import shlex
import time
from pathlib import Path


class BuildLockBusy(RuntimeError):
    """يوجد بناء آخر حي أو قفل غير قابل للاسترداد."""


class BuildLock:
    def __init__(self, path: str | Path, *, stale_after: float = 3600.0):
        self.path = Path(path)
        self.owner_path = self.path / "owner.json"
        self.stale_after = float(stale_after)
        self._held = False

    @staticmethod
    def _alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _owner(self) -> dict:
        try:
            return json.loads(self.owner_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}

    def _owner_text(self) -> str:
        owner = self._owner()
        pid = owner.get("pid", "?")
        started = owner.get("started_utc", "وقت غير معروف")
        return f"بناء جارٍ: pid={pid} بدأ={started} القفل={self.path}"

    def _reclaim_if_dead(self) -> bool:
        owner = self._owner()
        try:
            pid = int(owner.get("pid", 0))
        except (TypeError, ValueError):
            pid = 0
        if pid and self._alive(pid):
            return False
        # لا نحذف إلا ما داخل دليل القفل؛ ثم نزيل الدليل نفسه. وجود مالك حي
        # يُرفض أعلاه، أما مالك ميت فيُسترد في المحاولة التالية بأمان.
        try:
            self.owner_path.unlink(missing_ok=True)
            self.path.rmdir()
            return True
        except OSError as exc:
            if exc.errno in (errno.ENOENT, errno.ENOTEMPTY):
                return True
            return False

    def acquire(self, timeout: float = 0.0, poll: float = 0.05) -> "BuildLock":
        deadline = time.monotonic() + max(0.0, float(timeout))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.path.mkdir()
            except FileExistsError:
                if self._reclaim_if_dead():
                    continue
                if time.monotonic() >= deadline:
                    raise BuildLockBusy(self._owner_text())
                time.sleep(min(poll, max(0.0, deadline - time.monotonic())))
                continue
            owner = {
                "pid": os.getpid(),
                "ppid": os.getppid(),
                "started_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "started_epoch": time.time(),
                "stale_after_seconds": self.stale_after,
                "command": shlex.join(os.sys.argv),
            }
            try:
                self.owner_path.write_text(json.dumps(owner, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            except Exception:
                self.path.rmdir()
                raise
            self._held = True
            return self

    def assert_owned_by_self_or_parent(self) -> None:
        owner = self._owner()
        try:
            pid = int(owner.get("pid", 0))
        except (TypeError, ValueError):
            pid = 0
        if pid not in {os.getpid(), os.getppid()} or not self._alive(pid):
            raise BuildLockBusy(f"قفل البناء غير مملوك للعملية الحالية: {self.path}")

    def release(self) -> None:
        if not self._held:
            return
        self._held = False
        try:
            self.owner_path.unlink(missing_ok=True)
            self.path.rmdir()
        except OSError as exc:
            if exc.errno != errno.ENOENT:
                raise

    def __enter__(self) -> "BuildLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def default_lock_path(brain: str | Path) -> Path:
    return Path(brain) / "logs" / "build-site.lock"
