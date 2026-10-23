#!/usr/bin/env bash
# اختبار القسم 9 (warnings): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "التحذيرات والنشرات الرسمية" "$R/reports/$D-sectioned.md" || { echo "✘ القسم التحذيرات والنشرات الرسمية غائب عن تقرير $D"; exit 2; }
test -f "/home/ubuntu/seawatch/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_code_spaces.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم التحذيرات والنشرات الرسمية مرتبط"
exit 0
