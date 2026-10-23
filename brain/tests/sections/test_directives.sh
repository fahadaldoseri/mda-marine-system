#!/usr/bin/env bash
# اختبار القسم 7 (directives): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "التوجيهات التشغيلية" "$R/reports/$D-sectioned.md" || { echo "✘ القسم التوجيهات التشغيلية غائب عن تقرير $D"; exit 2; }
test -f "/home/ubuntu/seawatch/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_points_rule.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم التوجيهات التشغيلية مرتبط"
exit 0
