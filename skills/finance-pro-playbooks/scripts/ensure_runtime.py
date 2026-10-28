#!/usr/bin/env python3
"""Prepare and verify the deterministic runtime required by Finance Analysis Pro."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = ROOT / "requirements.lock"
RUNTIME_CONTRACT = "finance-analysis-pro/runtime/1.0"
DEPENDENCY = "jsonschema"
REQUIRED_SPECIFIER = ">=4.18,<5"
MINIMUM_VERSION = (4, 18)
MAXIMUM_VERSION = (5, 0)
INSTALL_TIMEOUT_SECONDS = 180
DISABLE_AUTO_INSTALL_ENV = "FINANCE_SKILL_DISABLE_AUTO_INSTALL"

CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class RuntimePreparationError(RuntimeError):
    """Raised when the full validation runtime cannot be prepared safely."""

    def __init__(self, message: str, *, state: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.state = state or {}


def _parse_release(version: str) -> tuple[int, ...]:
    values: list[int] = []
    for component in version.split("+")[0].split("-")[0].split("."):
        digits = "".join(character for character in component if character.isdigit())
        if not digits:
            break
        values.append(int(digits))
    if not values:
        raise ValueError(f"unrecognized version: {version!r}")
    return tuple(values)


def _is_supported(version: str) -> bool:
    release = _parse_release(version)
    return release >= MINIMUM_VERSION and release < MAXIMUM_VERSION


def _probe_jsonschema() -> tuple[bool, str | None]:
    command = [
        sys.executable,
        "-c",
        (
            "from jsonschema import Draft202012Validator, FormatChecker; "
            "assert Draft202012Validator and FormatChecker"
        ),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return False, str(error)
    if completed.returncode == 0:
        return True, None
    detail = (completed.stderr or completed.stdout or "import probe failed").strip()
    return False, detail[-1000:]


def inspect_runtime() -> dict[str, Any]:
    """Return a machine-readable dependency state without changing the environment."""

    try:
        version = importlib.metadata.version(DEPENDENCY)
    except importlib.metadata.PackageNotFoundError:
        return {
            "runtime_contract": RUNTIME_CONTRACT,
            "status": "missing",
            "dependency": DEPENDENCY,
            "required": REQUIRED_SPECIFIER,
            "version": None,
        }

    try:
        supported = _is_supported(version)
    except ValueError as error:
        return {
            "runtime_contract": RUNTIME_CONTRACT,
            "status": "incompatible",
            "dependency": DEPENDENCY,
            "required": REQUIRED_SPECIFIER,
            "version": version,
            "detail": str(error),
        }
    if not supported:
        return {
            "runtime_contract": RUNTIME_CONTRACT,
            "status": "incompatible",
            "dependency": DEPENDENCY,
            "required": REQUIRED_SPECIFIER,
            "version": version,
        }

    importable, detail = _probe_jsonschema()
    if not importable:
        return {
            "runtime_contract": RUNTIME_CONTRACT,
            "status": "broken",
            "dependency": DEPENDENCY,
            "required": REQUIRED_SPECIFIER,
            "version": version,
            "detail": detail,
        }

    return {
        "runtime_contract": RUNTIME_CONTRACT,
        "status": "ready",
        "dependency": DEPENDENCY,
        "required": REQUIRED_SPECIFIER,
        "version": version,
    }


def _validate_lock_file() -> None:
    if not LOCK_FILE.is_file():
        raise RuntimePreparationError(
            f"locked dependency file is missing: {LOCK_FILE}",
            state={"status": "blocked", "dependency": DEPENDENCY},
        )
    declarations = {
        line.strip()
        for line in LOCK_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not any(line.startswith(f"{DEPENDENCY}==") for line in declarations):
        raise RuntimePreparationError(
            f"{LOCK_FILE.name} must pin {DEPENDENCY} with ==",
            state={"status": "blocked", "dependency": DEPENDENCY},
        )


def _default_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        timeout=INSTALL_TIMEOUT_SECONDS,
        check=False,
    )


def _install_locked(runner: CommandRunner) -> dict[str, Any]:
    _validate_lock_file()
    commands = (
        ("sudo", "uv", "pip", "install", "--system", "--requirement", str(LOCK_FILE)),
        (
            "sudo",
            "pip3",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--requirement",
            str(LOCK_FILE),
        ),
    )
    attempts: list[dict[str, Any]] = []
    for command in commands:
        try:
            completed = runner(command)
        except (OSError, subprocess.SubprocessError) as error:
            attempts.append({"command": command[1], "returncode": None, "detail": str(error)})
            continue
        detail = (completed.stderr or completed.stdout or "").strip()
        attempts.append(
            {
                "command": command[1],
                "returncode": completed.returncode,
                "detail": detail[-1000:] if detail else None,
            }
        )
        if completed.returncode == 0:
            return {"installer": command[1], "attempts": attempts}
    raise RuntimePreparationError(
        "unable to install the locked Finance Analysis Pro runtime",
        state={"status": "blocked", "dependency": DEPENDENCY, "attempts": attempts},
    )


def ensure_runtime(
    *,
    allow_install: bool = True,
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Ensure the full validator dependency is ready, or raise without degrading."""

    before = inspect_runtime()
    if before["status"] == "ready":
        return {**before, "action": "none"}

    disabled = os.environ.get(DISABLE_AUTO_INSTALL_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not allow_install or disabled:
        reason = "automatic installation is disabled" if disabled else "check-only mode"
        raise RuntimePreparationError(
            f"{DEPENDENCY} runtime is {before['status']} and {reason}",
            state={**before, "status": "blocked", "action": "none"},
        )

    installation = _install_locked(runner or _default_runner)
    importlib.invalidate_caches()
    after = inspect_runtime()
    if after["status"] != "ready":
        raise RuntimePreparationError(
            f"{DEPENDENCY} remained {after['status']} after locked installation",
            state={**after, "status": "blocked", "action": "install_failed", **installation},
        )
    return {**after, "action": "installed", **installation}


def _write_payload(payload: dict[str, Any], output: Path | None) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Check without installing missing dependencies")
    parser.add_argument("--output", type=Path, help="Write the machine-readable runtime status to a file")
    args = parser.parse_args()

    try:
        payload = ensure_runtime(allow_install=not args.check_only)
        _write_payload(payload, args.output)
        return 0
    except RuntimePreparationError as error:
        payload = {
            "runtime_contract": RUNTIME_CONTRACT,
            "status": "blocked",
            "dependency": DEPENDENCY,
            "required": REQUIRED_SPECIFIER,
            "error": str(error),
            **error.state,
        }
        _write_payload(payload, args.output)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
