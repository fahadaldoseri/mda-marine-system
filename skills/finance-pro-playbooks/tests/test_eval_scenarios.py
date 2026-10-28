"""P0 eval scenario suite: executable routing assertions from eval_scenarios.json.

Each scenario in tests/eval_scenarios.json carries:
- `expect`: machine-checkable routing assertions (verified here);
- `manual_asserts`: behavioural expectations for live agent-in-the-loop evals
  (not checkable offline; kept alongside as the acceptance checklist).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import _bootstrap  # noqa: F401  (bytecode hygiene)

from route_request import route  # noqa: E402

SCENARIOS_PATH = os.path.join(os.path.dirname(__file__), "eval_scenarios.json")

with open(SCENARIOS_PATH, encoding="utf-8") as f:
    SUITE = json.load(f)


class TestEvalScenarios(unittest.TestCase):
    """Machine-checkable half of the P0 eval suite."""

    def _route(self, request):
        return route(request)

    def test_all_scenarios(self):
        for scenario in SUITE["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                result = self._route(scenario["request"])
                expect = scenario["expect"]

                if "status" in expect:
                    self.assertEqual(
                        result["status"], expect["status"],
                        f"{scenario['id']}: status mismatch (got {result['status']})",
                    )
                if "status_in" in expect:
                    self.assertIn(
                        result["status"], expect["status_in"],
                        f"{scenario['id']}: status {result['status']} not in {expect['status_in']}",
                    )
                if "primary_module" in expect:
                    self.assertEqual(
                        result.get("primary_module"), expect["primary_module"],
                        f"{scenario['id']}: primary_module mismatch",
                    )
                if "governance_tier" in expect:
                    self.assertEqual(
                        result.get("governance_tier"), expect["governance_tier"],
                        f"{scenario['id']}: governance_tier mismatch",
                    )
                if "task_ids_include" in expect:
                    tasks = result.get("specialist_tasks", [])
                    task_ids = [
                        t["id"] if isinstance(t, dict) else t for t in tasks
                    ]
                    for tid in expect["task_ids_include"]:
                        self.assertIn(
                            tid, task_ids,
                            f"{scenario['id']}: task {tid} not matched (got {task_ids})",
                        )
                if "call_chain_includes" in expect:
                    chain = result.get("module_chain", [])
                    for mod in expect["call_chain_includes"]:
                        self.assertIn(
                            mod, chain,
                            f"{scenario['id']}: module {mod} missing from call chain {chain}",
                        )
                if "references_include" in expect:
                    refs = result.get("references", [])
                    for ref in expect["references_include"]:
                        self.assertIn(
                            ref, refs,
                            f"{scenario['id']}: reference {ref} missing",
                        )
                if "must_read_max_files" in expect:
                    refs = result.get("references", [])
                    self.assertLessEqual(
                        len(refs), expect["must_read_max_files"],
                        f"{scenario['id']}: {len(refs)} required references exceed "
                        f"light-tier budget of {expect['must_read_max_files']}",
                    )
                for field in (
                    "transaction_requested",
                    "transaction_request_disposition",
                    "skill_financial_transaction_possible",
                    "external_side_effect_possible",
                ):
                    if field in expect:
                        self.assertEqual(
                            result.get(field),
                            expect[field],
                            f"{scenario['id']}: {field} mismatch",
                        )

    def test_manual_asserts_documented(self):
        """Every scenario must ship a non-empty manual acceptance checklist."""
        for scenario in SUITE["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                self.assertTrue(
                    scenario.get("manual_asserts"),
                    f"{scenario['id']}: missing manual_asserts checklist",
                )


if __name__ == "__main__":
    unittest.main()
