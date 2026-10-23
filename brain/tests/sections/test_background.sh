#!/usr/bin/env bash
# اختبار القسم 16 (background): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "الخلفية القائمة" "$R/reports/$D-sectioned.md" || { echo "✘ القسم الخلفية القائمة غائب عن تقرير $D"; exit 2; }
test -f "/home/ubuntu/seawatch/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_carryover.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم الخلفية القائمة مرتبط"
exit 0
