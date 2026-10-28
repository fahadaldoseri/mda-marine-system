#!/usr/bin/env bash
# تشغيل خادم موقع التقارير إن لم يكن يعمل بالفعل.
# السبب: روابط الرفع السحابي تُخدَّم بترويسة content-disposition: attachment
# فيُنزّل المتصفح الملف بدل عرضه، وينتهي الأمر بفتح الأكواد في محرر نصوص.
# الخادم المحلي يخدم النوع text/html دون تلك الترويسة، فتُعرض الصفحة كصفحة.
set -u
PORT="${1:-8080}"
DIR="/home/ubuntu/brain-marine-news/web/site"

if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
  echo "الخادم يعمل بالفعل على المنفذ ${PORT}"
  exit 0
fi

cd "$(dirname "$0")" || exit 1
nohup python3 -m http.server "${PORT}" --directory "${DIR}" --bind 0.0.0.0 >/tmp/report_site.log 2>&1 &
sleep 2

if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
  echo "تم تشغيل الخادم على المنفذ ${PORT}"
  exit 0
fi

echo "فشل تشغيل الخادم على المنفذ ${PORT}" >&2
tail -5 /tmp/report_site.log >&2 2>/dev/null
exit 1