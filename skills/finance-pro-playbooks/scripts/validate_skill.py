#!/usr/bin/env python3
"""Validate the structure and internal consistency of finance-pro-playbooks."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_REFERENCES = {
    "routing-catalog.md",
    "equity-research.md",
    "fund-etf.md",
    "options-strategy.md",
    "crypto-analysis.md",
    "portfolio-management.md",
    "quant-backtesting.md",
    "trade-planning.md",
    "corporate-finance.md",
    "metric-dictionary.md",
    "data-source-policy.md",
    "scoring-standard.md",
    "privacy-security.md",
    "execution-safety.md",
    "output-contracts.md",
}

REQUIRED_SCRIPTS = {
    "route_request.py",
    "finance_metrics.py",
    "ensure_runtime.py",
    "validate_skill.py",
    "validate_result.py",
    "render_report.py",
}

REQUIRED_TEMPLATES = {
    "equity-research.md",
    "fund-etf.md",
    "options-strategy.md",
    "crypto-analysis.md",
    "portfolio-management.md",
    "quant-backtesting.md",
    "trade-planning.md",
    "corporate-finance.md",
}

REQUIRED_SCHEMA_VERSION = "finance-analysis-pro/1.2"
REQUIRED_LOCKED_REQUIREMENTS = {
    "attrs==26.1.0",
    "jsonschema==4.26.0",
    "jsonschema-specifications==2025.9.1",
    "referencing==0.37.0",
    "rpds-py==2026.6.3",
    "typing-extensions==4.16.0",
}
IMPORTANT_NOTICE_HEADING = '## Important Notice'
IMPORTANT_NOTICE_TEXT = (
    "This analysis is based on the data and assumptions stated above and does not guarantee future performance. "
    "It does not constitute legal, tax, accounting, or personalized investment advice. The SKILL did not and cannot "
    "place, modify, cancel, sign, transmit, or submit a financial transaction. This capability limit applies only to "
    "the SKILL and the tools or agents operating within it; it does not restrict the user's independent activity "
    "outside the SKILL. If the user chooses to transact, they may do so independently on the relevant broker, "
    "exchange, wallet, or other platform."
)
IMPORTANT_NOTICE_BLOCK = f"{IMPORTANT_NOTICE_HEADING}\n\n{IMPORTANT_NOTICE_TEXT}"
EXPECTED_TASK_COUNT = 54
EXPECTED_PLUGIN_GROUPS = {
    "market-research",
    "company-analysis",
    "valuation",
    "financial-models",
    "lbo-structuring",
    "returns-analysis",
    "due-diligence",
    "deal-materials",
}
EXPECTED_FORMAT_KEYS = {"excel", "document", "metrics"}

EXCLUDED_PATH_TOKEN_SEQUENCES = (
    ("agent", "workflow", "optimizer"),
    ("real", "estate", "investment", "suite"),
)

DOMAIN_REQUIRED_REFERENCES: dict[str, set[str]] = {
    "equity-research.md": {"data-source-policy.md", "metric-dictionary.md", "scoring-standard.md", "output-contracts.md"},
    "fund-etf.md": {"data-source-policy.md", "metric-dictionary.md", "scoring-standard.md", "output-contracts.md"},
    "options-strategy.md": {"data-source-policy.md", "metric-dictionary.md", "output-contracts.md"},
    "crypto-analysis.md": {"data-source-policy.md", "metric-dictionary.md", "output-contracts.md"},
    "portfolio-management.md": {"data-source-policy.md", "metric-dictionary.md", "scoring-standard.md", "privacy-security.md", "output-contracts.md"},
    "quant-backtesting.md": {"data-source-policy.md", "metric-dictionary.md", "scoring-standard.md", "output-contracts.md"},
    "trade-planning.md": {"data-source-policy.md", "metric-dictionary.md", "privacy-security.md", "execution-safety.md", "output-contracts.md"},
    "corporate-finance.md": {"data-source-policy.md", "metric-dictionary.md", "output-contracts.md"},
}

DOMAIN_CONDITIONAL_REFERENCES: dict[str, set[str]] = {
    "equity-research.md": {"privacy-security.md", "execution-safety.md"},
    "fund-etf.md": {"privacy-security.md", "execution-safety.md"},
    "options-strategy.md": {"scoring-standard.md", "privacy-security.md", "execution-safety.md"},
    "crypto-analysis.md": {"scoring-standard.md", "privacy-security.md", "execution-safety.md"},
    "portfolio-management.md": {"execution-safety.md"},
    "quant-backtesting.md": {"privacy-security.md", "execution-safety.md"},
    "trade-planning.md": set(),
    "corporate-finance.md": {"scoring-standard.md", "privacy-security.md", "execution-safety.md"},
}

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|private[_-]?key)\s*[:=]\s*['\"](?!\[redacted)[A-Za-z0-9_\-/.+=]{12,}['\"]"
)
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter is not closed")
    raw = text[4:end]
    body = text[end + 5 :]
    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, body


def _read_json(path: Path, errors: list[str], skill_root: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"invalid JSON in {path.relative_to(skill_root)}: {error}")
        return None


def _scan_file(path: Path, skill_root: Path, errors: list[str], warnings: list[str]) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    relative = path.relative_to(skill_root)
    if SECRET_ASSIGNMENT.search(content):
        errors.append(f"possible hardcoded secret in {relative}")
    for match in EMAIL.finditer(content):
        warnings.append(f"possible email in {relative}: {match.group(0)}")

    if path.suffix == ".py":
        try:
            ast.parse(content, filename=str(path))
        except SyntaxError as error:
            errors.append(f"Python syntax error in {relative}: {error}")

    if path.suffix == ".md":
        for target in MARKDOWN_LINK.findall(content):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean_target = target.split("#", 1)[0]
            if not clean_target:
                continue
            resolved = (path.parent / clean_target).resolve()
            try:
                resolved.relative_to(skill_root.resolve())
            except ValueError:
                errors.append(f"link escapes Skill root in {relative}: {target}")
                continue
            if not resolved.exists():
                errors.append(f"broken local link in {relative}: {target}")


def _validate_domain_documents(
    references_dir: Path,
    errors: list[str],
) -> int:
    declaration_count = 0
    for filename, expected_required in DOMAIN_REQUIRED_REFERENCES.items():
        path = references_dir / filename
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        if content.count("## Common Dependency Declaration") != 1:
            errors.append(f"domain reference must contain exactly one dependency declaration: {filename}")
            continue
        declaration_count += 1
        if "## Output Contract" in content:
            errors.append(f"duplicate output contract remains in {filename}")
        if content.count("## Output Format") != 1:
            errors.append(f"domain reference must contain exactly one output format section: {filename}")

        required_rows = set(re.findall(r"\|\s*Required\s*\|\s*\[`([^`]+\.md)`\]\([^)]+\)", content))
        conditional_rows = set(re.findall(r"\|\s*Conditional\s*\|\s*\[`([^`]+\.md)`\]\([^)]+\)", content))
        expected_conditional = DOMAIN_CONDITIONAL_REFERENCES[filename]
        missing_required = sorted(expected_required - required_rows)
        extra_required = sorted(required_rows - expected_required)
        missing_conditional = sorted(expected_conditional - conditional_rows)
        extra_conditional = sorted(conditional_rows - expected_conditional)
        if missing_required:
            errors.append(f"missing required dependency rows in {filename}: {missing_required}")
        if extra_required:
            errors.append(f"unexpected required dependency rows in {filename}: {extra_required}")
        if missing_conditional:
            errors.append(f"missing conditional dependency rows in {filename}: {missing_conditional}")
        if extra_conditional:
            errors.append(f"unexpected conditional dependency rows in {filename}: {extra_conditional}")

        module = path.stem
        markers = (
            f"primary_module={module}",
            f"presentation.profile={module}",
            f"../templates/{module}.md",
            REQUIRED_SCHEMA_VERSION,
            "validate_result.py",
        )
        for marker in markers:
            if marker not in content:
                errors.append(f"missing output format marker in {filename}: {marker}")
    return declaration_count


def _validate_task_catalog(
    skill_root: Path,
    errors: list[str],
    warnings: list[str],
) -> tuple[int, int, int, set[str]]:
    plugin_dir = skill_root / "references" / "corporate-finance"
    catalog_path = plugin_dir / "task-catalog.json"
    if not catalog_path.is_file():
        errors.append("corporate-finance task catalog is missing")
        return 0, 0, 0, set()

    catalog = _read_json(catalog_path, errors, skill_root)
    if not isinstance(catalog, dict):
        return 0, 0, 0, set()
    if catalog.get("catalog_version") != "1.0":
        errors.append("corporate-finance catalog_version must be 1.0")
    if catalog.get("primary_module") != "corporate-finance":
        errors.append("corporate-finance catalog primary_module is invalid")

    format_registry = catalog.get("format_registry")
    if not isinstance(format_registry, dict):
        errors.append("corporate-finance format_registry must be an object")
        format_registry = {}
    if set(format_registry) != EXPECTED_FORMAT_KEYS:
        errors.append(
            f"corporate-finance format registry must use {sorted(EXPECTED_FORMAT_KEYS)}, got {sorted(format_registry)}"
        )
    for key, relative_path in format_registry.items():
        if not isinstance(relative_path, str) or not (skill_root / relative_path).is_file():
            errors.append(f"corporate-finance format resource missing for {key}: {relative_path!r}")

    tasks = catalog.get("tasks")
    if not isinstance(tasks, list):
        errors.append("corporate-finance tasks must be a list")
        return 0, 0, len(format_registry), set()
    if len(tasks) != EXPECTED_TASK_COUNT:
        errors.append(f"corporate-finance task count must be {EXPECTED_TASK_COUNT}, got {len(tasks)}")

    task_ids: set[str] = set()
    groups: set[str] = set()
    playbooks: set[str] = set()
    for index, task in enumerate(tasks):
        location = f"references/corporate-finance/task-catalog.json#tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{location} must be an object")
            continue
        missing = sorted({"id", "label", "group", "playbook", "playbook_overview", "formats", "artifacts", "patterns"} - set(task))
        if missing:
            errors.append(f"{location} missing fields: {missing}")
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", task_id):
            errors.append(f"{location}.id must be lowercase kebab-case")
        elif task_id in task_ids:
            errors.append(f"duplicate corporate-finance task id: {task_id}")
        else:
            task_ids.add(task_id)
        group = task.get("group")
        if isinstance(group, str):
            groups.add(group)
        playbook = task.get("playbook")
        expected_playbook = f"references/corporate-finance/playbooks/{group}/{task_id}.md"
        if playbook != expected_playbook:
            errors.append(f"{location}.playbook must be task-level path {expected_playbook!r}, got {playbook!r}")
        elif not (skill_root / playbook).is_file():
            errors.append(f"{location}.playbook file is missing: {playbook!r}")
        else:
            playbooks.add(playbook)
            label = task.get("label")
            if isinstance(label, str):
                text = (skill_root / playbook).read_text(encoding="utf-8")
                if label.lower() not in text.lower():
                    warnings.append(f"task label not found verbatim in playbook for {task_id}: {label}")
        overview = task.get("playbook_overview")
        expected_overview = f"references/corporate-finance/playbooks/{group}/_overview.md"
        if overview != expected_overview or not (skill_root / expected_overview).is_file():
            errors.append(
                f"{location}.playbook_overview must be {expected_overview!r} and the file must exist, got {overview!r}"
            )
        formats = task.get("formats")
        if not isinstance(formats, list) or not all(isinstance(item, str) for item in formats):
            errors.append(f"{location}.formats must be a string array")
        else:
            unknown_formats = sorted(set(formats) - set(format_registry))
            if unknown_formats:
                errors.append(f"{location}.formats contains unknown keys: {unknown_formats}")
        for field in ("artifacts", "patterns"):
            values = task.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(item, str) and item for item in values):
                errors.append(f"{location}.{field} must be a non-empty string array")
        patterns = task.get("patterns")
        if isinstance(patterns, list):
            for pattern in patterns:
                if not isinstance(pattern, str):
                    continue
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error as error:
                    errors.append(f"invalid route pattern for {task_id}: {pattern!r}: {error}")

    if groups != EXPECTED_PLUGIN_GROUPS:
        errors.append(
            f"corporate-finance groups mismatch: expected {sorted(EXPECTED_PLUGIN_GROUPS)}, got {sorted(groups)}"
        )
    playbooks_dir = skill_root / "references/corporate-finance/playbooks"
    for group in EXPECTED_PLUGIN_GROUPS:
        if not (playbooks_dir / group / "_overview.md").is_file():
            errors.append(f"playbook group overview missing: playbooks/{group}/_overview.md")
    if playbooks_dir.is_dir():
        catalog_playbooks = {
            str(path.relative_to(skill_root))
            for path in playbooks_dir.rglob("*.md")
            if path.name != "_overview.md"
        }
        orphans = sorted(catalog_playbooks - playbooks)
        if orphans:
            errors.append(f"task-level playbook files not referenced by task catalog: {orphans}")
    return len(tasks), len(playbooks), len(format_registry), task_ids


def _validate_schema(
    schema_path: Path,
    expected_profiles: set[str],
    catalog_task_ids: set[str],
    errors: list[str],
    skill_root: Path,
) -> None:
    if not schema_path.is_file():
        errors.append("finance-analysis result JSON Schema is missing")
        return
    schema = _read_json(schema_path, errors, skill_root)
    if not isinstance(schema, dict):
        return
    version = schema.get("properties", {}).get("schema_version", {}).get("const")
    if version != REQUIRED_SCHEMA_VERSION:
        errors.append(f"schema version must be {REQUIRED_SCHEMA_VERSION}, got {version}")

    payload_routes: dict[str, str] = {}
    for branch in schema.get("allOf", []):
        module = branch.get("if", {}).get("properties", {}).get("primary_module", {}).get("const")
        payload_ref = branch.get("then", {}).get("properties", {}).get("payload", {}).get("$ref")
        if isinstance(module, str) and isinstance(payload_ref, str):
            payload_routes[module] = payload_ref
    if set(payload_routes) != expected_profiles or len(set(payload_routes.values())) != len(expected_profiles):
        errors.append("schema must map exactly nine domain modules to nine unique payload definitions")
    profile_values = set(schema.get("$defs", {}).get("module", {}).get("enum", []))
    if profile_values != expected_profiles:
        errors.append("schema module enum does not match domain templates")

    schema_task_ids = set(
        schema.get("$defs", {})
        .get("corporateFinanceTaskId", {})
        .get("enum", [])
    )
    if schema_task_ids != catalog_task_ids:
        errors.append("corporate-finance task IDs in Schema do not match task catalog")
    if "corporateFinancePayload" not in schema.get("$defs", {}):
        errors.append("schema is missing corporateFinancePayload definition")


def _validate_metric_authority(skill_root: Path, errors: list[str]) -> None:
    """O1 guard: metric_disambiguation must stay a data-source appendix, not a second formula source."""
    appendix = skill_root / "references/corporate-finance/formats/metric_disambiguation.md"
    dictionary = skill_root / "references/metric-dictionary.md"
    if not appendix.is_file() or not dictionary.is_file():
        errors.append("metric authority files missing (metric_disambiguation.md or metric-dictionary.md)")
        return
    appendix_text = appendix.read_text(encoding="utf-8")
    dictionary_text = dictionary.read_text(encoding="utf-8")
    for heading in ("## Custom and Adjusted Metrics", "## General Valuation Discipline"):
        if heading not in dictionary_text:
            errors.append(f"metric-dictionary.md is missing normative section: {heading}")
    sections = re.split(r"^## ", appendix_text, flags=re.MULTILINE)[1:]
    for section in sections:
        title = section.splitlines()[0].strip()
        if "metric-dictionary.md" not in section:
            errors.append(
                f"metric_disambiguation.md section lacks authority link to metric-dictionary.md: {title}"
            )


def _validate_module_catalog(skill_root: Path, errors: list[str]) -> int:
    """Check that references/module-catalog.json is the coherent single source of truth."""
    catalog_path = skill_root / "references" / "module-catalog.json"
    if not catalog_path.is_file():
        errors.append("references/module-catalog.json is missing")
        return 0
    catalog = _read_json(catalog_path, errors, skill_root)
    if not isinstance(catalog, dict):
        return 0
    modules = catalog.get("modules")
    if not isinstance(modules, dict):
        errors.append("module-catalog modules must be an object")
        return 0

    expected_modules = {Path(name).stem for name in REQUIRED_TEMPLATES}
    if set(modules) != expected_modules:
        errors.append(
            f"module-catalog modules mismatch: expected {sorted(expected_modules)}, got {sorted(modules)}"
        )
    for field in ("dependency_order", "primary_priority"):
        values = catalog.get(field)
        if not isinstance(values, list) or set(values) != set(modules) or len(values) != len(modules):
            errors.append(f"module-catalog {field} must be a permutation of module names")
    merge_rules = catalog.get("merge_rules")
    if not isinstance(merge_rules, dict) or not isinstance(merge_rules.get("boundary_rule"), str):
        errors.append("module-catalog merge_rules.boundary_rule must be a string")
    if not isinstance(catalog.get("out_of_scope_patterns"), list):
        errors.append("module-catalog out_of_scope_patterns must be a list")

    for module, spec in modules.items():
        location = f"references/module-catalog.json#modules.{module}"
        if not isinstance(spec, dict):
            errors.append(f"{location} must be an object")
            continue
        reference = spec.get("reference")
        if not isinstance(reference, str) or not (skill_root / reference).is_file():
            errors.append(f"{location}.reference is missing: {reference!r}")
        patterns = spec.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            errors.append(f"{location}.patterns must be a non-empty list")
        else:
            for pattern in patterns:
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error as error:
                    errors.append(f"invalid module pattern for {module}: {pattern!r}: {error}")
        for field in ("required_references",):
            refs = spec.get(field)
            if not isinstance(refs, list) or not all(
                isinstance(item, str) and (skill_root / item).is_file() for item in refs
            ):
                errors.append(f"{location}.{field} contains missing reference files")
        conditional = spec.get("conditional_references")
        if not isinstance(conditional, dict):
            errors.append(f"{location}.conditional_references must be an object")
        else:
            for condition, refs in conditional.items():
                if condition not in {"privacy", "execution", "scoring", "metrics"}:
                    errors.append(f"{location} unknown condition flag: {condition}")
                if not isinstance(refs, list) or not all(
                    isinstance(item, str) and (skill_root / item).is_file() for item in refs
                ):
                    errors.append(f"{location}.conditional_references.{condition} contains missing files")

        # Cross-check with the domain document declaration matrix.
        doc_name = f"{module}.md"
        declared_required = {f"references/{name}" for name in DOMAIN_REQUIRED_REFERENCES.get(doc_name, set())}
        catalog_required = set(spec.get("required_references", []))
        if declared_required and catalog_required != declared_required:
            errors.append(
                f"{location}.required_references diverges from domain declaration matrix: "
                f"catalog={sorted(catalog_required)}, declared={sorted(declared_required)}"
            )
        declared_conditional = {f"references/{name}" for name in DOMAIN_CONDITIONAL_REFERENCES.get(doc_name, set())}
        catalog_conditional = {
            ref for refs in (spec.get("conditional_references") or {}).values() if isinstance(refs, list) for ref in refs
        }
        if catalog_conditional != declared_conditional:
            errors.append(
                f"{location}.conditional_references diverges from domain declaration matrix: "
                f"catalog={sorted(catalog_conditional)}, declared={sorted(declared_conditional)}"
            )
    return len(modules)


def _validate_field_contract_consistency(skill_root: Path, errors: list[str]) -> None:
    """P1-1: normalized fields in SKILL.md must stay consistent with the schema and domain docs."""
    references_dir = skill_root / "references"
    # 1. The deprecated `depth: quick` contract variant must not reappear anywhere.
    for path in references_dir.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"`?depth`?\s*[|:].*quick", text):
            errors.append(f"deprecated field contract `depth: quick/...` found in {path.relative_to(skill_root)}; use `detail_level: brief/standard/deep`")
    # 2. Every audience value in SKILL.md must exist in the schema enum.
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    schema_path = references_dir / "schemas" / "finance-analysis-result.schema.json"
    if schema_path.is_file():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_audience = set(schema.get("$defs", {}).get("presentation", {}).get("properties", {}).get("audience", {}).get("enum", []))
        match = re.search(r"^audience:\s*(.+)$", skill_text, re.MULTILINE)
        if match and schema_audience:
            declared = {token.strip() for token in match.group(1).split("|")}
            orphans = sorted(declared - schema_audience)
            if orphans:
                errors.append(f"SKILL.md audience values missing from schema enum: {orphans}")
        match = re.search(r"^detail_level:\s*(.+)$", skill_text, re.MULTILINE)
        schema_detail = set(schema.get("$defs", {}).get("presentation", {}).get("properties", {}).get("detail_level", {}).get("enum", []))
        if match and schema_detail:
            declared = {token.strip() for token in match.group(1).split("|")}
            orphans = sorted(declared - schema_detail)
            if orphans:
                errors.append(f"SKILL.md detail_level values missing from schema enum: {orphans}")


def _validate_nav_headers(skill_root: Path, errors: list[str]) -> None:
    """B-layer anti-rot: every task playbook's nav header must match its live
    headings and catalog formats (re-derived via gen_nav_headers)."""
    scripts_dir = str(skill_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        import gen_nav_headers as nav
    except Exception as error:  # pragma: no cover
        errors.append(f"nav header validation unavailable: {error}")
        return
    try:
        by_playbook, registry = nav.load_catalog()
    except Exception as error:
        errors.append(f"nav header validation cannot load task catalog: {error}")
        return
    playbooks_dir = skill_root / "references" / "corporate-finance" / "playbooks"
    if not playbooks_dir.is_dir():
        return
    for path in sorted(playbooks_dir.rglob("*.md")):
        if path.name == "_overview.md":
            continue
        rel = str(path.relative_to(skill_root))
        text = path.read_text(encoding="utf-8")
        expected = nav.build_nav(text, by_playbook.get(rel), registry)
        current = nav.NAV_BLOCK.search(text)
        if not current:
            errors.append(f"playbook missing nav header (run scripts/gen_nav_headers.py): {rel}")
        elif current.group(0).rstrip("\n") != expected:
            errors.append(f"stale nav header (run scripts/gen_nav_headers.py): {rel}")


TASK_INDEX_START = "<!-- task-index:start (generated by scripts/validate_skill.py --sync-index; do not edit by hand) -->"
TASK_INDEX_END = "<!-- task-index:end -->"
TASK_INDEX_BLOCK = re.compile(re.escape(TASK_INDEX_START) + r".*?" + re.escape(TASK_INDEX_END), re.DOTALL)


def _build_task_index(skill_root: Path) -> str:
    """C-layer: derive the SKILL.md inline task index from task-catalog.json
    (a validated projection, never a second source of truth)."""
    catalog_path = skill_root / "references" / "corporate-finance" / "task-catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    groups: dict[str, list[dict[str, Any]]] = {}
    for task in catalog["tasks"]:
        groups.setdefault(task["group"], []).append(task)
    lines = [
        TASK_INDEX_START,
        "<details>",
        "<summary>Plugin task quick-access index (generated by task-catalog.json; expand to jump directly to any task-level Playbook)</summary>",
        "",
    ]
    for group in sorted(groups):
        tasks = sorted(groups[group], key=lambda t: t["id"])
        lines.append(f"- **{group}**({len(tasks)}):" + " · ".join(
            f"[`{task['id']}`]({task['playbook']})" for task in tasks
        ))
    lines.extend(["", "</details>", TASK_INDEX_END])
    return "\n".join(lines)


def _sync_task_index(skill_root: Path) -> bool:
    """Rewrite the SKILL.md inline task index. Returns True when file changed."""
    skill_file = skill_root / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")
    if not TASK_INDEX_BLOCK.search(text):
        raise ValueError("SKILL.md has no task-index markers; add the marker pair before syncing")
    new_text = TASK_INDEX_BLOCK.sub(lambda _m: _build_task_index(skill_root), text, count=1)
    if new_text != text:
        skill_file.write_text(new_text, encoding="utf-8")
        return True
    return False


def _validate_task_index(skill_root: Path, errors: list[str]) -> None:
    """C-layer anti-rot: the SKILL.md inline index must match task-catalog.json."""
    skill_file = skill_root / "SKILL.md"
    if not skill_file.is_file():
        return
    text = skill_file.read_text(encoding="utf-8")
    found = TASK_INDEX_BLOCK.search(text)
    if not found:
        errors.append("SKILL.md is missing the inline task index (run validate_skill.py --sync-index)")
        return
    try:
        expected = _build_task_index(skill_root)
    except (OSError, json.JSONDecodeError, KeyError) as error:
        errors.append(f"task index validation cannot load task catalog: {error}")
        return
    if found.group(0) != expected:
        errors.append("SKILL.md inline task index is stale (run validate_skill.py --sync-index)")


def validate(skill_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    skill_file = skill_root / "SKILL.md"
    references_dir = skill_root / "references"
    scripts_dir = skill_root / "scripts"
    templates_dir = skill_root / "templates"
    schema_path = references_dir / "schemas" / "finance-analysis-result.schema.json"
    requirements_path = skill_root / "requirements.txt"
    requirements_lock_path = skill_root / "requirements.lock"

    if not skill_file.is_file():
        return {"status": "failed", "errors": ["SKILL.md is missing"], "warnings": []}

    text = skill_file.read_text(encoding="utf-8")
    try:
        metadata, body = parse_frontmatter(text)
    except ValueError as error:
        metadata, body = {}, text
        errors.append(str(error))

    allowed_keys = {"name", "description"}
    extra_keys = sorted(set(metadata) - allowed_keys)
    missing_keys = sorted(allowed_keys - set(metadata))
    if extra_keys:
        errors.append(f"unsupported frontmatter keys: {extra_keys}")
    if missing_keys:
        errors.append(f"missing frontmatter keys: {missing_keys}")
    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("name must be lowercase kebab-case")
    if len(name) > 64:
        errors.append("name exceeds 64 characters")
    if not description:
        errors.append("description is empty")
    if len(description) > 1024:
        errors.append("description exceeds 1024 characters")
    if "<" in description or ">" in description:
        errors.append("description must not contain angle brackets")
    if len(body.splitlines()) > 500:
        warnings.append("SKILL.md body exceeds 500 lines; progressive disclosure may be weak")

    for marker in (
        "`primary_module`",
        "required_references =",
        "governance_tier",
        "`scripts/ensure_runtime.py`",
        "task-level",
    ):
        if marker not in body:
            errors.append(f"SKILL.md is missing required workflow marker: {marker}")

    if not references_dir.is_dir():
        errors.append("references directory is missing")
    if not scripts_dir.is_dir():
        errors.append("scripts directory is missing")
    if not templates_dir.is_dir():
        errors.append("templates directory is missing")

    actual_references = {path.name for path in references_dir.glob("*.md")} if references_dir.is_dir() else set()
    actual_scripts = {path.name for path in scripts_dir.glob("*.py")} if scripts_dir.is_dir() else set()
    actual_templates = {path.name for path in templates_dir.glob("*.md")} if templates_dir.is_dir() else set()
    missing_references = sorted(REQUIRED_REFERENCES - actual_references)
    missing_scripts = sorted(REQUIRED_SCRIPTS - actual_scripts)
    missing_templates = sorted(REQUIRED_TEMPLATES - actual_templates)
    if missing_references:
        errors.append(f"missing required references: {missing_references}")
    if missing_scripts:
        errors.append(f"missing required scripts: {missing_scripts}")
    if missing_templates:
        errors.append(f"missing required templates: {missing_templates}")
    if not requirements_path.is_file():
        errors.append("requirements.txt is missing")
    elif "jsonschema>=4.18,<5" not in requirements_path.read_text(encoding="utf-8"):
        errors.append("requirements.txt must declare jsonschema>=4.18,<5")

    if not requirements_lock_path.is_file():
        errors.append("requirements.lock is missing")
    else:
        locked_requirements = {
            line.strip()
            for line in requirements_lock_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        if locked_requirements != REQUIRED_LOCKED_REQUIREMENTS:
            errors.append(
                "requirements.lock must exactly match the reviewed Finance Analysis Pro runtime pins"
            )

    forbidden_auxiliary = {"README.md", "CHANGELOG.md", "INSTALLATION.md", "QUICK_REFERENCE.md"}
    for path in skill_root.rglob("*.md"):
        if path.name in forbidden_auxiliary:
            errors.append(f"unnecessary auxiliary document in Skill: {path.relative_to(skill_root)}")

    # Development caches (__pycache__/.pyc/.git) are ignored: they are not part of the
    # published artifact and must not fail validation on a working tree (P1-3).
    ignored_dir_names = {"__pycache__", ".git"}
    for path in skill_root.rglob("*"):
        if any(part in ignored_dir_names for part in path.relative_to(skill_root).parts):
            continue
        if path.is_file() and path.suffix == ".pyc":
            continue
        relative_tokens = tuple(filter(None, re.split(r"[^a-z0-9]+", str(path.relative_to(skill_root)).lower())))
        for sequence in EXCLUDED_PATH_TOKEN_SEQUENCES:
            if all(token in relative_tokens for token in sequence):
                errors.append(f"excluded module path remains in deliverable: {path.relative_to(skill_root)}")
        if path.is_file() and path.suffix in {".md", ".py", ".json", ".txt"}:
            _scan_file(path, skill_root, errors, warnings)
        if path.is_file() and path.suffix == ".json":
            _read_json(path, errors, skill_root)

    declaration_count = _validate_domain_documents(references_dir, errors) if references_dir.is_dir() else 0
    task_count, playbook_count, format_count, task_ids = _validate_task_catalog(skill_root, errors, warnings)
    module_catalog_count = _validate_module_catalog(skill_root, errors)
    _validate_metric_authority(skill_root, errors)
    _validate_field_contract_consistency(skill_root, errors)
    _validate_nav_headers(skill_root, errors)
    _validate_task_index(skill_root, errors)

    template_required_headings = {"## Executive Summary", "## Risks and Failure Conditions", "## Data and Sources", IMPORTANT_NOTICE_HEADING}
    if templates_dir.is_dir():
        for template_name in sorted(REQUIRED_TEMPLATES):
            template_path = templates_dir / template_name
            if not template_path.is_file():
                continue
            template_text = template_path.read_text(encoding="utf-8")
            missing_headings = sorted(heading for heading in template_required_headings if heading not in template_text)
            if missing_headings:
                errors.append(f"template missing required headings in {template_name}: {missing_headings}")
            if IMPORTANT_NOTICE_BLOCK not in template_text:
                errors.append(f"template missing canonical Important Notice text in {template_name}")
            elif not template_text.rstrip().endswith(IMPORTANT_NOTICE_BLOCK):
                errors.append(f"template must end with canonical Important Notice in {template_name}")
            for placeholder in ("{{subject}}", "{{status}}", "{{data_cutoff}}", "{{as_of}}"):
                if placeholder not in template_text:
                    errors.append(f"template missing placeholder in {template_name}: {placeholder}")

    _validate_schema(schema_path, {Path(name).stem for name in REQUIRED_TEMPLATES}, task_ids, errors, skill_root)

    status = "passed" if not errors else "failed"
    return {
        "status": status,
        "skill_root": str(skill_root),
        "metadata": metadata,
        "counts": {
            "references": len(actual_references),
            "scripts": len(actual_scripts),
            "templates": len(actual_templates),
            "schemas": 1 if schema_path.is_file() else 0,
            "skill_body_lines": len(body.splitlines()),
            "domain_dependency_declarations": declaration_count,
            "module_catalog_modules": module_catalog_count,
            "corporate_finance_tasks": task_count,
            "corporate_finance_playbooks": playbook_count,
            "corporate_finance_formats": format_count,
        },
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--sync-index",
        action="store_true",
        help="regenerate the SKILL.md inline task index from task-catalog.json before validating",
    )
    args = parser.parse_args()
    if args.sync_index:
        changed = _sync_task_index(args.skill_root.resolve())
        print(f"task index {'updated' if changed else 'already up to date'}", file=sys.stderr)
    result = validate(args.skill_root.resolve())
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
