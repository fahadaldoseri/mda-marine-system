#!/usr/bin/env bash
# تهيئة نظام «مركز الوعي بالمجال البحري» على جهاز أو بيئة سحابية جديدة — بأمر واحد.
#
# الاستخدام:
#   bash bootstrap.sh                    تثبيت كامل: حزم النظام + بايثون + متصفح Playwright
#   bash bootstrap.sh --skip-system      تخطّي حزم النظام (عند غياب sudo أو صلاحية تثبيت)
#   bash bootstrap.sh --link-default-paths  إنشاء /home/ubuntu/{brain-marine-news,seawatch} كروابط لهذا المشروع
#   bash bootstrap.sh --verify-only      فحص ما هو مثبّت بلا تثبيت أي شيء
#
# المصادر المدعومة: Ubuntu/Debian (apt) · RHEL/Fedora (dnf) · macOS (brew) · GitHub Codespaces (apt + sudo)
set -u

B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
SITE="${SITE_DIR:-$(dirname "$B")/seawatch}"
SKIP_SYS=0
LINK=0
VERIFY_ONLY=0
# sudo بلا كلمة مرور إن توفّر (Codespaces/devcontainer يوفر ذلك افتراضيًا)
SUDO=""
command -v sudo >/dev/null 2>&1 && SUDO="sudo -n"
if [ -n "$SUDO" ] && ! $SUDO true 2>/dev/null; then SUDO=""; fi
for a in "$@"; do
  case "$a" in
    --skip-system) SKIP_SYS=1 ;;
    --link-default-paths) LINK=1 ;;
    --verify-only) VERIFY_ONLY=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "خيار غير معروف: $a"; exit 2 ;;
  esac
done

ok()  { printf '  ✔ %s\n' "$*"; }
bad() { printf '  ✘ %s\n' "$*"; }
log() { printf '\n\033[1m%s\033[0m\n' "$*"; }

FAIL=0
log "1) فحص بايثون"
if command -v python3 >/dev/null; then
  PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
  ok "بايثون $PYV"
  python3 - <<'PY' || { bad "الإصدار أقل من 3.10"; exit 1; }
import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)
PY
else
  bad "بايثون غير مثبّت — ثبّته ثم أعد التشغيل"; exit 1
fi

if [ "$VERIFY_ONLY" -eq 0 ] && [ "$SKIP_SYS" -eq 0 ]; then
  log "2) حزم النظام (LibreOffice · poppler · خطوط عربية · أدوات المتصفح)"
  [ -z "$SUDO" ] && bad "لا sudo متاح — ثبّت الحزم يدويًا أو استخدم --skip-system"
  if command -v apt-get >/dev/null; then
    APT_OK=1
    $SUDO apt-get update -qq 2>&1 | tail -2
    $SUDO apt-get install -y -qq --no-install-recommends poppler-utils fontconfig curl unzip python3-pip 2>&1 | tail -3 || APT_OK=0
    $SUDO apt-get install -y -qq --no-install-recommends fonts-hosny-amiri fonts-noto-core 2>&1 | tail -3 || APT_OK=0
    $SUDO apt-get install -y -qq libreoffice 2>&1 | tail -3 || APT_OK=0
    command -v fc-cache >/dev/null && $SUDO fc-cache -f >/dev/null 2>&1
    [ "$APT_OK" -eq 1 ] && ok "حزم النظام: poppler · خطوط عربية · libreoffice" || bad "بعض حزم النظام لم تُثبَّت — راجع الرسائل أعلاه"
  elif command -v dnf >/dev/null; then
    $SUDO dnf install -y libreoffice poppler-utils google-noto-sans-arabic-fonts \
      python3-pip curl unzip || bad "تثبيت حزم dnf لم يكتمل"
  elif command -v brew >/dev/null; then
    brew install --cask libreoffice >/dev/null 2>&1 || bad "تثبيت LibreOffice عبر brew لم يكتمل"
    brew install poppler || bad "تثبيت poppler عبر brew لم يكتمل"
  else
    bad "لا مدير حزم معروف — ثبّت يدويًا: LibreOffice + poppler-utils + خط عربي"
  fi
else
  log "2) تخطّي حزم النظام"
fi

if [ "$VERIFY_ONLY" -eq 0 ]; then
  log "3) حزم بايثون"
  if [ -f "$B/requirements.txt" ]; then
    python3 -m pip install -q --disable-pip-version-check -r "$B/requirements.txt" \
      || python3 -m pip install -q --break-system-packages -r "$B/requirements.txt" \
      || { bad "تثبيت حزم بايثون فشل"; FAIL=1; }
    [ "$FAIL" -eq 0 ] && ok "حزم بايثون مثبّتة"
  else
    bad "requirements.txt غير موجود في $B"; FAIL=1
  fi

  log "4) متصفح Playwright (لتوليد PDF والتدقيق البصري)"
  python3 -m playwright install chromium >/dev/null 2>&1 \
    || bad "تنزيل متصفح Playwright لم يكتمل — نفّذ: python3 -m playwright install chromium"
  # تبعيات Chromium على مستوى النظام (libnss3 وغيره) — لازمة ليعمل التشغيل بلا فشل صامت
  if [ -n "$SUDO" ]; then
    $SUDO python3 -m playwright install-deps chromium >/dev/null 2>&1 \
      || bad "تبعيات Chromium لم تُثبَّت — نفّذ: sudo python3 -m playwright install-deps chromium"
  fi
  [ -d "$HOME/.cache/ms-playwright" ] && ok "متصفح Playwright جاهز"
fi

log "5) التحقق"
python3 - <<PY
import sys
mods = {"docx": "python-docx", "playwright": "playwright", "PIL": "Pillow",
        "shapely": "shapely", "bs4": "beautifulsoup4", "pymysql": "PyMySQL"}
missing = [p for m, p in mods.items() if not __import__("importlib.util", fromlist=["x"]).find_spec(m)]
print("  ✔ كل حزم بايثون المطلوبة موجودة" if not missing else "  ✘ ناقص: " + ", ".join(missing))
raise SystemExit(1 if missing else 0)
PY
[ $? -ne 0 ] && FAIL=1

for c in soffice pdftoppm pdftotext pdfinfo; do
  command -v "$c" >/dev/null && ok "$c" || { bad "$c غير مثبّت"; FAIL=1; }
done
if ls "$HOME"/.cache/ms-playwright/chromium* >/dev/null 2>&1; then
  ok "متصفح Playwright مثبّت"
else
  bad "متصفح Playwright غير مثبّت — نفّذ: python3 -m playwright install chromium --with-deps"; FAIL=1
fi
if command -v fc-list >/dev/null; then
  if fc-list :lang=ar family 2>/dev/null | grep -q .; then
    ok "خطوط عربية متاحة: $(fc-list :lang=ar family 2>/dev/null | sort -u | head -3 | paste -sd', ')"
  else
    bad "لا خط عربي متاح — PDF العربي سيظهر بمربعات"; FAIL=1
  fi
fi

if [ "$LINK" -eq 1 ]; then
  log "6) إنشاء المسارات الافتراضية كروابط"
  $SUDO mkdir -p /home/ubuntu 2>/dev/null
  for pair in "$B:/home/ubuntu/brain-marine-news" "$SITE:/home/ubuntu/seawatch"; do   # مسار مقصود: هو غرض هذا الخيار
    src="${pair%%:*}"; dst="${pair##*:}"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
      bad "$dst موجود مسبقًا وليس رابطًا — لم يُمسّ"
      continue
    fi
    $SUDO ln -sfn "$src" "$dst" && ok "$dst → $src"
  done
fi

log "النتيجة"
if [ "$FAIL" -eq 0 ]; then
  cat <<'NEXT'
  ✔ التهيئة مكتملة.
  الخطوات التالية:
    1) الأسرار:  cp brain/.env.example brain/.env   ثم املأ القيم (أو مرّرها كمتغيّرات بيئة)
    2) إثبات وظيفي كامل بأمر واحد:  bash brain/tools/verify_codespace.sh
       (تصريف كل الملفات · البوابات العامة وبوابات الإصدار · بناء الموقع · PDF المعتمد · Word)
    3) فحص سريع: python3 brain/validators/check_sources_count.py
    4) بناء الموقع: python3 site/generator/build_site.py
  التفاصيل في brain/SETUP.md
NEXT
else
  echo "  ✘ التهيئة ناقصة — راجع البنود المعلّمة أعلاه، والتفاصيل في brain/SETUP.md"
fi
exit "$FAIL"
