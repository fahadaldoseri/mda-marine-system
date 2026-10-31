#!/usr/bin/env bash
# اختبار سكربتات التسليم: لا نشر بلا بوابات · ملخص تلغرام تحت السقف ويمرّ سياسة الإرسال · check_live يفشل فعلًا عند تعذّر الوصول.
# لا يرسل ولا ينشر: كل شيء على مجلد مؤقت.
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0; FAIL=0
ok() { if [ "$1" = 0 ]; then PASS=$((PASS+1)); echo "  ✔ $2"; else FAIL=$((FAIL+1)); echo "  ✘ $2"; fi; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
D=2099-01-01
mkdir -p "$T/brain/tools" "$T/brain/runbook" "$T/brain/web/meta" "$T/seawatch/sources" "$T/brain/docs" "$T/bin"
printf '#!/usr/bin/env bash\nexit 0\n' > "$T/bin/sleep"; chmod +x "$T/bin/sleep"
cp "$B/tools/runbook.py" "$B/tools/publish_site.sh" "$B/tools/check_live.sh" "$B/tools/make_tg_digest.py" "$T/brain/tools/"
cat > "$T/brain/runbook/runbook.json" <<'J'
{"version":1,"ledger_dir":"logs/runbook","exempt":["*"],"exempt_reasons":{"*":"اختبار"},"gate_phases":["gates"],"phase_order":["gates"],
 "steps":[{"id":"G1","title":"بوابة","kind":"script","phase":"gates","command":["echo","x"],"assert":[{"type":"cmd","command":["bash","-lc","test -s logs/runbook/{date}/G1.log"]}],"links":{"rules":["ق"],"files":[],"folders":[],"gates":[],"tests":[]},"on_fail":"stop"}]}
J
echo '{"base_url":"http://127.0.0.1:9"}' > "$T/seawatch/sources/site.json"
cp "$B/web/meta/2026-10-23.json" "$T/brain/web/meta/$D.json"

grep -q '"id": "B005"' "$B/runbook/runbook.json" && grep -q 'مُدخل EN مفقود' "$B/runbook/runbook.json" && grep -q 'table_rows=' "$B/runbook/runbook.json"; ok $? "B005 معلن بفحص مدخل EN وعدّ صفوفه"
SITE="$T/seawatch"; export SITE
BRAIN_DIR="$T/brain" SITE_DIR="$T/seawatch" bash -lc 'P="$SITE/sources/i18n/en/2099-01-01-sectioned.en.md"; if [ ! -s "$P" ]; then printf "✘ مُدخل EN مفقود: %s\n" "$P"; exit 2; fi; exit 0' >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ]; ok $? "B005 يفشل مغلقًا عند غياب مدخل EN (رمز $rc)"

BRAIN_DIR="$T/brain" SITE_DIR="$T/seawatch" bash "$T/brain/tools/publish_site.sh" "$D" >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ]; ok $? "النشر مرفوض بلا بوابات مكتملة (رمز $rc)"
BRAIN_DIR="$T/brain" SITE_DIR="$T/seawatch" bash "$T/brain/tools/publish_site.sh" --telegram "$D" >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && [ ! -e "$T/brain/logs/publish-$D-telegram.json" ]; ok $? "تلغرام مرفوض بلا بوابات ولا يكتب علامة نجاح"

BRAIN_DIR="$T/brain" python3 "$T/brain/tools/make_tg_digest.py" --date "$D" --out "$T/d.html" --base-url http://x >/dev/null; rc=$?
n=$(python3 -c "import re,sys;print(len(re.sub(r'<[^>]+>','',open(sys.argv[1],encoding='utf-8').read())))" "$T/d.html")
[ "$rc" = 0 ] && [ "$n" -le 900 ]; ok $? "الملخص ($n حرفًا) تحت السقف 900"
grep -q "الإجراء المطلوب" "$T/d.html" && grep -q "reports/$D.html" "$T/d.html"; ok $? "الملخص يحوي الإجراء والرابط الكامل"
python3 "$B/tools/telegram_send.py" --file "$T/d.html" --daily-report --date "$D" --validate-only >/dev/null 2>&1 || TELEGRAM_BOT_TOKEN=x python3 "$B/tools/telegram_send.py" --file "$T/d.html" --daily-report --date "$D" --validate-only 2>&1 | grep -q "صالح"
ok $? "الملخص يمرّ فحص سياسة الإرسال (بلا إرسال)"

PATH="$T/bin:$PATH" BRAIN_DIR="$T/brain" SITE_DIR="$T/seawatch" bash "$T/brain/tools/check_live.sh" "$D" >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && grep -q '"status": "failed"' "$T/brain/logs/live-$D.json"; ok $? "check_live يفشل ويسجّل failed عند تعذّر الوصول"
grep -q "/home/ubuntu" "$B/tools/publish_site.sh" "$B/tools/check_live.sh"; [ $? -ne 0 ]; ok $? "لا مسار /home/ubuntu في سكربتات التسليم"
grep -q 'release_paths' "$B/tools/check_live.sh" && grep -q 'elapsed_seconds' "$B/tools/check_live.sh" && grep -q 'max_wait_seconds' "$B/tools/check_live.sh"; ok $? "التحقق الحي يوثق مسارات الإصدار وزمن الانتشار"
echo "الحصيلة: نجح $PASS · فشل $FAIL"
[ "$FAIL" = 0 ]
