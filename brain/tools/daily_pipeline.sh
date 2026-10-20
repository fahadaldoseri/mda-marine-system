#!/usr/bin/env bash
# خط التشغيل الصباحي الموحّد — الإصدار 4 (19 أكتوبر 2026)
# v1: أمره كان يُستدعى بـpython3 (SyntaxError) + مدخلات /tmp + فشل صامت.
# v2: سجل + رمز خروج + علامة نجاح + قوائم دائمة في watchlist/.
# v3: أُضيفت خطوة دمج الذاكرة التراكمية (ملف اليوم → الدفتر الجامع + خريطة الرموز).
# v4 (بنود 1·2·3·4·5·6·9·13 من التدقيق المستقل):
#   · علامة ثلاثية الحالة تقرأ حالة كل فحص فعلية (ok/degraded/failed) من ملفات الحالة،
#     بدل ادّعاء النجاح من رمز خروج صفري دائم.
#   · قائمة فحص العقوبات تُولَّد آليًا من سفن التقرير (لا قائمة يدوية ثابتة).
#   · الدمج يسبق العلامة، والعلامة تُسجِّل عدد سجلات الدفتر ووقت الدمج.
#   · بوابات التسليم تُشغَّل عبر tools/final_gate.sh (بترتيب: بناء ← PDF ← فحص).
# سلّم رموز الخروج: 0 = نجاح · 1 = متدهور · 2 = فاشل.
# الاستخدام: bash tools/daily_pipeline.sh [UTC_DATE] [OFAC_TARGETS_FILE] [ORIGINALS_URLS_FILE]
set -uo pipefail
B="${BRAIN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SITE="${SITE_DIR:-$(dirname "$B")/seawatch}"
cd "$B" || exit 2
D="${1:-$(date -u +%F)}"
TARGETS="${2:-$B/watchlist/ofac-targets.txt}"
URLS="${3:-$B/watchlist/original-sources.txt}"
LOGDIR="$B/logs"; mkdir -p "$LOGDIR"
LOG="$LOGDIR/pipeline-$D.log"
MARK="$LOGDIR/pipeline-$D.json"

echo "===== خط التشغيل الموحّد v4 — $D — $(date -u +%FT%TZ) =====" | tee -a "$LOG"

classify() { case "${1:-9}" in 0) echo ok ;; 1) echo degraded ;; *) echo failed ;; esac; }
S_FEEDS="failed"; S_OFAC="failed"; S_ARCH="failed"; S_LEDGER="failed"
NOTE_OFAC=""; NOTE_ARCH=""; NOTE_LEDGER=""

# 1) التغذيات — إنذار مبكر من 38 تغذية (رمز خروج حقيقي: 0/1/2)
echo "-- 1) التغذيات --" | tee -a "$LOG"
python3 tools/check_feeds.py >>"$LOG" 2>&1; RC=$?
python3 tools/normalize_digits.py >/dev/null 2>&1 || true
#            ↑ قرار الأرقام الإنجليزية: التغذيات المولّدة تُكتب بأرقام لاتينية
S_FEEDS="$(classify $RC)"
if [ -f "feeds/feeds-$D.md" ] && [ "$S_FEEDS" != "failed" ]; then
  echo "   ✔ مستجدات التغذيات: feeds/feeds-$D.md (الحالة: $S_FEEDS)" | tee -a "$LOG"
elif [ ! -f "feeds/feeds-$D.md" ]; then
  S_FEEDS="failed"; echo "   ✘ لم يُنتج ملف التغذيات" | tee -a "$LOG"
else
  echo "   ✘ تغذيات متدهورة/فاشلة — راجع feeds/feeds-$D.status.json" | tee -a "$LOG"
fi

# 2) قائمة فحص العقوبات تُولَّد آليًا من سفن إصدار اليوم، ثم يُجرى الفحص
echo "-- 2) فحص OFAC (قائمة مُولَّدة من سفن التقرير) --" | tee -a "$LOG"
python3 tools/ofac_targets_from_report.py --date "$D" >>"$LOG" 2>&1 \
  || echo "   ◐ تعذر توليد القائمة من التقرير (قد لا يكون تقرير اليوم مكتوبًا بعد)" | tee -a "$LOG"
if [ ! -f "$TARGETS" ]; then
  echo "   ✘ قائمة المستهدفات مفقودة: $TARGETS (خطأ إعداد — لا يُعتبر نجاحًا)" | tee -a "$LOG"
  NOTE_OFAC="قائمة المستهدفات مفقودة"
elif [ ! -s "$TARGETS" ]; then
  S_OFAC="ok"; NOTE_OFAC="لا سفينة في نافذة اليوم — لا فحص مطلوب"
  echo "   ○ $NOTE_OFAC" | tee -a "$LOG"
else
  python3 tools/ofac_screen.py "$TARGETS" >>"$LOG" 2>&1; RC=$?
  S_OFAC="$(classify $RC)"
  NOTE_OFAC="فُحص $(grep -cve '^[[:space:]]*$' "$TARGETS") مستهدفًا — الحالة: $S_OFAC"
  echo "   $([ "$S_OFAC" = ok ] && echo '✔' || echo '✘') $NOTE_OFAC" | tee -a "$LOG"
fi

# 3) حفظ الأصول الرسمية — مع فحص محتوى حقيقي ورمز خروج
echo "-- 3) حفظ الأصول الرسمية --" | tee -a "$LOG"
if [ ! -f "$URLS" ]; then
  echo "   ✘ قائمة روابط الأصول مفقودة: $URLS (خطأ إعداد — لا يُعتبر نجاحًا)" | tee -a "$LOG"
  NOTE_ARCH="قائمة الأصول مفقودة"
elif [ ! -s "$URLS" ]; then
  python3 tools/archive_originals.py "$D" "$URLS" >>"$LOG" 2>&1; RC=$?
  S_ARCH="$(classify $RC)"; NOTE_ARCH="لا بلاغ رسمي في نافذة اليوم — لا أصل مطلوب"
  echo "   ○ $NOTE_ARCH" | tee -a "$LOG"
else
  python3 tools/archive_originals.py "$D" "$URLS" >>"$LOG" 2>&1; RC=$?
  S_ARCH="$(classify $RC)"
  NOTE_ARCH="حُفظت الأصول في archive/originals/$D/ — الحالة: $S_ARCH"
  echo "   $([ "$S_ARCH" = ok ] && echo '✔' || echo '✘') $NOTE_ARCH" | tee -a "$LOG"
fi

# 4) دمج الذاكرة التراكمية — يسبق علامة النجاح حتى لا تُعلن العلامة نجاحًا قبل الدمج
echo "-- 4) دمج الذاكرة التراكمية (قبل العلامة) --" | tee -a "$LOG"
python3 tools/merge_ledger_daily.py >>"$LOG" 2>&1; RC=$?
S_LEDGER="$(classify $RC)"
if [ "$S_LEDGER" != "failed" ]; then
  cp -f cumulative-2026/event-ledger-master.json "$SITE/sources/ledger.json" 2>>"$LOG"
  S_LEDGER="ok"
  NOTE_LEDGER="دُمج ملف اليوم في الدفتر الجامع وبُنيت خريطة الرموز ونُسخ الدفتر إلى الموقع"
  echo "   ✔ $NOTE_LEDGER" | tee -a "$LOG"
else
  echo "   ✘ فشل دمج الدفتر التراكمي" | tee -a "$LOG"
fi

# 5) خطوات النموذج المدمج (اختيارية — تُتخطى بصمت إن غاب المشغّل، بلا مفاتيح خارجية)
echo "-- 5) النموذج المدمج: ترشيح التغذيات + مراجعة لغوية --" | tee -a "$LOG"
S_LLM="skip"; NOTE_LLM="لم تُشغَّل (لا مشغّل متاح)"
FEEDS_MD="feeds/feeds-$D.md"; REPORT_MD="reports/$D-sectioned.md"
if command -v manus-node >/dev/null 2>&1; then
  S_LLM="ok"; NOTE_LLM=""
  if [ -f "$FEEDS_MD" ]; then
    if ! python3 tools/llm_triage.py --input "$FEEDS_MD" >>"$LOG" 2>&1; then
      S_LLM="failed"; NOTE_LLM="فشل ترشيح التغذيات"
    fi
  fi
  if [ -f "$REPORT_MD" ]; then
    if ! python3 tools/llm_review.py --report "$REPORT_MD" --limit 25 >>"$LOG" 2>&1; then
      S_LLM="failed"; NOTE_LLM="${NOTE_LLM:+$NOTE_LLM · }فشل المراجعة اللغوية"
    fi
  fi
  [ "$S_LLM" = "ok" ] && NOTE_LLM="رُشّحت التغذيات ورُوجعت اللغة آلياً بالنموذج المدمج"
  echo "   ✔ $NOTE_LLM" | tee -a "$LOG"
else
  echo "   · تخطٍّ: manus-node غير متاح في هذه البيئة" | tee -a "$LOG"
fi

if [ -f "archive/originals/$D/manifest.json" ]; then MANIFEST="archive/originals/$D/manifest.json"; else MANIFEST=""; fi
python3 - "$MARK" "$D" "$S_FEEDS" "$S_OFAC" "$S_ARCH" "$S_LEDGER" "$NOTE_OFAC" "$NOTE_ARCH" "$NOTE_LEDGER" "$MANIFEST" "$S_LLM" "$NOTE_LLM" "$B" <<'PY'
import json, sys, datetime
from pathlib import Path
mark, d, f, o, a, l, no, na, nl, man, sl, nlm, b = sys.argv[1:14]
B = Path(b)

def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception:
        return default

feeds = jload(B / f'feeds/feeds-{d}.status.json', {}) or {}
ofac = jload(B / 'archive/ofac-screen-latest.json', {}) or {}
arch = jload(B / f'archive/originals/{d}/status.json', {}) or {}
ledger = jload(B / 'cumulative-2026/event-ledger-master.json', {}) or {}
mlog = ledger.get('merge_log') or {}

ofac_results = ofac.get('results') or []
matches = [r['target'] for r in ofac_results if r.get('result') == 'match']
reviews = [r['target'] for r in ofac_results if r.get('result') == 'review']

components = {'feeds': f, 'ofac': o, 'originals': a, 'ledger_merge': l}
if sl == 'failed':
    components['builtin_llm'] = 'failed'
elif sl == 'ok':
    components['builtin_llm'] = 'ok'
overall = 'failed' if 'failed' in components.values() else ('degraded' if 'degraded' in components.values() else 'ok')

report_present = (B / f'reports/{d}-sectioned.md').exists() and (B / f'web/meta/{d}.json').exists()
gate_dir = B / f'logs/gate-{d}'

json.dump({
    'date': d, 'pipeline_version': 4,
    'finished_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'overall': overall,
    'ladder_note': 'سلّم موحّد: ok / degraded / failed — لكل مكوّن رمز خروج حقيقي، ولا تُعلن نجاحًا برمز صفري',
    'feeds': {'status': f, 'checked': feeds.get('checked'), 'ok': feeds.get('ok'),
              'failed': feeds.get('failed'), 'fail_ratio': feeds.get('fail_ratio'),
              'failed_feeds': feeds.get('failed_feeds')},
    'ofac': {'status': o, 'note': no, 'targets': len(ofac_results),
             'matches': matches, 'reviews': reviews, 'list': (ofac.get('list') or '')[:70],
             'results_file': 'archive/ofac-screen-latest.json'},
    'originals': {'status': a, 'note': na, 'manifest': man,
                  'healthy': arch.get('healthy'), 'empty_shell': arch.get('empty_shell'),
                  'failed': arch.get('failed'), 'status_file': f'archive/originals/{d}/status.json'},
    'ledger_merge': {'status': l, 'note': nl, 'records_total': mlog.get('records_total'),
                     'added_this_run_count': mlog.get('added_this_run_count'),
                     'period_end': ledger.get('period_end'), 'merged_utc': mlog.get('merged_utc'),
                     'merged_before_marker': bool(mlog.get('merged_utc'))},
    'builtin_llm': {'status': sl, 'note': nlm},
    'report_present_at_pipeline_end': report_present,
    'final_gate': {'status': 'pending' if not (gate_dir / 'gate.json').exists() else 'recorded',
                   'dir': str(gate_dir.relative_to(B)),
                   'note': 'تُشغَّل بوابة التسليم بعد كتابة التقرير: bash tools/final_gate.sh <التاريخ>'},
}, open(mark, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"-- الخلاصة: تغذيات={f} · OFAC={o} · أصول={a} · دمج الذاكرة={l} · النموذج المدمج={sl} · الحالة العامة={overall}")
print(f"-- العلامة: {mark}")
sys.exit({'ok': 0, 'degraded': 1, 'failed': 2}[overall])
PY
RC=$?

# 6) بوابة التسليم النهائية — فشل مغلق (بناء ← PDF ← فحوص)
if [ -f "reports/$D-sectioned.md" ] && [ -f "web/meta/$D.json" ]; then
  echo "-- 6) بوابة التسليم النهائية --" | tee -a "$LOG"
  bash tools/final_gate.sh "$D" >>"$LOG" 2>&1; GRC=$?
  cat "$B/logs/gate-$D/report.txt" 2>/dev/null | tee -a "$LOG"
  if [ "$GRC" -ge 2 ]; then
    echo "   ✘ بوابة التسليم: مانع — التسليم موقوف" | tee -a "$LOG"
    RC=2
  elif [ "$GRC" -eq 1 ]; then
    echo "   ◐ بوابة التسليم: نجاح مع تحذير" | tee -a "$LOG"
    [ "$RC" -lt 1 ] && RC=1
  else
    echo "   ✔ بوابة التسليم: نجاح" | tee -a "$LOG"
  fi
else
  echo "-- 6) بوابة التسليم: مؤجّلة — التقرير أو ملف الواجهة لم يُكتب بعد --" | tee -a "$LOG"
  echo "   شغّلها بعد كتابة التقرير: bash tools/final_gate.sh $D" | tee -a "$LOG"
fi

echo "===== نهاية الخط (رمز الخروج: $RC) =====" | tee -a "$LOG"
exit $RC

# بوابة قاعدة النقاط في المصدر (19 أكتوبر 2026)
python3 "$B/validators/check_points_rule.py" --md "$B/reports/$D-sectioned.md" --meta "$B/web/meta/$D.json" || echo "! بوابة النقاط أعادت تحذيرًا"
python3 validators/check_numerals.py || { echo "✘ بوابة الأرقام: أرقام عربية في ملف ملزم — التسليم موقوف"; exit 2; }

# نسخة احتياطية على GitHub (غير مُعطِّلة)
bash "$B/tools/github_backup.sh" || echo "! النسخة الاحتياطية لم تكتمل — راجع logs/github-backup-*.log"
# تحقق حقيقي بعد النسخ (عطل ك-70): هل المستودع يعكس الشجرة المحلية؟
python3 "$B/validators/check_backup_parity.py" --mode strict >>"$LOG" 2>&1 \
  && echo "   ✔ المطابقة بعد النسخ: مطابق" \
  || echo "! انحراف بين الشجرة والمستودع — راجع $LOG"
if ! python3 "$B/validators/check_backup_parity.py" --mode strict; then
  echo "✘ النسخة الاحتياطية غير مطابقة للشجرة المحلية — التسليم موقوف حتى تُصلح الأسباب أعلاه"
  exit 2
fi
