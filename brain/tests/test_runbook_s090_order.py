#!/usr/bin/env python3
"""Regression guard: report review must run after the daily report is written."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))
steps = manifest["steps"]
index = {step["id"]: i for i, step in enumerate(steps)}

assert index["W010"] < index["S090"], (
    "S090 reads reports/{date}-sectioned.md but is ordered before W010"
)
s090 = steps[index["S090"]]
command = " ".join(s090.get("command", []))
assert "reports/{date}-sectioned.md" in command, "S090 input contract changed unexpectedly"
assert steps[index["W010"]].get("writes") == ["reports/{date}-sectioned.md"], (
    "W010 must remain the producer of S090's report input"
)
print("OK: W010 precedes S090 and produces reports/{date}-sectioned.md")
