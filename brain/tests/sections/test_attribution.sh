#!/usr/bin/env bash
# اختبار القسم 12 (attribution): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "الاحتمالات ونسبة الحوادث إلى جهات" "$R/reports/$D-sectioned.md" || { echo "✘ القسم الاحتمالات ونسبة الحوادث إلى جهات غائب عن تقرير $D"; exit 2; }
test -f "/home/ubuntu/seawatch/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_comprehension.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم الاحتمالات ونسبة الحوادث إلى جهات مرتبط"
exit 0
