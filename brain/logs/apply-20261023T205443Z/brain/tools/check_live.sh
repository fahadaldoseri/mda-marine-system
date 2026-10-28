#!/usr/bin/env bash
# تحقق حي (قراءة فقط) من النسخة المنشورة: الصفحة الرئيسية · صفحة التقرير · PDF · صفحة المصادر
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
D="${1:-$(date -u +%F)}"
BASE=https://seawatch-xp4qirmr.manus.space
OUT="$B/logs/live-$D.json"
{
  echo "{"
  echo "  \"date\": \"$D\","
  echo "  \"checked_at\": \"$(date -u +%FT%TZ)\","
  first=1
  for u in "" "reports/$D.html" "reports/pdf/$D.pdf" "sources.html"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/$u")
    size=$(curl -s -o /dev/null -w '%{size_download}' "$BASE/$u")
    [ $first -eq 1 ] || echo ","
    first=0
    printf '  "/%s": {"code": %s, "bytes": %s}' "$u" "$code" "$size"
  done
  echo ""
  echo "}"
} > "$OUT"
python3 - "$OUT" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
bad = [k for k, v in d.items() if isinstance(v, dict) and v.get('code') != 200]
print('  ✔ كل المسارات ترد 200' if not bad else f'  ✘ مسارات لا ترد 200: {bad}')
sys.exit(2 if bad else 0)
PY