#!/usr/bin/env bash
# غلاف تشغيل النموذج المدمج في Manus — بلا مفاتيح خارجية ولا رصيد منفصل.
# الاستخدام: bash tools/llm.sh models | single --prompt "…" | batch --input F --template "…"
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec manus-node "$HERE/llm.mjs" "$@"