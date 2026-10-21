#!/usr/bin/env bash
# استعادة المهارات من المستودع إلى النسخة المحلية — تصحيح التماثل (عطل ك-77).
# القاعدة: المصدر الموثوق هو المستودع، والنسخة المحلية في /home/ubuntu/skills مرآة
# تُستعاد آليًا قبل أي تشغيل وقبل أي دفع؛ لأن مجلد المهارات الرسمي قد يُعاد من المنصة.
set -uo pipefail
B="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="${REPO_DIR:-$B/../mda-marine-system}"
REPO="$REPO_DIR/skills"
SK="${SKILLS_DIR:-/home/ubuntu/skills}"
CHECK_ONLY=0; [ "${1:-}" = "--check" ] && CHECK_ONLY=1
[ -d "$REPO" ] || { echo "✘ لا مستودع مهارات في $REPO"; exit 3; }
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" fetch -q origin 2>/dev/null && git -C "$REPO_DIR" checkout -q origin/main -- skills 2>/dev/null || true
fi
diff_list=(); restored=0; newer=0
while IFS= read -r f; do
  rel="${f#"$REPO"/}"
  if [ ! -f "$SK/$rel" ] || ! cmp -s "$f" "$SK/$rel"; then
    diff_list+=("$rel")
    if [ "$CHECK_ONLY" -eq 0 ]; then
      # حاجز ك-79: لا يُستبدل ملف محلي أحدث من نسخة المستودع، لئلا تُفقد تعديلات لم تُدفع.
      if [ -f "$SK/$rel" ] && [ "$SK/$rel" -nt "$f" ]; then
        echo "  ⚠ محلي أحدث ولم يُستبدل (يحتاج دفعًا): $rel"; newer=$((newer + 1))
      else
        mkdir -p "$(dirname "$SK/$rel")"; cp "$f" "$SK/$rel"
        echo "  ↑ استُعيد من المستودع: $rel"; restored=$((restored + 1))
      fi
    fi
  fi
done < <(find "$REPO" -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.txt" \) | sort)
echo "  ملفات المستودع: $(find "$REPO" -type f | wc -l) · مختلفة قبل الاستعادة: ${#diff_list[@]} · مستعاد: $restored · محلي أحدث: $newer"
if [ "$CHECK_ONLY" -eq 1 ] && [ "${#diff_list[@]}" -gt 0 ]; then
  echo "  ✘ التماثل مكسور: ${diff_list[*]:0:5}"; exit 1
fi
echo "  ✔ التماثل سليم: المحلي = المستودع"
