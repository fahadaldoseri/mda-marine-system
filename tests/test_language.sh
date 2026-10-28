#!/usr/bin/env bash
set -u
B="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0
ok() { PASS=$((PASS+1)); printf '  ✔ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ✘ %s\n' "$1"; }
check() {
  if [ "$1" = "$2" ]; then ok "$3 (=$1)"; else bad "$3 — المتوقع $2 والواقع $1"; fi
}
run() { python3 "$1" "${@:2}" >"$TMP/out" 2>&1; return $?; }

BRAIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export BRAIN_DIR
echo "===== اختبار بوابات اللغة والتسرب ====="

cat >"$TMP/defects.md" <<'EOF'
فقرة فيها خلل، . وخلل آخر .، وخلل ثالث ،، وخلل رابع ..
خلل مسافة قبل ، وخلل مسافة قبل . وخلل مسافة قبل : وخلل مسافة قبل ؛ وخلل مسافة قبل ؟ وخلل مسافة قبل !.
هذه هوية معلنةة، وهذه نشرة استشاريةان، ولفظ ممنوع عبورات.
نفّذوا — القرار الأول. نفّذوا — القرار الثاني. نفّذوا — القرار الثالث.
الله في النص المشروع، وكلمة زرقون غير معروفة.
EOF
if run "$B/validators/check_prose_defects.py" --md "$TMP/defects.md"; then st=0; else st=$?; fi
check "$st" "2" "عيوب الصياغة المانعة تُخرج الرمز 2"
if grep -q "، \." "$TMP/out" && grep -q "معلنةة" "$TMP/out" && grep -q "عبورات" "$TMP/out" && grep -q "نفّذوا" "$TMP/out"; then
  ok "بوابة الصياغة تطبع أمثلة العيوب المانعة"
else
  bad "بوابة الصياغة لم تطبع أمثلة العيوب المطلوبة"
fi
if grep -q "الله" "$TMP/out"; then
  bad "الكلمة البيضاء الله رُصدت خطأً"
else
  ok "القائمة البيضاء للحروف المضاعفة تستبعد الله"
fi

cat >"$TMP/warning.md" <<'EOF'
نص سليم لغويًا، لكنه يذكر كلمة زرقون.
EOF
if run "$B/validators/check_prose_defects.py" --md "$TMP/warning.md"; then st=0; else st=$?; fi
check "$st" "1" "الكلمات خارج المعجم تحذير غير مانع"

cat >"$TMP/clean.md" <<'EOF'
أفادت الجهة البحرية بأن السفينة واصلت رحلتها بلا حادث.
EOF
if run "$B/validators/check_prose_defects.py" --md "$TMP/clean.md"; then st=0; else st=$?; fi
check "$st" "0" "النص النظيف ينجح"

cat >"$TMP/leak.md" <<'EOF'
## الخلاصة
تحدثت المراجعة الداخلية عن التشغيل في هذه الفقرة.
EOF
if run "$B/validators/check_internal_leak.py" --md "$TMP/leak.md"; then st=0; else st=$?; fi
check "$st" "2" "بوابة التسرب تمنع الفقرة الداخلية"
if grep -q "المراجعة الداخلية" "$TMP/out" && grep -q "السطر" "$TMP/out"; then
  ok "بوابة التسرب تطبع السطر والسبب"
else
  bad "بوابة التسرب لم تطبع السطر والسبب"
fi

cat >"$TMP/clean-leak.md" <<'EOF'
## الخلاصة
أفادت جهة ملاحية بأن حركة السفن عادت إلى مستواها المعتاد.
EOF
if run "$B/validators/check_internal_leak.py" --md "$TMP/clean-leak.md"; then st=0; else st=$?; fi
check "$st" "0" "المتن الخالي من التسرب ينجح"

cat >"/tmp/marine-language-leak-test.md" <<'EOF'
هذه فقرة تجريبية عن validators/check_secret.py داخل التقرير.
EOF
if run "$B/validators/check_internal_leak.py" --md /tmp/marine-language-leak-test.md; then st=0; else st=$?; fi
check "$st" "2" "السطر المحقون في /tmp يُلتقط"

if tail -8 "$B/validators/check_prose_defects.py" | grep -q 'from _guard import run' && tail -8 "$B/validators/check_internal_leak.py" | grep -q 'from _guard import run'; then
  ok "المدققان ينتهيان بالحارس الموحد"
else
  bad "نهاية أحد المدققين لا تستخدم الحارس الموحد"
fi

if python3 - <<'PY'
import json, os
from pathlib import Path
for name in ('forbidden-coinages.json','simplified-vocabulary.json'):
    data=json.loads((Path(os.environ['BRAIN_DIR'])/'appendices'/name).read_text(encoding='utf-8'))
    assert isinstance(data, dict)
    assert data.get('entries')
    assert all(item.get('source') for item in data['entries'])
PY
then
  ok "ملفا المفردات والمنع صالحان ولهما مصادر"
else
  bad "ملفا المفردات والمنع غير صالحين أو بلا مصادر"
fi

echo "----- الحصيلة -----"
printf '  نجح: %s · فشل: %s\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
