#!/usr/bin/env bash
# نشر تقرير واحد من Markdown إلى رابط يعمل فعليًا في المتصفح.
# الاستخدام: ./publish_report.sh <التقرير.md> <الواجهة.json> <التاريخ YYYY-MM-DD> [--allow-restricted]
# المخرجات: رابط الصفحة + تحديث صفحة الأرشيف.
# حاجز التصنيف: الإصدار المقيّد أو الحساس لا يُنشر علنًا إلا بتمرير --allow-restricted.
set -u
WEB="/home/ubuntu/brain-marine-news/web"
PORT="${PORT:-8080}"
BASE="https://${PORT}-inequo0pv79t1xf0di2ng-950d50aa.sg2.manus.computer"

MD="${1:?مسار التقرير مطلوب}"
META="${2:?مسار ملف الواجهة مطلوب}"
DATE="${3:?التاريخ مطلوب بصيغة YYYY-MM-DD}"
ALLOW="${4:-}"

CLASS=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8')).get('classification','عام'))" "$META" 2>/dev/null || echo "عام")
if [ "$CLASS" = "مقيّد" ] || [ "$CLASS" = "حساس" ]; then
  if [ "$ALLOW" != "--allow-restricted" ]; then
    echo "رفض النشر: تصنيف الإصدار (${CLASS}) لا يُنشر على رابط عام." >&2
    echo "سلّم هذا الإصدار عبر قناة وصول مقيّدة، أو مرّر --allow-restricted عند الموافقة الصريحة." >&2
    exit 2
  fi
  echo "تنبيه: نشر إصدار ${CLASS} بموجب --allow-restricted."
fi

cd "$WEB" || exit 1
mkdir -p site/reports

echo "== 1) توليد الصفحة =="
python3 build_report.py --md "$MD" --out "out/التقرير-الصباحي-${DATE}.html" --meta "$META" || exit 3

echo "== 2) الفحص الآلي قبل النشر =="
python3 verify.py "out/التقرير-الصباحي-${DATE}.html" shots >/tmp/verify_out.txt 2>&1
if [ $? -ne 0 ]; then
  echo "فشل الفحص الآلي، أوقف النشر:" >&2
  tail -20 /tmp/verify_out.txt >&2
  exit 4
fi
tail -2 /tmp/verify_out.txt

echo "== 3) النشر في مجلد الموقع =="
cp "out/التقرير-الصباحي-${DATE}.html" "site/reports/${DATE}.html"

echo "== 4) تحديث صفحة الأرشيف =="
python3 - "$DATE" <<'PY'
import sys, re
from pathlib import Path
date = sys.argv[1]
site = Path("/home/ubuntu/brain-marine-news/web/site")
rep = site / "reports"
rows = []
for f in sorted(rep.glob("*.html"), reverse=True):
    if f.stem == "index":
        continue
    label = "السجل التراكمي" if f.stem.startswith("cumulative") else f.stem
    rows.append(f'<li><a href="reports/{f.name}">{label}</a></li>')
(site / "index.html").write_text(
    '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<meta name="robots" content="noindex, nofollow, noarchive">'
    '<title>أرشيف التقارير الصباحية</title>'
    '<style>body{background:#050a12;color:#e9f0f9;font-family:system-ui,Tahoma,sans-serif;'
    'line-height:2;padding:40px 22px;max-width:820px;margin:0 auto}'
    'a{color:#22c3b6;text-decoration:none}a:hover{text-decoration:underline}'
    'li{margin:8px 0}h1{font-size:24px}hr{border:0;border-top:1px solid #1d2e4a;margin:22px 0}</style>'
    '</head><body><h1>أرشيف التقارير الصباحية</h1>'
    '<p>تُحدَّث هذه الصفحة تلقائيًا مع كل تقرير جديد.</p><hr><ul>'
    + "".join(rows) + "</ul></body></html>",
    encoding="utf-8",
)
print(f"صفحة الأرشيف تضم {len(rows)} تقريرًا")
PY

echo "== 5) تشغيل الخادم =="
./serve_site.sh "$PORT" || exit 5

echo "== 6) التحقق النهائي من الرابط =="
URL="${BASE}/reports/${DATE}.html"
HDR=$(curl -sI "$URL")
echo "$HDR" | grep -i '^content-type' | head -1
if echo "$HDR" | grep -qi 'content-disposition'; then
  echo "تحذير: الرابط يفرض التنزيل بدل العرض" >&2
fi
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$URL")
echo "رمز الاستجابة: ${CODE}"
[ "$CODE" = "200" ] || exit 6

echo
echo "رابط التقرير:   ${URL}"
echo "صفحة الأرشيف:  ${BASE}/"
