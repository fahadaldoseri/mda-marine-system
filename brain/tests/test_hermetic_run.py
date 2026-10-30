#!/usr/bin/env python3
"""Live regression tests for the hermetic command runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "hermetic_run.sh"
EVIDENCE_DIR = ROOT / "evidence" / "hermetic"


def run_runner(*args: str, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(RUNNER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def evidence_after(before: set[Path]) -> tuple[Path, dict]:
    created = sorted(EVIDENCE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime_ns)
    new = [path for path in created if path not in before]
    assert new, f"no evidence JSON created; stdout/stderr should explain failure"
    path = new[-1]
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_help_is_successful() -> None:
    result = run_runner("--help")
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
    assert "--timeout" in result.stdout


def test_unknown_runner_option_is_usage_error() -> None:
    result = run_runner("--unknown-runner-option")
    assert result.returncode == 2
    assert "unknown" in (result.stderr + result.stdout).lower()


def test_read_only_command_runs_and_emits_evidence() -> None:
    before = set(EVIDENCE_DIR.glob("*.json"))
    result = run_runner(
        "--timeout",
        "10",
        "--",
        sys.executable,
        "-c",
        "from pathlib import Path; print(Path('/home/ubuntu/brain-marine-news/CLAUDE.md').read_text().splitlines()[0])",
    )
    assert result.returncode == 0, result.stderr
    assert "CLAUDE.md" in result.stdout
    evidence_path, evidence = evidence_after(before)
    assert evidence_path.exists()
    assert evidence["exit_code"] == 0
    assert evidence["changed_files_outside_isolation"] == 0
    assert evidence["net_packets"] == 0
    assert Path(evidence["trace"]).exists()


def test_project_write_is_contained_and_project_stays_unchanged() -> None:
    target = ROOT / f".hermetic-write-attempt-{os.getpid()}-{time.time_ns()}"
    script = Path("/var/tmp") / f"hermetic-write-attempt-{os.getpid()}-{time.time_ns()}.py"
    script.write_text(
        textwrap.dedent(
            f"""
            from pathlib import Path
            target = Path({str(target)!r})
            try:
                target.write_text('must not reach the host project', encoding='utf-8')
            except OSError as exc:
                print(f'WRITE_FAILED:{{exc.__class__.__name__}}')
                raise SystemExit(7)
            print('WRITE_UNEXPECTEDLY_SUCCEEDED')
            raise SystemExit(8)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    try:
        before = set(EVIDENCE_DIR.glob("*.json"))
        result = run_runner("--timeout", "10", "--", sys.executable, str(script))
        assert result.returncode == 7, result.stderr
        assert "WRITE_FAILED" in result.stdout
        assert not target.exists(), "the host project was modified by the negative test"
        _, evidence = evidence_after(before)
        assert evidence["changed_files_outside_isolation"] == 0
        assert evidence["impact_summary"]["files_opened_for_write"]
    finally:
        script.unlink(missing_ok=True)


def test_network_attempt_fails_and_packet_count_is_zero() -> None:
    before = set(EVIDENCE_DIR.glob("*.json"))
    result = run_runner(
        "--timeout",
        "10",
        "--",
        sys.executable,
        "-c",
        "import socket; socket.create_connection(('1.1.1.1', 80), 3)",
    )
    assert result.returncode != 0
    _, evidence = evidence_after(before)
    assert evidence["net_packets"] == 0
    assert evidence["network_proof"]["exit_code"] != 0
    assert evidence["impact_summary"]["connect_attempts"] >= 1


def test_timeout_kills_long_running_command_with_clear_code() -> None:
    before = set(EVIDENCE_DIR.glob("*.json"))
    result = run_runner(
        "--timeout",
        "1",
        "--",
        sys.executable,
        "-c",
        "while True: pass",
        timeout=15,
    )
    assert result.returncode == 124, result.stderr
    _, evidence = evidence_after(before)
    assert evidence["exit_code"] == 124
    assert evidence["timeout_enforced"] is True
    assert evidence["changed_files_outside_isolation"] == 0
