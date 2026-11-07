#!/usr/bin/env bash
# قناة المحتوى العامة البديلة — raw.githack/jsDelivr، لا تُستدعى إلا من D010 أو بتفويض تشغيل صريح.
# الاستخدام: bash tools/publish_fallback.sh YYYY-MM-DD
set -u
B="${BRAIN_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
if [ -n "${SITE_DIR:-}" ]; then
  SITE="$SITE_DIR"
else
  SITE=""
  SEARCH_BASE="$B"
  for _ in 1 2 3 4; do
    for NAME in seawatch site; do
      CANDIDATE="$(cd "$SEARCH_BASE/../$NAME" 2>/dev/null && pwd || true)"
      if [ -n "$CANDIDATE" ] && [ -d "$CANDIDATE/dist" ]; then
        SITE="$CANDIDATE"
        break 2
      fi
    done
    NEXT_BASE="$(cd "$SEARCH_BASE/.." 2>/dev/null && pwd || true)"
    [ -n "$NEXT_BASE" ] && [ "$NEXT_BASE" != "$SEARCH_BASE" ] || break
    SEARCH_BASE="$NEXT_BASE"
  done
  [ -n "$SITE" ] || SITE="$B/../site"
fi
D="${1:-$(date -u +%F)}"
REPO="${FALLBACK_REPO:-fahadaldoseri/seawatch-live}"
BRANCH="main"
OWNER="${REPO%%/*}"
NAME="${REPO#*/}"
GITHACK_ROOT="${FALLBACK_GITHACK_ROOT:-https://raw.githack.com/$OWNER/$NAME/$BRANCH}"
JSDELIVR_ROOT="${FALLBACK_JSDELIVR_ROOT:-https://cdn.jsdelivr.net/gh/$OWNER/$NAME@$BRANCH}"
LOG="$B/logs/publish-$D-fallback.json"
WORK="${FALLBACK_WORKDIR:-$(mktemp -d "${TMPDIR:-/tmp}/seawatch-pages.XXXXXX")}"
KEEP_WORK=0
mkdir -p "$B/logs"

record() {
  local rc="$1" status="$2" head="${3:-}" fp="${4:-}" why="${5:-}"
  python3 - "$LOG" "$D" "$REPO" "$GITHACK_ROOT" "$JSDELIVR_ROOT" "$rc" "$status" "$head" "$fp" "$why" <<'PY'
import datetime, json, pathlib, sys
out, date, repo, githack, jsdelivr, rc, status, head, fp, why = sys.argv[1:]
previous = date.replace("-07", "-06") if date.endswith("-07") else date
urls = [
    f"{githack}/",
    f"{githack}/reports/{date}.html",
    f"{githack}/reports/{previous}.html",
    f"{jsdelivr}/",
    f"{jsdelivr}/reports/{date}.html",
    f"{jsdelivr}/reports/{previous}.html",
]
doc = {
    "date": date, "channel": "github-pages", "repo": repo,
    "transport": ["raw.githack", "jsDelivr"],
    "url": f"{githack.rstrip('/')}/reports/{date}.html", "urls": urls, "rc": int(rc),
    "status": status, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "head": head or None, "content_sha256": fp or None,
}
if why:
    doc["why"] = why
pathlib.Path(out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

if [ ! -d "$SITE/dist" ]; then
  record 2 failed "" "" "site dist is missing"
  echo "✘ fallback: dist مفقود في $SITE"
  exit 2
fi
if ! command -v gh >/dev/null 2>&1; then
  record 127 failed "" "" "gh is unavailable"
  echo "✘ fallback: gh غير متاح"
  exit 127
fi
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  record 10 failed "" "" "gh auth status failed"
  echo "✘ fallback: gh auth status فشل"
  exit 10
fi
rm -rf "$WORK/repo" 2>/dev/null || true
if ! git clone -q "https://github.com/$REPO.git" "$WORK/repo"; then
  record 2 failed "" "" "clone failed"
  echo "✘ fallback: clone فشل"
  exit 2
fi
cd "$WORK/repo" || { record 2 failed "" "" "worktree unavailable"; exit 2; }
if git show-ref --verify --quiet refs/heads/main; then
  if ! git switch -q main; then
    record 2 failed "" "" "main branch unavailable"
    echo "✘ fallback: فرع main غير متاح"
    exit 2
  fi
else
  if ! git checkout -q --orphan main; then
    record 2 failed "" "" "could not initialize main branch"
    echo "✘ fallback: تعذر إنشاء فرع main"
    exit 2
  fi
fi
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf -- {} +
cp -a "$SITE/dist/." ./
FP="$(python3 - "$B/tools/publish_channels.py" "$WORK/repo" <<'PY'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("publish_channels", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(mod.content_fingerprint(pathlib.Path(sys.argv[2])))
PY
)" || { record 2 failed "" "" "fingerprint failed"; exit 2; }
git config user.email "fahadaldoseri@users.noreply.github.com"
git config user.name "fahadaldoseri"
git add -A
if git diff --cached --quiet; then
  HEAD="$(git rev-parse HEAD 2>/dev/null || true)"
else
  if ! git commit -qm "publish: Seawatch report $D"; then
    record 3 failed "" "$FP" "commit failed"
    exit 3
  fi
  HEAD="$(git rev-parse HEAD)"
fi
if ! git push -q origin HEAD:main; then
  record 1 failed "$HEAD" "$FP" "push failed"
  echo "✘ fallback: push فشل"
  exit 1
fi
record 0 ok "$HEAD" "$FP"
echo "✔ fallback: public raw/jsDelivr content pushed — $HEAD — sha256=$FP"
exit 0
