#!/usr/bin/env bash
# النشر وتلغرام: لا يعملان إلا بخطوة في المانيفست وبسجل بوابات مكتمل في المحرّك.
# الاستخدام: bash tools/publish_site.sh [--telegram] UTC_DATE
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
SITE=/home/ubuntu/seawatch
MODE=publish
D=""
for a in "$@"; do
  case "$a" in
    --telegram) MODE=telegram ;;
    *) D="$a" ;;
  esac
done
[ -n "$D" ] || D="$(date -u +%F)"

echo "── بوابة المحرّك قبل $MODE ($D) ──"
python3 "$B/tools/runbook.py" gates-status --date "$D" --root "$B" || {
  echo "✘ رُفض $MODE: سجل المحرّك لا يُظهر اكتمال البوابات. لا نشر خارج المحرّك."
  exit 2; }

if [ "$MODE" = telegram ]; then
  python3 "$B/tools/telegram_send.py" --daily-report --date "$D" \
    --file "/tmp/tg-digest-$D.html" \
    --document "$SITE/dist/reports/pdf/$D.pdf" 2>&1 | tail -3
  echo "{\"date\":\"$D\",\"mode\":\"telegram\",\"gates_ok\":true}" > "$B/logs/publish-$D-telegram.json"
  exit 0
fi

cd "$SITE" || exit 2
git add -A >/dev/null 2>&1
if ! git diff --cached --quiet; then
  git -c user.email=manus@local -c user.name=manus commit -q -m "نشر تقرير $D (عبر محرّك الكتيب)"
fi
git push -q origin main 2>&1 | tail -2
echo "{\"date\":\"$D\",\"mode\":\"publish\",\"gates_ok\":true,\"head\":\"$(git rev-parse --short HEAD)\"}" > "$B/logs/publish-$D.json"
echo "✔ نُشر عبر المحرّك — $D"