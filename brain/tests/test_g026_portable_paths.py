#!/usr/bin/env python3
"""حاجز انحدار يمنع إعادة literals جذور التشغيل في الشيفرة التنفيذية."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_BRAIN = Path.home() / "brain-marine-news"
RUNTIME_SITE = Path.home() / "seawatch"
TARGETS = (
    ROOT / "tests/test_gate_guard_contracts.py",
    ROOT / "skills/source-coverage-route-ops/scripts/probe_source_routes.py",
    ROOT / "skills/bilingual-master-direction-ops/scripts/verify_master_direction.py",
)


class PortablePathContractTest(unittest.TestCase):
    def test_reported_files_do_not_embed_runtime_roots(self) -> None:
        literals = (RUNTIME_BRAIN.as_posix(), RUNTIME_SITE.as_posix())
        hits = []
        for path in TARGETS:
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), 1):
                if any(literal in line for literal in literals):
                    hits.append(f"{path.relative_to(ROOT)}:{line_no}")
        self.assertEqual([], hits, "مسارات تشغيل ثابتة في: " + ", ".join(hits))


if __name__ == "__main__":
    unittest.main(verbosity=2)
