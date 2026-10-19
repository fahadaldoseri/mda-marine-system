#!/usr/bin/env bash
# ضمان عمل خادم المعاينة (المنفذ 3000) — الإصدار المعتمد 13 أكتوبر 2026
# السبب الجذري لحادثة 13 أكتوبر: خادم المعاينة عملية مرتبطة بالجلسة، تُقتل عند انتهاء الجلسة،
# فلا شيء يعيد تشغيلها → لوحة المعاينة تعرض «الخادم لا يستجيب» ونسخة المتصفح لا تفتح.
# الحل: يُستدعى هذا السكربت في بداية كل تشغيل (صباحي أو تفاعلي) فيعيد الخادم إن كان متوقفًا.
set -uo pipefail
P="${1:-3000}"
B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SITE="${SITE_DIR:-$(dirname "$B")/seawatch}"
DIST="$SITE/dist"
LOG="$B/logs/devserver-$P.log"
mkdir -p "$B/logs"

probe() { curl -s -o /dev/null -w '%{http_code}' --max-time 6 "http://127.0.0.1:$P/" 2>/dev/null || true; }

if [ ! -d "$DIST" ]; then echo "  ✘ مجلد المخرجات مفقود: $DIST — شغّل build_site.py أولًا"; exit 2; fi
if [ "$(probe)" = "200" ]; then echo "  ✔ خادم المعاينة يعمل على $P"; exit 0; fi

echo "  ↻ خادم المعاينة متوقف — إعادة تشغيل على $P…"
pkill -f "http.server $P" 2>/dev/null || true
sleep 1
nohup python3 -m http.server "$P" --directory "$DIST" --bind 0.0.0.0 >>"$LOG" 2>&1 &
for _ in $(seq 1 15); do
  sleep 1
  if [ "$(probe)" = "200" ]; then echo "  ✔ يعمل الآن على $P (سجل: $LOG)"; exit 0; fi
done
echo "  ✘ تعذّر تشغيل الخادم على $P — راجع $LOG"; exit 1