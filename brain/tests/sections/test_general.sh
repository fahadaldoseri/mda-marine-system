#!/usr/bin/env bash
# اختبار القسم 3 (general): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "عام (بطاقة القرار)" "$R/reports/$D-sectioned.md" || { echo "✘ القسم عام (بطاقة القرار) غائب عن تقرير $D"; exit 2; }
test -f "/home/ubuntu/seawatch/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_comprehension.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم عام (بطاقة القرار) مرتبط"
exit 0
