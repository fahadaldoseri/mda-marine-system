#!/usr/bin/env bash
# جمع أدلة إغلاق الجولة في تقرير واحد: حالة الكتيب · التماثل · حارس الإغلاق ·
# الروابط الحية · مطابقة بصمة PDF · آخر صفوف سجل الأعطال.
# قراءة فقط — لا يعدّل شيئًا.
#
# الاستعمال: bash round_close_check.sh --date 2026-10-30 [--brain DIR] [--site DIR] [--url ORIGIN]
set -uo pipefail

DATE=""; BRAIN="/home/ubuntu/brain-marine-news"; SITE="/home/ubuntu/seawatch"; URL="https://seawatch-xp4qirmr.manus.space"
while [ $# -gt 0 ]; do
  case "$1" in
    --date) DATE="$2"; shift 2;;
    --brain) BRAIN="$2"; shift 2;;
    --site) SITE="$2"; shift 2;;
    --url) URL="$2"; shift 2;;
    *) echo "وسيط غير معروف: $1" >&2; exit 64;;
  esac
done
[ -n "$DATE" ] || { echo "مطلوب --date" >&2; exit 64; }

OUT="/home/ubuntu/audit-${DATE}/round-close-${DATE}.md"
mkdir -p "$(dirname "$OUT")"
cd "$BRAIN" || exit 66
say() { printf '%s\n' "$*" >> "$OUT"; }

say "# أدلة إغلاق جولة ${DATE}"
say ""
say "زمن التوليد: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
say ""

say "## 1) حالة الكتيب"
python3 tools/runbook.py status --date "$DATE" >> "$OUT" 2>&1 || say "(تعذّر قراءة الحالة)"
say ""

say "## 2) التماثل بين الخادم والمستودع"
PAR=$(python3 validators/check_backup_parity.py 2>&1); PAR_RC=$?
say '```'
say "$(printf '%s' "$PAR" | tail -6)"
say '```'
say "رمز الخروج: ${PAR_RC}"
say ""

say "## 3) حارس الإغلاق (الأعطال والدروس)"
CL=$(python3 validators/check_closure.py --brain . 2>&1); CL_RC=$?
say '```'
say "$(printf '%s' "$CL" | tail -5)"
say '```'
say "رمز الخروج: ${CL_RC}"
say ""

say "## 4) الروابط الحية"
for p in / "/reports/${DATE}.html" "/reports/en/${DATE}.html" "/reports/pdf/${DATE}.pdf" /sources.html /additions.html /manus-routes.json; do
  code=$(curl -s -o /dev/null -w '%{http_code} %{size_download}B' "$URL$p")
  say "- \`$p\` → $code"
done
say ""

say "## 5) مطابقة بصمة PDF الحي للمحلي"
LOCAL="$SITE/dist/reports/pdf/${DATE}.pdf"
TMP="/tmp/roundclose-${DATE}.pdf"
curl -s -A 'Mozilla/5.0' "$URL/reports/pdf/${DATE}.pdf" -o "$TMP"
if [ -f "$LOCAL" ]; then
  say "- المحلي: \`$(sha256sum "$LOCAL" | cut -c1-24)…\`"
  say "- الحي:   \`$(sha256sum "$TMP" | cut -c1-24)…\`"
  if cmp -s "$LOCAL" "$TMP"; then say "- النتيجة: مطابق"; else say "- النتيجة: مختلف — لا تُعلن الإغلاق"; fi
else
  say "- ملف PDF المحلي غير موجود: $LOCAL"
fi
say ""

say "## 6) آخر صفوف سجل الأعطال"
say '```'
say "$(grep -a '^| ك-' audit/سجل-الأعطال-والثغرات.md | tail -5 | cut -c1-150)"
say '```'
say ""
say "## 7) الحكم"
if [ "$PAR_RC" -eq 0 ] && [ "$CL_RC" -eq 0 ]; then
  say "التماثل مطابق وحارس الإغلاق مجتاز — الجولة قابلة للإعلان بشرط مطابقة بصمة PDF أعلاه."
else
  say "غير جاهز للإعلان: التماثل=${PAR_RC} · حارس الإغلاق=${CL_RC}."
fi
echo "   كُتب: $OUT"
tail -14 "$OUT" | sed 's/^/   /'