#!/usr/bin/env python3
"""اختبار عقد توزيع ف4.3 والاشتقاق القابل لإعادة التشغيل من النطاقات."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validators" / "validate_report.py"
TOOL = ROOT / "tools" / "hypothesis_distribution.py"
RULE = (
    "منتصف كل نطاق ثم إعادة تسوية إلى 100 بأكبر البواقي "
    "(largest remainder)؛ الإصدار 1"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


MOD = _load(VALIDATOR, "validate_report")


def _hypotheses(
    values: list[tuple[str, str, str]],
    *,
    rule: str | None = RULE,
) -> dict:
    data = {
        "hypotheses": [
            {
                "statement": f"فرضية {i}",
                "support": "سند",
                "against": "اعتراض",
                "likelihood": likelihood,
                "likelihood_range": likelihood_range,
                "likelihood_kind": kind,
            }
            for i, (likelihood, likelihood_range, kind) in enumerate(values, start=1)
        ]
    }
    if rule is not None:
        data["distribution_rule"] = rule
    return data


VALID = [
    ("45%", "55–80%", "point_from_range"),
    ("33%", "45–55%", "point_from_range"),
    ("22%", "20–45%", "point_from_range"),
]


class LikelihoodContract(unittest.TestCase):
    def test_derived_point_distribution_passes_and_sums_to_100(self):
        data = _hypotheses(VALID)
        self.assertEqual(MOD.check_hypotheses(data), [])
        self.assertEqual(sum(int(item[0].rstrip("%")) for item in VALID), 100)

    def test_tool_uses_midpoints_and_largest_remainder(self):
        tool = _load(TOOL, "hypothesis_distribution")
        self.assertEqual(tool.calculate_distribution([item[1] for item in VALID]), [45, 33, 22])

    def test_tool_write_then_check_updates_only_distribution_fields(self):
        source = {
            "title": "اختبار",
            "hypotheses": [
                {"est": "1", "likelihood": "55–80%", "likelihood_kind": "range"},
                {"est": "2", "likelihood": "45–55%", "likelihood_kind": "range"},
                {"est": "3", "likelihood": "20–45%", "likelihood_kind": "range"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            meta = Path(tmp) / "meta.json"
            meta.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            write = subprocess.run(
                [sys.executable, str(TOOL), "--meta", str(meta), "--write"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(write.returncode, 0, write.stdout + write.stderr)
            check = subprocess.run(
                [sys.executable, str(TOOL), "--meta", str(meta), "--check"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            saved = json.loads(meta.read_text(encoding="utf-8"))
            self.assertEqual([h["likelihood"] for h in saved["hypotheses"]], ["45%", "33%", "22%"])
            self.assertEqual(saved["distribution_rule"], RULE)

    def test_point_does_not_equal_derived_distribution_is_rejected(self):
        data = _hypotheses(
            [("44%", "55–80%", "point_from_range"), *VALID[1:]],
        )
        self.assertTrue(MOD.check_hypotheses(data))

    def test_sum_other_than_100_is_rejected(self):
        data = _hypotheses(
            [("45%", "55–80%", "point_from_range"), ("33%", "45–55%", "point_from_range"), ("21%", "20–45%", "point_from_range")],
        )
        self.assertTrue(MOD.check_hypotheses(data))

    def test_malformed_range_is_rejected(self):
        data = _hypotheses(
            [("45%", "55-80%", "point_from_range"), *VALID[1:]],
        )
        self.assertTrue(MOD.check_hypotheses(data))

    def test_out_of_bounds_range_is_rejected(self):
        data = _hypotheses(
            [("45%", "120–140%", "point_from_range"), *VALID[1:]],
        )
        self.assertTrue(MOD.check_hypotheses(data))

    def test_mixed_likelihood_kinds_are_rejected(self):
        data = _hypotheses(
            [VALID[0], ("50%", "45–55%", "range"), VALID[2]],
        )
        self.assertTrue(MOD.check_hypotheses(data))

    def test_unsupported_likelihood_kind_is_rejected(self):
        data = _hypotheses(
            [("45%", "55–80%", "manual"), *VALID[1:]],
        )
        self.assertTrue(MOD.check_hypotheses(data))

    def test_missing_or_wrong_rule_is_rejected(self):
        self.assertTrue(MOD.check_hypotheses(_hypotheses(VALID, rule=None)))
        self.assertTrue(MOD.check_hypotheses(_hypotheses(VALID, rule="منتصف النطاق فقط")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
