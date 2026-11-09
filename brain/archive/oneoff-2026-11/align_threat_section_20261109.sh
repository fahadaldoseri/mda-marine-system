#!/usr/bin/env bash
# مواءمة قسم مستوى التهديد في المتنين مع بطاقة القطاعات المحوكمة، ثم إكمال W020 واستئناف الجولة.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) إعادة كتابة قسم التهديد في المتنين ═══"
python3 - <<'PY'
import pathlib, re

AR_BLOCK = """## مستوى التهديد
المستوى العام: مرتفع جدًا — أعلى قطاع: مضيق هرمز وخليج عُمان والخليج العربي.

مستوى التهديد في مضيق هرمز وخليج عُمان والخليج العربي: مرتفع جدًا
مستوى التهديد في باب المندب والبحر الأحمر: منخفض
مستوى التهديد في بحر العرب: منخفض
مستوى التهديد في القرن الأفريقي: متوسط
مستوى التهديد في المحيط الهندي: منخفض
مستوى التهديد العام: مرتفع جدًا

| القطاع | المستوى | ما يبرّره في كلمات قليلة |
|---|---|---|
| مضيق هرمز وخليج عُمان والخليج العربي | مرتفع جدًا | أربع وقائع مؤهّلة في مادة اليوم: عنوان UKMTO عن واقعة مصنفة هجومًا في مضيق هرمز، وتحديث عنوان UKMTO عن واقعة هجوم شرق خصب، وعناوين إعلامية عن ناقلة احترقت أو أصيبت بألغام، وعناوين مهنية عن تعطيل أو إصابة سفينة بضائع وحريق ناقلة. |
| باب المندب والبحر الأحمر | منخفض | لا واقعة جديدة مؤهّلة في مادة اليوم. |
| بحر العرب | منخفض | لا واقعة جديدة مؤهّلة في مادة اليوم. |
| القرن الأفريقي | متوسط | مستوى مستمر بلا مستجد مؤكد في هذه الفترة. |
| المحيط الهندي | منخفض | لا واقعة جديدة مؤهّلة في مادة اليوم. |

ما يبرّره: بطاقة القطاعات المعتمدة تختار أعلى نطاق وهو مضيق هرمز وخليج عُمان والخليج العربي، وفي مادته أربع وقائع مؤهّلة لهذا اليوم. ما يخفضه: النص الكامل لبلاغ UKMTO لم يثبت تعطيل الممر أو غرق سفينة أو خسائر مؤكدة، ولا واقعة مؤهّلة جديدة في القطاعات الأربعة الأخرى.
"""

EN_BLOCK = """## Threat Level
Overall level: Very High — highest sector: Strait of Hormuz and Gulf of Oman and the Arab Gulf.

| Sector | Level | Brief basis |
|---|---|---|
| Strait of Hormuz, Gulf of Oman, and Arab Gulf | Very High | Four qualifying items in today's material: a UKMTO title classified as an attack in the Strait of Hormuz, a UKMTO title update on an attack east of Khasab, media titles on a tanker burned or struck by mines, and professional titles on a bulk carrier disabled or hit and a tanker fire. |
| Bab el-Mandeb and Red Sea | Low | No new qualifying incident in today's material. |
| Arabian Sea | Low | No new qualifying incident in today's material. |
| Horn of Africa | Medium | Continuing level with no confirmed new item in this period. |
| Indian Ocean | Low | No new qualifying incident in today's material. |

What supports it: the approved sector card takes the highest zone, the Strait of Hormuz and Gulf of Oman and the Arab Gulf, where four qualifying items stand for today. What would lower it: the full UKMTO text does not establish corridor disruption, a sinking, or confirmed casualties, and no new qualifying incident appears in the other four zones.
"""

def swap(path, start_pat, block):
    p = pathlib.Path(path)
    lines = p.read_text(encoding='utf-8').splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(start_pat, l)), None)
    if start is None:
        print(f'   ⚠ لم أجد قسم التهديد في {path}')
        return
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('## ')), len(lines))
    new = lines[:start] + block.rstrip('\n').splitlines() + [''] + lines[end:]
    p.write_text('\n'.join(new).rstrip('\n') + '\n', encoding='utf-8')
    print(f'   ✔ {path}: قُسم {end - start} سطرًا')

swap('reports/2026-11-09-sectioned.md', r'^## مستوى التهديد', AR_BLOCK)
swap('/home/ubuntu/seawatch/sources/i18n/en/2026-11-09-sectioned.en.md', r'^## Threat Level', EN_BLOCK)
PY

echo "   ═══ 2) بوابات الاتساق والتحقق ═══"
printf "   %-26s" "اتساق مستوى التهديد:"
timeout 300 python3 validators/check_threat_consistency.py --date "$D" --brain . >/tmp/tc2.txt 2>&1
echo "rc=$? · $(grep -c '✘' /tmp/tc2.txt) منع"
grep "✘" /tmp/tc2.txt | head -4 | cut -c1-175 | sed 's/^/     /'
printf "   %-26s" "مدقق التقرير:"
timeout 300 python3 validators/validate_report.py "web/meta/$D.json" --md "reports/$D-sectioned.md" >/tmp/vr2.txt 2>&1
echo "rc=$?"
grep -E "✘|مخالف" /tmp/vr2.txt | head -4 | cut -c1-175 | sed 's/^/     /'

echo "   ═══ 3) إكمال W020 واستئناف الجولة ═══"
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 300 python3 tools/runbook.py complete W020 --date "$D" 2>&1 | tail -2 | cut -c1-160 | sed 's/^/   /'
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909h.log 2>&1
echo "   rc=$?"
tail -18 /tmp/run0909h.log | cut -c1-185 | sed 's/^/   /'