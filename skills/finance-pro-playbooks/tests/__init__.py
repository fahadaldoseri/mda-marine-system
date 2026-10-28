"""Test package marker; bootstrap lives in tests/_bootstrap.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _bootstrap  # noqa: E402,F401
