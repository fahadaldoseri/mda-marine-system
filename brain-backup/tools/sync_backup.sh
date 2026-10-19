#!/usr/bin/env bash
# مزامنة النسخة الاحتياطية للعقل داخل مستودع الموقع (brain-backup)
# سبب الوجود: أداة rsync غير مثبّتة في البيئة، وكانت المزامنة تفشل بصمت.
# الاعتماد على cp فقط، مع تحقق نهائي من حداثة الملفات.
set -u

_B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
_S="${SITE_DIR:-$(dirname "$_B")/seawatch}"
SRC="${1:-$_B}"
DST="${2:-$_S/brain-backup}"
DATE="${3:-$(date -u +%F)}"

mkdir -p "$DST"
DIRS=(sections appendices validators tools docs reports web memory cumulative-2026 historical watchlist schedule feeds logs brain)
for d in "${DIRS[@]}"; do
  if [ -d "$SRC/$d" ]; then
    mkdir -p "$DST/$d"
    cp -aL "$SRC/$d/." "$DST/$d/" 2>/dev/null
  fi
done
for f in INDEX.md; do
  [ -f "$SRC/$f" ] && cp -aL "$SRC/$f" "$DST/" 2>/dev/null
done
# ملفات الجذر المفردة (سجلات ومخرجات يومية)
find "$SRC" -maxdepth 1 -type f \( -name '*.json' -o -name '*.md' -o -name '*.txt' \) -exec cp -aL {} "$DST/" \; 2>/dev/null

# إزالة أي روابط رمزية: تُفشل حزم النشر وتشير إلى مسارات خارج المستودع
find "$DST" -type l -delete 2>/dev/null
FILES=$(find "$DST" -type f 2>/dev/null | wc -l)
echo "  ✔ النسخة الاحتياطية: $FILES ملفًا في $DST"

FAIL=0
if [ -f "$SRC/reports/$DATE-sectioned.md" ]; then
  if cmp -s "$SRC/reports/$DATE-sectioned.md" "$DST/reports/$DATE-sectioned.md"; then
    echo "  ✔ تقرير اليوم مُزامن: $DATE-sectioned.md"
  else
    echo "  ✘ تقرير اليوم غير مُزامن — أعد التنفيذ"; FAIL=1
  fi
fi
if [ -f "$SRC/tools/preflight_check.py" ]; then
  if cmp -s "$SRC/tools/preflight_check.py" "$DST/tools/preflight_check.py"; then
    echo "  ✔ أدوات التشغيل مُزامنة"
  else
    echo "  ✘ أدوات التشغيل غير مُزامنة"; FAIL=1
  fi
fi
exit $FAIL