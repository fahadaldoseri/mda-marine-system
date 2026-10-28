#!/usr/bin/env bash
# اختبار القسم 1 (what-changed): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "ما تغيّر منذ التقرير السابق" "$R/reports/$D-sectioned.md" || { echo "✘ القسم ما تغيّر منذ التقرير السابق غائب عن تقرير $D"; exit 2; }
test -f "${SITE:-$HOME/seawatch}/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_carryover.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم ما تغيّر منذ التقرير السابق مرتبط"
exit 0
