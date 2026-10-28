#!/usr/bin/env bash
# اختبار انحدار دائم: المصلح لا يغيّر شيئًا في تقارير 12→23 إلا «معلنةة» (مراجعة 23 أكتوبر ثالثًا-1)
set -u
cd "$(dirname "$0")/.."
python3 - <<'PY'
import importlib.util, io, sys, re
from pathlib import Path
B = Path('.')
spec = importlib.util.spec_from_file_location("rp", B/'tools/repair_prose.py')
rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)
rules = rp.load_rules()
total, files = 0, 0
for f in sorted((B/'reports').glob('2026-10-*-sectioned.md')):
    src = f.read_text(encoding='utf-8')
    t, _ = rp.fix_punctuation(src)
    t, _ = rp.fix_doubled_letters(t, rules)
    t, _ = rp.fix_fixed_terms(t, rules)
    files += 1
    if t != src:
        diff = sum(1 for a, b in zip(src.splitlines(), t.splitlines()) if a != b) + abs(len(src.splitlines())-len(t.splitlines()))
        # كل اختلاف مسموح فقط إن كان «معلنةة» ← «معلنة» أو «معلنة» مكرّرة
        def allowed(line):
            x, _ = rp.fix_punctuation(line)          # الترقيم المعلن (لا يعبر الأسطر)
            x = re.sub(r'ةة+', 'ة', x)
            for item in rules.get('autoreplace', []):
                if item.get('auto'):
                    x = re.sub(rf"(?<![\w\u0600-\u06FF]){re.escape(item['term'])}(?![\w\u0600-\u06FF])", item['replacement'], x)
            return x
        bad = [(a, b) for a, b in zip(src.splitlines(), t.splitlines()) if a != b and allowed(a) != b]
        total += diff
        if bad:
            print(f"  ✘ {f.name}: {len(bad)} تغييرًا غير مسموح — مثال: {bad[0][0][:60]} ← {bad[0][1][:60]}")
            sys.exit(2)
        print(f"  ✔ {f.name}: التغيير المسموح الوحيد (ةة) — {diff} موضعًا")
print(f"  ✓ {files} تقريرًا · صفر تغيير غير مسموح (المجموع المسموح {total})")
PY
