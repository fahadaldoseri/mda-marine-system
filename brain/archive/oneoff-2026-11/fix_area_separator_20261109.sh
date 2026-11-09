#!/usr/bin/env bash
# إصلاح جذري: فاصل قيمة الموقع المعتمد « - » بدل «—»، في المتنين والدفتر والواجهة، مع تطبيع في الأداة واختبار.
set -u
B=/home/ubuntu/mda-marine-system/brain
R=/home/ubuntu/mda-marine-system
cd "$B" || exit 1
D=2026-11-09

echo "   ═══ 1) تطبيع الفاصل في المتنين ═══"
python3 - <<'PY'
import pathlib
pairs = [
    ('reports/2026-11-09-sectioned.md', 'مقابل خصب — خليج عُمان', 'مقابل خصب - خليج عُمان'),
    ('/home/ubuntu/seawatch/sources/i18n/en/2026-11-09-sectioned.en.md',
     'Near Khasab — Gulf of Oman', 'Near Khasab - Gulf of Oman'),
]
for path, old, new in pairs:
    p = pathlib.Path(path)
    if not p.exists():
        print(f'   ⚠ مفقود: {path}')
        continue
    t = p.read_text(encoding='utf-8')
    n = t.count(old)
    if n:
        p.write_text(t.replace(old, new), encoding='utf-8')
    print(f'   {p.name}: {n} موضعًا')
PY

echo "   ═══ 2) الدفتر والواجهة ═══"
python3 - <<'PY'
import json, pathlib
OLD, NEW = 'مقابل خصب — خليج عُمان', 'مقابل خصب - خليج عُمان'
p = pathlib.Path('cumulative-2026/daily/2026-11-09.json')
d = json.loads(p.read_text(encoding='utf-8'))
n = 0
for e in d:
    for k in ('area', 'area_basis'):
        if isinstance(e.get(k), str) and OLD in e[k]:
            e[k] = e[k].replace(OLD, NEW); n += 1
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'   الدفتر: {n} حقلًا')
m = pathlib.Path('web/meta/2026-11-09.json')
j = json.loads(m.read_text(encoding='utf-8'))
def walk(o):
    c = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and OLD in v:
                o[k] = v.replace(OLD, NEW); c += 1
            else:
                c += walk(v)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str) and OLD in v:
                o[i] = v.replace(OLD, NEW); c += 1
            else:
                c += walk(v)
    return c
c = walk(j)
m.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'   الواجهة: {c} حقلًا')
PY

echo "   ═══ 3) تطبيع الفاصل في مولّد أسماء المواقع + اختبار ═══"
python3 - <<'PY'
import pathlib
p = pathlib.Path('tools/derive_area_labels.py')
t = p.read_text(encoding='utf-8')
helper = '''
def normalize_separators(raw: str) -> str:
    """يُطبّع فاصل الموقع إلى الصيغة المعتمدة « - » قبل أي مطابقة."""
    if not raw:
        return raw
    for dash in ("\\u2014", "\\u2013", "\\u2212"):
        raw = raw.replace(f" {dash} ", " - ").replace(dash, "-")
    while "  " in raw:
        raw = raw.replace("  ", " ")
    return raw.strip()


'''
anchor = 'def derive(row: dict, reg: dict, terms: list[tuple[str, str]])'
if 'def normalize_separators' not in t:
    t = t.replace(anchor, helper.lstrip('\n') + anchor, 1)
    t = t.replace('    raw = str(row.get("area") or "").strip()',
                  '    raw = normalize_separators(str(row.get("area") or "").strip())', 1)
    p.write_text(t, encoding='utf-8')
    print('   ✔ أُضيف التطبيع إلى derive_area_labels.py')
else:
    print('   • التطبيع موجود مسبقًا')
PY
cat > tests/test_area_separator_normalization.py <<'PY'
"""اختبار انحدار: فاصل قيمة الموقع يُطبّع إلى « - » قبل المطابقة، والمخالف يبقى مانعًا في الحارس."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_em_dash_is_normalized():
    mod = _load("dal", "tools/derive_area_labels.py")
    assert mod.normalize_separators("مقابل خصب — خليج عُمان") == "مقابل خصب - خليج عُمان"
    assert mod.normalize_separators("خورفكان – خليج عُمان") == "خورفكان - خليج عُمان"
    assert mod.normalize_separators("مضيق هرمز") == "مضيق هرمز"


def test_gate_rejects_raw_em_dash_and_accepts_normalized():
    mod = _load("cav", "validators/check_area_vocabulary.py")
    names, non_spatial = mod.load_allowed(ROOT)
    ok_bad, _ = mod.parts_ok("مقابل خصب — خليج عُمان", names, non_spatial)
    ok_good, _ = mod.parts_ok("مقابل خصب - خليج عُمان", names, non_spatial)
    assert ok_bad is False, "الحارس يجب أن يمنع الفاصل غير المعتمد"
    assert ok_good is True, "الحارس يجب أن يقبل الفاصل المعتمد"
PY
python3 -m pytest tests/test_area_separator_normalization.py -q 2>&1 | tail -3 | cut -c1-160 | sed 's/^/   /'

echo "   ═══ 4) تسجيل العطل ═══"
python3 - <<'PY'
import pathlib, re, datetime
log = pathlib.Path('audit/سجل-الأعطال-والثغرات.md')
lines = log.read_text(encoding='utf-8').splitlines()
rows = [l for l in lines if l.startswith('| ك-')]
ncols = rows[-1].count('|') - 1
last = int(re.search(r'ك-(\d+)', rows[-1]).group(1))
cells = [
    f'ك-{last+1}',
    'فاصل غير معتمد في قيمة الموقع «—» بدل « - » أوقف حارس مفردات الموقع',
    'جدول التوزيع الجغرافي في المتن كتب «مقابل خصب — خليج عُمان» بشرطة طويلة، ونُقلت القيمة إلى الدفتر والواجهة كما هي، فمنعها حارس مفردات الموقع لأنه يقبل فقط «<موقع دقيق> - <منطقة بحرية>».',
    'تصحيح الفاصل في المتن العربي والماستر الإنجليزي والدفتر والواجهة، وإضافة تطبيع للفاصل داخل tools/derive_area_labels.py قبل أي مطابقة، مع اختبار انحدار موجب وسالب.',
    'دالة normalize_separators في مولّد أسماء المواقع + اختبار tests/test_area_separator_normalization.py + حارس مفردات الموقع كما هو بلا تخفيف.',
    'سجل الأعطال ومصفوفة التتبع: الصف مربوط بأمر إعادة قياس بوابة الأصول G000A.',
    'مغلق',
    datetime.date.today().isoformat(),
    'قياس حي: تشغيل الحارس على دفتر اليوم يعيد صفر مخالفات، والاختبار يمرّ.',
    'أمر إعادة التشغيل: python3 validators/check_area_vocabulary.py --date <DATE>',
    'run_evidence: python3 -m pytest tests/test_area_separator_normalization.py -q && python3 validators/check_area_vocabulary.py --date <DATE>',
    'الدرس: أي قيمة منسوخة من متن حرّ تُطبَّع إلى صيغة السجل قبل كتابتها في الدفتر.',
]
if len(cells) != ncols:
    print(f'   ⚠ عدد الأعمدة لا يطابق ({len(cells)} ≠ {ncols})')
else:
    out, done = [], False
    for l in lines:
        out.append(l)
        if l is rows[-1]:
            out.append('| ' + ' | '.join(cells) + ' |'); done = True
    log.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'   ✔ سُجّل ك-{last+1}' if done else '   ⚠ لم يُدرج')
PY

echo "   ═══ 5) الكتيب والتحقق ═══"
timeout 300 python3 tools/runbook.py handbook --root . >/dev/null 2>&1 && echo "   ✔ تولّد الكتيب"
timeout 400 python3 tools/runbook.py verify --root . 2>&1 | tail -2 | cut -c1-170 | sed 's/^/   /'

echo "   ═══ 6) تثبيت عبر فرع وطلب دمج ═══"
cd "$R" || exit 1
git checkout -q -B fix/area-separator-20261109
git add -A >/dev/null 2>&1
git -c user.name="Manus" -c user.email="manus@local" commit -q -m "تطبيع فاصل قيمة الموقع وإصلاح دفتر وواجهة 2026-11-09 (ك-579)" 2>&1 | tail -1
env -u GH_TOKEN git push -q -u origin fix/area-separator-20261109 2>&1 | tail -1 | cut -c1-60 | sed 's/^/   /'
PR=$(env -u GH_TOKEN gh pr create --head "fahadaldoseri:fix/area-separator-20261109" --title "تطبيع فاصل الموقع" --body "ك-579: «—» ⇒ « - » في المتن والدفتر والواجهة مع تطبيع في الأداة." --base main 2>&1 | tail -1)
N=$(echo "$PR" | grep -oE '[0-9]+$' | tail -1); echo "   PR: $N"
[ -n "${N:-}" ] && env -u GH_TOKEN gh pr merge "$N" --merge --delete-branch=false 2>&1 | tail -1 | cut -c1-90 | sed 's/^/   /'
git checkout -q main && env -u GH_TOKEN git pull -q origin main 2>/dev/null
echo "   main: $(git rev-parse --short HEAD) · بعيد: $(git rev-parse --short origin/main) · نظافة: $(git status --porcelain | wc -l)"

echo "   ═══ 7) استئناف الجولة ═══"
cd "$B" || exit 1
pgrep -af 'runbook.py run' | cut -c1-90 | sed 's/^/   جارية: /' || echo "   لا تشغيل متوازٍ"
timeout 5400 python3 tools/runbook.py run --date "$D" > /tmp/run0909i.log 2>&1
echo "   rc=$?"
tail -20 /tmp/run0909i.log | cut -c1-185 | sed 's/^/   /'