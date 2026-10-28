#!/usr/bin/env bash
# فحص النموذج المدمج في Manus: المشغّل + الكتالوج الحي + نداء توليد فعلي (بلا كلفة تُذكر).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "===== فحص النموذج المدمج ====="
if ! command -v manus-node >/dev/null 2>&1; then
  echo "  ✘ manus-node غير متاح — يلزم تحديث بيئة Manus"; exit 1
fi
echo "  ✔ المشغّل: $(command -v manus-node) ($(manus-node --version))"
python3 - "$HERE/llm.mjs" <<'PY'
import json, subprocess, sys
out = subprocess.run(['manus-node', sys.argv[1], 'models'], capture_output=True, text=True)
if out.returncode != 0:
    print('  ✘ تعذّر جلب الكتالوج:', (out.stderr or out.stdout)[:200]); sys.exit(1)
rows = json.loads(out.stdout)
print(f'  ✔ الكتالوج الحي: {len(rows)} نموذجاً')
for r in rows[:6]:
    print(f'     · {r["id"]:<26} دخل {r["in"]}$/1M · خرج {r["out"]}$/1M · تفكير: {r["thinking"]}')
PY
echo "  · نداء توليد فعلي:"
bash "$HERE/llm.sh" single --model gpt-5-mini --prompt "أجب بجملة واحدة قصيرة: النظام يعمل." 2>&1 | sed 's/^/     /'
