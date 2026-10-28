#!/usr/bin/env bash
# اختبار القسم 15 (monitoring): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "المراقبة المستمرة" "$R/reports/$D-sectioned.md" || { echo "✘ القسم المراقبة المستمرة غائب عن تقرير $D"; exit 2; }
test -f "${SITE:-$HOME/seawatch}/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_style.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم المراقبة المستمرة مرتبط"
exit 0
