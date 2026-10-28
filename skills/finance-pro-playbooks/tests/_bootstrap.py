"""Shared test bootstrap: keep the skill tree free of bytecode litter.

Imported by every test module (after they insert tests/ into sys.path), so it
works under any invocation style: `python3 -m unittest discover -s tests`,
`discover -s .`, or running a single test file directly.
"""

import atexit
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True

_SKILL_ROOT = Path(__file__).resolve().parents[1]
_registered = getattr(sys, "_fap_sweep_registered", False)


def _sweep_bytecode_caches() -> None:
    for cache_dir in _SKILL_ROOT.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
    for pyc in _SKILL_ROOT.rglob("*.pyc"):
        try:
            pyc.unlink()
        except OSError:
            pass


if not _registered:
    atexit.register(_sweep_bytecode_caches)
    sys._fap_sweep_registered = True  # type: ignore[attr-defined]
