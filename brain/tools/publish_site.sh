#!/usr/bin/env bash
# النشر وتلغرام: لا يعملان إلا بخطوة في المانيفست وبسجل بوابات مكتمل في المحرّك.
# الاستخدام: bash tools/publish_site.sh [--telegram] [UTC_DATE]
# يكتب logs/publish-D.json (أو publish-D-telegram.json) بحالة حقيقية، ويخرج بغير الصفر عند الفشل.
set -uo pipefail
B="${BRAIN_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
if [ -n "${SITE_DIR:-}" ]; then SITE="$SITE_DIR"
elif [ -d "$B/../seawatch" ]; then SITE="$(cd "$B/../seawatch" && pwd)"
else SITE="$(cd "$B/../site" 2>/dev/null && pwd)"; fi
MODE=publish
D=""
for a in "$@"; do
  case "$a" in
    --telegram) MODE=telegram ;;
    *) D="$a" ;;
  esac
done
[ -n "$D" ] || D="$(date -u +%F)"
mkdir -p "$B/logs"

record() {  # record FILE STATUS RC EXTRA_JSON_FRAGMENT
  python3 - "$1" "$2" "$3" "$D" "$MODE" "${4:-}" <<'PY'
import json, sys, datetime
f, status, rc, d, mode, extra = sys.argv[1:7]
doc = {"date": d, "mode": mode, "status": status, "rc": int(rc), "gates_ok": True,
       "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
if extra:
    doc.update(json.loads(extra))
open(f, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
PY
}

publish_failure() {
  local rc="$1" why="$2" head="" branch=""
  head="$(git rev-parse HEAD 2>/dev/null || true)"
  branch="$(git symbolic-ref --short -q HEAD 2>/dev/null || true)"
  record "$B/logs/publish-$D.json" failed "$rc" "{\"why\":\"$why\",\"head\":\"$head\",\"branch\":\"$branch\"}"
  echo "✘ فشل النشر فشلًا مغلقًا: $why (رمز $rc)"
  return "$rc"
}

fail_publish() {
  publish_failure "$@"
  exit "$1"
}

echo "── بوابة المحرّك قبل $MODE ($D) ──"
python3 "$B/tools/runbook.py" gates-status --date "$D" --root "$B" || {
  echo "✘ رُفض $MODE: سجل المحرّك لا يُظهر اكتمال البوابات. لا نشر خارج المحرّك."
  exit 2; }
# ك-312: حكم البوابات الفعلي — لا يكفي الاكتمال، يجب ألّا يكون في أي سجل حكم مانع.
# حدّ القياس يختلف: النشر يقف عند D010، أما الرسالة فتقف عند D030 بعد D010/D020.
DELIVERY_STEP="D010"
[ "$MODE" = telegram ] && DELIVERY_STEP="D030"
  # ك-591: البوابة التي صار سجلها قديمًا لأن خطوة نشر أُعيد تشغيلها بعده تُعاد
  # هي نفسها بقياس حقيقي عند حدّ خطوة التسليم؛ والمانع الحقيقي يبقى مانعًا.
  python3 "$B/tools/refresh_stale_gates.py" --date "$D" --root "$B" --delivery-step "$DELIVERY_STEP" || {
    echo "✘ رُفض $MODE: بوابة متقادمة لم تُجدَّد عند حدّ $DELIVERY_STEP. لا نشر."
    exit 2; }
python3 "$B/tools/gate_verdict.py" --date "$D" --root "$B" --delivery-step "$DELIVERY_STEP" --json "$B/logs/gate-verdict-$D.json" || {
  echo "✘ رُفض $MODE: بوابة بحكم مانع في سجل $D. أصلح ثم أعد تشغيل البوابة. لا نشر."
  exit 2; }
# ك-315: تماثل النسخة الإنجليزية يُفحص في النشر نفسه (فشل مغلق).
python3 "$B/validators/check_en_parity.py" --date "$D" || {
  echo "✘ رُفض $MODE: النسخة الإنجليزية غير مطابقة للعربية. لا نشر."
  exit 2; }

if [ "$MODE" = telegram ]; then
  OUT="$B/logs/publish-$D-telegram.json"
  DIG="$B/logs/tg-digest-$D.html"
  PDF="$SITE/dist/reports/pdf/$D.pdf"
  python3 "$B/tools/make_tg_digest.py" --date "$D" --out "$DIG" || { record "$OUT" failed 2 '{"why":"digest"}'; exit 2; }
  # الرسالة لا تسبق النشر (19 نوفمبر 2026): رابط التقرير في الرسالة يجب أن يعيد 200 حيًّا،
  # وإلا فلا إرسال (فشل مغلق). يُعاد تشغيل D030 وحده بعد النشر: runbook.py run --only D030.
  LINK="$(grep -o "https://[^<\" ]*/reports/$D\.html" "$DIG" | tail -1)"
  [ -n "$LINK" ] || { record "$OUT" failed 2 '{"why":"no-report-link"}'; echo "✘ لا رابط تقرير في الرسالة"; exit 2; }
  CODE="$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$LINK" || true)"
  if [ "$CODE" != "200" ]; then
    record "$OUT" failed 2 "{\"why\":\"report-not-live\",\"http\":\"$CODE\"}"
    echo "✘ صفحة التقرير غير منشورة بعد ($CODE): $LINK — لا إرسال قبل النشر"
    exit 2
  fi
  # الطباعة معطلة بأمر المالك (2026-11-03)؛ فيُرسل الملخص نصًّا بلا مرفق PDF.
  if [ -s "$PDF" ]; then
    python3 "$B/tools/telegram_send.py" --daily-report --date "$D" --file "$DIG" --document "$PDF" 2>&1 | tee "$B/logs/telegram-$D.out" | tail -3
    rc=${PIPESTATUS[0]}
    PDF_STATE=attached
  else
    echo "⚠ لا PDF (الطباعة معطلة بأمر المالك) — يُرسل الملخص نصًّا بلا مرفق"
    APPROVAL="$B/logs/owner-approval-$D.txt"
    TODAY="$(date -u +%F)"
    if [ "$D" != "$TODAY" ] && [ -s "$APPROVAL" ]; then
      REASON="$(head -3 "$APPROVAL" | tr '\n' ' ')"
      python3 "$B/tools/telegram_send.py" --daily-report --date "$D" --file "$DIG" --owner-approved --reason "$REASON" 2>&1 | tee "$B/logs/telegram-$D.out" | tail -3
    else
      python3 "$B/tools/telegram_send.py" --daily-report --date "$D" --file "$DIG" 2>&1 | tee "$B/logs/telegram-$D.out" | tail -3
    fi
    rc=${PIPESTATUS[0]}
    PDF_STATE=skipped-printing-disabled
  fi
  if [ "$rc" -eq 0 ]; then record "$OUT" ok 0 "{\"pdf\":\"$PDF_STATE\"}"; echo "✔ أُرسل ملخص $D"; else record "$OUT" failed "$rc"; echo "✘ فشل إرسال تلغرام (رمز $rc)"; fi
  exit "$rc"
fi

cd "$SITE" || { record "$B/logs/publish-$D.json" failed 2 '{"why":"no-site"}'; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || fail_publish 2 no-git-site
git symbolic-ref --short -q HEAD >/dev/null 2>&1 || fail_publish 4 detached-head
# اجلب مرجع main قبل أي دفع؛ الدفع اللاحق لا يُسمح له بتجاوز تقدّم بعيد غير مُثبت.
git fetch -q origin main || fail_publish 4 fetch-origin-main
origin_before="$(git rev-parse refs/remotes/origin/main 2>/dev/null || true)"
[ -n "$origin_before" ] || fail_publish 4 missing-origin-main
# تُسجّل مخرجات البناء، ثم لا يُسمح بالدفع إلا من شجرة نظيفة فعلًا.
git add -A >/dev/null 2>&1 || fail_publish 3 stage
if ! git diff --cached --quiet; then
  git -c user.email=manus@local -c user.name=manus commit -q -m "نشر تقرير $D (عبر محرّك الكتيب)" || fail_publish 3 commit
fi
[ -z "$(git status --porcelain)" ] || fail_publish 4 dirty-tree
head="$(git rev-parse HEAD)"
head_short="$(git rev-parse --short HEAD)"
# رأس النسخة المقصودة يجب أن يحمل صفحة اليوم وفهرس المسارات؛ وإلا لا ندفع إصدارًا آخر بالخطأ.
git cat-file -e "HEAD:dist/reports/$D.html" 2>/dev/null || fail_publish 4 intended-head-missing-report
if ! git show "HEAD:dist/manus-routes.json" 2>/dev/null | grep -Fq "/reports/$D.html"; then
  fail_publish 4 intended-head-missing-route
fi
# لا force-push: origin/main يجب أن يكون سلفًا لرأس النسخة المقصودة.
git merge-base --is-ancestor "$origin_before" "$head" || fail_publish 4 origin-main-not-ancestor
PUSH_LOG="$(mktemp)"
trap 'rm -f "$PUSH_LOG"' EXIT
if ! git push -q origin HEAD:main >"$PUSH_LOG" 2>&1; then
  tail -5 "$PUSH_LOG"
  rc=1
  record "$B/logs/publish-$D.json" failed "$rc" "{\"why\":\"push\",\"head\":\"$head\",\"head_short\":\"$head_short\",\"origin_before\":\"$origin_before\",\"branch\":\"$(git symbolic-ref --short HEAD)\",\"pushed_ref\":\"HEAD:main\"}"
  echo "✘ فشل الدفع إلى HEAD:main (رمز $rc)"
  exit "$rc"
fi
tail -5 "$PUSH_LOG"
# جلب مرجع origin/main من جديد ثم قارنه بالرأس المدفوع فعليًا؛ نجاح الدفع وحده ليس دليل نشر.
git fetch -q origin main || fail_publish 5 post-push-fetch-origin-main
origin_after="$(git rev-parse refs/remotes/origin/main 2>/dev/null || true)"
if [ "$origin_after" != "$head" ]; then
  record "$B/logs/publish-$D.json" failed 5 "{\"why\":\"post-push-origin-mismatch\",\"head\":\"$head\",\"head_short\":\"$head_short\",\"origin_before\":\"$origin_before\",\"origin_main\":\"$origin_after\",\"branch\":\"$(git symbolic-ref --short HEAD)\",\"pushed_ref\":\"HEAD:main\"}"
  echo "✘ فشل التحقق بعد الدفع: origin/main=$origin_after والرأس=$head"
  exit 5
fi
BASE_URL="${LIVE_BASE_URL:-}"
if [ -z "$BASE_URL" ] && [ -s "$SITE/sources/site.json" ]; then
  BASE_URL="$(python3 - "$SITE/sources/site.json" <<'PY'
import json, sys
try:
    print(str(json.load(open(sys.argv[1], encoding='utf-8')).get('base_url') or '').rstrip('/'))
except (OSError, json.JSONDecodeError):
    print('')
PY
)"
fi
[ -n "$BASE_URL" ] || fail_publish 2 missing-live-base-url
if ! LIVE_BASE_URL="$BASE_URL" bash "$B/tools/check_live.sh" "$D"; then
  record "$B/logs/publish-$D.json" failed 2 "{\"why\":\"live-http-verification\",\"head\":\"$head\",\"head_short\":\"$head_short\",\"origin_main\":\"$origin_after\",\"live_base\":\"$BASE_URL\"}"
  echo "✘ فشل التحقق الحي بعد Git — لا status=ok بلا HTTP 200"
  exit 2
fi
LIVE_JSON="$(cat "$B/logs/live-$D.json")"
record "$B/logs/publish-$D.json" ok 0 "{\"head\":\"$head\",\"head_short\":\"$head_short\",\"origin_before\":\"$origin_before\",\"origin_main\":\"$origin_after\",\"branch\":\"$(git symbolic-ref --short HEAD)\",\"pushed_ref\":\"HEAD:main\",\"report_path\":\"/reports/$D.html\",\"live\":$LIVE_JSON}"
echo "✔ نُشر عبر HEAD:main — $D ($head_short) — origin/main مطابق — live HTTP 200 verified"
exit 0
