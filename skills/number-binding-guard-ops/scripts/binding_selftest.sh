#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKER="$ROOT/scripts/number_binding_template.py"
TMP="$(mktemp -d /tmp/number-binding-selftest.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT

mkdir -p "$TMP/owners" "$TMP/current/runbook"
cat > "$TMP/owners/sources.json" <<'JSON'
{"approved":62,"qualified":{"checked":60,"at_time":37},"unit_terms":["مصدر","مصادر"]}
JSON
cat > "$TMP/owners/imo_attacks.json" <<'JSON'
{"approved":122,"unit_terms":["هجمة","هجمات","IMO"]}
JSON
cat > "$TMP/owners/sailor_deaths.json" <<'JSON'
{"approved":24,"unit_terms":["وفاة","وفيات","بحار","البحارة"]}
JSON
cat > "$TMP/current/report.md" <<'MD'
القائمة المعتمدة ذات **62 مصدرًا**.
العدد المعتمد لهجمات IMO: **122 هجمة IMO**.
العدد المعتمد لوفيات البحارة: **24 وفاة بحار**.
في ذلك التشغيل جرى فحص **60 مصدرًا**.
MD
cat > "$TMP/current/runbook/runbook.json" <<'JSON'
{"date":"2026-11-02","sources":"القائمة المعتمدة ذات **62 مصدرًا**","imo":"العدد المعتمد **122 هجمة IMO**","deaths":"العدد المعتمد **24 وفاة بحار**"}
JSON

# حرّف مالكًا واحدًا؛ الأسطح تبقى على 62، ولذلك يجب أن يفشل الربط مغلقًا.
cat > "$TMP/owners/sources.json" <<'JSON'
{"approved":61,"qualified":{"checked":60,"at_time":37},"unit_terms":["مصدر","مصادر"]}
JSON
set +e
python3 "$CHECKER" --brain "$TMP" --date 2026-11-02 > "$TMP/negative.log" 2>&1
NEGATIVE_RC=$?
set -e
NEGATIVE_VERDICTS="$(grep -c '^VERDICT:' "$TMP/negative.log" || true)"
if [[ "$NEGATIVE_RC" -ne 2 || "$NEGATIVE_VERDICTS" -ne 1 ]]; then
    echo "SELFTEST: FAIL (السالب: رمز=$NEGATIVE_RC، أحكام=$NEGATIVE_VERDICTS)" >&2
    cat "$TMP/negative.log" >&2
    exit 1
fi

# أعد النسخة الصحيحة، ثم أثبت أن الأسطح الحالية تجتاز.
cat > "$TMP/owners/sources.json" <<'JSON'
{"approved":62,"qualified":{"checked":60,"at_time":37},"unit_terms":["مصدر","مصادر"]}
JSON
set +e
python3 "$CHECKER" --brain "$TMP" --date 2026-11-02 > "$TMP/positive.log" 2>&1
POSITIVE_RC=$?
set -e
POSITIVE_VERDICTS="$(grep -c '^VERDICT:' "$TMP/positive.log" || true)"
if [[ "$POSITIVE_RC" -ne 0 || "$POSITIVE_VERDICTS" -ne 1 ]]; then
    echo "SELFTEST: FAIL (الموجب: رمز=$POSITIVE_RC، أحكام=$POSITIVE_VERDICTS)" >&2
    cat "$TMP/positive.log" >&2
    exit 1
fi

# افحص رمز النجاح صراحة بعد استدعاء مستقل حتى لا يمر نجاح جزئي.
if ! grep -q '^VERDICT: PASS$' "$TMP/positive.log"; then
    echo "SELFTEST: FAIL (الموجب لم يطبع PASS)" >&2
    cat "$TMP/positive.log" >&2
    exit 1
fi

echo "SELFTEST: PASS"
echo "الحالات: 2 (سالب/موجب)"
echo "السالب: رمز 2، حكم واحد"
echo "الموجب: رمز 0، حكم واحد"
