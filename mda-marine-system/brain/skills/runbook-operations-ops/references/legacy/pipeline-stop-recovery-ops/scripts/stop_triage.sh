#!/usr/bin/env bash
# لقطة تشخيص حية لخط تشغيل متوقف — تُقرأ ولا تُعدّل شيئًا.
# الاستخدام: stop_triage.sh --date 2026-10-29 [--brain DIR] [--site DIR] [--url ORIGIN]
set -u

DATE=""
BRAIN="/home/ubuntu/brain-marine-news"
SITE="/home/ubuntu/seawatch"
URL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --date) DATE="${2:-}"; shift 2 ;;
    --brain) BRAIN="${2:-}"; shift 2 ;;
    --site) SITE="${2:-}"; shift 2 ;;
    --url) URL="${2:-}"; shift 2 ;;
    *) echo "✘ خيار غير معروف: $1" >&2; exit 2 ;;
  esac
done
[ -n "$DATE" ] || { echo "✘ يلزم --date" >&2; exit 2; }
cd "$BRAIN" || exit 2

echo "══ لقطة توقف الخط · $DATE ══"
echo "── حالة الكتيب ──"
python3 tools/runbook.py status --date "$DATE" 2>&1 | grep -aE "failed|لم تبدأ" | head -6 | sed 's/^/   /'
done_n=$(python3 tools/runbook.py status --date "$DATE" 2>&1 | grep -acE "done")
echo "   خطوات منتهية: $done_n"

echo "── الخطوة المتوقفة وذيل سجلها ──"
STEP=$(python3 tools/runbook.py status --date "$DATE" 2>&1 | grep -a "failed" | head -1 | awk '{print $1}')
if [ -n "${STEP:-}" ]; then
  echo "   المتوقفة: $STEP"
  tail -14 "logs/runbook/$DATE/$STEP.log" 2>/dev/null | cut -c1-170 | sed 's/^/   /' || echo "   لا سجل للخطوة"
else
  echo "   لا خطوة فاشلة مسجّلة — تحقّق من خطوات «لم تبدأ» أو من سجل المحرّك."
fi

echo "── عمليات كتيب جارية ──"
pgrep -af "runbook.py run --date $DATE" | sed 's/^/   /' || echo "   لا شيء"

if [ -n "$URL" ]; then
  echo "── الروابط الحية ──"
  for p in / "/reports/$DATE.html" "/reports/pdf/$DATE.pdf" /sources.html /additions.html /feed.xml; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$URL$p" 2>/dev/null)
    echo "   $code  $p"
  done
else
  echo "── الروابط الحية: (لم يُمرَّر --url) ──"
fi

echo "── التماثل ──"
python3 validators/check_backup_parity.py --mode strict 2>&1 | tail -4 | cut -c1-170 | sed 's/^/   /'

echo "── شجرة الموقع: ملفات غير ملتزم بها ──"
if [ -d "$SITE/.git" ]; then
  git -C "$SITE" status --porcelain | wc -l | sed 's/^/   معدّل: /'
else
  echo "   لا مستودع في $SITE"
fi
