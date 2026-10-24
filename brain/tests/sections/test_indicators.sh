#!/usr/bin/env bash
# اختبار القسم 5 (indicators): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "مؤشرات الموقف" "$R/reports/$D-sectioned.md" || { echo "✘ القسم مؤشرات الموقف غائب عن تقرير $D"; exit 2; }
test -f "${SITE:-$HOME/seawatch}/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_style.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم مؤشرات الموقف مرتبط"
exit 0
