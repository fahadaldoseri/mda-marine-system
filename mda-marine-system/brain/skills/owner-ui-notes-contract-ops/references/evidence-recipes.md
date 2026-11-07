# أوامر قياس جاهزة

## بناء ومزامنة
```bash
cd <SITE>
python3 generator/sync_from_brain.py --date <DATE>
python3 generator/build_site.py; echo "exit=$?"
```

## عدّ في المخرج (عدّ تكرارات لا أسطر)
```bash
python3 - <<'PY'
import pathlib
h = pathlib.Path('dist/reports/<DATE>.html').read_text(encoding='utf-8')
for s in ('عنوان ثابت', 'سطر متغيّر', 'لفظ ممنوع'):
    print(s, h.count(s))
PY
```

## قياس DOM ولقطات
```bash
python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width':1440,'height':1000})
    pg.goto('file:///home/ubuntu/seawatch/dist/reports/<DATE>.html')
    print('بطاقات:', pg.locator('[data-kpi-id]').count())
    pg.screenshot(path='/tmp/shot-desktop.png', full_page=False)
    pg.set_viewport_size({'width':390,'height':844})
    pg.screenshot(path='/tmp/shot-mobile.png', full_page=False)
    b.close()
PY
```
اعرض اللقطات بصريًا قبل أي ادّعاء.

## مقارنة اللغتين
```bash
python3 validators/check_en_parity.py --date <DATE>; echo "exit=$?"
```

## حارس الإغلاق
```bash
python3 tools/closure_round.py --apply
python3 tools/check_closure.py; echo "exit=$?"
```
