#!/usr/bin/env python3
"""عقد الجذر الصريح: موجب مع --root، وسالب للجذر المفقود أو المخالف."""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ENGINE = pathlib.Path(__file__).resolve().parents[1] / "tools" / "runbook.py"
ROOT = ENGINE.parents[1]


def run(*args: str, cwd: str = "/tmp") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ENGINE), *args], cwd=cwd, capture_output=True, text=True
    )


def main() -> int:
    ok = True

    # من /tmp لا يوجد مانيفست في cwd أو آبائه؛ العقد الصريح لا يخمّن الجذر من
    # موضع ملف المحرّك، لذلك غياب --root حالة سالبة ويجب أن يفشل مغلقًا.
    noflag = run("status", "--date", "2026-11-07")
    print("NEGATIVE_NOFLAG_CMD=python3 <engine> status --date 2026-11-07  (cwd=/tmp بلا --root)")
    print(f"NEGATIVE_NOFLAG_RC={noflag.returncode}")
    ok &= noflag.returncode == 2

    explicit = run("status", "--date", "2026-11-07", "--root", str(ROOT))
    print(f"POSITIVE_EXPLICIT_RC={explicit.returncode}")
    ok &= explicit.returncode == 0

    wrong = run("status", "--date", "2026-11-07", "--root", "/tmp")
    print("NEGATIVE_WRONG_CMD=python3 <engine> status --date 2026-11-07 --root /tmp")
    print(f"NEGATIVE_WRONG_RC={wrong.returncode}")
    ok &= wrong.returncode == 2

    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / "tools"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ENGINE, target / "runbook.py")
        copied = subprocess.run(
            [sys.executable, str(target / "runbook.py"), "status", "--date", "2026-11-07"],
            cwd="/tmp", capture_output=True, text=True,
        )
    print("NEGATIVE_COPIED_CMD=نسخة مزروعة خارج الشجرة بلا --root (جذر مشتق بلا مانيفست)")
    print(f"NEGATIVE_COPIED_RC={copied.returncode}")
    ok &= copied.returncode == 2

    print("ROOT_CONTRACT=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
