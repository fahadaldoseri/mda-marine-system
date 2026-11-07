#!/usr/bin/env bash
# اختبار القسم 4 (incident-map): وجوده في تقرير اليوم ووجود كتلته ومدققه
set -u
D="${1:-$(date -u +%F)}"
R="$(cd "$(dirname "$0")/../.." && pwd)"
grep -q "خريطة الوقائع" "$R/reports/$D-sectioned.md" || { echo "✘ القسم خريطة الوقائع غائب عن تقرير $D"; exit 2; }
test -f "${SITE:-$HOME/seawatch}/generator/blocks.py" || { echo "✘ كتلة التوليد غائبة"; exit 2; }
test -f "$R/validators/check_pdf_format.py" || { echo "✘ مدقق القسم غائب"; exit 2; }
echo "✔ القسم خريطة الوقائع مرتبط"
exit 0
