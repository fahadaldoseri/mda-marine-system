#!/usr/bin/env python3
"""Run CLI tools in a bwrap sandbox and record live side-effect evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

DEFAULT_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
WORK_MOUNT = "/var/tmp"
NET_MARKER_TEMPLATE = "__HERMETIC_NET_{token}__"
WRAPPER_TEMPLATE = r'''before=$(awk 'NR > 2 {rx += $3; tx += $11} END {print rx+tx+0}' /proc/net/dev 2>/dev/null || printf '')
"$@"
rc=$?
after=$(awk 'NR > 2 {rx += $3; tx += $11} END {print rx+tx+0}' /proc/net/dev 2>/dev/null || printf '')
if [ -n "$before" ] && [ -n "$after" ]; then
  packets=$((after-before))
  [ "$packets" -lt 0 ] && packets=0
  printf '\n{marker} before=%s after=%s packets=%s\n' "$before" "$after" "$packets"
fi
exit "$rc"
'''

WRITE_FLAGS = re.compile(r"O_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND|EXCL)")
MUTATION_CALL = re.compile(
    r"\b(?:mkdir|mkdirat|rename|renameat|renameat2|unlink|unlinkat|"
    r"symlink|symlinkat|link|linkat|truncate|ftruncate|creat|open|openat|"
    r"mknod|chmod|fchmod|utimensat|rmdir)\("
)
QUOTED = re.compile(r'"((?:\\.|[^"\\])*)"')


class ConfigError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe CLI tools in bwrap with a read-only project and a /tmp work copy."
    )
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument("--tools-file", help="newline-delimited tool paths")
    parser.add_argument("tools", nargs="*", help="tool paths relative to project_root or absolute")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError("config root must be a JSON object")
    return value


def absolute(path: str | Path) -> Path:
    return Path(os.path.expanduser(str(path))).resolve()


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def read_tools(args: argparse.Namespace, config: dict[str, Any]) -> list[str]:
    tools: list[str] = list(args.tools)
    if args.tools_file:
        try:
            lines = Path(args.tools_file).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ConfigError(f"cannot read tools file: {exc}") from exc
        tools.extend(line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#"))
    if not tools:
        configured = config.get("tools", [])
        if not isinstance(configured, list) or not all(isinstance(item, str) for item in configured):
            raise ConfigError("config.tools must be a list of strings")
        tools = configured
    if not tools:
        raise ConfigError("provide at least one tool path")
    return tools


def validate_config(config: dict[str, Any]) -> tuple[Path, Path, Path, list[str], float, dict[str, list[str]], dict[str, str]]:
    if not isinstance(config.get("project_root"), str):
        raise ConfigError("config.project_root is required")
    project_root = absolute(config["project_root"])
    if project_root == Path("/") or not project_root.is_dir():
        raise ConfigError(f"project_root is not a usable directory: {project_root}")

    work_parent = absolute(config.get("work_parent", "/tmp/hermetic-live-probe-work"))
    output_dir = absolute(config.get("output_dir", "/tmp/hermetic-live-probe-results"))
    for name, candidate in (("work_parent", work_parent), ("output_dir", output_dir)):
        if is_under(candidate, project_root):
            raise ConfigError(f"{name} must not be inside project_root")
        candidate.mkdir(parents=True, exist_ok=True)

    try:
        timeout_seconds = float(config.get("timeout_seconds", 10))
    except (TypeError, ValueError) as exc:
        raise ConfigError("timeout_seconds must be a positive number") from exc
    if timeout_seconds <= 0:
        raise ConfigError("timeout_seconds must be positive")

    raw_runner = config.get("runner", [])
    if isinstance(raw_runner, str):
        runner = [raw_runner]
    elif isinstance(raw_runner, list) and all(isinstance(item, str) for item in raw_runner):
        runner = list(raw_runner)
    else:
        raise ConfigError("runner must be a string or list of strings")

    raw_modes = config.get("modes", {})
    if not isinstance(raw_modes, dict):
        raise ConfigError("modes must be a JSON object")
    modes: dict[str, list[str]] = {}
    defaults = {"help": ["--help"], "unknown": ["--__hermetic_unknown__"], "safe": []}
    for mode in ("help", "unknown", "safe"):
        value = raw_modes.get(mode, defaults[mode])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ConfigError(f"modes.{mode} must be a list of strings")
        modes[mode] = list(value)

    raw_env = config.get("env", {})
    if not isinstance(raw_env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in raw_env.items()):
        raise ConfigError("env must be an object of string values")
    return project_root, work_parent, output_dir, runner, timeout_seconds, modes, dict(raw_env)


def resolve_tool(raw: str, project_root: Path) -> tuple[Path, Path]:
    candidate = absolute(raw) if Path(raw).is_absolute() else (project_root / raw).resolve()
    if not is_under(candidate, project_root):
        raise ConfigError(f"tool is outside project_root: {raw}")
    if not candidate.is_file():
        raise ConfigError(f"tool is not a regular file: {candidate}")
    return candidate, candidate.relative_to(project_root)


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def snapshot_one(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    if path.is_symlink():
        entries["."] = "symlink:" + os.readlink(path)
        return entries
    if path.is_file():
        entries["."] = "file:" + digest_file(path)
        return entries
    if not path.is_dir():
        entries["."] = "other"
        return entries
    entries["."] = "dir"
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        for name in list(dirs):
            candidate = root_path / name
            rel = candidate.relative_to(path).as_posix()
            if candidate.is_symlink():
                entries[rel] = "symlink:" + os.readlink(candidate)
                dirs.remove(name)
            else:
                entries[rel] = "dir"
        for name in files:
            candidate = root_path / name
            rel = candidate.relative_to(path).as_posix()
            if candidate.is_symlink():
                entries[rel] = "symlink:" + os.readlink(candidate)
            else:
                try:
                    entries[rel] = "file:" + digest_file(candidate)
                except OSError as exc:
                    entries[rel] = "unreadable:" + repr(exc)
    return entries


def snapshot(paths: list[Path]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for path in paths:
        entries = snapshot_one(path)
        packed = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        result[str(path)] = {
            "count": len(entries),
            "digest": hashlib.sha256(packed).hexdigest(),
            "entries": entries,
        }
    return result


def snapshot_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for path in sorted(set(before) | set(after)):
        if before.get(path, {}).get("digest") != after.get(path, {}).get("digest"):
            changed.append(path)
    return changed


def unescape_strace(value: str) -> str:
    return value.replace(r'\"', '"').replace(r"\\", "\\")


def first_quoted(line: str) -> str | None:
    match = QUOTED.search(line)
    return unescape_strace(match.group(1)) if match else None


def syscall_success(line: str) -> bool:
    if "=" not in line:
        return False
    return not re.search(r"=\s*-1(?:\s|$)", line)


def trace_path(raw: str) -> str:
    if raw.startswith("/"):
        return posixpath.normpath(raw)
    return posixpath.normpath(WORK_MOUNT + "/" + raw)


def parse_trace(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    connect = len(re.findall(r"\bconnect\(", text))
    execve = len(re.findall(r"\bexecve\(", text))
    lines = text.splitlines()
    child_start = 0
    for index, line in enumerate(lines):
        if 'execve("/bin/sh"' in line:
            child_start = index
    inside: set[str] = set()
    outside_attempts: set[str] = set()
    outside_successes: set[str] = set()
    for line in lines[child_start:]:
        call_match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\(", line)
        if not call_match:
            continue
        call_name = call_match.group(1)
        if call_name not in {
            "mkdir", "mkdirat", "rename", "renameat", "renameat2", "unlink", "unlinkat",
            "symlink", "symlinkat", "link", "linkat", "truncate", "ftruncate", "creat",
            "open", "openat", "mknod", "chmod", "fchmod", "utimensat", "rmdir",
        }:
            continue
        is_open_write = call_name in {"open", "openat", "creat"} and bool(WRITE_FLAGS.search(line))
        is_mutation = call_name not in {"open", "openat", "creat"}
        if not (is_open_write or is_mutation):
            continue
        raw = first_quoted(line)
        if not raw:
            continue
        normalized = trace_path(raw)
        if normalized == WORK_MOUNT or normalized.startswith(WORK_MOUNT + "/"):
            if syscall_success(line):
                inside.add(normalized)
        elif normalized.startswith(("/tmp", "/proc", "/dev")):
            continue
        else:
            outside_attempts.add(normalized)
            if syscall_success(line):
                outside_successes.add(normalized)
    return {
        "connect": connect,
        "execve": execve,
        "files_written_inside_copy": sorted(inside),
        "outside_write_attempts": sorted(outside_attempts),
        "outside_successful_writes": sorted(outside_successes),
        "trace_bytes": len(text.encode("utf-8", errors="replace")),
    }


def clip(value: str, limit: int = 20000) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    return value[:limit] + "\n[truncated]", True


def build_bwrap(
    project_root: Path,
    work_dir: Path,
    runner: list[str],
    tool_rel: Path,
    args: list[str],
    env: dict[str, str],
    marker: str,
) -> list[str]:
    command = runner + [WORK_MOUNT + "/" + tool_rel.as_posix()] + args
    wrapper = WRAPPER_TEMPLATE.replace("{marker}", marker)
    result = [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--unshare-net",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/tmp",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--ro-bind",
        str(project_root),
        str(project_root),
        "--bind",
        str(work_dir),
        WORK_MOUNT,
        "--chdir",
        WORK_MOUNT,
        "--clearenv",
        "--setenv",
        "PATH",
        DEFAULT_PATH,
        "--setenv",
        "HOME",
        "/tmp",
        "--setenv",
        "TMPDIR",
        "/tmp",
    ]
    for key, value in env.items():
        result.extend(["--setenv", key, value])
    result.extend(["--", "/bin/sh", "-c", wrapper, "hermetic-wrapper", *command])
    return result


def run_mode(
    project_root: Path,
    watch_paths: list[Path],
    work_parent: Path,
    runner: list[str],
    tool_rel: Path,
    mode: str,
    mode_args: list[str],
    timeout_seconds: float,
    env: dict[str, str],
    trace_dir: Path,
) -> dict[str, Any]:
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    try:
        before = snapshot(watch_paths)
    except OSError as exc:
        return {
            "mode": mode,
            "args": mode_args,
            "returncode": None,
            "duration_ms": 0,
            "stdout": "",
            "stderr": "",
            "measurement": "unmeasurable inside barrier",
            "measurement_reason": f"before fingerprint failed: {exc}",
            "net_packets": None,
            "connect": None,
            "execve": None,
            "files_written_inside_copy": [],
            "outside_changes": ["before-fingerprint"],
            "fingerprints_before": None,
            "fingerprints_after": None,
        }

    work_dir = Path(tempfile.mkdtemp(prefix="probe-", dir=str(work_parent)))
    trace_path = trace_dir / f"{mode}-{uuid.uuid4().hex}.strace"
    marker = NET_MARKER_TEMPLATE.format(token=uuid.uuid4().hex)
    command = build_bwrap(project_root, work_dir, runner, tool_rel, mode_args, env, marker)
    try:
        shutil.copytree(project_root, work_dir, dirs_exist_ok=True, symlinks=True)
        wrapped = [
            "timeout",
            "--signal=TERM",
            "--kill-after=1s",
            str(timeout_seconds),
            "strace",
            "-f",
            "-qq",
            "-o",
            str(trace_path),
            "-e",
            "trace=%file,%network,execve",
            *command,
        ]
        started = time.monotonic()
        try:
            completed = subprocess.run(
                wrapped,
                capture_output=True,
                text=True,
                errors="replace",
                start_new_session=True,
                timeout=timeout_seconds + 3,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        duration_ms = round((time.monotonic() - started) * 1000)
        try:
            after = snapshot(watch_paths)
        except OSError as exc:
            after = None
        trace = parse_trace(trace_path)
        output = stdout + "\n" + stderr
        match = re.search(
            re.escape(marker) + r"\s+before=(\d+)\s+after=(\d+)\s+packets=(\d+)",
            output,
        )
        net_packets = int(match.group(3)) if match else None
        outside_changes = snapshot_changes(before, after) if after is not None else ["after-fingerprint"]
        outside_changes.extend(trace["outside_successful_writes"])
        outside_changes = sorted(set(outside_changes))
        measurement_ok = trace_path.exists() and match is not None and after is not None
        stdout_clipped, stdout_was_clipped = clip(stdout)
        stderr_clipped, stderr_was_clipped = clip(stderr)
        result = {
            "mode": mode,
            "args": mode_args,
            "returncode": returncode,
            "duration_ms": duration_ms,
            "stdout": stdout_clipped,
            "stderr": stderr_clipped,
            "stdout_truncated": stdout_was_clipped,
            "stderr_truncated": stderr_was_clipped,
            "measurement": "measured" if measurement_ok else "unmeasurable inside barrier",
            "measurement_reason": None if measurement_ok else "missing trace, net_packets marker, or after fingerprint",
            "net_packets": net_packets,
            "connect": trace["connect"],
            "execve": trace["execve"],
            "files_written_inside_copy": trace["files_written_inside_copy"],
            "outside_write_attempts": trace["outside_write_attempts"],
            "outside_changes": outside_changes,
            "fingerprints_before": {key: value["digest"] for key, value in before.items()},
            "fingerprints_after": ({key: value["digest"] for key, value in after.items()} if after is not None else None),
            "trace_file": str(trace_path),
            "trace_bytes": trace["trace_bytes"],
        }
        return result
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def tool_slug(tool: str, index: int) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(tool).name or "tool")
    return f"{index:03d}-{stem}"


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["tool", "mode", "rc", "ms", "writes", "connect", "execve", "net_packets", "outside", "measurement"]
    print("\t".join(headers))
    for row in rows:
        values = [
            row.get("tool", ""),
            row.get("mode", ""),
            str(row.get("returncode", "")),
            str(row.get("duration_ms", "")),
            str(len(row.get("files_written_inside_copy", []))),
            str(row.get("connect", "")),
            str(row.get("execve", "")),
            str(row.get("net_packets", "")),
            str(len(row.get("outside_changes", []))),
            row.get("measurement", ""),
        ]
        print("\t".join(values))


def main() -> int:
    args = parse_args()
    if not args.config:
        print("error: --config is required", file=sys.stderr)
        return 2
    try:
        config = load_json(absolute(args.config))
        project_root, work_parent, output_dir, runner, timeout_seconds, modes, env = validate_config(config)
        raw_tools = read_tools(args, config)
        resolved_tools = [resolve_tool(raw, project_root) for raw in raw_tools]
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    watch_config = config.get("watch_paths", [str(project_root)])
    if not isinstance(watch_config, list) or not all(isinstance(item, str) for item in watch_config):
        print("error: watch_paths must be a list of strings", file=sys.stderr)
        return 2
    watch_paths = [absolute(item) for item in watch_config]
    trace_dir = output_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[str] = []

    for index, raw_tool in enumerate(raw_tools, start=1):
        result: dict[str, Any] = {
            "tool": raw_tool,
            "project_root": str(project_root),
            "sandbox": {
                "engine": "bwrap",
                "unshare_net": True,
                "project_mount": "read-only",
                "work_copy": "/tmp host path mounted at /var/tmp",
                "tmpfs": "/tmp",
                "timeout_seconds": timeout_seconds,
            },
            "modes": {},
        }
        try:
            _, tool_rel = resolved_tools[index - 1]
            expected = {"help": 0, "unknown": 2}
            for mode in ("help", "unknown", "safe"):
                mode_result = run_mode(
                    project_root,
                    watch_paths,
                    work_parent,
                    runner,
                    tool_rel,
                    mode,
                    modes[mode],
                    timeout_seconds,
                    env,
                    trace_dir,
                )
                mode_result["expected_returncode"] = expected.get(mode)
                mode_result["contract_match"] = (
                    mode_result["returncode"] == mode_result["expected_returncode"]
                    if mode_result["expected_returncode"] is not None
                    else None
                )
                result["modes"][mode] = mode_result
                rows.append({"tool": raw_tool, **mode_result})
                if mode_result["measurement"] != "measured":
                    failures.append(f"{raw_tool}:{mode}:measurement-missing")
                if mode_result.get("net_packets") is None or mode_result.get("net_packets", 0) > 0:
                    failures.append(f"{raw_tool}:{mode}:net_packets")
                if mode_result.get("outside_changes"):
                    failures.append(f"{raw_tool}:{mode}:outside-change")
            measured = all(item["measurement"] == "measured" for item in result["modes"].values())
            result["decision"] = "measured" if measured else "unmeasurable inside barrier"
        except ConfigError as exc:
            result["decision"] = "unmeasurable inside barrier"
            result["error"] = str(exc)
            failures.append(f"{raw_tool}:tool-resolution")
        output_path = output_dir / (tool_slug(raw_tool, index) + ".json")
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["json"] = str(output_path)
        print(f"JSON\t{output_path}")

    print_table(rows)
    if failures:
        print("FAILURES\t" + "\t".join(sorted(set(failures))), file=sys.stderr)
        return 1
    print("RESULT\tmeasured\tall modes have net_packets=0 and no outside changes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
