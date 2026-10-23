#!/usr/bin/env bash
# اختبار القسم 10 (imo-log): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "سجل IMO والحوادث المؤكدة" "$R/reports/$D-sectioned.md" || { echo "✘ القسم سجل IMO والحوادث المؤكدة غائب عن تقرير $D"; exit 2; }
test -f "/home/ubuntu/seawatch/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_carryover.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم سجل IMO والحوادث المؤكدة مرتبط"
exit 0
