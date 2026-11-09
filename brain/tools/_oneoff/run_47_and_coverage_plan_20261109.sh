#!/usr/bin/env bash
# 1) تشغيل دفعة الأوامر الحقيقية · 2) خطة تغطية المُفعِّلات · 3) مهارة جديدة.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
S=enforcer-coverage-burndown-ops
cd "$B" || exit 1

echo "   ═══ 1) بناء أوامر الدفعة من الصفوف المفتوحة ═══"
python3 - <<'PY'
import json, pathlib, re
FAULT = re.compile(r'^\|\s*[\u0621-\u064A]{1,3}-\d')
TOKEN = re.compile(r'(?:validators|tests|tools|generator|skills)/[\w\u0600-\u06FF./-]+\.(?:py|sh)')
BASE = re.compile(r'\b([A-Za-z_][\w-]*\.(?:py|sh))\b')
idx = {}
for d in ('validators', 'tests', 'tools', 'generator'):
    for p in pathlib.Path(d).rglob('*'):
        if p.is_file() and p.suffix in ('.py', '.sh'):
            idx.setdefault(p.name, p)
rows = {}
for line in pathlib.Path('audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines():
    if FAULT.match(line):
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 12:
            rows[c[0]] = c
d = json.loads(pathlib.Path('audit/traceability.json').read_text(encoding='utf-8'))
open_ids = [r['fault_id'] for r in (d['rows'] if isinstance(d, dict) else d)
            if r.get('state') in ('مفتوح', 'بانتظار التحقق')]
armed, unarmed = {}, []
for fid in open_ids:
    c = rows.get(fid)
    if not c:
        continue
    blob = ' '.join(c[4:11])
    rel = next((t for t in TOKEN.findall(blob) if pathlib.Path(t).exists()), None)
    if rel:
        armed[fid] = f'timeout 120 python3 {rel}'; continue
    bn = next((n for n in BASE.findall(blob) if n in idx), None)
    if bn:
        armed[fid] = f'timeout 120 python3 {idx[bn]}'; continue
    unarmed.append(fid)
pathlib.Path('audit/measurements/batches/commands-E2.json').write_text(
    json.dumps({'commands': armed}, ensure_ascii=False, indent=1), encoding='utf-8')
pathlib.Path('audit/measurements/batches/no-command-rows-2.json').write_text(
    json.dumps({'rows': unarmed}, ensure_ascii=False, indent=1), encoding='utf-8')
print(f"   مفتوح/بانتظار: {len(open_ids)} · بأمر حقيقي: {len(armed)} · بلا دليل مسمّى: {len(unarmed)}")
PY

echo "   ═══ 2) تشغيل الدفعة عبر المشغّل الدائم ═══"
timeout 4000 python3 tools/measurement_batch_runner.py --root . --batch E2 --timeout 120 --write-every 5 2>&1 | tail -8 | cut -c1-150 | sed 's/^/   /'
echo "   ── توزيع رموز الخروج ──"
python3 - <<'PY'
import json, pathlib, collections
p = pathlib.Path('audit/measurements/batches/result-E2.json')
if p.exists():
    d = json.loads(p.read_text(encoding='utf-8'))
    rs = d.get('results', d if isinstance(d, list) else [])
    c = collections.Counter(str(r.get('rc')) for r in rs)
    print('   ', ' · '.join(f'rc={k}: {v}' for k, v in sorted(c.items())))
    ok = [r['fault_id'] for r in rs if str(r.get('rc')) == '0']
    bad = [r['fault_id'] for r in rs if str(r.get('rc')) != '0']
    print(f"   نجح: {len(ok)} · فشل: {len(bad)}")
    print(f"   عيّنة نجاح: {', '.join(ok[:6])} · عيّنة فشل: {', '.join(bad[:6])}")
else:
    print('   لا ملف نتيجة')
PY

echo "   ═══ 3) التطبيق والاشتقاق والحراس ═══"
timeout 300 python3 tools/apply_batch_results.py --root . --apply 2>&1 | grep -E "مطبَّق" | head -1 | cut -c1-120 | sed 's/^/   /'
timeout 600 python3 tools/closure_round.py --apply 2>&1 | grep -E "الحالة التشغيلية" | cut -c1-140 | sed 's/^/   /'
timeout 300 python3 validators/check_closure.py --brain . 2>&1 | tail -2 | cut -c1-140 | sed 's/^/   /'
timeout 300 python3 validators/check_ledger_matrix_parity.py --brain . 2>&1 | tail -1 | sed 's/^/   /'

echo "   ═══ 4) أساس خطة تغطية المُفعِّلات ═══"
python3 - <<'PY'
import json, pathlib, re, collections
FAULT = re.compile(r'^\|\s*[\u0621-\u064A]{1,3}-\d')
rows = []
for line in pathlib.Path('audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines():
    if FAULT.match(line):
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 12:
            rows.append(c)
def has_enforcer(c):
    b = c[10]
    return any(k in b for k in ('مطبَّق', 'فعّال', 'حارس', 'بوابة', 'اختبار'))
no_env = [c for c in rows if not has_enforcer(c)]
by_axis = collections.Counter(c[2] for c in no_env)
state = collections.Counter(c[11] for c in no_env)
print(f"   بلا مُفعِّل: {len(no_env)} من {len(rows)}")
print('   أعلى المحاور:', ' · '.join(f'{k}: {v}' for k, v in by_axis.most_common(6)))
print('   الحالة التشغيلية لها:', ' · '.join(f'{k}: {v}' for k, v in state.most_common(5)))
pathlib.Path('audit/measurements/enforcer-gap.json').write_text(json.dumps({
    'total': len(rows), 'without_enforcer': len(no_env),
    'by_axis': by_axis.most_common(), 'state': state.most_common()},
    ensure_ascii=False, indent=1), encoding='utf-8')
lessons = pathlib.Path('audit/موجز-التحسين-2026-11-09.md')
if lessons.exists():
    t = lessons.read_text(encoding='utf-8')
    for line in t.splitlines():
        if 'بلا مُفعِّل' in line:
            print('   من الموجز:', line.strip()[:120])
PY

echo "   ═══ 5) خطة التغطية ═══"
python3 - <<'PY'
import json, pathlib
g = json.loads(pathlib.Path('audit/measurements/enforcer-gap.json').read_text(encoding='utf-8'))
axes = '\n'.join(f"| {k} | {v} | {(v / max(1, g['without_enforcer']) * 100):.0f}% |" for k, v in g['by_axis'][:10])
doc = f"""# خطة تغطية المُفعِّلات (البوابات والحراس)

القياس: **{g['without_enforcer']} عطلًا بلا مُفعِّل** من أصل {g['total']} صفًا. المُفعِّل = بوابة أو حارس أو اختبار انحدار مرتبط بخطوة معلنة في المانيفست.

## التوزيع على المحاور

| المحور | بلا مُفعِّل | النسبة |
|---|---|---|
{axes}

## المراحل قبل الموعد النهائي (2027-01-07)

| المرحلة | الفترة | النطاق | معيار الإنجاز |
|---|---|---|---|
| م1 — الحصر والتصنيف | 2026-11-09 → 11-16 | تصنيف الـ{g['without_enforcer']} إلى: قابل للتشغيل الآلي · يحتاج قاعدة · استثناء مؤرّخ | ملف تصنيف لكل صف بلا استثناء |
| م2 — المدفوعة الأعلى تكرارًا | 11-17 → 12-07 | أعلى ثلاثة محاور في الجدول أعلاه | مُفعِّل لكل صف + اختبار موجب/سالب |
| م3 — المدفوعة الوسطى | 12-08 → 12-20 | المحاور المتوسطة | مُفعِّل أو استثناء بمهلة مكتوبة |
| م4 — الإقفال | 12-21 → 2027-01-07 | المتبقي + مراجعة كل استثناء | صفر بلا مُفعِّل بلا استثناء مؤرّخ |

## الدروس (27)

كل درس بلا مُفعِّل يُحوَّل إلى أحد ثلاثة: قاعدة في مهارة · بوابة في المانيفست · بند في مدير الانحدار. لا يُقبل درس «مدوَّن فقط».

## الحراسة

- `tools/self_improve.py` يقيس التغطية ويُخرج الرقم في كل جولة.
- `validators/check_exceptions_burndown.py` يمنع بقاء الاستثناءات بلا مهلة.
- الحارس الجديد في هذه الجولة يفشل مغلقًا إذا انخفضت التغطية عن خط الأساس.
"""
pathlib.Path('audit/خطة-تغطية-المُفعِّلات-2026-11-09.md').write_text(doc, encoding='utf-8')
print('   ✔ كُتبت الخطة: audit/خطة-تغطية-المُفعِّلات-2026-11-09.md')
PY

echo "   ═══ 6) حارس التغطية (لا انحدار في نسبة المُفعِّلات) ═══"
cat > validators/check_enforcer_coverage.py <<'PY'
#!/usr/bin/env python3
"""حارس تغطية المُفعِّلات: يمنع انحدار نسبة الأعطال ذات المُفعِّل، ويحفظ خط الأساس."""
from __future__ import annotations

import json
import pathlib
import re
import sys

FAULT = re.compile(r'^\|\s*[\u0621-\u064A]{1,3}-\d')
KEYS = ('مطبَّق', 'فعّال', 'حارس', 'بوابة', 'اختبار')


def main() -> int:
    root = pathlib.Path(sys.argv[sys.argv.index('--brain') + 1] if '--brain' in sys.argv else '.')
    rows = []
    for line in (root / 'audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines():
        if FAULT.match(line):
            c = [x.strip() for x in line.strip().strip('|').split('|')]
            if len(c) >= 12:
                rows.append(c)
    with_env = [c for c in rows if any(k in c[10] for k in KEYS)]
    pct = round(len(with_env) / max(1, len(rows)) * 100, 1)
    base_p = root / 'audit/measurements/enforcer-baseline.json'
    prev = json.loads(base_p.read_text(encoding='utf-8'))['percent'] if base_p.exists() else 0.0
    print(f'   التغطية: {len(with_env)}/{len(rows)} = {pct}% · خط الأساس: {prev}%')
    if pct < prev:
        print('   ✘ انحدار في تغطية المُفعِّلات')
        return 2
    base_p.parent.mkdir(parents=True, exist_ok=True)
    base_p.write_text(json.dumps({'percent': pct, 'rows': len(rows), 'updated': '2026-11-09'},
                                 ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('   ✔ لا انحدار')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
PY
timeout 200 python3 validators/check_enforcer_coverage.py --brain . 2>&1 | tail -2 | sed 's/^/   /'

echo "   ═══ 7) المهارة الجديدة ═══"
python3 /home/ubuntu/skills/skill-creator/scripts/init_skill.py "$S" --output-dir "$B/skills" >/dev/null 2>&1
rm -f "$B/skills/$S/SKILL.md" "$B/skills/$S/scripts/example.py" "$B/skills/$S/references/example.md"
rmdir "$B/skills/$S/templates" 2>/dev/null
cat > "$B/skills/$S/SKILL.md" <<'MD'
---
name: enforcer-coverage-burndown-ops
description: خفض عدد الأعطال والدروس بلا مُفعِّل (بوابة أو حارس أو اختبار) قبل موعد نهائي، بقياس حي وحارس يمنع الانحدار. استخدمها عند وجود أعداد كبيرة من الأعطال بلا مُفعِّل، أو عند بناء خطة إقفال بمراحل ومهل، أو عند انخفاض نسبة التغطية بين جولتين، أو عند تحويل درس مدوَّن إلى قاعدة أو بوابة، أو قبل الإعلان أن التغطية تحسّنت.
---

# خفض المُفعِّلات غير المغطّاة

المُفعِّل = بوابة أو حارس أو اختبار انحدار مرتبط بخطوة معلنة. صفّ بلا مُفعِّل هو عطل يمكن أن يعود بصمت.

## المسار

```bash
cd <brain-root>
python3 tools/self_improve.py --date $(date -u +%F)     # يطبع التغطية الحالية
python3 validators/check_enforcer_coverage.py --brain .  # يفشل مغلقًا على الانحدار
python3 tools/measurement_batch_runner.py --root . --batch <دفعة> --timeout 120 --write-every 5
python3 tools/apply_batch_results.py --root . --apply
python3 tools/closure_round.py --apply
```

## قواعد التحويل

| نوع البند | التحويل الصحيح |
|---|---|
| عطل قابل للتشغيل الآلي | أمر قياس حقيقي + ربطه بخطوة في المانيفست |
| عطل يحتاج قاعدة | بند في المهارة الحاكمة + مرجعها |
| عطل لا يقبل الحكم الآلي | استثناء **بمهلة مؤرخة وسبب مكتوب**، وحارس ميزانية الاستثناءات يمنعه بلا مهلة |
| درس | قاعدة أو بوابة أو بند في مدير الانحدار — لا تدوين فقط |

## حلقة التعلّم الذاتي

كل عطل يُغلق في هذه السلسلة يُنتج أثرين إلزاميين: **حارسًا يمنع عودته** و**مدخلًا في سجل الدروس** يربطه بالحارس. وحين يعود نمط عطل مُغلق، يُرفع خط الأساس ويُضاف اختبار سلبي — فالغرض ليس إغلاق الصف بل منع تكراره.

## الحراسة

- `validators/check_enforcer_coverage.py`: يفشل مغلقًا إذا انخفضت نسبة التغطية عن خط الأساس في `audit/measurements/enforcer-baseline.json`.
- خطة المراحل والمهل في `audit/خطة-تغطية-المُفعِّلات-<التاريخ>.md`.
- لا يُعلن تحسّن بلا رقم قبل/بعد من تشغيلين حقيقيين.

## المراجع

- `references/burndown-playbook.md` — جدول المراحل وقواعد قراءة الأرقام.
MD
mkdir -p "$B/skills/$S/references"
cat > "$B/skills/$S/references/burndown-playbook.md" <<'MD'
# قراءة الأرقام وقواعد المراحل

| الرقم | المصدر | الدلالة |
|---|---|---|
| `بلا مُفعِّل` | `self_improve.py` | أعطال بلا بوابة/حارس/اختبار في عمود الحاجز |
| `دروس بلا مُفعِّل` | `self_improve.py` | دروس مدوَّنة بلا قاعدة أو بوابة |
| `التغطية %` | `check_enforcer_coverage.py` | نسبة الأعطال ذات مُفعِّل؛ خط الأساس يمنع الانحدار |
| `استثناءات` | `check_exceptions_burndown.py` | كل استثناء يجب أن يحمل مهلة مؤرخة |

## قواعد المراحل

1. **الحصر أولًا**: لا تبدأ الإصلاح قبل تصنيف كل صف إلى (آلي · قاعدة · استثناء). الحصر هو ما يمنع التكرار.
2. **الأعلى تكرارًا أولًا**: رتّب المحاور بعدد الصفوف لا بسهولة الإصلاح.
3. **كل مُفعِّل يُختبر موجبًا وسالبًا**: الموجب يمر، والسالب (مدخل مخالف عمدًا) يُمنع. مُفعِّل بلا اختبار سلبي غير مثبت.
4. **الاستثناء مهلة لا حل**: بلا تاريخ انتهاء يُرفض.
5. **الرقم قبل/بعد**: أي إعلان تحسّن يحتاج تشغيلين مسجَّلين.

## مزالق مقيسة

- عدّ الصفوف بمُعرّف واحد (`ك-`) يُخفي عائلات أخرى ويُنتج تباعدًا وهميًا — استخدم `^\\|\\s*[\\u0621-\\u064A]{1,3}-\\d`.
- حصر «المُفعِّل» بوجود كلمة «اختبار» في أي عمود يُنتج تغطية كاذبة؛ اقرأ عمود الحاجز وحده.
- اعتبار التدوين مُفعِّلًا: أكبر سبب لعودة الأعطال المغلقة.
MD
python3 /home/ubuntu/skills/skill-creator/scripts/quick_validate.py --path "$B/skills/$S" 2>&1 | tail -1 | sed 's/^/   /'
for D in /home/ubuntu/skills /home/ubuntu/mda-marine-system/skills; do rm -rf "$D/$S"; cp -r "$B/skills/$S" "$D/$S"; done
python3 - <<'PY'
import hashlib, pathlib
S = 'enforcer-coverage-burndown-ops'
v = [hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16] for p in (
    f'/home/ubuntu/skills/{S}/SKILL.md', f'/home/ubuntu/mda-marine-system/skills/{S}/SKILL.md',
    f'/home/ubuntu/mda-marine-system/brain/skills/{S}/SKILL.md')]
print('   تماثل الأسطح:', 'مطابق' if len(set(v)) == 1 else 'مختلف', v[0])
t = pathlib.Path('/home/ubuntu/mda-marine-system/brain/INDEX.md')
txt = t.read_text(encoding='utf-8')
if S not in txt:
    line = f'- `skills/{S}` — خفض الأعطال والدروس بلا مُفعِّل بحارس يمنع انحدار التغطية.\n'
    i = txt.find('\n## ')
    t.write_text((txt[:i] + '\n' + line + txt[i:]) if i > 0 else txt + '\n' + line, encoding='utf-8')
    print('   ✔ سُجّلت في INDEX.md')
PY

echo "   ═══ 8) الدفع عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -B feat/enforcer-burndown-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "دفعة الأدلة الحقيقية وخطة تغطية المُفعِّلات وحارسها (ك-581)

- تشغيل دفعة الأوامر الحقيقية عبر المشغّل الدائم مع تقرير رموز الخروج.
- خطة تغطية المُفعِّلات بمراحل ومهل حتى 2027-01-07.
- حارس تغطية يفشل مغلقًا على انحدار نسبة المُفعِّلات.
- مهارة enforcer-coverage-burndown-ops مع حلقة تعلّم ذاتي." 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin feat/enforcer-burndown-20261109 2>&1 | tail -1 | cut -c1-60 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:feat/enforcer-burndown-20261109" --title "تغطية المُفعِّلات: خطة وحارس ومهارة" --body "دفعة أدلة حقيقية، خطة مراحل حتى 2027-01-07، حارس يمنع انحدار التغطية، ومهارة جديدة." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"