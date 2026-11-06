#!/usr/bin/env bash
# تحقق حي قراءة فقط لموقع ثابت منشور على استضافة Manus.
# لا ينفّذ commit أو push أو publish؛ القرار والنشر خطوتان منفصلتان.
# الاستخدام: bash check_live.sh [--brain PATH] [--site PATH] [--date YYYY-MM-DD]
#                 [--compare] [--retries N] [--retry-seconds N]
# رمز الخروج: 0 تحقق مثبت · 2 فشل تحقق أو مدخل ناقص.
set -uo pipefail

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRAIN="${BRAIN_DIR:-$SCRIPT_ROOT/../../brain-marine-news}"
SITE="${SITE_DIR:-$SCRIPT_ROOT/../../seawatch}"
DATE="$(date -u +%F)"
COMPARE=0
RETRIES="${LIVE_RETRIES:-6}"
RETRY_SECONDS="${LIVE_RETRY_SECONDS:-45}"
TIMEOUT="${LIVE_TIMEOUT_SECONDS:-60}"

usage() {
  sed -n '1,8p' "${BASH_SOURCE[0]}"
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --brain) BRAIN="$2"; shift 2 ;;
    --site) SITE="$2"; shift 2 ;;
    --date) DATE="$2"; shift 2 ;;
    --compare) COMPARE=1; shift ;;
    --retries) RETRIES="$2"; shift 2 ;;
    --retry-seconds) RETRY_SECONDS="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "✘ وسيط غير معروف: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$DATE" in
  ????-??-??) ;;
  *) echo "✘ التاريخ يجب أن يكون YYYY-MM-DD: $DATE" >&2; exit 2 ;;
esac
[ -d "$BRAIN" ] || { echo "✘ جذر Brain غير موجود: $BRAIN" >&2; exit 2; }
[ -d "$SITE" ] || { echo "✘ جذر الموقع غير موجود: $SITE" >&2; exit 2; }
command -v curl >/dev/null 2>&1 || { echo "✘ curl مطلوب لأن الاستضافة ترفض عميل Python في بعض البيئات" >&2; exit 2; }

BASE="${LIVE_BASE_URL:-}"
if [ -z "$BASE" ] && [ -s "$SITE/sources/site.json" ]; then
  BASE="$(python3 - "$SITE/sources/site.json" <<'PY'
import json, sys
try:
    print(str(json.loads(open(sys.argv[1], encoding='utf-8').read()).get('base_url') or '').strip().rstrip('/'))
except Exception:
    print('')
PY
)"
fi
[ -n "$BASE" ] || { echo "✘ لا رابط للموقع المنشور؛ اضبط LIVE_BASE_URL أو sources/site.json:base_url" >&2; exit 2; }
case "$BASE" in https://*|http://*) ;; *) echo "✘ رابط النشر غير صالح: $BASE" >&2; exit 2 ;; esac

mkdir -p "$BRAIN/logs"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
LOG="$BRAIN/logs/live-$DATE.json"
START_EPOCH="$(date +%s.%N)"
START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# مصفوفة الإثبات المطلوبة: لا يكفي أن ترد الصفحة الرئيسية وحدها.
ROUTES=(
  "الرئيسية|/|dist/index.html"
  "صفحة التقرير|/reports/$DATE.html|dist/reports/$DATE.html"
  "صفحة الإضافات|/additions.html|dist/additions.html"
  "صفحة المصادر|/sources.html|dist/sources.html"
  "التغذية|/feed.xml|dist/feed.xml"
  "اللوحة|/reports/monthly-${DATE:0:7}.html|dist/reports/monthly-${DATE:0:7}.html"
  "السجل|/reports/cumulative-${DATE:0:4}.html|dist/reports/cumulative-${DATE:0:4}.html"
)

attempt=1
while [ "$attempt" -le "$RETRIES" ]; do
  ATTEMPT_START="$(date +%s.%N)"
  rm -f "$TMP"/body-* "$TMP"/err-* "$TMP"/rows.tsv
  : > "$TMP/rows.tsv"
  bad=()
  marker=0
  compare_bad=0

  for spec in "${ROUTES[@]}"; do
    IFS='|' read -r label route local_rel <<< "$spec"
    key="$(printf '%s' "$route" | tr '/:' '__' | tr -cd '[:alnum:]_-' | sed 's/^$/root/')"
    body="$TMP/body-$key"
    err="$TMP/err-$key"
    code="$(curl -L --silent --show-error --max-time "$TIMEOUT" \
      -A 'seawatch-check/1.0' -o "$body" -w '%{http_code}' \
      "$BASE$route" 2>"$err" || true)"
    [ -n "$code" ] || code=000
    bytes=0; live_sha=""; local_sha=""; compare="not-requested"; reason=""
    [ -s "$body" ] && bytes="$(wc -c < "$body" | tr -d ' ')"
    [ -s "$body" ] && live_sha="$(sha256sum "$body" | awk '{print $1}')"
    local_file="$SITE/$local_rel"
    if [ -s "$local_file" ]; then
      local_sha="$(sha256sum "$local_file" | awk '{print $1}')"
      if [ "$COMPARE" -eq 1 ]; then
        compare="match"; [ "$live_sha" = "$local_sha" ] || { compare="diff"; compare_bad=$((compare_bad+1)); bad+=("$route:local-live-diff"); }
      fi
    elif [ "$COMPARE" -eq 1 ]; then
      compare="local-missing"; compare_bad=$((compare_bad+1)); bad+=("$route:local-missing")
    fi
    if [ "$code" != "200" ] || [ "$bytes" -eq 0 ]; then
      bad+=("$route:http-$code-or-empty")
      reason="HTTP $code أو جسم فارغ"
    fi
    if [ "$route" = "/reports/$DATE.html" ] && [ "$code" = "200" ] && grep -Fq "$DATE" "$body" 2>/dev/null; then
      marker=1
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$label" "$route" "$code" "$bytes" "$local_sha" "$live_sha" "$compare" >> "$TMP/rows.tsv"
    [ -z "$reason" ] || echo "  · $route: $reason" >&2
  done

  # إثبات الإصدار الجديد: رمز 200 وحده لا يثبت أن الإصدار المطلوب وصل.
  [ "$marker" -eq 1 ] || { bad+=("/reports/$DATE.html:deployment-marker-missing"); }
  ATTEMPT_END="$(date +%s.%N)"
  elapsed="$(python3 - "$ATTEMPT_START" "$ATTEMPT_END" <<'PY'
import sys
print(round(float(sys.argv[2])-float(sys.argv[1]), 3))
PY
)"
  END_EPOCH="$(date +%s.%N)"

  python3 - "$LOG" "$DATE" "$BASE" "$COMPARE" "$attempt" "$START_ISO" "$START_EPOCH" "$END_EPOCH" "$elapsed" "$marker" "$TMP/rows.tsv" "${bad[*]-}" <<'PY'
import datetime, json, sys
(log, day, base, compare, attempt, started_iso, start_epoch, end_epoch,
 attempt_seconds, marker, rows_file, bad_text) = sys.argv[1:]
rows=[]
for line in open(rows_file, encoding='utf-8'):
    label, route, code, size, local_sha, live_sha, match = line.rstrip('\n').split('\t')
    rows.append({'label': label, 'path': route, 'code': int(code) if code.isdigit() else 0,
                 'bytes': int(size), 'local_sha256': local_sha or None,
                 'live_sha256': live_sha or None, 'comparison': match})
bad=[x for x in bad_text.split() if x]
doc={'date': day, 'base_url': base, 'checked_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
     'started_at': started_iso, 'attempt': int(attempt), 'attempt_seconds': float(attempt_seconds),
     'propagation_seconds': round(float(end_epoch)-float(start_epoch), 3), 'compare': compare == '1',
     'publish_performed': False, 'decision_required': True, 'deployment_marker_visible': marker == '1',
     'routes': rows, 'status': 'ok' if not bad else 'failed', 'bad': bad}
open(log, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
PY

  if [ "${#bad[@]}" -eq 0 ]; then
    echo "  ✔ تحقق حي مثبت للمسارات السبعة · إصدار $DATE ظاهر · زمن التحقق/الانتشار ${elapsed}s · المحاولة $attempt"
    [ "$COMPARE" -eq 1 ] && echo "  ✔ المقارنة المحلية/الحية مطابقة بالبصمة SHA-256 لكل ملف محلي موجود"
    exit 0
  fi

  echo "  ✘ فشل التحقق في المحاولة $attempt: ${bad[*]}" >&2
  if [ "$attempt" -lt "$RETRIES" ]; then
    echo "  · شخّص السجل $LOG ثم أعد الفحص بعد ${RETRY_SECONDS}s؛ لا يُعاد النشر تلقائيًا ولا يُعلن النجاح"
    sleep "$RETRY_SECONDS"
  fi
  attempt=$((attempt+1))
done

echo "✘ التحقق النهائي فاشل؛ راجع $LOG، شخّص السبب الجذري، ثم قرر إعادة النشر يدويًا قبل إعادة التحقق" >&2
exit 2
