#!/usr/bin/env bash
# خط التشغيل الصباحي الموحّد — تغذيات + فحص OFAC + حفظ الأصول الرسمية
# الاستخدام: tools/daily_pipeline.sh [UTC_DATE] [OFAC_TARGETS_FILE] [ORIGINALS_URLS_FILE]
set -uo pipefail
D="${1:-$(date -u +%F)}"
TARGETS="${2:-/tmp/ofac-targets.txt}"
URLS="${3:-/tmp/originals.txt}"
B=/home/ubuntu/brain-marine-news
cd "$B" || exit 1
echo "===== خط التشغيل الموحّد — $D ====="

echo "-- 1) التغذيات (38 تغذية) --"
python3 tools/check_feeds.py 2>/dev/null | tail -4

echo "-- 2) فحص OFAC للسفن والوسطاء المذكورين --"
if [ -s "$TARGETS" ]; then python3 tools/ofac_screen.py "$TARGETS" 2>/dev/null | tail -7
else echo "  لا سفن أو وسطاء في نافذة اليوم — تُكتب النتيجة: لا مستهدف" ; fi

echo "-- 3) حفظ الأصول الرسمية --"
if [ -s "$URLS" ]; then python3 tools/archive_originals.py "$D" "$URLS" 2>/dev/null | tail -7
else echo "  لا بلاغ رسمي في نافذة اليوم — لا أصل مطلوب" ; fi

echo "-- خلاصة الخط --"
[ -f "archive/originals/$D/manifest.json" ] && echo "  بيان الأصول: archive/originals/$D/manifest.json" || echo "  بيان الأصول: غير مطلوب/متعذر — يُذكر صراحة في التقرير"
[ -f "archive/ofac-screen-latest.json" ] && echo "  نتيجة OFAC: archive/ofac-screen-latest.json"
[ -f "feeds/feeds-$D.md" ] && echo "  مستجدات التغذيات: feeds/feeds-$D.md"
