#!/usr/bin/env bash
# فحص مسبق مبكر (المقترح 2، اعتماد فهد 20 نوفمبر 2026) — خطوة S015 بعد استعادة المهارات مباشرة.
#
# القياس قبل الإصلاح: في الاختبار الحي (20 نوفمبر مساءً) توقف الخط عند G000 ثم عند G049 بعد نحو
# 15 و20 دقيقة من البدء، وكان العطلان قابلين للكشف في الدقيقة الأولى بفحوص تستغرق أقل من ثانية.
# هذه الخطوة تشغّل الفحوص الرخيصة نفسها مبكرًا ولا تكتب شيئًا، ولا تحل محل G000 ولا G049:
# تبقى البوابتان في مكانهما وتبقيان مانعتين.
#
#   1) أرضية الأصول الحاكمة (فحص G000 بلا --update): نقص أصل بعد دمج أو تجهيز بيئة.
#   2) عقدا G000 وG049: tests/test_asset_floor.py وtests/test_zone_strip.py.
#   3) شريط نسب القطاعات (مدقق G049) على أحدث صفحة مبنية قبل اليوم: تعارض المولّد والمدقق بعد دمج.
#      إن لم تكن صفحة مبنية بعد (حاوية جديدة) يُعلن التخطي، ويبقى الإنفاذ في G049.
#
# الاستعمال: bash tools/early_preflight.sh DATE   (من جذر brain)
# الرموز: 0 سليم · 2 عطل يمنع المتابعة (يُكتشف الآن بدل الدقيقة 15).
set -uo pipefail
B="${B:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
D="${1:-${D:-$(date -u +%F)}}"
cd "$B" || exit 2
FAIL=0
T0=$(date +%s%N)
run() {  # run "الوصف" أمر...
  local name="$1"; shift
  local out; out="$("$@" 2>&1)"; local rc=$?
  if [ "$rc" -eq 0 ]; then
    printf '  ✔ %s\n' "$name"
  else
    FAIL=$((FAIL+1)); printf '  ✘ %s (رمز %s)\n' "$name" "$rc"; printf '%s\n' "$out" | tail -8 | sed 's/^/      /'
  fi
}

echo "فحص مسبق مبكر — $D"
run "G000: أرضية الأصول الحاكمة (قراءة فقط)" python3 validators/check_asset_floor.py --quiet ${ASSET_FLOOR:+--floor "$ASSET_FLOOR"}
run "G000: عقد أرضية الأصول" python3 tests/test_asset_floor.py
run "G049: عقد شريط نسب القطاعات" python3 -m pytest -q -p no:cacheprovider tests/test_zone_strip.py

. "$B/tools/site_root.sh"
PREV=""
if site_root_resolve "$B"; then
  for f in $(ls -1 "$SITE"/dist/reports/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].html 2>/dev/null | sort -r); do
    d="$(basename "$f" .html)"
    if [[ "$d" < "$D" ]] && [ -f "web/zones/$d.json" ]; then PREV="$d"; break; fi
  done
fi
if [ -n "$PREV" ]; then
  run "G049: شريط نسب القطاعات على أحدث صفحة مبنية ($PREV)" \
    python3 validators/check_zone_strip.py --date "$PREV" --brain "$B" --site "$SITE"
else
  echo "  • تخطٍّ معلن: لا صفحة مبنية قبل $D بعد — يُنفَّذ الفحص في G049 بعد البناء"
fi

printf 'المدة: %s م.ث · الإخفاقات: %s\n' "$(( ($(date +%s%N) - T0) / 1000000 ))" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 2
exit 0
