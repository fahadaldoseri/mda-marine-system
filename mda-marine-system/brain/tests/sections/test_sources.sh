#!/usr/bin/env bash
# اختبار القسم 17 (sources): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "المصادر والمراجع" "$R/reports/$D-sectioned.md" || { echo "✘ القسم المصادر والمراجع غائب عن تقرير $D"; exit 2; }
test -f "${SITE:-$HOME/seawatch}/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_sources_count.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم المصادر والمراجع مرتبط"
exit 0
