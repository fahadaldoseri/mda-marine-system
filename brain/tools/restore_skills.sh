#!/usr/bin/env bash
# مزامنة المهارات ثنائية الاتجاه — إصلاح عطل ك-86.
# السبب الجذري: الأداة كانت تعتبر المستودع المصدر الوحيد، وتُنفّذ checkout عليه
# قبل المقارنة، فيُمحى ما نُسخ محليًا ولم يُدفع بعد، ويُعلن التماثل مكسورًا.
# القاعدة الجديدة: الأحدث زمنًا يفوز، والنقص يُكمَل من الجهة الأخرى،
# و`checkout` لا يُنفَّذ إلا إذا كانت شجرة المستودع نظيفة (بلا تعديل غير مدفوع).
set -uo pipefail
B="$(cd "$(dirname "$0")/.." && pwd)"
if [ -z "${REPO_DIR:-}" ]; then   # داخل نسخة المستودع نفسها: جذره أب brain/ ؛ وعلى الخادم: المستودع شقيق
  if [ -d "$B/../skills" ] && [ -e "$B/../.git" ]; then REPO_DIR="$B/.."; else REPO_DIR="$B/../mda-marine-system"; fi
fi
REPO="$REPO_DIR/skills"
if [ -n "${SKILLS_DIR:-}" ]; then SK="$SKILLS_DIR"; elif [ -d /home/ubuntu/skills ]; then SK=/home/ubuntu/skills; else SK="$B/../skills"; fi
CHECK_ONLY=0; [ "${1:-}" = "--check" ] && CHECK_ONLY=1

[ -d "$REPO" ] || { echo "✘ لا مستودع مهارات في $REPO"; exit 3; }

# ── تحديث المستودع بلا محو تعديلات غير مدفوعة ──
dirty="$(git -C "$REPO_DIR" status --porcelain -- skills 2>/dev/null | head -1 || true)"
if [ -d "$REPO_DIR/.git" ] && [ -z "$dirty" ]; then
  git -C "$REPO_DIR" fetch -q origin 2>/dev/null \
    && git -C "$REPO_DIR" checkout -q origin/main -- skills 2>/dev/null || true
fi

to_local=0; to_repo=0; equal=0
mkdir -p "$REPO"

# ── 1) ملفات المستودع: تُقارن وتُنقل حسب الأحدث ──
OUR_SKILLS="approved-output-change-ops bilingual-master-direction-ops bilingual-surface-parity-ops card-branch-integrity-ops crossing-gate-ops decision-registry-backfill-ops destructive-op-guard-ops fault-closure-and-learning-ops gate-lifecycle-ops governed-cleanup-audit governed-rename-ops governing-assets-recovery-ops macr-system map-clarity-ops marine-news-brain military-arabic-editing multi-agent-audit-ops official-ledger-backfill-ops operation-to-skill-ops owner-approval-launch-gate-ops owner-notes-measured-triage owner-ui-notes-contract-ops parity-and-publish-ops pre-execution-plan-audit-ops project-evidence-and-coverage-ops report-build-export-ops report-surface-and-print-ops runbook-operations-ops secret-rotation-ops skill-adoption-governance-ops skill-coverage-audit-ops skill-ownership-merge-ops source-coverage-route-ops source-ingest-ops superpowers-method threat-zone-card-ops vocabulary-guard-ops waw-density-control-ops writing-rules-wiring-ops"
CANON_SCOPE="$B/skills"
in_scope() {  # مهارات المشروع = كل ما هو موجود في المرجع brain/skills (مشتق لا ثابت)
  case "$1" in */*) : ;; *) return 1 ;; esac
  [ -d "$CANON_SCOPE/${1%%/*}" ] && return 0
  # مهارات المشروع فقط، لا كل مهارات المنصة
  case "$1" in marine-news-brain/*|military-arabic-editing/*|macr-system/*|superpowers-method/*|self-learning-loop-ops/*|vocabulary-guard-ops/*|owner-ui-notes-contract-ops/*) return 0 ;; print-layout-gate-ops/*) return 0 ;; *) return 1 ;; esac
}

# ── 0) نسخة الدماغ مرجع حاكم (ك-340) ──
# السبب الجذري لعطل G018: المقارنة كانت بين المحلي والمستودع فقط، فإذا كان
# المستودع يحمل نسخة مختصرة (من تصدير قديم) هزمت النسخة الغنية ومسحت الشواهد.
# القاعدة: أي ملف مهارة موجود في "$B/skills" هو المرجع، يُفرض على المحلي والمستودع.
CANON="$B/skills"
if [ -d "$CANON" ]; then
  while IFS= read -r cf; do
    rel="${cf#"$CANON"/}"
    in_scope "$rel" || continue
    case "$(basename "$rel")" in *.md|*.json|*.py|*.txt) ;; *) continue ;; esac
    for tgt in "$SK/$rel" "$REPO/$rel"; do
      if [ ! -f "$tgt" ] || ! cmp -s "$cf" "$tgt"; then
        BK="${B:-.}/logs/skills-canon-$(date -u +%Y%m%d-%H%M%S)"
        mkdir -p "$BK/$(dirname "$rel")" "$(dirname "$tgt")"
        [ -f "$tgt" ] && cp -f "$tgt" "$BK/$(basename "$tgt").bak" 2>/dev/null || true
        cp -f "$cf" "$tgt"
        echo "  ⇧ فُرضت نسخة الدماغ: $rel → ${tgt#"$B"/}"
      fi
    done
  done < <(find "$CANON" -type f | sort)
fi


while IFS= read -r f; do
  rel="${f#"$REPO"/}"
  in_scope "$rel" || continue
  lf="$SK/$rel"
  [ -f "$lf" ] || { mkdir -p "$(dirname "$lf")"; cp "$f" "$lf"; to_local=$((to_local+1)); echo "  ↓ نُزّل: $rel"; continue; }
  if cmp -s "$f" "$lf"; then equal=$((equal+1)); continue; fi
  # قاعدة إصلاح (ك-XX): لا يُحكم بالتاريخ وحده — فسحب git يعطي الملف طابعًا زمنيًا حديثًا
  # فيقطع نسخة محلية أغنى بالمحتوى. الحكم: عدد الأسطر أولًا، ثم التاريخ، وبنسخة احتياطية دائمًا.
  BK="${B:-.}/logs/skills-sync-$(date -u +%Y%m%d-%H%M%S)"
  mkdir -p "$BK/$(dirname "$rel")"
  cp -f "$lf" "$BK/$rel.local.bak" 2>/dev/null || true
  ln_f=$(wc -l < "$f"); ln_lf=$(wc -l < "$lf")
  if [ "$ln_f" -gt "$ln_lf" ]; then
    cp "$f" "$lf"; to_local=$((to_local+1)); echo "  ↓ نُزّل (المستودع أكثر محتوى $ln_f>$ln_lf): $rel"
  elif [ "$ln_lf" -gt "$ln_f" ]; then
    cp "$lf" "$f"; to_repo=$((to_repo+1)); echo "  ↑ رُفع (المحلي أكثر محتوى $ln_lf>$ln_f · نسخة احتياطية في $BK): $rel"
  elif [ "$lf" -nt "$f" ]; then
    cp "$lf" "$f"; to_repo=$((to_repo+1)); echo "  ↑ رُفع (المحلي أحدث · نسخة احتياطية في $BK): $rel"
  else
    cp "$f" "$lf"; to_local=$((to_local+1)); echo "  ↓ نُزّل (المستودع أحدث · نسخة احتياطية في $BK): $rel"
  fi
done < <(find "$REPO" -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.txt" \) | sort)

# ── 2) ملفات محلية غير موجودة في المستودع: تُرفع ──
while IFS= read -r f; do
  rel="${f#"$SK"/}"
  in_scope "$rel" || continue
  case "$(basename "$rel")" in *.md|*.json|*.py|*.txt) ;; *) continue ;; esac
  if [ ! -f "$REPO/$rel" ]; then
    mkdir -p "$(dirname "$REPO/$rel")"; cp "$f" "$REPO/$rel"
    to_repo=$((to_repo+1)); echo "  ＋ رُفع ملف مفقود: $rel"
  fi
done < <(find "$SK" -type f | sort)

echo "  ملفات المستودع: $(find "$REPO" -type f | wc -l) · نُزّل: $to_local · رُفع: $to_repo · مطابق: $equal"

# ── 3) تحقق نهائي بالبصمة لا بالزمن ──
broken=()
while IFS= read -r f; do
  rel="${f#"$REPO"/}"
  in_scope "$rel" || continue   # ك-339: التحقق النهائي كان بلا مرشّح النطاق، فيعلن كسرًا لملفات لم تُنسخ أصلًا
  [ -f "$SK/$rel" ] && cmp -s "$f" "$SK/$rel" || broken+=("$rel")
done < <(find "$REPO" -type f \( -name "*.md" -o -name "*.json" -o -name "*.py" -o -name "*.txt" \) | sort)

if [ "${#broken[@]}" -gt 0 ]; then
  echo "  ✘ التماثل مكسور: ${broken[*]:0:5}"; exit 1
fi
if [ "$CHECK_ONLY" -eq 1 ] && { [ "$to_local" -gt 0 ] || [ "$to_repo" -gt 0 ]; }; then
  echo "  ✔ التماثل أُصلح الآن (مزامنة فورية)"
  exit 0
fi
echo "  ✔ التماثل سليم: المحلي = المستودع"
