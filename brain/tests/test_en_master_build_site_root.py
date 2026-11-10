#!/usr/bin/env python3
"""عقد جذر الموقع في en_master_build.sh: موجب بلا SITE_DIR وسالب بفشل مغلق."""
from __future__ import annotations

import os
import pathlib
import stat
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "en_master_build.sh"
REAL_SITE = pathlib.Path("/home/ubuntu/seawatch")


def _fake_python(bin_dir: pathlib.Path) -> None:
    shim = bin_dir / "python3"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'FAKE_PYTHON_ARGS=%s\\n' \"$*\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "2026-11-10"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    if not (REAL_SITE / "dist").is_dir():
        print(f"TEST_FIXTURE_MISSING={REAL_SITE / 'dist'}")
        return 2
    with tempfile.TemporaryDirectory(prefix="en-master-build-root-") as raw:
        tmp = pathlib.Path(raw)
        fake_bin = tmp / "bin"
        fake_bin.mkdir()
        _fake_python(fake_bin)
        base = os.environ.copy()
        for key in ("SITE", "SITE_DIR", "SITE_CANDIDATES"):
            base.pop(key, None)
        base["BRAIN_DIR"] = str(ROOT)
        base["PATH"] = f"{fake_bin}:{base.get('PATH', '')}"

        positive = _run(base)
        print("POSITIVE_NO_SITE_DIR_CMD=bash tools/en_master_build.sh 2026-11-10")
        print(f"POSITIVE_NO_SITE_DIR_RC={positive.returncode}")
        print(positive.stdout + positive.stderr, end="")
        positive_ok = (
            positive.returncode == 0
            and f"--site {REAL_SITE}" in positive.stdout
            and "FAKE_PYTHON_ARGS=" in positive.stdout
        )

        negative_env = base.copy()
        negative_env["SITE_CANDIDATES"] = str(tmp / "site-does-not-exist")
        negative = _run(negative_env)
        print("NEGATIVE_MISSING_SITE_CMD=SITE_CANDIDATES=/tmp/nonexistent bash tools/en_master_build.sh 2026-11-10")
        print(f"NEGATIVE_MISSING_SITE_RC={negative.returncode}")
        print(negative.stdout + negative.stderr, end="")
        negative_ok = (
            negative.returncode == 2
            and "فشل مغلق" in (negative.stdout + negative.stderr)
            and "FAKE_PYTHON_ARGS=" not in (negative.stdout + negative.stderr)
        )

    print("EN_MASTER_BUILD_SITE_ROOT=" + ("PASS" if positive_ok and negative_ok else "FAIL"))
    return 0 if positive_ok and negative_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
