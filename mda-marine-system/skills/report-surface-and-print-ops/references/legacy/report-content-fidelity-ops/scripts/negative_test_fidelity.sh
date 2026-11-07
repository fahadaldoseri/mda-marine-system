#!/usr/bin/env bash
# اختبار سلبي لأمانة المحتوى: يعيد إنتاج الخلل الحقيقي في نسخة مؤقتة
# (بطاقات بيانات القسم تُستبدل ببطاقات مصدر = سقوط الأعمدة)، ويتأكد أن المقياس
# يمنع (رمز 1)، ثم يتأكد أن الأصل يمرّ (رمز 0).
# الاستعمال: negative_test_fidelity.sh REPORT.md PAGE.html "قسم أ"
set -u
MD="$1"; HTML="$2"; SEC="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"; cp "$HTML" "$TMP/page.html"; trap 'rm -rf "$TMP"' EXIT
python3 "$HERE/inject_fidelity_break.py" "$TMP/page.html" "$SEC" || exit 2
python3 "$HERE/check_surface_fidelity.py" --md "$MD" --html "$TMP/page.html" --sections "$SEC" >/dev/null 2>&1
neg=$?
python3 "$HERE/check_surface_fidelity.py" --md "$MD" --html "$HTML" --sections "$SEC" >/dev/null 2>&1
pos=$?
printf "   بعد الحقن (يُتوقع 1): %s\n   الأصل (يُتوقع 0): %s\n" "$neg" "$pos"
if [ "$neg" = 1 ] && [ "$pos" = 0 ]; then echo "   ✓ الاختبار السلبي ناجح — الحاجز يمنع"; exit 0; fi
echo "   ✗ الاختبار السلبي فاشل — الحاجز لا يمنع"; exit 1
