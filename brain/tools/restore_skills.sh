#!/usr/bin/env bash
# استعادة المهارات من المستودع عند نقص القواعد المعتمدة (عطل ك-48).
# لا يُدفع نقص فوق المستودع؛ يُستعاد المستودع إلى المجلد المحلي أولًا.
set -uo pipefail
B="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$B/../mda-marine-system/skills"
SK="/home/ubuntu/skills"
[ -d "$REPO" ] || { echo "✘ لا مستودع مهارات في $REPO"; exit 3; }
cd "$B/../mda-marine-system" && git fetch -q origin 2>/dev/null && git checkout -q origin/main -- skills 2>/dev/null || true
restored=0
while IFS= read -r f; do
  rel="${f#$REPO/}"
  if [ ! -f "$SK/$rel" ] || ! cmp -s "$f" "$SK/$rel"; then
    if python3 "$B/validators/check_skills_integrity.py" >/dev/null 2>&1; then break; fi
    mkdir -p "$(dirname "$SK/$rel")"
    cp "$f" "$SK/$rel"
    echo "  ↑ استُعيد: $rel"
    restored=$((restored+1))
  fi
done < <(find "$REPO" -type f -name "*.md")
echo "  عدد المستعاد: $restored"
