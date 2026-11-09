#!/usr/bin/env bash
# اشتقاق جذر الموقع — مصدر واحد يستهلكه أي فحص يحتاج `dist`.
# السبب الجذري (ك-598): كان الاشتقاق مكتوبًا داخل بوابة G001 ويسقط إلى مسار مُخمَّن بلا dist،
# فتفشل فحوص الأسطح بأسباب كاذبة. الآن: مصدر واحد + فشل مغلق + مرساة اختبار صريحة.
#
# الاستعمال في بوابة أو أداة:
#     . "$(dirname "$0")/site_root.sh"
#     site_root_resolve "$B" || exit 2
#
# المرشّحون: SITE (إن مُرِّر صريحًا) ← SITE_CANDIDATES (مرساة اختبار) ← SITE_DIR ←
#            $B/../seawatch · $B/../../seawatch · $HOME/seawatch
# لا مسار مطلق محفور: الجذور تُشتق من $B أو من $HOME أو تُمرَّر صريحة (حارس قابلية النقل).
# الشرط: المجلد يحتوي `dist` فعليًا. ولا مسار مُخمَّن بلا dist.

site_root_resolve() {
  local base="${1:-}"
  # 1) جذر مُصرَّح به: يُحترم كما هو — فإن كان بلا dist فالنتيجة فشل مغلق لا بحث صامت.
  if [ -n "${SITE:-}" ]; then
    [ -d "$SITE/dist" ] && return 0
    return 2
  fi
  # 2) قائمة المرشّحين: مرساة الاختبار أولًا، ثم SITE_DIR، ثم المسارات المعتادة.
  local candidates
  if [ -n "${SITE_CANDIDATES:-}" ]; then
    # مرساة اختبار: تحلّ محل القائمة كلها (تُمكِّن إثبات الفشل المغلق بلا مرشّح موجود).
    candidates="$SITE_CANDIDATES"
  else
    candidates="${SITE_DIR:-} $base/../seawatch $base/../../seawatch $HOME/seawatch"
  fi
  local c
  for c in $candidates; do
    if [ -n "$c" ] && [ -d "$c/dist" ]; then
      SITE="$(cd "$c" && pwd)"
      return 0
    fi
  done
  return 2
}

site_root_message() {
  printf '  ✘ محيط البوابة: جذر الموقع غير محدد (مرّر SITE أو SITE_DIR إلى مجلد فيه dist) — فشل مغلق.\n'
}

# وضع المسبار: يُستخدم في الاختبار السلبي/الموجب بلا تشغيل بقية البوابة.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  case "${1:-}" in
    --probe)
      if site_root_resolve "${2:-}"; then
        printf 'OK %s\n' "$SITE"
        exit 0
      fi
      site_root_message
      exit 2
      ;;
    *)
      printf 'الاستعمال: site_root.sh --probe [الجذر الأساسي]\n'
      exit 64
      ;;
  esac
fi
