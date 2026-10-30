#!/usr/bin/env bash
# Hermetic command runner for the marine-awareness project.
# The command is never evaluated through a host shell; arguments after -- are argv.
set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEAWATCH_ROOT="/home/ubuntu/seawatch"
EVIDENCE_DIR="${HERMETIC_EVIDENCE_DIR:-$PROJECT_ROOT/evidence/hermetic}"
TIMEOUT_SECONDS=60
MEMORY_MB=512
CPU_QUOTA="50%"
TASKS_MAX=64
REQUESTED_WORKDIR=""
TOOL_NAME=""

usage() {
  cat <<'USAGE'
usage: hermetic_run.sh [options] -- command [args...]

Run an argv command inside a read-only bubblewrap sandbox with no network.

options:
  --timeout SEC       hard wall-clock timeout (default: 60)
  --memory-mb MB      MemoryMax/ulimit virtual-memory ceiling (default: 512)
  --cpu-quota PCT     CPUQuota for systemd-run (default: 50%)
  --tasks-max N       TasksMax/ulimit process ceiling (default: 64)
  --workdir DIR       isolated writable directory outside the project
  --name NAME         evidence name (default: basename of command)
  -h, --help          show this help

The separator -- is mandatory. Unknown options exit 2. Every command run emits
 evidence/hermetic/<name>.json and a raw strace file at a stable, overwriting path.
USAGE
}

fail_usage() {
  printf 'hermetic_run.sh: %s\n' "$1" >&2
  printf 'Try --help for usage.\n' >&2
  exit 2
}

while (($#)); do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --timeout)
      (($# >= 2)) || fail_usage '--timeout requires a value'
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --memory-mb)
      (($# >= 2)) || fail_usage '--memory-mb requires a value'
      MEMORY_MB="$2"
      shift 2
      ;;
    --cpu-quota)
      (($# >= 2)) || fail_usage '--cpu-quota requires a value'
      CPU_QUOTA="$2"
      shift 2
      ;;
    --tasks-max)
      (($# >= 2)) || fail_usage '--tasks-max requires a value'
      TASKS_MAX="$2"
      shift 2
      ;;
    --workdir)
      (($# >= 2)) || fail_usage '--workdir requires a directory'
      REQUESTED_WORKDIR="$2"
      shift 2
      ;;
    --name)
      (($# >= 2)) || fail_usage '--name requires a value'
      TOOL_NAME="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    --*)
      fail_usage "unknown option: $1"
      ;;
    *)
      fail_usage "options must precede --; unexpected argument: $1"
      ;;
  esac
done

(($# > 0)) || fail_usage 'a command is required after --'
[[ "$TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail_usage '--timeout must be a positive integer'
[[ "$MEMORY_MB" =~ ^[1-9][0-9]*$ ]] || fail_usage '--memory-mb must be a positive integer'
[[ "$TASKS_MAX" =~ ^[1-9][0-9]*$ ]] || fail_usage '--tasks-max must be a positive integer'
[[ "$CPU_QUOTA" =~ ^[1-9][0-9]*%$ ]] || fail_usage '--cpu-quota must be an integer percentage such as 50%'

CMD=("$@")
if [[ -z "$TOOL_NAME" ]]; then
  TOOL_NAME="$(basename -- "${CMD[0]}")"
fi
SAFE_NAME="$(printf '%s' "$TOOL_NAME" | tr -c 'A-Za-z0-9._-' '_')"
[[ -n "$SAFE_NAME" ]] || SAFE_NAME="tool"

case "$PROJECT_ROOT" in
  /|/tmp|/var/tmp) fail_usage "unsafe project root: $PROJECT_ROOT" ;;
esac

if [[ -n "$REQUESTED_WORKDIR" ]]; then
  WORKDIR="$(realpath -m -- "$REQUESTED_WORKDIR")" || fail_usage "cannot resolve workdir: $REQUESTED_WORKDIR"
  [[ "$WORKDIR" = /* ]] || fail_usage '--workdir must be absolute'
  case "$WORKDIR" in
    "$PROJECT_ROOT"|"$PROJECT_ROOT"/*|"$SEAWATCH_ROOT"|"$SEAWATCH_ROOT"/*)
      fail_usage '--workdir may not be inside the project or seawatch tree'
      ;;
    /|/tmp|/tmp/*)
      fail_usage '--workdir may not be /tmp; use /var/tmp so --tmpfs /tmp stays effective'
      ;;
  esac
  mkdir -p -- "$WORKDIR" || { printf 'cannot create workdir: %s\n' "$WORKDIR" >&2; exit 70; }
  OWN_WORKDIR=0
else
  WORKDIR="$(mktemp -d /var/tmp/hermetic-work.XXXXXX)" || { printf 'cannot create isolated workdir\n' >&2; exit 70; }
  OWN_WORKDIR=1
fi

mkdir -p -- "$EVIDENCE_DIR/traces" "$EVIDENCE_DIR/raw" "$EVIDENCE_DIR/fingerprints" || {
  printf 'cannot create evidence directories: %s\n' "$EVIDENCE_DIR" >&2
  exit 70
}

TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_ID="${SAFE_NAME}"
RAW_DIR="$EVIDENCE_DIR/raw/$RUN_ID"
FP_DIR="$EVIDENCE_DIR/fingerprints/$RUN_ID"
mkdir -p -- "$RAW_DIR" "$FP_DIR" || { printf 'cannot create run evidence directory\n' >&2; exit 70; }
EVIDENCE_PATH="$EVIDENCE_DIR/${SAFE_NAME}.json"
TRACE_PATH="$EVIDENCE_DIR/traces/${SAFE_NAME}.strace"
SUMMARY_PATH="$RAW_DIR/impact-summary.json"
PROJECT_COMPARE_PATH="$RAW_DIR/project-compare.json"
SEAWATCH_COMPARE_PATH="$RAW_DIR/seawatch-compare.json"
RUN_STDOUT="$RAW_DIR/stdout.log"
RUN_STDERR="$RAW_DIR/stderr.log"
META_PREFIX="$WORKDIR/.hermetic-net-${TS}-$$"

BWRAP_VERSION="$(bwrap --version 2>/dev/null || true)"
UNSHARE_VERSION="$(unshare --version 2>/dev/null | head -1 || true)"
STRACE_VERSION="$(strace -V 2>/dev/null | head -1 || true)"
SYSTEMD_VERSION="$(systemd-run --version 2>/dev/null | head -1 || true)"

snapshot_tree() {
  local root="$1"
  local output="$2"
  python3 - "$root" > "$output" <<'PY'
import hashlib
import json
import os
import stat
import sys

root = os.path.abspath(sys.argv[1])
result = {"root": root, "exists": os.path.isdir(root), "files": {}}
if result["exists"]:
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        filenames.sort()
        for name in filenames:
            path = os.path.join(directory, name)
            rel = os.path.relpath(path, root)
            try:
                info = os.lstat(path)
                if stat.S_ISREG(info.st_mode):
                    digest = hashlib.sha256()
                    with open(path, "rb") as handle:
                        for block in iter(lambda: handle.read(1024 * 1024), b""):
                            digest.update(block)
                    value = {"kind": "file", "sha256": digest.hexdigest(), "size": info.st_size}
                elif stat.S_ISLNK(info.st_mode):
                    value = {"kind": "symlink", "target": os.readlink(path)}
                else:
                    value = {"kind": "other", "mode": stat.S_IFMT(info.st_mode)}
                result["files"][rel] = value
            except (OSError, PermissionError) as exc:
                print(f"fingerprint failed for {path}: {exc}", file=sys.stderr)
                raise SystemExit(2)
json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
PY
}

compare_snapshots() {
  local before="$1"
  local after="$2"
  local output="$3"
  local root="$4"
  python3 - "$before" "$after" "$output" "$root" <<'PY'
import json
import os
import sys

before_path, after_path, output_path, root = sys.argv[1:]
with open(before_path, encoding="utf-8") as handle:
    before = json.load(handle)
with open(after_path, encoding="utf-8") as handle:
    after = json.load(handle)

def relevant(data):
    result = {}
    for rel, value in data.get("files", {}).items():
        absolute = os.path.join(root, rel)
        # Evidence and traces are harness-owned outputs, not command effects.
        if root == os.path.abspath(os.path.dirname(os.path.dirname(output_path))):
            pass
        if absolute == os.path.join(root, "evidence", "hermetic") or absolute.startswith(os.path.join(root, "evidence", "hermetic") + os.sep):
            continue
        result[rel] = value
    return result

left = relevant(before)
right = relevant(after)
changed = sorted(set(left) | set(right))
changed = [rel for rel in changed if left.get(rel) != right.get(rel)]
result = {
    "root": root,
    "before_file_count": len(left),
    "after_file_count": len(right),
    "changed_files": changed,
    "count": len(changed),
    "measurement_excludes": ["evidence/hermetic/** (harness-owned evidence and traces)"],
}
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
PY
}

PROJECT_BEFORE="$FP_DIR/project-before.json"
PROJECT_AFTER="$FP_DIR/project-after.json"
SEAWATCH_BEFORE="$FP_DIR/seawatch-before.json"
SEAWATCH_AFTER="$FP_DIR/seawatch-after.json"
if ! snapshot_tree "$PROJECT_ROOT" "$PROJECT_BEFORE" || ! snapshot_tree "$SEAWATCH_ROOT" "$SEAWATCH_BEFORE"; then
  printf 'fingerprint-before failed; refusing to run\n' >&2
  exit 70
fi

cleanup() {
  if [[ "$OWN_WORKDIR" -eq 1 && -n "${WORKDIR:-}" && -d "$WORKDIR" ]]; then
    rm -rf -- "$WORKDIR"
  fi
}
trap cleanup EXIT

if command -v strace >/dev/null 2>&1 && strace -e trace=%file,%network,execve -o /dev/null true >/dev/null 2>&1; then
  TRACE_SPEC='trace=%file,%network,execve'
else
  TRACE_SPEC='trace=openat,open,connect,execve'
fi

INNER_SCRIPT='\
set +e
packet_count() {
  awk '\''NR > 2 { rx += $2; tx += $10 } END { print (rx + tx + 0) }'\'' /proc/net/dev 2>/dev/null || printf "0\n"
}
net_before="$(packet_count)"
python3 -c "import socket; socket.create_connection((\"1.1.1.1\", 80), 3)" >"${HERMETIC_META}.probe.out" 2>&1
probe_rc=$?
net_after_probe="$(packet_count)"
printf "%s\n" "$probe_rc" >"${HERMETIC_META}.probe.rc"
printf "%s\n" "$net_before" >"${HERMETIC_META}.probe.before"
printf "%s\n" "$net_after_probe" >"${HERMETIC_META}.probe.after"
"$@"
command_rc=$?
printf "%s\n" "$(packet_count)" >"${HERMETIC_META}.run.after"
exit "$command_rc"
'

SANDBOX_MODE=""
if command -v bwrap >/dev/null 2>&1; then
  SANDBOX_MODE="bwrap"
  SANDBOX_ARGS=(
    --unshare-all
    --die-with-parent
    --unshare-net
    --new-session
    --ro-bind / /
    --tmpfs /tmp
    --proc /proc
    --dev /dev
    --bind "$WORKDIR" "$WORKDIR"
    --chdir "$WORKDIR"
    --clearenv
    --setenv PATH '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
    --setenv HOME /tmp
    --setenv TMPDIR /tmp
    --setenv LANG C
    --setenv LC_ALL C
    --setenv PYTHONNOUSERSITE 1
    --setenv HERMETIC_META "$META_PREFIX"
  )
  SANDBOX_CMD=(bwrap "${SANDBOX_ARGS[@]}" -- /bin/sh -c "$INNER_SCRIPT" hermetic-inner "${CMD[@]}")
else
  if ! command -v unshare >/dev/null 2>&1; then
    printf 'neither bwrap nor unshare is available; refusing to run\n' >&2
    exit 70
  fi
  SANDBOX_MODE="unshare-fallback"
  # Fallback is deliberately fail-closed: it must create a private mount namespace,
  # remount the root and both monitored trees read-only, then restore only workdir.
  FALLBACK_SCRIPT="
set -eu
mount --make-rprivate / || exit 70
mount -o remount,ro / || exit 70
mount --bind '$PROJECT_ROOT' '$PROJECT_ROOT' || exit 70
mount -o remount,bind,ro '$PROJECT_ROOT' || exit 70
if [ -d '$SEAWATCH_ROOT' ]; then
  mount --bind '$SEAWATCH_ROOT' '$SEAWATCH_ROOT' || exit 70
  mount -o remount,bind,ro '$SEAWATCH_ROOT' || exit 70
fi
mount -t tmpfs tmpfs /tmp || exit 70
mount --bind '$WORKDIR' '$WORKDIR' || exit 70
mount -o remount,bind,rw '$WORKDIR' || exit 70
exec /bin/sh -c $(printf '%q' "$INNER_SCRIPT") hermetic-inner \"\$@\"
"
  SANDBOX_CMD=(unshare --user --map-root-user --mount --pid --net --ipc --uts --fork --mount-proc /bin/sh -c "$FALLBACK_SCRIPT" hermetic-fallback "${CMD[@]}")
fi

# Probe systemd-run separately: if the scope cannot be created, use ulimit+timeout.
RESOURCE_MODE="ulimit+timeout"
USE_SYSTEMD=0
if command -v systemd-run >/dev/null 2>&1 && systemd-run --scope --quiet \
    -p "MemoryMax=${MEMORY_MB}M" -p "CPUQuota=${CPU_QUOTA}" \
    -p "TasksMax=${TASKS_MAX}" true >/dev/null 2>"$RAW_DIR/systemd-probe.stderr"; then
  USE_SYSTEMD=1
  RESOURCE_MODE="systemd-run+timeout"
fi

START_NS="$(date +%s%N)"
if [[ "$USE_SYSTEMD" -eq 1 ]]; then
  systemd-run --scope --quiet \
    -p "MemoryMax=${MEMORY_MB}M" -p "CPUQuota=${CPU_QUOTA}" \
    -p "TasksMax=${TASKS_MAX}" -- \
    timeout --signal=TERM --kill-after=5s "${TIMEOUT_SECONDS}s" \
    strace -f -qq -o "$TRACE_PATH" -e "$TRACE_SPEC" "${SANDBOX_CMD[@]}" \
    >"$RUN_STDOUT" 2>"$RUN_STDERR"
  RUN_RC=$?
else
  (
    # ulimit is a fallback only; timeout remains mandatory in both modes.
    ulimit -v "$((MEMORY_MB * 1024))" 2>/dev/null || true
    ulimit -t "$((TIMEOUT_SECONDS > 1 ? TIMEOUT_SECONDS : 1))" 2>/dev/null || true
    # RLIMIT_NPROC is per-user, so include the already-running user processes;
    # otherwise the wrapper itself can exhaust the limit before bwrap starts.
    baseline_user_threads="$(ps -eLf -u "$(id -u)" --no-headers 2>/dev/null | wc -l | tr -d ' ')"
    [[ "$baseline_user_threads" =~ ^[0-9]+$ ]] || baseline_user_threads=0
    ulimit -u "$((baseline_user_threads + TASKS_MAX))" 2>/dev/null || true
    timeout --signal=TERM --kill-after=5s "${TIMEOUT_SECONDS}s" \
      strace -f -qq -o "$TRACE_PATH" -e "$TRACE_SPEC" "${SANDBOX_CMD[@]}"
  ) >"$RUN_STDOUT" 2>"$RUN_STDERR"
  RUN_RC=$?
fi
END_NS="$(date +%s%N)"
DURATION_MS="$(( (END_NS - START_NS) / 1000000 ))"

cat "$RUN_STDOUT"
cat "$RUN_STDERR" >&2

if ! snapshot_tree "$PROJECT_ROOT" "$PROJECT_AFTER" || ! snapshot_tree "$SEAWATCH_ROOT" "$SEAWATCH_AFTER"; then
  printf 'fingerprint-after failed; refusing to write a success claim\n' >&2
  exit 70
fi
compare_snapshots "$PROJECT_BEFORE" "$PROJECT_AFTER" "$PROJECT_COMPARE_PATH" "$PROJECT_ROOT" || exit 70
compare_snapshots "$SEAWATCH_BEFORE" "$SEAWATCH_AFTER" "$SEAWATCH_COMPARE_PATH" "$SEAWATCH_ROOT" || exit 70

python3 - "$TRACE_PATH" > "$SUMMARY_PATH" <<'PY'
import json
import re
import sys

trace_path = sys.argv[1]
write_lines = []
connect_lines = []
exec_paths = []
try:
    with open(trace_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.rstrip("\n")
            if re.search(r"\b(?:open|openat|creat|truncate|ftruncate)\(", stripped):
                if any(flag in stripped for flag in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC")) or re.search(r"\b(?:creat|truncate|ftruncate)\(", stripped):
                    write_lines.append(stripped)
            if "connect(" in stripped:
                connect_lines.append(stripped)
            match = re.search(r'execve\("([^"\\]*(?:\\.[^"\\]*)*)"', stripped)
            if match:
                exec_paths.append(match.group(1))
except FileNotFoundError:
    pass
json.dump(
    {
        "files_opened_for_write": sorted(set(write_lines)),
        "connect_attempts": len(connect_lines),
        "connect_lines": connect_lines[:100],
        "execve": sorted(set(exec_paths)),
    },
    sys.stdout,
    ensure_ascii=False,
    indent=2,
    sort_keys=True,
)
PY

python3 - "$EVIDENCE_PATH" "$TS" "$TOOL_NAME" "$RUN_RC" "$DURATION_MS" "$RESOURCE_MODE" "$SANDBOX_MODE" "$TRACE_PATH" "$SUMMARY_PATH" "$PROJECT_COMPARE_PATH" "$SEAWATCH_COMPARE_PATH" "$PROJECT_BEFORE" "$PROJECT_AFTER" "$SEAWATCH_BEFORE" "$SEAWATCH_AFTER" "$META_PREFIX" "$TIMEOUT_SECONDS" "$MEMORY_MB" "$CPU_QUOTA" "$TASKS_MAX" "$BWRAP_VERSION" "$UNSHARE_VERSION" "$STRACE_VERSION" "$SYSTEMD_VERSION" -- "${CMD[@]}" <<'PY'
from __future__ import annotations

import json
import os
import pathlib
import sys

(
    evidence_path,
    run_timestamp,
    tool_name,
    run_rc,
    duration_ms,
    resource_mode,
    sandbox_mode,
    trace_path,
    summary_path,
    project_compare_path,
    seawatch_compare_path,
    project_before,
    project_after,
    seawatch_before,
    seawatch_after,
    meta_prefix,
    timeout_seconds,
    memory_mb,
    cpu_quota,
    tasks_max,
    bwrap_version,
    unshare_version,
    strace_version,
    systemd_version,
    separator,
    *command,
) = sys.argv[1:]
assert separator == "--"

def read_text(suffix: str, default: str = "") -> str:
    try:
        return pathlib.Path(meta_prefix + suffix).read_text(encoding="utf-8").strip()
    except OSError:
        return default

def read_int(suffix: str, default: int = 0) -> int:
    try:
        return int(read_text(suffix, str(default)).splitlines()[0])
    except (ValueError, IndexError):
        return default

def read_json(path: str, default: dict) -> dict:
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

probe_rc = read_int(".probe.rc", 70)
probe_before = read_int(".probe.before", 0)
probe_after = read_int(".probe.after", probe_before)
run_after = read_int(".run.after", probe_after)
net_packets = max(0, run_after - probe_before)
summary = read_json(summary_path, {"files_opened_for_write": [], "connect_attempts": 0, "connect_lines": [], "execve": []})
project_compare = read_json(project_compare_path, {"count": 70, "changed_files": []})
seawatch_compare = read_json(seawatch_compare_path, {"count": 70, "changed_files": []})
changed_paths = sorted(set(project_compare.get("changed_files", [])) | set(seawatch_compare.get("changed_files", [])))
probe_output = read_text(".probe.out")[:1000]
run_code = int(run_rc)
evidence = {
    "schema": "hermetic-run/v1",
    "timestamp_utc": run_timestamp,
    "tool": command[0] if command else tool_name,
    "tool_name": tool_name,
    "arguments": command[1:],
    "argv": command,
    "exit_code": run_code,
    "duration_ms": int(duration_ms),
    "duration_seconds": round(int(duration_ms) / 1000, 3),
    "timeout_seconds": int(timeout_seconds),
    "timeout_enforced": run_code == 124,
    "resource_limits": {
        "memory_mb": int(memory_mb),
        "cpu_quota": cpu_quota,
        "tasks_max": int(tasks_max),
        "mode": resource_mode,
    },
    "isolation": {
        "mode": sandbox_mode,
        "root": "read-only in bwrap; monitored-root remount attempt in unshare fallback",
        "tmp": "tmpfs in bwrap/fallback",
        "network": "unshared",
        "workdir": "single bind-mounted writable directory outside monitored trees",
    },
    "network_proof": {
        "command": "python3 -c 'import socket; socket.create_connection((\"1.1.1.1\",80),3)'",
        "exit_code": probe_rc,
        "failed_as_expected": probe_rc != 0,
        "packets_before": probe_before,
        "packets_after_probe": probe_after,
        "packets_after_command": run_after,
        "output": probe_output,
    },
    "net_packets": net_packets,
    "impact_summary": summary,
    "changed_files_outside_isolation": len(changed_paths),
    "changed_paths_outside_isolation": changed_paths,
    "fingerprints": {
        "project_root": "/home/ubuntu/brain-marine-news",
        "seawatch_root": "/home/ubuntu/seawatch",
        "project_before": project_before,
        "project_after": project_after,
        "seawatch_before": seawatch_before,
        "seawatch_after": seawatch_after,
        "comparison_excludes": ["evidence/hermetic/** (harness-owned evidence, traces, and fingerprints)"],
    },
    "trace": trace_path,
    "raw_trace": trace_path,
    "versions": {
        "bubblewrap": bwrap_version,
        "unshare": unshare_version,
        "strace": strace_version,
        "systemd_run": systemd_version,
    },
    "evidence_files": {
        "raw_stdout": str(pathlib.Path(summary_path).with_name("stdout.log")),
        "raw_stderr": str(pathlib.Path(summary_path).with_name("stderr.log")),
        "impact_summary": summary_path,
        "project_compare": project_compare_path,
        "seawatch_compare": seawatch_compare_path,
    },
}
with open(evidence_path, "w", encoding="utf-8") as handle:
    json.dump(evidence, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
print(f"hermetic evidence: {evidence_path}", file=sys.stderr)
PY

exit "$RUN_RC"
