#!/usr/bin/env bash
# اختبار القسم 6 (threat-level): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "مستوى التهديد" "$R/reports/$D-sectioned.md" || { echo "✘ القسم مستوى التهديد غائب عن تقرير $D"; exit 2; }
test -f "${SITE:-$HOME/seawatch}/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_intel.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم مستوى التهديد مرتبط"
exit 0
