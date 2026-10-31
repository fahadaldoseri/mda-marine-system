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
STARTED_EPOCH="$(date +%s)"
for attempt in 1 2 3 4 5 6; do
python3 - "$B" "$SITE" "$BASE" "$D" "$CMP" "$attempt" "$STARTED_EPOCH" <<'PY'
import hashlib, json, sys, datetime, urllib.request, urllib.error
B, SITE, BASE, D, CMP, ATTEMPT, STARTED = sys.argv[1:8]
RELEASE_PATHS = ("", f"reports/{D}.html", f"reports/pdf/{D}.pdf", "sources.html")
checked_at = datetime.datetime.now(datetime.timezone.utc)
elapsed = max(0, int(checked_at.timestamp()) - int(STARTED))
def get(path):
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "seawatch-check"}), timeout=60) as r:
            body = r.read()
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""
doc = {"date": D, "checked_at": checked_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
       "release_paths": [f"/{p}" if p else "/" for p in RELEASE_PATHS],
       "propagation": {"attempt": int(ATTEMPT), "elapsed_seconds": elapsed, "max_wait_seconds": 225},
       "paths": {}}
bad = []
bodies = {}
for u in RELEASE_PATHS:
    code, body = get(u)
    bodies[u] = body
    doc["paths"][f"/{u}"] = {"code": code, "bytes": len(body)}
    if code != 200 or not body:
        bad.append(f"/{u}")
if CMP == "1":
    import os
    import subprocess
    import tempfile
    loc = os.path.join(SITE, "dist", "reports", "pdf", f"{D}.pdf")
    if os.path.isfile(loc):
        a = hashlib.sha256(open(loc, "rb").read()).hexdigest()
        b = hashlib.sha256(bodies[f"reports/pdf/{D}.pdf"]).hexdigest()
        # ك-358 (2026-10-30): مقارنة البايتات كانت تفشل لأن PDF يُعاد توليده بزمن إنشاء جديد
        # فيختلف الـhash بلا أي فرق في المحتوى. القياس الآن على المحتوى: عدد الصفحات + بصمة النص.
        def sig(path):
            try:
                txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, timeout=120).stdout
                pages = subprocess.run(["pdfinfo", path], capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
                np = next((l.split(":")[1].strip() for l in pages.splitlines() if l.startswith("Pages:")), "?")
                return np, hashlib.sha256(txt).hexdigest()[:24]
            except Exception as e:  # noqa: BLE001
                return "?", f"خطأ: {e}"
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(bodies[f"reports/pdf/{D}.pdf"])
            live_p = tf.name
        lp, lh = sig(loc)
        vp, vh = sig(live_p)
        os.unlink(live_p)
        doc["pdf_sha256"] = {"local": a, "live": b, "match": a == b,
                             "content": {"pages_local": lp, "pages_live": vp,
                                         "text_local": lh, "text_live": vh,
                                         "match": (lp == vp and lh == vh)}}
        if lp != vp or lh != vh:
            bad.append("pdf-content-differs-from-local")
        elif a != b:
            doc["pdf_sha256"]["note"] = "البايتات تختلف (زمن إنشاء PDF) والمحتوى مطابق — مقبول"
    else:
        doc["pdf_sha256"] = {"local": None, "note": "لا نسخة محلية للمقارنة"}
        bad.append("no-local-pdf")
doc["status"] = "ok" if not bad else "failed"
doc["bad"] = bad
open(f"{B}/logs/live-{D}.json", "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
print("  ✔ كل المسارات ترد 200" + (" وPDF مطابق للمحلي" if CMP == "1" else "") if not bad else f"  ✘ خلل: {bad}")
sys.exit(2 if bad else 0)
PY
rc=$?
if [ "$rc" -eq 0 ]; then exit 0; fi
if [ "$attempt" -lt 6 ]; then
  echo "  · محاولة $attempt: الانتشار لم يكتمل — انتظار 45 ثانية ثم إعادة (حتى 4.5 دقيقة)"
  sleep 45
else
  exit "$rc"
fi
done
