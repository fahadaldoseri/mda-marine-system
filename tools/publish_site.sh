#!/usr/bin/env bash
# النشر وتلغرام: لا يعملان إلا بخطوة في المانيفست وبسجل بوابات مكتمل في المحرّك.
# الاستخدام: bash tools/publish_site.sh [--telegram] [UTC_DATE]
# يكتب logs/publish-D.json (أو publish-D-telegram.json) بحالة حقيقية: status=ok|failed وrc؛ ويخرج بغير الصفر عند الفشل.
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

echo "── بوابة المحرّك قبل $MODE ($D) ──"
python3 "$B/tools/runbook.py" gates-status --date "$D" --root "$B" || {
  echo "✘ رُفض $MODE: سجل المحرّك لا يُظهر اكتمال البوابات. لا نشر خارج المحرّك."
  exit 2; }

if [ "$MODE" = telegram ]; then
  OUT="$B/logs/publish-$D-telegram.json"
  DIG="$B/logs/tg-digest-$D.html"
  PDF="$SITE/dist/reports/pdf/$D.pdf"
  python3 "$B/tools/make_tg_digest.py" --date "$D" --out "$DIG" || { record "$OUT" failed 2 '{"why":"digest"}'; exit 2; }
  [ -s "$PDF" ] || { echo "✘ لا PDF: $PDF"; record "$OUT" failed 2 '{"why":"pdf-missing"}'; exit 2; }
  python3 "$B/tools/telegram_send.py" --daily-report --date "$D" --file "$DIG" --document "$PDF" 2>&1 | tee "$B/logs/telegram-$D.out" | tail -3
  rc=${PIPESTATUS[0]}
  if [ "$rc" -eq 0 ]; then record "$OUT" ok 0; echo "✔ أُرسل ملخص $D"; else record "$OUT" failed "$rc"; echo "✘ فشل إرسال تلغرام (رمز $rc)"; fi
  exit "$rc"
fi

cd "$SITE" || { record "$B/logs/publish-$D.json" failed 2 '{"why":"no-site"}'; exit 2; }
git add -A >/dev/null 2>&1
if ! git diff --cached --quiet; then
  git -c user.email=manus@local -c user.name=manus commit -q -m "نشر تقرير $D (عبر محرّك الكتيب)" || { record "$B/logs/publish-$D.json" failed 3 '{"why":"commit"}'; exit 3; }
fi
git push -q origin main 2>&1 | tail -2
rc=${PIPESTATUS[0]}
head="$(git rev-parse --short HEAD)"
if [ "$rc" -eq 0 ]; then
  record "$B/logs/publish-$D.json" ok 0 "{\"head\":\"$head\"}"; echo "✔ نُشر عبر المحرّك — $D ($head)"
else
  record "$B/logs/publish-$D.json" failed "$rc" "{\"head\":\"$head\"}"; echo "✘ فشل الدفع (رمز $rc)"
fi
exit "$rc"
