#!/usr/bin/env python3
"""Regression contract for the English glossary shape guard."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
VALIDATOR = BRAIN / "validators" / "check_glossary_shape.py"


def _check(data: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "glossary.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--file", str(path)],
            cwd=BRAIN,
            capture_output=True,
            text=True,
        )


def test_exact_only_manifest_is_allowed_as_glossary_metadata() -> None:
    key = "المصدر والموقع والوقت"
    result = _check(
        {
            "entries": {key: "Source, location, and time"},
            "exact_match_only_entries": [key],
        }
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_unknown_glossary_root_key_remains_fail_closed() -> None:
    result = _check({"entries": {}, "unexpected_root_key": "must be rejected"})

    assert result.returncode == 2
    assert "مفاتيح في الجذر بدل entries" in result.stdout
