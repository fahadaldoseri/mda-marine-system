#!/usr/bin/env python3
"""Validate a finance-analysis-pro/1.2 result and cross-field invariants."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from ensure_runtime import RuntimePreparationError, ensure_runtime


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "references" / "schemas" / "finance-analysis-result.schema.json"
TASK_CATALOG = ROOT / "references" / "corporate-finance" / "task-catalog.json"

SECRET_VALUE = re.compile(
    r"(?i)(?:bearer\s+|sk-[A-Za-z0-9_-]{12,}|"
    r"(?:api[_-]?key|token|password|secret)\s*[:=]\s*[A-Za-z0-9_\-/.+=]{12,})"
)
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
RFC3339_DATETIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FULL_WALLET = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
SENSITIVE_IDENTIFIER = re.compile(
    r"(?i)(?:account|acct|wallet|idcard|passport|mobile|phone)[_-]?(?:id|number|no)?\s*[:=]\s*[A-Za-z0-9-]{8,}"
)
FORBIDDEN_TRANSACTION_KEYS = frozenset(
    {
        "account_id",
        "account_number",
        "broker_order_id",
        "client_order_id",
        "order_id",
        "execution_result",
        "execution_receipt",
        "receipt",
        "fills",
        "fill_price",
        "average_fill_price",
        "transaction_id",
        "transaction_hash",
        "tx_hash",
        "raw_transaction",
        "signed_transaction",
        "signed_payload",
        "signature",
        "wallet_signature",
        "broadcast_result",
        "settlement",
        "reconciliation",
        "confirmation",
    }
)
FORBIDDEN_TRANSACTION_STATES = frozenset(
    {
        "submitted",
        "accepted",
        "working",
        "partially_filled",
        "filled",
        "cancelled",
        "canceled",
        "rejected",
        "settled",
        "broadcast",
        "confirmed_onchain",
    }
)
MANUAL_EXECUTION_NOTICE = (
    "The SKILL did not and cannot perform this financial transaction. "
    "This capability limit applies only to the SKILL and the tools or agents operating within it; "
    "it does not restrict the user's independent activity outside the SKILL. "
    "If the user chooses to transact, they may do so independently on the relevant platform."
)


MODEL_TASK_GROUPS = {
    "financial-models",
    "valuation",
    "lbo-structuring",
    "returns-analysis",
}

MATERIALS_REVIEW_TASKS = {
    "deal-screening-scorecard",
    "pre-ic-consistency-review",
    "meeting-minutes",
}

MODULE_DEPENDENCY_ORDER = (
    "equity-research",
    "fund-etf",
    "crypto-analysis",
    "options-strategy",
    "corporate-finance",
    "quant-backtesting",
    "portfolio-management",
    "trade-planning",
)
MODULE_ORDER_INDEX = {module: index for index, module in enumerate(MODULE_DEPENDENCY_ORDER)}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_path(parts: Iterable[Any]) -> str:
    values = [str(part) for part in parts]
    return "$" if not values else "$." + ".".join(values)


@lru_cache(maxsize=1)
def _jsonschema_api() -> tuple[Any, Any, dict[str, Any]]:
    """Prepare the runtime once, then import the full JSON Schema implementation."""

    runtime = ensure_runtime()
    from jsonschema import Draft202012Validator, FormatChecker

    return Draft202012Validator, FormatChecker, runtime


def _schema_errors(
    result: dict[str, Any],
    schema: dict[str, Any],
    validator_class: Any,
    format_checker_class: Any,
) -> list[str]:
    validator = validator_class(schema, format_checker=format_checker_class())
    errors: list[str] = []
    for error in sorted(validator.iter_errors(result), key=lambda item: list(item.absolute_path)):
        errors.append(f"{_format_path(error.absolute_path)}: {error.message}")
    return errors


def _is_rfc3339_datetime(value: str) -> bool:
    """Validate the contract's timezone-qualified RFC 3339 lexical subset."""

    if RFC3339_DATETIME.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _is_iso_date(value: str) -> bool:
    if ISO_DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _top_level_temporal_errors(result: dict[str, Any]) -> list[str]:
    """Fail closed even when jsonschema optional format checkers are unavailable."""

    errors: list[str] = []
    as_of = result.get("as_of")
    if isinstance(as_of, str) and not _is_rfc3339_datetime(as_of):
        errors.append("$.as_of: must be a valid RFC 3339 date-time with timezone")
    data_cutoff = result.get("data_cutoff")
    if isinstance(data_cutoff, str) and not (
        _is_iso_date(data_cutoff) or _is_rfc3339_datetime(data_cutoff)
    ):
        errors.append(
            "$.data_cutoff: must be a valid ISO 8601 date or RFC 3339 date-time with timezone"
        )
    return errors


def _collect_source_refs(result: dict[str, Any]) -> set[str]:
    refs: set[str] = set()

    def visit(value: Any, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, child_key)
        elif isinstance(value, list):
            for item in value:
                visit(item, key)
        elif isinstance(value, str) and value and key in {"source_ref", "source_refs"}:
            refs.add(value)

    visit(result.get("facts"))
    visit(result.get("metrics"))
    visit(result.get("assumptions"))
    visit(result.get("payload"))
    return refs


def _load_task_index() -> dict[str, dict[str, Any]]:
    catalog = _load_json(TASK_CATALOG)
    tasks = catalog.get("tasks", []) if isinstance(catalog, dict) else []
    return {str(task["id"]): task for task in tasks if isinstance(task, dict) and task.get("id")}


def _is_remote_path(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "s3", "gs", "manus"}


def _resolve_local_artifact(path_value: str, result_path: Path | None) -> Path:
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate
    base = result_path.parent if result_path is not None else Path.cwd()
    return (base / candidate).resolve()


def _validate_artifacts(
    result: dict[str, Any],
    result_path: Path | None,
    errors: list[str],
    warnings: list[str],
) -> set[str]:
    artifact_ids: set[str] = set()
    for index, artifact in enumerate(result.get("artifacts", [])):
        if not isinstance(artifact, dict):
            continue
        artifact_id = artifact.get("artifact_id")
        if isinstance(artifact_id, str):
            if artifact_id in artifact_ids:
                errors.append(f"$.artifacts.{index}.artifact_id: duplicate artifact_id {artifact_id!r}")
            artifact_ids.add(artifact_id)
        status = artifact.get("status")
        path_value = artifact.get("path")
        if status == "ready" and not isinstance(path_value, str):
            errors.append(f"$.artifacts.{index}.path: ready artifact requires a path")
        if status == "ready" and isinstance(path_value, str) and not _is_remote_path(path_value):
            local_path = _resolve_local_artifact(path_value, result_path)
            if not local_path.is_file():
                errors.append(f"$.artifacts.{index}.path: ready local artifact does not exist: {local_path}")
        if artifact.get("editable") is True and artifact.get("format") in {"pdf", "png"}:
            warnings.append(f"$.artifacts.{index}.editable: {artifact.get('format')} is normally not the editable source")
    return artifact_ids


PROFESSIONAL_ARTIFACT_FORMATS = {"xlsx", "docx", "pptx"}
PROFESSIONAL_ARTIFACT_SUFFIXES = (".xlsx", ".docx", ".pptx")


def _validate_governance_tier(
    result: dict[str, Any],
    errors: list[str],
) -> None:
    """light tier results must not carry professional editable artifacts or external side effects."""
    if result.get("governance_tier") != "light":
        return
    for index, artifact in enumerate(result.get("artifacts", [])):
        if not isinstance(artifact, dict):
            continue
        artifact_format = artifact.get("format")
        path_value = artifact.get("path")
        is_professional = (
            isinstance(artifact_format, str) and artifact_format.lower() in PROFESSIONAL_ARTIFACT_FORMATS
        ) or (
            isinstance(path_value, str) and path_value.lower().endswith(PROFESSIONAL_ARTIFACT_SUFFIXES)
        )
        if is_professional:
            errors.append(
                f"$.artifacts.{index}: governance_tier=light must not include editable professional "
                "artifacts (xlsx/docx/pptx); rerun the request under the full tier"
            )
    execution = result.get("execution")
    if isinstance(execution, dict) and execution.get("external_side_effect") is True:
        errors.append(
            "$.execution: governance_tier=light must not declare external_side_effect=true; "
            "rerun the request under the full tier"
        )


def _validate_trade_planning(
    payload: dict[str, Any],
    execution: dict[str, Any] | None,
    errors: list[str],
) -> None:
    """Enforce the non-overridable plan-only boundary for every trade-planning result."""

    if not isinstance(execution, dict):
        errors.append("$.execution: trade-planning requires an explicit no-side-effect execution object")
    else:
        if execution.get("external_side_effect") is not False:
            errors.append("$.execution.external_side_effect: trade-planning must always be false")
        if execution.get("confirmation_status") != "not_applicable":
            errors.append("$.execution.confirmation_status: trade-planning must be not_applicable")

    if payload.get("manual_execution_notice") != MANUAL_EXECUTION_NOTICE:
        errors.append("$.payload.manual_execution_notice: required immutable SKILL-capability notice is missing")
    disposition = payload.get("transaction_request_disposition")
    if disposition not in {
        "no_transaction_requested",
        "redirected_to_manual_plan",
    }:
        errors.append("$.payload.transaction_request_disposition: invalid plan-only disposition")

    order_plan = payload.get("order_plan")
    if isinstance(order_plan, dict):
        if order_plan.get("status") != "proposed_unsubmitted":
            errors.append("$.payload.order_plan.status: must remain proposed_unsubmitted")
        if order_plan.get("platform_verification_required") is not True:
            errors.append("$.payload.order_plan.platform_verification_required: must be true")

    if disposition == "redirected_to_manual_plan":
        if payload.get("mode") != "manual_plan":
            errors.append(
                "$.payload.mode: a redirected transaction request must be handled in manual_plan mode"
            )
        if not isinstance(order_plan, dict) and not payload.get("errors"):
            errors.append(
                "$.payload.order_plan: a redirected transaction request requires a proposed manual plan "
                "or an explicit planning error"
            )
        action_steps = payload.get("user_action_steps")
        if not isinstance(action_steps, list) or len(action_steps) < 3:
            errors.append(
                "$.payload.user_action_steps: a redirected transaction request requires at least three "
                "user-controlled verification and self-execution steps"
            )
        plan_checks = payload.get("plan_checks")
        has_user_verification = isinstance(plan_checks, list) and any(
            isinstance(check, dict) and check.get("status") == "user_verification_required"
            for check in plan_checks
        )
        if not has_user_verification:
            errors.append(
                "$.payload.plan_checks: a redirected transaction request requires at least one "
                "user_verification_required check"
            )

    def visit(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = (*path, str(key))
                normalized_key = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
                if normalized_key in FORBIDDEN_TRANSACTION_KEYS:
                    errors.append(
                        f"{_format_path(child_path)}: transaction execution field is forbidden in trade-planning"
                    )
                if normalized_key in {"status", "state"} and isinstance(child, str):
                    normalized_state = re.sub(r"[^a-z0-9]+", "_", child.lower()).strip("_")
                    if normalized_state in FORBIDDEN_TRANSACTION_STATES:
                        errors.append(
                            f"{_format_path(child_path)}: executed transaction state is forbidden in trade-planning"
                        )
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, (*path, str(index)))

    visit(payload, ("payload",))


def _validate_corporate_finance(
    result: dict[str, Any],
    artifact_ids: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    payload = result.get("payload")
    if not isinstance(payload, dict):
        return

    task_index = _load_task_index()
    task_ids = payload.get("specialist_tasks", [])
    task_results = payload.get("task_results", [])
    requested = {item for item in task_ids if isinstance(item, str)}
    returned = {
        item.get("task_id")
        for item in task_results
        if isinstance(item, dict) and isinstance(item.get("task_id"), str)
    }
    if requested != returned:
        errors.append(
            "$.payload.task_results: task IDs must exactly match specialist_tasks; "
            f"missing={sorted(requested - returned)}, unexpected={sorted(returned - requested)}"
        )

    unknown = sorted(requested - set(task_index))
    if unknown:
        errors.append(f"$.payload.specialist_tasks: unknown task IDs {unknown}")

    model_tasks = {
        task_id
        for task_id in requested
        if task_index.get(task_id, {}).get("group") in MODEL_TASK_GROUPS
    }
    model_checks = payload.get("model_checks")
    if model_tasks and not model_checks:
        errors.append(
            "$.payload.model_checks: model, valuation, LBO or returns tasks require explicit checks"
        )

    for index, task_result in enumerate(task_results):
        if not isinstance(task_result, dict):
            continue
        for artifact_ref in task_result.get("artifact_refs", []):
            if artifact_ref not in artifact_ids:
                errors.append(
                    f"$.payload.task_results.{index}.artifact_refs: unknown artifact_id {artifact_ref!r}"
                )

    artifact_paths = {
        item.get("path")
        for item in result.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    for index, deliverable in enumerate(payload.get("deliverables", [])):
        if not isinstance(deliverable, dict):
            continue
        status = deliverable.get("status")
        path_value = deliverable.get("path")
        if status == "ready" and not path_value:
            errors.append(f"$.payload.deliverables.{index}.path: ready deliverable requires a path")
        if status == "ready" and path_value not in artifact_paths:
            errors.append(
                f"$.payload.deliverables.{index}: ready deliverable must match a top-level artifact path"
            )

    materials_review = payload.get("materials_review")
    materials_tasks_requested = requested & MATERIALS_REVIEW_TASKS
    if materials_tasks_requested and not isinstance(materials_review, dict):
        errors.append(
            "$.payload.materials_review: existing-material tasks "
            f"{sorted(materials_tasks_requested)} require the materials_review payload"
        )
    if isinstance(materials_review, dict):
        review_task = materials_review.get("task_type")
        if review_task not in materials_tasks_requested:
            errors.append(
                "$.payload.materials_review.task_type: must be one of the requested "
                f"existing-material specialist_tasks {sorted(materials_tasks_requested) or '[]'}"
            )

    review_status = payload.get("review_status")
    if isinstance(review_status, dict):
        overall = review_status.get("overall")
        result_status = result.get("status")
        failed_checks = [
            item.get("name")
            for item in model_checks or []
            if isinstance(item, dict) and item.get("status") == "failed"
        ]
        if overall == "ready" and result_status != "complete":
            errors.append("$.payload.review_status.overall: ready requires top-level status=complete")
        if overall == "ready" and failed_checks:
            errors.append(
                f"$.payload.review_status.overall: ready is incompatible with failed checks {failed_checks}"
            )
        if result_status == "complete" and overall != "ready":
            warnings.append(
                "$.payload.review_status.overall: complete result normally requires corporate review status ready"
            )


def validate_result(
    result: dict[str, Any],
    schema_path: Path | None = None,
    result_path: Path | None = None,
) -> dict[str, Any]:
    """Return a deterministic validation report without mutating the result."""

    errors: list[str] = []
    warnings: list[str] = []
    schema_file = schema_path or DEFAULT_SCHEMA

    try:
        Draft202012Validator, FormatChecker, runtime = _jsonschema_api()
    except RuntimePreparationError as error:
        return {
            "status": "blocked",
            "schema": str(schema_file),
            "runtime": {"status": "blocked", **error.state},
            "errors": [f"runtime preparation failed: {error}"],
            "warnings": [],
        }

    try:
        schema = _load_json(schema_file)
        if not isinstance(schema, dict):
            raise ValueError("schema top-level value must be an object")
        Draft202012Validator.check_schema(schema)
        errors.extend(_schema_errors(result, schema, Draft202012Validator, FormatChecker))
        errors.extend(_top_level_temporal_errors(result))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"schema loading failed: {error}")
    except Exception as error:  # jsonschema exposes implementation-specific schema errors
        errors.append(f"invalid schema: {error}")

    module = result.get("primary_module")
    chain = result.get("module_chain")
    presentation = result.get("presentation")
    if isinstance(chain, list) and chain:
        if len(chain) != len(set(chain)):
            errors.append("$.module_chain: must not contain duplicate modules")
        if module is not None and module not in chain:
            errors.append("$.module_chain: must include primary_module")
        elif module is not None and chain[-1] != module:
            errors.append("$.module_chain: primary_module must be the final delivery node")
        known_chain = [item for item in chain if item in MODULE_ORDER_INDEX]
        expected_chain = sorted(known_chain, key=MODULE_ORDER_INDEX.__getitem__)
        if known_chain != expected_chain:
            errors.append("$.module_chain: modules must follow framework dependency order")
    if isinstance(presentation, dict) and presentation.get("profile") != module:
        errors.append("$.presentation.profile: must equal primary_module")

    if result.get("skill_financial_transaction_possible") is not False:
        errors.append(
            "$.skill_financial_transaction_possible: must always be false; this SKILL cannot execute "
            "real financial transactions, while the user remains free to act independently outside it"
        )

    status = result.get("status")
    data_gaps = result.get("data_gaps")
    if status == "complete" and isinstance(data_gaps, list) and data_gaps:
        warnings.append("$.status: complete result contains data_gaps; confirm gaps are immaterial or use provisional")
    if status in {"insufficient_data", "failed", "blocked"}:
        risks = result.get("risks")
        if not data_gaps and not risks:
            warnings.append("$.status: non-complete result should explain data gaps or risks")

    execution = result.get("execution")
    if isinstance(execution, dict):
        side_effect = execution.get("external_side_effect")
        confirmation = execution.get("confirmation_status")
        if side_effect is True and confirmation != "confirmed":
            errors.append("$.execution: external_side_effect=true requires confirmation_status=confirmed")
        if side_effect is False and confirmation == "confirmed":
            warnings.append("$.execution: confirmed without an external side effect; verify status is intentional")

    payload = result.get("payload")
    if module == "trade-planning" and isinstance(payload, dict):
        _validate_trade_planning(payload, execution if isinstance(execution, dict) else None, errors)

    declared_refs = {
        item.get("source_ref")
        for item in result.get("source_manifest", [])
        if isinstance(item, dict) and isinstance(item.get("source_ref"), str)
    }
    used_refs = _collect_source_refs(result)
    missing_refs = sorted(used_refs - declared_refs)
    if missing_refs:
        errors.append(f"$.source_manifest: missing referenced sources {missing_refs}")

    artifact_ids = _validate_artifacts(result, result_path, errors, warnings)
    _validate_governance_tier(result, errors)
    if module == "corporate-finance":
        _validate_corporate_finance(result, artifact_ids, errors, warnings)

    serialized = json.dumps(result, ensure_ascii=False)
    if SECRET_VALUE.search(serialized):
        errors.append("possible credential or secret in result")
    if FULL_WALLET.search(serialized):
        warnings.append("full wallet address detected; mask unless strictly required and authorized")
    if EMAIL.search(serialized):
        warnings.append("email address detected; confirm necessity and authorization")
    if SENSITIVE_IDENTIFIER.search(serialized):
        warnings.append("possible full personal or financial identifier detected; minimize or mask")

    template_path = ROOT / "templates" / f"{module}.md"
    if isinstance(module, str) and not template_path.is_file():
        errors.append(f"missing presentation template: {template_path.relative_to(ROOT)}")

    return {
        "status": "passed" if not errors else "failed",
        "schema": str(schema_file),
        "runtime": runtime,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="Path to result JSON")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--warnings-as-errors", action="store_true")
    args = parser.parse_args()

    try:
        data = _load_json(args.result)
        if not isinstance(data, dict):
            raise ValueError("top-level JSON value must be an object")
        report = validate_result(data, args.schema, args.result.resolve())
    except (OSError, json.JSONDecodeError, ValueError) as error:
        report = {
            "status": "failed",
            "schema": str(args.schema),
            "errors": [str(error)],
            "warnings": [],
        }

    if args.warnings_as_errors and report["warnings"]:
        report["status"] = "failed"
        report["errors"].extend(f"warning promoted to error: {item}" for item in report["warnings"])

    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
