#!/usr/bin/env bash
# يجلب أحدث main من المستودع ويطبّق الشيفرة والقواعد على الخادم (انظر tools/apply_from_github.py).
# الاستعمال: bash tools/apply_from_github.sh [--dry-run] [--accept-repo]
set -uo pipefail
B="${BRAIN_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
REPO="${BACKUP_REPO_DIR:-$(dirname "$B")/mda-marine-system}"
[ -e "$REPO/.git" ] || { echo "✘ لا مستودع في $REPO"; exit 2; }
if [ -n "$(git -C "$REPO" status --porcelain 2>/dev/null | head -1)" ]; then
  echo "✘ شجرة المستودع غير نظيفة: يوجد تعديل غير مدفوع في $REPO. ادفعه أو أرجعه أولًا."; exit 2
fi
git -C "$REPO" fetch -q origin main || { echo "✘ تعذّر الجلب من origin"; exit 2; }
git -C "$REPO" checkout -q main 2>/dev/null
git -C "$REPO" merge -q --ff-only origin/main || { echo "✘ main المحلي لا يتقدّم إلى origin/main بلا دمج (تباعد)"; exit 2; }
exec python3 "$B/tools/apply_from_github.py" --repo "$REPO" --brain "$B" "$@"
