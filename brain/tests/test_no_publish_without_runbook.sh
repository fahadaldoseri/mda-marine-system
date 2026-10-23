#!/usr/bin/env bash
# اختبار 10: محاولة نشر مباشر دون المرور بالمحرّك (سجل بوابات ناقص) → رفض.
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
D="${1:-$(date -u +%F)}"
L="$B/logs/runbook/$D.jsonl"
BAK=""
if [ -f "$L" ]; then BAK="$L.bak-test"; cp "$L" "$BAK"; fi
mkdir -p "$(dirname "$L")"
echo '{"step":"S000","status":"done","ts":"x"}' > "$L"   # سجل ناقص عمدًا
out=$(bash "$B/tools/publish_site.sh" "$D" 2>&1); rc=$?
[ -f "$BAK" ] && mv "$BAK" "$L" || rm -f "$L"
if [ "$rc" = 2 ] && echo "$out" | grep -q "رُفض"; then
  echo "  ✔ النشر خارج المحرّك مرفوض (رمز 2)"; exit 0
fi
echo "  ✘ النشر خارج المحرّك لم يُرفض (رمز $rc)"; echo "$out" | tail -3; exit 2