#!/usr/bin/env bash
# خط البناء باتجاه «النسخة الإنجليزية أصل» (قرار المالك 2026-11-03).
#
# المبدأ: المتن الإنجليزي sources/i18n/en/<DATE>-sectioned.en.md هو أصل النص الإنجليزي.
# فإذا بقيت وحدة عربية في صفحة مبنية بلا مقابل، تُشتقّ من المتن الإنجليزي الحاكم
# (generator/derive_en_units.py) وتُقيَّد في المعجم، ثم يُعاد البناء. لا تخمين ولا ترجمة آلية.
#
# الاستعمال: bash tools/en_master_build.sh <DATE> [SITE]
set -uo pipefail
D="${1:?تاريخ مطلوب YYYY-MM-DD}"
SITE="${2:-${SITE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../seawatch" && pwd)}}"
export SITE
cd "$SITE" || exit 2

echo "── 1) بناء أول (قد يفشل مغلقًا على وحدات بلا مقابل) ──"
timeout 1800 python3 generator/build_site.py > /tmp/en_master_build_1.log 2>&1
rc1=$?
echo "   rc=$rc1"
if [ "$rc1" -eq 0 ]; then
  echo "   ✔ لا وحدة ناقصة — لا حاجة للاشتقاق"
  exit 0
fi
grep -nE "نصوص عربية بلا ترجمة" /tmp/en_master_build_1.log | tail -1 | cut -c1-160 | sed 's/^/   |/'

echo "── 2) اشتقاق الوحدات من المتن الإنجليزي الحاكم ──"
timeout 900 python3 generator/derive_en_units.py --date "$D" --apply 2>&1 | tail -8 | cut -c1-190 | sed 's/^/   |/'
rc2=$?
if [ "$rc2" -ne 0 ]; then
  echo "✘ تعذّر اشتقاق وحدة أو أكثر — راجع المخرَج أعلاه (فشل مغلق، بلا تخمين)"
  exit 2
fi

echo "── 3) إعادة البناء ──"
timeout 1800 python3 generator/build_site.py > /tmp/en_master_build_2.log 2>&1
rc3=$?
echo "   rc=$rc3"
tail -4 /tmp/en_master_build_2.log | cut -c1-180 | sed 's/^/   |/'
exit "$rc3"