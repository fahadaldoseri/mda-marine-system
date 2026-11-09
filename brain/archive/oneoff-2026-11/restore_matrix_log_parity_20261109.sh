#!/usr/bin/env bash
# استعادة تباعد المصفوفة/السجل + حارس تكامل + مهارة + دمج.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
S=fault-ledger-matrix-parity-ops
cd "$B" || exit 1

echo "   ═══ 1) قياس التباعد الحقيقي ═══"
python3 - <<'PY'
import json, pathlib
log_ids = []
for line in pathlib.Path('audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines():
    if line.startswith('| ك-'):
        log_ids.append(line.strip().strip('|').split('|')[0].strip())
d = json.loads(pathlib.Path('audit/traceability.json').read_text(encoding='utf-8'))
rows = d['rows'] if isinstance(d, dict) else d
mids = [r['fault_id'] for r in rows]
missing = [m for m in mids if m not in set(log_ids)]
print(f"   السجل: {len(log_ids)} · المصفوفة: {len(mids)} · في المصفوفة وليست في السجل: {len(missing)}")
print("   أول 6:", ', '.join(missing[:6]))
pathlib.Path('audit/measurements/matrix-log-gap.json').write_text(
    json.dumps({'missing': missing, 'log_count': len(log_ids), 'matrix_count': len(mids)},
               ensure_ascii=False, indent=1), encoding='utf-8')
PY

echo "   ═══ 2) الاستعادة من المصفوفة ═══"
python3 - <<'PY'
import json, pathlib, sys
sys.path.insert(0, 'tools')
import importlib.util
spec = importlib.util.spec_from_file_location('cr', 'tools/closure_round.py')
cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)

gap = json.loads(pathlib.Path('audit/measurements/matrix-log-gap.json').read_text(encoding='utf-8'))
d = json.loads(pathlib.Path('audit/traceability.json').read_text(encoding='utf-8'))
rows = {r['fault_id']: r for r in (d['rows'] if isinstance(d, dict) else d)}
p = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = p.read_text(encoding='utf-8').splitlines()
new_rows = []
for fid in gap['missing']:
    r = rows.get(fid)
    if not r:
        continue
    date = r.get('date') or '—'
    axis = r.get('axis') or 'غير مصنّف'
    cells = [fid, date, axis, r.get('symptom') or '—', r.get('cause') or '—',
             r.get('fix') or '—', r.get('barrier') or '—', r.get('status') or 'مفتوح']
    cells += cr.derive(date, cells[5], cells[6], cells[7])
    new_rows.append('| ' + ' | '.join(x or '—' for x in cells) + ' |')
last = max(i for i, l in enumerate(lines) if l.startswith('| ك-'))
lines = lines[:last + 1] + new_rows + lines[last + 1:]
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f"   ✔ استُعيد {len(new_rows)} صفًا من المصفوفة إلى السجل")
PY

echo "   ═══ 3) حارس تكامل المزامنة ═══"
cat > validators/check_ledger_matrix_parity.py <<'PY'
#!/usr/bin/env python3
"""حارس تكامل المزامنة: لا صفّ في المصفوفة خارج السجل، ولا تكرار، ولا انحدار في العدّ.

يفشل مغلقًا (rc=2) عند أي تباعد، ويحفظ خط الأساس في audit/measurements/ledger-baseline.json.
"""
from __future__ import annotations

import json
import pathlib
import sys


def main() -> int:
    root = pathlib.Path(sys.argv[sys.argv.index('--brain') + 1] if '--brain' in sys.argv else '.')
    log = root / 'audit/سجل-الأعطال-والثغرات.md'
    mat = root / 'audit/traceability.json'
    base_p = root / 'audit/measurements/ledger-baseline.json'
    ids = [l.strip().strip('|').split('|')[0].strip()
           for l in log.read_text(encoding='utf-8').splitlines() if l.startswith('| ك-')]
    rows = json.loads(mat.read_text(encoding='utf-8'))
    mids = [r['fault_id'] for r in (rows['rows'] if isinstance(rows, dict) else rows)]
    problems = []
    outside = sorted({m for m in mids if m not in set(ids)})
    if outside:
        problems.append(f'صفوف في المصفوفة خارج السجل: {len(outside)} → {", ".join(outside[:6])}')
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        problems.append(f'معرّفات مكررة في السجل: {len(dups)} → {", ".join(dups[:6])}')
    base = json.loads(base_p.read_text(encoding='utf-8')) if base_p.exists() else {}
    prev = int(base.get('log_rows', 0))
    if len(ids) < prev:
        problems.append(f'انحدار في عدّ الصفوف: {prev} ← {len(ids)}')
    if not problems and len(ids) >= prev:
        base_p.parent.mkdir(parents=True, exist_ok=True)
        base_p.write_text(json.dumps({'log_rows': len(ids), 'matrix_rows': len(mids),
                                      'updated': '2026-11-09'}, ensure_ascii=False, indent=1) + '\n',
                          encoding='utf-8')
    print(f'   السجل: {len(ids)} · المصفوفة: {len(mids)} · خط الأساس السابق: {prev}')
    if problems:
        for x in problems:
            print(f'   ✘ {x}')
        return 2
    print('   ✔ تكامل المزامنة سليم: لا صفّ خارج السجل · لا تكرار · لا انحدار')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
PY
chmod +x validators/check_ledger_matrix_parity.py
timeout 300 python3 validators/check_ledger_matrix_parity.py --brain . 2>&1 | tail -4 | sed 's/^/   /'

echo "   ═══ 4) إعادة الاشتقاق والحارس ═══"
timeout 600 python3 tools/closure_round.py --apply 2>&1 | grep -E "الحالة التشغيلية" | cut -c1-140 | sed 's/^/   /'
timeout 300 python3 validators/check_closure.py --brain . 2>&1 | tail -2 | cut -c1-140 | sed 's/^/   /'
timeout 300 python3 validators/check_ledger_matrix_parity.py --brain . 2>&1 | tail -2 | sed 's/^/   /'

echo "   ═══ 5) المهارة الجديدة ═══"
python3 /home/ubuntu/skills/skill-creator/scripts/init_skill.py "$S" --output-dir "$B/skills" >/dev/null 2>&1
rm -f "$B/skills/$S/SKILL.md" "$B/skills/$S/scripts/example.py" "$B/skills/$S/references/example.md"
rmdir "$B/skills/$S/templates" 2>/dev/null
cat > "$B/skills/$S/SKILL.md" <<'MD'
---
name: fault-ledger-matrix-parity-ops
description: حفظ تكامل المزامنة بين سجل الأعطال ومصفوفة التتبع واستعادة أي تباعد بينهما. استخدمها عند اختلاف عدد الصفوف بين السجل والمصفوفة، أو الاشتباه في فقدان صفوف أعطال، أو ظهور صفوف في المصفوفة بلا مقابل في السجل، أو تكرار معرّفات، أو قبل الإعلان أن السجل مكتمل، أو بعد أي جولة إغلاق عدّلت السجل.
---

# تكامل السجل والمصفوفة

السجل (`audit/سجل-الأعطال-والثغرات.md`) هو المصدر الحاكم، والمصفوفة (`audit/traceability.json`) مشتقّة منه. أي صفّ في المصفوفة بلا مقابل في السجل = تباعد، لا «فقدان» تلقائي.

## القاعدة الحاكمة قبل أي استعادة

**قِس المصدر قبل أن تدّعي الفقدان.** تحقق من ثلاثة مصادر مستقلة: النسخ الاحتياطية في `audit/backups/*`، وتاريخ Git للملف (`git show <rev>:<path> | grep -c '^| ك-'`)، والمصفوفة. إن لم يحمل أي منها العدد المزعوم، فالفارق تباعد لا فقدان.

## المسار

```bash
cd <brain-root>
# 1) قياس التباعد
python3 - <<'PY'
import json, pathlib
log = [l.strip().strip('|').split('|')[0].strip()
       for l in pathlib.Path('audit/سجل-الأعطال-والثغرات.md').read_text(encoding='utf-8').splitlines()
       if l.startswith('| ك-')]
rows = json.loads(pathlib.Path('audit/traceability.json').read_text(encoding='utf-8'))
mids = [r['fault_id'] for r in (rows['rows'] if isinstance(rows, dict) else rows)]
print(len(log), len(mids), sorted(set(mids) - set(log))[:6])
PY
# 2) الاستعادة من المصفوفة ثم إعادة الاشتقاق
python3 validators/check_ledger_matrix_parity.py --brain .   # يكشف ويحفظ خط الأساس
python3 tools/closure_round.py --apply
python3 validators/check_closure.py --brain .
```

## الاستعادة

تُبنى الصفوف المستعادة من حقول المصفوفة نفسها (المعرّف · التاريخ · المحور · العَرَض · السبب · الإصلاح · الحاجز · الحالة الأصلية)، ثم تُشتق الأعمدة 9–12 بدالة `closure_round.derive` — لا تُكتب يدويًا.

## الحراسة

`validators/check_ledger_matrix_parity.py` يفشل مغلقًا (rc=2) عند: صفّ في المصفوفة خارج السجل · معرّف مكرر · انحدار في العدّ عن خط الأساس في `audit/measurements/ledger-baseline.json`. أضف الخطوة إلى المانيفست بعد خطوة توليد المصفوفة.

## المزالق المقيسة

- مقارنة عدد السجل بعدد المصفوفة ثم تسمية الفرق «فقدانًا»: الفرق تباعد حتى يثبت العكس من مصدر مستقل.
- الاعتماد على نسخة احتياطية أقدم بلا قياس عدد صفوفها.
- كتابة الأعمدة المشتقّة مباشرة بدل ضبط الأعمدة الأصلية ثم إعادة الاشتقاق.

## المراجع

- `references/parity-evidence.md` — جدول مصادر التحقق وقراءة المخرجات.
MD
mkdir -p "$B/skills/$S/references"
cat > "$B/skills/$S/references/parity-evidence.md" <<'MD'
# مصادر التحقق وقراءة المخرجات

| المصدر | الأمر | الدلالة |
|---|---|---|
| السجل الحاكم | `grep -c '^| ك-' audit/سجل-الأعطال-والثغرات.md` | العدد الفعلي للصفوف |
| المصفوفة | `len(traceability.json.rows)` | المشتقّ؛ يجب أن يكون جزئيًا من السجل |
| النسخ الاحتياطية | `find audit/backups -name '*الأعطال*'` ثم عدّ الصفوف | أقرب لقطة زمنية |
| تاريخ Git | `git show <rev>:brain/audit/سجل-الأعطال-والثغرات.md \| grep -c '^| ك-'` | التطور الحقيقي للعدد |

| مخرج الحارس | الدلالة |
|---|---|
| `صفوف في المصفوفة خارج السجل` | تباعد يوجب الاستعادة من المصفوفة |
| `معرّفات مكررة` | خلل توليد أو استعادة مزدوجة |
| `انحدار في عدّ الصفوف` | فقدان مؤكد — يُعالج من أقرب مصدر يثبت العدد |
| `تكامل المزامنة سليم` | لا تباعد ولا تكرار ولا انحدار |
MD
python3 /home/ubuntu/skills/skill-creator/scripts/quick_validate.py --path "$B/skills/$S" 2>&1 | tail -1 | sed 's/^/   /'
for D in /home/ubuntu/skills /home/ubuntu/mda-marine-system/skills; do rm -rf "$D/$S"; cp -r "$B/skills/$S" "$D/$S"; done
python3 - <<'PY'
import hashlib, pathlib
S = 'fault-ledger-matrix-parity-ops'
vals = [hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16] for p in (
    f'/home/ubuntu/skills/{S}/SKILL.md',
    f'/home/ubuntu/mda-marine-system/skills/{S}/SKILL.md',
    f'/home/ubuntu/mda-marine-system/brain/skills/{S}/SKILL.md')]
print('   تماثل الأسطح الثلاثة:', 'مطابق' if len(set(vals)) == 1 else 'مختلف', vals[0])
t = pathlib.Path('/home/ubuntu/mda-marine-system/brain/INDEX.md')
txt = t.read_text(encoding='utf-8')
line = '- `skills/fault-ledger-matrix-parity-ops` — حارس تكامل السجل والمصفوفة واستعادة التباعد.\n'
if S not in txt:
    i = txt.find('\n## ')
    t.write_text((txt[:i] + '\n' + line + txt[i:]) if i > 0 else txt + '\n' + line, encoding='utf-8')
    print('   ✔ سُجّلت في INDEX.md')
PY

echo "   ═══ 6) الدفع والدمج ═══"
cd "$R" || exit 1
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "استعادة تباعد المصفوفة/السجل وحارس تكامل المزامنة (ك-580)

- قياس المصادر أثبت أن السجل لم يفقد صفوفًا: تاريخ Git والنسخ لم تتجاوز 593.
- استعادة 13 صفًا موجودة في المصفوفة وحدها إلى السجل واشتقاق أعمدتها.
- حارس جديد check_ledger_matrix_parity يفشل مغلقًا على التباعد والتكرار والانحدار.
- مهارة fault-ledger-matrix-parity-ops مع مرجع مصادر التحقق." 2>&1 | tail -1
BR=$(git rev-parse --abbrev-ref HEAD)
env -u GH_TOKEN git push -q -u origin "$BR" 2>&1 | tail -1 | cut -c1-100 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:$BR" --title "تكامل السجل والمصفوفة واستعادة التباعد" --body "استعادة 13 صفًا من المصفوفة، حارس تكامل يفشل مغلقًا، مهارة جديدة." --base main 2>&1 | tail -1)
echo "   PR: $(echo "$PR" | cut -c1-95)"
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1)
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -2 | cut -c1-110 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main محلي: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"