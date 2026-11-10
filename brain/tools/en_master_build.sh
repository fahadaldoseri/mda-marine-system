#!/usr/bin/env bash
# خط البناء باتجاه «النسخة الإنجليزية أصل».
# المسار الوحيد: قفل single-flight → بصمة النص النهائي → بناء HTML → تحقق فوري.
# الاستعمال: bash tools/en_master_build.sh <DATE> [SITE]
set -uo pipefail
D="${1:?تاريخ مطلوب YYYY-MM-DD}"
B="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$B/tools/site_root.sh"
SITE="${2:-${SITE_DIR:-}}"
if ! site_root_resolve "$B"; then
  site_root_message
  exit 2
fi
SITE="$(cd "$SITE" && pwd)"
export B BRAIN_DIR SITE SITE_DIR="$SITE"

exec python3 "$B/tools/build_transaction.py" \
  --date "$D" \
  --brain "$B" \
  --site "$SITE" \
  --timeout "${BUILD_TIMEOUT_SECONDS:-1800}"
