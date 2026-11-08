#!/usr/bin/env bash
# مساعد تشغيل مؤقت: يشغّل الكتيب ويعرض سبب التوقف مع سجل الخطوة المانعة.
# لا يغيّر أي عقد؛ يُستخدم لتقليل دورات التشخيص أثناء الإصلاح.
set -u
cd /home/ubuntu/mda-marine-system/brain || exit 1
D=$(date -u +%F)
if pgrep -f 'runbook.py run' >/dev/null; then
  echo "   ⚠ تشغيل جارٍ — لا تشغيل متوازٍ"
  exit 3
fi
echo "   البداية: $(date -u +%H:%M:%SZ)"
out=$(python3 tools/runbook.py run --date "$D" 2>&1)
rc=$?
echo "$out" | tail -12 | sed 's/^/   /'
echo "   رمز المحرّك: $rc · النهاية: $(date -u +%H:%M:%SZ)"
if [ "$rc" -ne 0 ]; then
  step=$(echo "$out" | grep -oE 'توقف عند [A-Z0-9]+' | head -1 | awk '{print $3}')
  if [ -n "${step:-}" ]; then
    echo "   ═══ سجل الخطوة المانعة $step ═══"
    tail -16 "logs/runbook/$D/$step.log" 2>/dev/null | cut -c1-180 | sed 's/^/   /'
  fi
fi
exit "$rc"