#!/usr/bin/env bash
# يشغّل FreeLLMAPI محليًا (127.0.0.1 فقط) لخطوتي S080 وS090 خارج Manus.
# الإصدار مثبّت على التزام راجعه Claude في 2026-11-26.
# مفاتيح المزوّدين تُقرأ من متغيرات البيئة السرية ولا تُطبع:
#   FREELLMAPI_GROQ_KEY  FREELLMAPI_GOOGLE_KEY  FREELLMAPI_OPENROUTER_KEY  FREELLMAPI_CEREBRAS_KEY  FREELLMAPI_MISTRAL_KEY
# الناتج: ملف بيئة (0600) يُحمَّل قبل الخطوتين:  . "$FREELLMAPI_ENV_FILE"
# رمز الخروج: 0 جاهز، 3 لا مفاتيح مزوّدين (تبقى الخطوتان اختياريتين وتفشلان بأمان)، 1 عطل.
set -uo pipefail
REPO=https://github.com/tashfeenahmed/freellmapi.git
COMMIT=5bd4e72
DIR="${FREELLMAPI_DIR:-$HOME/freellmapi}"
PORT="${FREELLMAPI_PORT:-3001}"
ENV_OUT="${FREELLMAPI_ENV_FILE:-$HOME/.freellmapi.env}"

keys_json=$(node -e '
const m={groq:"FREELLMAPI_GROQ_KEY",google:"FREELLMAPI_GOOGLE_KEY",openrouter:"FREELLMAPI_OPENROUTER_KEY",cerebras:"FREELLMAPI_CEREBRAS_KEY",mistral:"FREELLMAPI_MISTRAL_KEY"};
const keys=Object.entries(m).filter(([,v])=>process.env[v]).map(([p,v])=>({platform:p,key:process.env[v],label:"seawatch"}));
process.stdout.write(JSON.stringify({keys}));')
nkeys=$(node -e 'console.log(JSON.parse(process.argv[1]).keys.length)' "$keys_json")
if [ "$nkeys" = "0" ]; then echo "freellmapi: لا مفاتيح مزوّدين في البيئة — تخطٍّ"; exit 3; fi

if [ ! -d "$DIR/.git" ]; then
  git clone -q "$REPO" "$DIR" || { echo "freellmapi: فشل الاستنساخ"; exit 1; }
fi
git -C "$DIR" fetch -q --depth 1 origin "$COMMIT" 2>/dev/null || true
git -C "$DIR" checkout -q "$COMMIT" || { echo "freellmapi: الالتزام $COMMIT غير متاح"; exit 1; }
[ -d "$DIR/node_modules" ] || (cd "$DIR" && npm ci --no-audit --no-fund >/dev/null 2>&1) || { echo "freellmapi: فشل تثبيت الحزم"; exit 1; }

if [ ! -f "$DIR/.env" ]; then
  umask 077
  printf 'ENCRYPTION_KEY=%s\nPORT=%s\nHOST=127.0.0.1\nFREELLMAPI_UPDATE_CHECK=off\n' \
    "$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")" "$PORT" > "$DIR/.env"
fi

if ! curl -s -o /dev/null "http://127.0.0.1:$PORT/v1/models"; then
  (cd "$DIR/server" && set -a && . ../.env && set +a && FREEAPI_CONFIG_JSON="$keys_json" \
     nohup npx tsx src/index.ts > "$DIR/server.log" 2>&1 &)
  for _ in $(seq 1 60); do curl -s -o /dev/null "http://127.0.0.1:$PORT/v1/models" && break; sleep 1; done
fi
curl -s -o /dev/null "http://127.0.0.1:$PORT/v1/models" || { echo "freellmapi: الخادم لم يبدأ"; exit 1; }

# يُطفأ كل مزوّد لم يُضف بمفتاح SeaWatch، ومنها المزوّدون بلا مفتاح (aihorde وkilo وovh وparallel)
# التي تفعّلها الأداة تلقائيًا بعد أول مزامنة للكتالوج (بعد بدء الخادم بثوانٍ)، لأن بعضها شبكات متطوعين
# يرون نص الطلب. أثبت تشغيل GitHub الأول (26 نوفمبر) أن UPDATE واحدًا بعد البدء يسبقها فيُلغى أثره
# وتُوجَّه الطلبات إلى kilo وaihorde. لذلك: علامة keyless_defaults=skip، ثم تكرار الإطفاء حتى انتهاء
# المزامنة، ثم تحقق مغلق: أي مفتاح مفعّل بغير وسم seawatch يُفشل الإعداد (لا يُرسل أي نص).
guard() {
  (cd "$DIR" && node -e "const D=require('./node_modules/better-sqlite3');const d=new D('server/data/freeapi.db');
d.prepare(\"INSERT INTO settings(key,value) VALUES('keyless_defaults','skip') ON CONFLICT(key) DO UPDATE SET value='skip'\").run();
d.prepare(\"update api_keys set enabled=0 where label<>'seawatch'\").run();
const left=d.prepare(\"select count(*) c from api_keys where enabled=1 and label<>'seawatch'\").get().c;
const synced=d.prepare(\"select count(*) c from settings where key='catalog_applied_json'\").get().c;
console.log(left+' '+synced)")
}
for _ in $(seq 1 45); do
  read -r left synced < <(guard)
  [ "${synced:-0}" != "0" ] && break
  sleep 2
done
sleep 3
read -r left _ < <(guard)
[ "${left:-1}" = "0" ] || { echo "freellmapi: بقي مزوّد غير مفتاح SeaWatch مفعّلًا ($left) — إيقاف"; exit 1; }
key=$(cd "$DIR" && node -e "const D=require('./node_modules/better-sqlite3');const d=new D('server/data/freeapi.db');process.stdout.write(d.prepare(\"select value from settings where key='unified_api_key'\").get().value)")
[ -n "$key" ] || { echo "freellmapi: تعذّر قراءة المفتاح الموحّد"; exit 1; }
umask 077
printf 'export LLM_BASE_URL=http://127.0.0.1:%s/v1\nexport LLM_API_KEY=%s\nexport LLM_NODE=node\n' "$PORT" "$key" > "$ENV_OUT"
echo "freellmapi: جاهز على 127.0.0.1:$PORT بعدد مزوّدين $nkeys · ملف البيئة: $ENV_OUT"
exit 0
