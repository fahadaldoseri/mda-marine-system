#!/usr/bin/env python3
"""استثناء المرساة بقرار المالك: رابط واحد ويوم واحد فقط، وغير ذلك لا يمر."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://example.org/a/b"


def _mod():
    spec = importlib.util.spec_from_file_location("bm_waiver", ROOT / "tools/browser_measure.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class OwnerWaiverTests(unittest.TestCase):
    def _root(self, waivers):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        (Path(d.name) / "appendices").mkdir()
        (Path(d.name) / "appendices" / "anchor-waivers.json").write_text(json.dumps(waivers), encoding="utf-8")
        return d.name

    def test_matching_url_and_date_passes(self):
        root = self._root([{"url": URL, "date": "2026-11-28", "reason": "r", "approved_by": "x"}])
        got = _mod().owner_waiver(root, "2026-11-28", URL + "#:~:text=a")
        self.assertTrue(got and got["exists"] and got["method"] == "owner_waiver")

    def test_other_day_or_other_url_blocks(self):
        root = self._root([{"url": URL, "date": "2026-11-28", "reason": "r", "approved_by": "x"}])
        self.assertIsNone(_mod().owner_waiver(root, "2026-11-29", URL))
        self.assertIsNone(_mod().owner_waiver(root, "2026-11-28", "https://example.org/other"))

    def test_no_file_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(_mod().owner_waiver(d, "2026-11-28", URL))


if __name__ == "__main__":
    unittest.main()
