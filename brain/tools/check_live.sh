#!/usr/bin/env bash
# تحقق حي (قراءة فقط) من النسخة المنشورة: الرئيسية · صفحة التقرير · PDF · المصادر.
# --compare: يقارن بصمة PDF المنشور بالنسخة المحلية في dist (يكشف نشرًا قديمًا يرد 200).
# الاستخدام: bash tools/check_live.sh [--compare] [UTC_DATE]    رمز الخروج: 0 سليم · 2 خلل
set -uo pipefail
B="${BRAIN_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
if [ -n "${SITE_DIR:-}" ]; then SITE="$SITE_DIR"
elif [ -d "$B/../seawatch" ]; then SITE="$B/../seawatch"; else SITE="$B/../site"; fi
CMP=0; D=""
for a in "$@"; do case "$a" in --compare) CMP=1 ;; *) D="$a" ;; esac; done
[ -n "$D" ] || D="$(date -u +%F)"
BASE="${LIVE_BASE_URL:-$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['base_url'])" "$SITE/sources/site.json" 2>/dev/null)}"
[ -n "$BASE" ] || { echo "✘ لا رابط للموقع المنشور (sources/site.json:base_url)"; exit 2; }
mkdir -p "$B/logs"
python3 - "$B" "$SITE" "$BASE" "$D" "$CMP" <<'PY'
import hashlib, json, sys, datetime, urllib.request, urllib.error
B, SITE, BASE, D, CMP = sys.argv[1:6]
def get(path):
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "seawatch-check"}), timeout=60) as r:
            body = r.read()
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""
doc = {"date": D, "checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "paths": {}}
bad = []
bodies = {}
for u in ("", f"reports/{D}.html", f"reports/pdf/{D}.pdf", "sources.html"):
    code, body = get(u)
    bodies[u] = body
    doc["paths"][f"/{u}"] = {"code": code, "bytes": len(body)}
    if code != 200 or not body:
        bad.append(f"/{u}")
if CMP == "1":
    import os
    loc = os.path.join(SITE, "dist", "reports", "pdf", f"{D}.pdf")
    if os.path.isfile(loc):
        a = hashlib.sha256(open(loc, "rb").read()).hexdigest()
        b = hashlib.sha256(bodies[f"reports/pdf/{D}.pdf"]).hexdigest()
        doc["pdf_sha256"] = {"local": a, "live": b, "match": a == b}
        if a != b:
            bad.append("pdf-differs-from-local")
    else:
        doc["pdf_sha256"] = {"local": None, "note": "لا نسخة محلية للمقارنة"}
        bad.append("no-local-pdf")
doc["status"] = "ok" if not bad else "failed"
doc["bad"] = bad
open(f"{B}/logs/live-{D}.json", "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
print("  ✔ كل المسارات ترد 200" + (" وPDF مطابق للمحلي" if CMP == "1" else "") if not bad else f"  ✘ خلل: {bad}")
sys.exit(2 if bad else 0)
PY
