from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
TESTS = SKILL_ROOT / "tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import _bootstrap  # noqa: E402,F401
import route_request as router  # noqa: E402
from render_report import (  # noqa: E402
    IMPORTANT_NOTICE_HEADING,
    TRANSACTION_REQUEST_BOUNDARY,
    render_report,
)
from result_fixtures import ALL_MODULES, valid_result  # noqa: E402
from validate_result import (  # noqa: E402
    FORBIDDEN_TRANSACTION_KEYS,
    FORBIDDEN_TRANSACTION_STATES,
    MANUAL_EXECUTION_NOTICE,
    validate_result,
)


CASE_CATALOG = TESTS / "complete_test_cases.json"
MODULE_CATALOG = SKILL_ROOT / "references" / "module-catalog.json"
TASK_CATALOG = SKILL_ROOT / "references" / "corporate-finance" / "task-catalog.json"
RESULT_SCHEMA = SKILL_ROOT / "references" / "schemas" / "finance-analysis-result.schema.json"
FORMAT_REFERENCE = {
    "excel": "references/corporate-finance/formats/excel_standards.md",
    "document": "references/corporate-finance/formats/document_standards.md",
    "metrics": "references/corporate-finance/formats/metric_disambiguation.md",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def task_request(task: dict) -> str:
    if task["id"] == "ecm-company-profile":
        text = "Create an ECM pre-meeting company profile deliverable"
    else:
        text = f"Create a professional {task['label']} deliverable"
    if task.get("require_deliverable_signal"):
        text += " as a memo presentation"
    return text


class CompleteCaseCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_json(CASE_CATALOG)
        cls.cases = cls.catalog["cases"]

    def test_catalog_metadata_and_case_ids_are_complete_and_unique(self) -> None:
        self.assertEqual(self.catalog["skill"], "finance-pro-playbooks")
        self.assertEqual(self.catalog["catalog_version"], "1.0")
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 40)
        for case in self.cases:
            with self.subTest(case=case.get("id")):
                self.assertRegex(case["id"], r"^P[0-2]-[A-Z]{3}-\d{3}$")
                self.assertIn(case["priority"], {"P0", "P1", "P2"})
                self.assertIsInstance(case["area"], str)
                self.assertIn("request", case)
                self.assertIsInstance(case["expected"], dict)
                self.assertNotIn("known_gap", case)
                if "regression" in case:
                    self.assertTrue(case["regression"].startswith("Fixed "))

    def test_all_catalog_route_cases_match_expected_contract(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["id"], request=case["request"]):
                actual = router.route(case["request"])
                for expected_key, expected_value in case["expected"].items():
                    if expected_key.endswith("_contains"):
                        actual_key = expected_key.removesuffix("_contains")
                        self.assertIn(actual_key, actual)
                        for value in expected_value:
                            self.assertIn(value, actual[actual_key])
                    else:
                        self.assertEqual(
                            actual.get(expected_key),
                            expected_value,
                            msg=f"{case['id']} field {expected_key}: {actual}",
                        )

    def test_fixed_router_regressions_remain_closed(self) -> None:
        regressions = [case for case in self.cases if case.get("regression")]
        self.assertEqual(len(regressions), 5)
        failures = []
        for case in regressions:
            actual = router.route(case["request"])
            for expected_key, expected_value in case["expected"].items():
                if actual.get(expected_key) != expected_value:
                    failures.append(
                        f"{case['id']} {expected_key}: expected {expected_value!r}, "
                        f"got {actual.get(expected_key)!r}; {case['regression']}"
                    )
        self.assertFalse(failures, "\n".join(failures))


class ModuleCatalogCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_json(MODULE_CATALOG)
        cls.modules = cls.catalog["modules"]

    def test_module_catalog_exactly_matches_public_modules(self) -> None:
        self.assertEqual(set(self.modules), set(ALL_MODULES))
        self.assertEqual(set(self.catalog["dependency_order"]), set(ALL_MODULES))
        self.assertEqual(set(self.catalog["primary_priority"]), set(ALL_MODULES))
        self.assertEqual(len(self.catalog["dependency_order"]), len(set(self.catalog["dependency_order"])))
        self.assertEqual(len(self.catalog["primary_priority"]), len(set(self.catalog["primary_priority"])))

    def test_every_module_has_compilable_patterns_reference_template_and_dependencies(self) -> None:
        for module, spec in self.modules.items():
            with self.subTest(module=module):
                self.assertTrue(spec["patterns"])
                for pattern in spec["patterns"]:
                    re.compile(pattern, flags=re.IGNORECASE)
                self.assertTrue((SKILL_ROOT / spec["reference"]).is_file())
                self.assertTrue((SKILL_ROOT / "templates" / f"{module}.md").is_file())
                self.assertIn("references/output-contracts.md", spec["required_references"])
                self.assertTrue(
                    set(spec["conditional_references"]).issubset(
                        {"privacy", "execution", "scoring", "metrics"}
                    )
                )
                for references in spec["conditional_references"].values():
                    for reference in references:
                        self.assertTrue((SKILL_ROOT / reference).is_file())

    def test_declared_router_constants_match_catalog(self) -> None:
        self.assertEqual(tuple(self.catalog["dependency_order"]), router.DEPENDENCY_ORDER)
        self.assertEqual(tuple(self.catalog["primary_priority"]), router.PRIMARY_PRIORITY)
        self.assertEqual(set(router.PATTERNS), set(self.modules))
        for module, spec in self.modules.items():
            with self.subTest(module=module):
                self.assertEqual(tuple(spec["patterns"]), router.PATTERNS[module])
                self.assertEqual(spec["reference"], router.REFERENCE_BY_MODULE[module])
                self.assertEqual(tuple(spec["required_references"]), router.REQUIRED_REFERENCE_BY_MODULE[module])


class CorporateFinanceTaskCatalogCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_json(TASK_CATALOG)
        cls.tasks = cls.catalog["tasks"]

    def test_task_catalog_contains_54_unique_tasks(self) -> None:
        ids = [task["id"] for task in self.tasks]
        self.assertEqual(len(ids), 54)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.catalog["primary_module"], "corporate-finance")

    def test_every_task_routes_to_itself_and_loads_exact_declared_dependencies(self) -> None:
        for task in self.tasks:
            request = task_request(task)
            with self.subTest(task=task["id"], request=request):
                result = router.route(request)
                self.assertEqual(result["primary_module"], "corporate-finance")
                self.assertIn(task["id"], result["specialist_tasks"])
                self.assertIn(task["playbook"], result["references"])
                self.assertIn(task["playbook_overview"], result["references"])
                self.assertIn(task["playbook"], result["reference_resolution"]["specialist_dependencies"])
                for format_name in task.get("formats", []):
                    self.assertIn(FORMAT_REFERENCE[format_name], result["references"])
                self.assertEqual(result["governance_tier"], "full")

    def test_expert_call_guide_is_not_misrouted_as_options_strategy(self) -> None:
        task = next(item for item in self.tasks if item["id"] == "expert-call-guide")
        result = router.route(task_request(task))
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn(task["id"], result["specialist_tasks"])

    def test_every_task_pattern_compiles_and_declared_paths_exist(self) -> None:
        for task in self.tasks:
            with self.subTest(task=task["id"]):
                self.assertTrue(task["patterns"])
                for pattern in task["patterns"]:
                    re.compile(pattern, flags=re.IGNORECASE)
                for pattern in task.get("deliverable_patterns", []):
                    re.compile(pattern, flags=re.IGNORECASE)
                self.assertTrue((SKILL_ROOT / task["playbook"]).is_file())
                self.assertTrue((SKILL_ROOT / task["playbook_overview"]).is_file())

    def test_tasks_requiring_deliverable_signal_do_not_activate_without_it(self) -> None:
        gated = [task for task in self.tasks if task.get("require_deliverable_signal")]
        self.assertTrue(gated)
        for task in gated:
            text = "Expert call" if task["id"] == "expert-call-guide" else task["label"]
            signaled_text = (
                "Expert Call Guide"
                if task["id"] == "expert-call-guide"
                else f"{text} memo presentation"
            )
            with self.subTest(task=task["id"]):
                result = router.route(text)
                self.assertNotIn(task["id"], result.get("specialist_tasks", []))
                signaled = router.route(signaled_text)
                self.assertIn(task["id"], signaled["specialist_tasks"])

    def test_tasks_requiring_research_upstream_add_equity_research_when_requested(self) -> None:
        upstream_tasks = [task for task in self.tasks if task.get("requires_research_upstream")]
        self.assertTrue(upstream_tasks)
        for task in upstream_tasks:
            text = f"Research and analyze a company, then {task_request(task)}"
            with self.subTest(task=task["id"]):
                result = router.route(text)
                self.assertIn(task["id"], result["specialist_tasks"])
                self.assertIn("equity-research", result["module_chain"])
                self.assertEqual(result["module_chain"][-1], "corporate-finance")


class ExpertCallRoutingRegressionTests(unittest.TestCase):
    def test_explicit_expert_call_guide_is_owned_by_corporate_finance(self) -> None:
        result = router.route("Create a professional Expert Call Guide deliverable")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertIn("expert-call-guide", result["specialist_tasks"])
        self.assertNotIn("options-strategy", result["module_chain"])
        self.assertIn(
            "final-owner-override:expert-call-guide",
            result["matched_evidence"]["corporate-finance"],
        )

    def test_equity_research_is_retained_upstream_for_expert_call_guide(self) -> None:
        result = router.route("Analyze Apple's fundamentals and prepare an expert call guide")
        self.assertEqual(result["primary_module"], "corporate-finance")
        self.assertEqual(result["module_chain"], ["equity-research", "corporate-finance"])
        self.assertIn("expert-call-guide", result["specialist_tasks"])

    def test_bare_expert_call_matches_neither_specialist_nor_options(self) -> None:
        result = router.route("Expert call")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertIsNone(result["primary_module"])
        self.assertNotIn("expert-call-guide", result["specialist_tasks"])
        self.assertNotIn("options-strategy", result["module_chain"])

    def test_earnings_call_does_not_activate_options_strategy(self) -> None:
        result = router.route("Summarize the earnings call and analyze fundamentals")
        self.assertEqual(result["primary_module"], "equity-research")
        self.assertNotIn("options-strategy", result["module_chain"])
        self.assertNotIn("expert-call-guide", result["specialist_tasks"])

    def test_conference_call_transcript_does_not_activate_options_strategy(self) -> None:
        result = router.route("Review the conference call transcript")
        self.assertNotIn("options-strategy", result["module_chain"])
        self.assertNotIn("expert-call-guide", result["specialist_tasks"])

    def test_covered_call_remains_owned_by_options_strategy(self) -> None:
        result = router.route("Design a covered call strategy")
        self.assertEqual(result["primary_module"], "options-strategy")
        self.assertIn("options-strategy", result["module_chain"])

    def test_call_option_context_remains_owned_by_options_strategy(self) -> None:
        result = router.route("Analyze a call option with strike, expiry and premium")
        self.assertEqual(result["primary_module"], "options-strategy")
        self.assertIn("options-strategy", result["module_chain"])

    def test_transaction_redirect_precedes_expert_call_final_owner(self) -> None:
        result = router.route("Prepare an expert call guide, then execute an options trade")
        self.assertEqual(result["primary_module"], "trade-planning")
        self.assertTrue(result["transaction_requested"])
        self.assertEqual(result["transaction_request_disposition"], "redirected_to_manual_plan")
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertIn("expert-call-guide", result["specialist_tasks"])
        self.assertEqual(
            result["module_chain"],
            ["options-strategy", "corporate-finance", "trade-planning"],
        )
        self.assertNotIn(
            "final-owner-override:expert-call-guide",
            result["matched_evidence"]["corporate-finance"],
        )


class ResultSchemaCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(RESULT_SCHEMA)
        cls.top_required = cls.schema["required"]
        cls.payload_definition_by_module = {}
        for conditional in cls.schema["allOf"]:
            module = conditional["if"]["properties"]["primary_module"].get("const")
            payload_ref = conditional["then"]["properties"]["payload"].get("$ref")
            if module and payload_ref:
                cls.payload_definition_by_module[module] = payload_ref.rsplit("/", 1)[-1]

    def assert_failed_with(self, result: dict, fragment: str) -> None:
        report = validate_result(result)
        self.assertEqual(report["status"], "failed", report)
        self.assertTrue(any(fragment in error for error in report["errors"]), report)

    def test_all_modules_have_payload_schema_mapping_and_valid_fixture(self) -> None:
        self.assertEqual(set(self.payload_definition_by_module), set(ALL_MODULES))
        for module in ALL_MODULES:
            with self.subTest(module=module):
                report = validate_result(valid_result(module))
                self.assertEqual(report["status"], "passed", report)

    def test_every_public_envelope_required_field_is_enforced_for_every_module(self) -> None:
        for module in ALL_MODULES:
            for field in self.top_required:
                with self.subTest(module=module, field=field):
                    result = valid_result(module)
                    result.pop(field)
                    report = validate_result(result)
                    self.assertEqual(report["status"], "failed", report)
                    self.assertTrue(any(field in error for error in report["errors"]), report)

    def test_every_payload_top_level_required_field_is_enforced(self) -> None:
        for module, definition_name in self.payload_definition_by_module.items():
            required = self.schema["$defs"][definition_name].get("required", [])
            self.assertTrue(required, module)
            for field in required:
                with self.subTest(module=module, field=field):
                    result = valid_result(module)
                    result["payload"].pop(field)
                    report = validate_result(result)
                    self.assertEqual(report["status"], "failed", report)
                    self.assertTrue(any(field in error for error in report["errors"]), report)

    def test_common_const_enum_format_and_additional_property_guards(self) -> None:
        mutations = (
            ("schema-version", lambda r: r.__setitem__("schema_version", "finance-analysis-pro/9.9"), "schema_version"),
            ("transaction-capability", lambda r: r.__setitem__("skill_financial_transaction_possible", True), "skill_financial_transaction_possible"),
            ("status", lambda r: r.__setitem__("status", "unknown"), "status"),
            ("governance", lambda r: r.__setitem__("governance_tier", "medium"), "governance_tier"),
            ("additional", lambda r: r.__setitem__("unexpected_top_level", True), "Additional properties"),
        )
        for name, mutate, fragment in mutations:
            with self.subTest(mutation=name):
                result = valid_result("equity-research")
                mutate(result)
                self.assert_failed_with(result, fragment)

    def test_as_of_rejects_non_rfc3339_datetime(self) -> None:
        result = valid_result("equity-research")
        result["as_of"] = "not-a-date"
        self.assert_failed_with(result, "as_of")

    def test_data_cutoff_rejects_non_iso_date(self) -> None:
        result = valid_result("equity-research")
        result["data_cutoff"] = "31/12/2026"
        self.assert_failed_with(result, "data_cutoff")

    def test_temporal_fields_accept_valid_rfc3339_and_iso_boundaries(self) -> None:
        cases = (
            ("2024-02-29T23:59:59Z", "2024-02-29"),
            ("2026-07-29T12:34:56.123+08:00", "2026-07-28T20:34:56-04:00"),
        )
        for as_of, data_cutoff in cases:
            with self.subTest(as_of=as_of, data_cutoff=data_cutoff):
                result = valid_result("equity-research")
                result["as_of"] = as_of
                result["data_cutoff"] = data_cutoff
                report = validate_result(result)
                self.assertEqual(report["status"], "passed", report)

    def test_temporal_fields_reject_missing_timezone_and_invalid_calendar_dates(self) -> None:
        cases = (
            ("as_of", "2026-07-29T12:00:00"),
            ("as_of", "2026-02-29T12:00:00Z"),
            ("data_cutoff", "2026-02-29"),
            ("data_cutoff", "2026-07-29T12:00:00"),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                result = valid_result("equity-research")
                result[field] = value
                self.assert_failed_with(result, field)

    def test_validation_does_not_mutate_input(self) -> None:
        for module in ALL_MODULES:
            with self.subTest(module=module):
                result = valid_result(module)
                before = copy.deepcopy(result)
                validate_result(result)
                self.assertEqual(result, before)

    def test_module_chain_semantics_reject_duplicate_missing_final_and_wrong_order(self) -> None:
        cases = []
        duplicate = valid_result("equity-research")
        duplicate["module_chain"] = ["equity-research", "equity-research"]
        cases.append((duplicate, "duplicate"))
        missing = valid_result("equity-research")
        missing["module_chain"] = ["fund-etf"]
        cases.append((missing, "include primary_module"))
        not_final = valid_result("portfolio-management")
        not_final["module_chain"] = ["portfolio-management", "trade-planning"]
        cases.append((not_final, "final delivery node"))
        wrong_order = valid_result("portfolio-management")
        wrong_order["module_chain"] = ["quant-backtesting", "equity-research", "portfolio-management"]
        cases.append((wrong_order, "dependency order"))
        for result, fragment in cases:
            with self.subTest(fragment=fragment):
                self.assert_failed_with(result, fragment)


class TradePlanningBoundaryCompletenessTests(unittest.TestCase):
    @staticmethod
    def redirected_result() -> dict:
        result = valid_result("trade-planning")
        result["payload"]["transaction_request_disposition"] = "redirected_to_manual_plan"
        return result

    def assert_trade_failure(self, result: dict, fragment: str) -> None:
        report = validate_result(result)
        self.assertEqual(report["status"], "failed", report)
        self.assertTrue(any(fragment in error for error in report["errors"]), report)

    def test_redirected_plan_contract_passes_without_side_effect(self) -> None:
        result = self.redirected_result()
        report = validate_result(result)
        self.assertEqual(report["status"], "passed", report)
        self.assertFalse(result["skill_financial_transaction_possible"])
        self.assertFalse(result["execution"]["external_side_effect"])
        self.assertEqual(result["execution"]["confirmation_status"], "not_applicable")
        self.assertEqual(result["payload"]["order_plan"]["status"], "proposed_unsubmitted")

    def test_every_forbidden_transaction_key_is_rejected(self) -> None:
        for key in sorted(FORBIDDEN_TRANSACTION_KEYS):
            with self.subTest(key=key):
                result = self.redirected_result()
                result["payload"][key] = "forbidden-value"
                self.assert_trade_failure(result, "transaction execution field is forbidden")

    def test_every_executed_transaction_state_is_rejected(self) -> None:
        for state in sorted(FORBIDDEN_TRANSACTION_STATES):
            with self.subTest(state=state):
                result = self.redirected_result()
                result["payload"]["order_plan"]["status"] = state
                self.assert_trade_failure(result, "executed transaction state is forbidden")

    def test_immutable_notice_disposition_and_execution_flags(self) -> None:
        mutations = (
            (lambda r: r["payload"].__setitem__("manual_execution_notice", "User confirmed execution."), "immutable SKILL-capability notice"),
            (lambda r: r["payload"].__setitem__("transaction_request_disposition", "executed"), "invalid plan-only disposition"),
            (lambda r: r["execution"].__setitem__("external_side_effect", True), "trade-planning must always be false"),
            (lambda r: r["execution"].__setitem__("confirmation_status", "confirmed"), "trade-planning must be not_applicable"),
            (lambda r: r["payload"]["order_plan"].__setitem__("status", "confirmed"), "must remain proposed_unsubmitted"),
            (lambda r: r["payload"]["order_plan"].__setitem__("platform_verification_required", False), "must be true"),
        )
        for mutate, fragment in mutations:
            with self.subTest(fragment=fragment):
                result = self.redirected_result()
                mutate(result)
                self.assert_trade_failure(result, fragment)

    def test_redirected_request_requires_plan_guidance_and_verification(self) -> None:
        mutations = (
            (lambda r: r["payload"].__setitem__("mode", "analysis"), "manual_plan mode"),
            (lambda r: r["payload"].__setitem__("order_plan", None), "requires a proposed manual plan"),
            (lambda r: r["payload"].__setitem__("user_action_steps", ["one", "two"]), "at least three"),
            (lambda r: r["payload"].__setitem__("plan_checks", []), "user_verification_required"),
        )
        for mutate, fragment in mutations:
            with self.subTest(fragment=fragment):
                result = self.redirected_result()
                mutate(result)
                self.assert_trade_failure(result, fragment)

    def test_trade_report_preserves_boundary_plan_guidance_stop_order(self) -> None:
        report = render_report(self.redirected_result())
        boundary = report.index(TRANSACTION_REQUEST_BOUNDARY)
        plan = report.index("## Proposed, Unsubmitted Order Plan")
        guidance = report.index("## User-Controlled Self-Execution Guidance")
        notice = report.rindex(IMPORTANT_NOTICE_HEADING)
        self.assertLess(boundary, plan)
        self.assertLess(plan, guidance)
        self.assertLess(guidance, notice)
        self.assertEqual(report.count(IMPORTANT_NOTICE_HEADING), 1)

    def test_manual_notice_constant_matches_fixture(self) -> None:
        self.assertEqual(valid_result("trade-planning")["payload"]["manual_execution_notice"], MANUAL_EXECUTION_NOTICE)


class ReportRenderingCompletenessTests(unittest.TestCase):
    def test_all_eight_module_reports_are_deterministic_and_end_with_notice(self) -> None:
        for module in ALL_MODULES:
            with self.subTest(module=module):
                result = valid_result(module)
                first = render_report(result)
                second = render_report(copy.deepcopy(result))
                self.assertEqual(first, second)
                self.assertTrue(first.startswith("# "))
                self.assertEqual(first.count(IMPORTANT_NOTICE_HEADING), 1)
                self.assertGreater(first.rfind(IMPORTANT_NOTICE_HEADING), first.find("## Executive Summary"))
                self.assertTrue(first.endswith("\n"))

    def test_rendering_escapes_markdown_table_pipes_and_line_breaks(self) -> None:
        result = valid_result("fund-etf")
        result["payload"]["candidates"][0]["name"] = "A|B\nFund"
        report = render_report(result)
        self.assertIn("A\\|B<br>Fund", report)


if __name__ == "__main__":
    unittest.main()
