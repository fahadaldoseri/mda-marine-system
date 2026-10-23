#!/usr/bin/env bash
# اختبار القسم 8 (new-incidents): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "الوقائع الجديدة" "$R/reports/$D-sectioned.md" || { echo "✘ القسم الوقائع الجديدة غائب عن تقرير $D"; exit 2; }
test -f "/home/ubuntu/seawatch/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_language.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم الوقائع الجديدة مرتبط"
exit 0
