#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مزامنة تنظيف قسم الاستنتاج على مصدر Brain ونسخة الموقع.
يطابق التعديل المطبّق على ملف Word:
  - نص استنتاج جديد (بلا جملة وقائع، وبلا الأثر التشغيلي/مؤشرات التحذير المبكر)
  - حذف بندَي «الأثر التشغيلي» و«مؤشرات التحذير المبكر» من قسم الاستنتاج
"""
from pathlib import Path
import re

NEW = ('الاستنتاج. تدير الجهة نفسها السفينتين، وخطّا خدمتهما متقاربان. '
       'وهذا يرفع احتمال أن نمط الاختيار لا يقتصر على سفينة بعينها؛ والتقييم: مرجّح. '
       'ولا يثبت ذلك جهة التنفيذ. وتربط مصادر مهنية الواقعتين بسفن مرتبطة بالإمارات، '
       'من دون الجزم بأن الواقعتين استهدفتا هذه الفئة تحديدًا؛ والقصد غير مثبت. '
       'ويبقى الحطام خطرًا ملاحيًا بعد الغرق، وتستوجب الحاويات الطافية تحذيرًا للملاحين. '
       'ويُحتمل أن تزيد المخاطر البيئية والمطالبات التأمينية؛ '
       'ولم يثبت ارتفاع أقساط التأمين بسبب الواقعتين.')

TARGETS = [
    Path('/home/ubuntu/brain-marine-news/reports/GFS-MACR-المعتمد-2026-10-17.md'),
    Path('/home/ubuntu/seawatch/sources/special/gfs-pride-giselle-2026-10-15.md'),
]

DROP_PREFIX = ('الأثر التشغيلي.', 'مؤشرات التحذير المبكر.')

def fix(path: Path) -> str:
    if not path.exists():
        return f'غير موجود: {path}'
    lines = path.read_text(encoding='utf-8').split('\n')
    out, done_new, dropped = [], 0, 0
    for ln in lines:
        s = ln.strip()
        if s.startswith('الاستنتاج.'):
            out.append(NEW)
            done_new += 1
            continue
        if any(s.startswith(k) for k in DROP_PREFIX):
            dropped += 1
            continue
        out.append(ln)
    text = '\n'.join(out)
    # تنظيف الأسطر الفارغة المتكررة الناتجة عن الحذف
    text = re.sub(r'\n{3,}', '\n\n', text)
    path.write_text(text, encoding='utf-8')
    return f'{path.name}: نُفّذ الاستنتاج={done_new} · حُذف={dropped}'

if __name__ == '__main__':
    for p in TARGETS:
        print(fix(p))