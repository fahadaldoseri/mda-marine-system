#!/usr/bin/env bash
set -u

WATCH_ROOT="/home/ubuntu/skills"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DURATION="${1:-600}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="$PROJECT_ROOT/evidence/watch"
LOG="$LOG_DIR/$STAMP.log"
mkdir -p "$LOG_DIR"

if ! command -v inotifywait >/dev/null 2>&1; then
  echo "[$(date --iso-8601=seconds)] inotifywait missing; attempting installation" >> "$LOG"
  if ! sudo apt-get update -qq >> "$LOG" 2>&1 || ! sudo apt-get install -y -qq inotify-tools >> "$LOG" 2>&1; then
    echo "[$(date --iso-8601=seconds)] install failed" >> "$LOG"
    exit 2
  fi
fi

{
  echo "watch_started=$(date --iso-8601=seconds)"
  echo "watch_root=$WATCH_ROOT"
  echo "duration_seconds=$DURATION"
  echo "events=modify,create,delete,moved_to,moved_from"
  echo "observer=inotifywait"
  echo "writer_pid=not exposed by inotifywait; event path/time only"
} >> "$LOG"

inotifywait -m -r -e modify,create,delete,moved_to,moved_from \
  --format '%T|%e|%w%f' --timefmt '%Y-%m-%dT%H:%M:%S%z' \
  "$WATCH_ROOT" >> "$LOG" 2>&1 &
WATCH_PID=$!
trap 'kill "$WATCH_PID" 2>/dev/null || true; wait "$WATCH_PID" 2>/dev/null || true' EXIT
sleep "$DURATION"
echo "watch_finished=$(date --iso-8601=seconds)" >> "$LOG"
exit 0
