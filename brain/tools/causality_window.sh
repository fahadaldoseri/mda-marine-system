#!/usr/bin/env bash
# نافذة رصد سببية طويلة: تراقب الأصول الحاكمة وكاتب .skill_versions عبر auditd
# الاستعمال: bash tools/causality_window.sh [seconds] [outdir]
set -u
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRAIN_ROOT="${BRAIN_DIR:-$PROJECT_ROOT}"
SECS="${1:-5400}"
OUT="${2:-$BRAIN_ROOT/evidence/causality}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$OUT/${TS}-causality-window.log"
SAMPLES="$OUT/${TS}-samples.tsv"
mkdir -p "$OUT"
SK="${SKILLS_DIR:-$PROJECT_ROOT/../skills}"
FILES=(
  "$SK/marine-news-brain/SKILL.md"
  "$SK/military-arabic-editing/SKILL.md"
  "$SK/superpowers-method/SKILL.md"
  "$SK/military-arabic-editing/references/ambiguity-map.md"
  "$SK/.skill_versions.json"
)
{
  echo "# نافذة سببية · بدأت $(date -u +%FT%TZ) · المدة ${SECS}s"
  echo "# أداة: auditd (-w $SK -p wa -k skills_write) + عيّنات أسطر/بصمات"
  echo "ts_utc	event	detail"
} > "$LOG"
printf 'ts_utc\t' > "$SAMPLES"
for f in "${FILES[@]}"; do printf '%s_lines\t%s_sha16\t%s_mtime\t' "$(basename "$f")" "$(basename "$f")" "$(basename "$f")" >> "$SAMPLES"; done
printf '\n' >> "$SAMPLES"

sample() {
  local ts; ts="$(date -u +%FT%TZ)"
  printf '%s\t' "$ts" >> "$SAMPLES"
  for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then
      local l s m
      l="$(wc -l < "$f" 2>/dev/null | tr -d ' ')"
      s="$(sha256sum "$f" 2>/dev/null | cut -c1-16)"
      m="$(date -r "$f" -u +%H:%M:%SZ 2>/dev/null)"
      printf '%s\t%s\t%s\t' "$l" "$s" "$m" >> "$SAMPLES"
    else
      printf 'MISSING\t-\t-\t' >> "$SAMPLES"
    fi
  done
  printf '\n' >> "$SAMPLES"
}

audit_sweep() {
  local ts; ts="$(date -u +%FT%TZ)"
  sudo ausearch -k skills_write -ts recent -i 2>/dev/null \
    | grep -aE "type=PATH|type=SYSCALL" \
    | grep -avE "auditctl|CONFIG_CHANGE" \
    | grep -aE "name=|comm=|exe=" \
    | tail -40 | sed "s|^|$ts\tAUDIT\t|" >> "$LOG"
}

END=$(( $(date +%s) + SECS ))
SNAP_EVERY=20
NEXT_SNAP=0
NEXT_AUDIT=0
i=0
while [ "$(date +%s)" -lt "$END" ]; do
  NOW=$(date +%s)
  if [ "$NOW" -ge "$NEXT_SNAP" ]; then sample; NEXT_SNAP=$((NOW + SNAP_EVERY)); fi
  if [ "$NOW" -ge "$NEXT_AUDIT" ]; then audit_sweep; NEXT_AUDIT=$((NOW + 60)); fi
  sleep 5
  i=$((i+1))
  if [ $((i % 60)) -eq 0 ]; then
    echo "progress $(date -u +%FT%TZ) elapsed=$(( SECS - (END - NOW) ))s"
  fi
done
sample
audit_sweep
echo "# انتهت النافذة $(date -u +%FT%TZ)" >> "$LOG"
echo "DONE log=$LOG samples=$SAMPLES"
