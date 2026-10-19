#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص أسماء السفن والوسطاء مقابل قائمة OFAC SDN، مع قيد قاعدة 50%."""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
import csv, io, json, re, sys, urllib.request, datetime as dt
from pathlib import Path
URLS = ['https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV',
        'https://www.treasury.gov/ofac/downloads/sdn.csv']
UA = {'User-Agent': 'Mozilla/5.0'}

def load():
    for u in URLS:
        try:
            raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
            txt = raw.decode('utf-8', 'ignore')
            names = []
            for row in csv.reader(io.StringIO(txt)):
                for c in row:
                    c = c.strip()
                    if len(c) > 3 and not c.isdigit():
                        names.append(c.upper())
                        break
            if names:
                return u, sorted(set(names))
        except Exception as e:
            print(f"  تعذر {u[:60]} → {str(e)[:60]}")
    return None, []

def main():
    seen, targets = set(), []
    for l in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines():
        t = l.strip()
        if t and t.upper() not in seen:
            seen.add(t.upper())
            targets.append(t)
    if not targets:
        print("  · لا مستهدف في القائمة — لا فحص مطلوب")
        return 0
    src, names = load()
    if not names:
        print("  ✘ تعذر تحميل قائمة SDN — تُسجَّل النتيجة (تعذر) ولا يُدَّعى فحص")
        (Path(f'{BRAIN}/archive') / 'ofac-screen-latest.json').write_text(
            json.dumps({'utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'list': None, 'names': 0, 'status': 'list_unavailable',
                        'rule_note': 'تعذر تحميل قائمة SDN — لا يُدَّعى فحص',
                        'results': [{'target': t, 'match': [], 'result': 'no_result'} for t in targets]},
                       ensure_ascii=False, indent=1), encoding='utf-8')
        return 2
    print(f"  قائمة SDN: {len(names)} اسمًا · المصدر: {src[:70]}")
    hits = []
    for t in targets:
        tu = t.upper()
        STOP = {'MSC','MV','MT','THE','AND','OF','LTD','CO','SHIP','LINE','MARINE','GROUP','GLOBAL','INTERNATIONAL','TRADING','COMPANY','SA','LLC','INC','STAR','SEA','OCEAN'}
        def tk(s): return [x for x in re.split(r'[^A-Z0-9]+', s) if len(x) >= 3 and x not in STOP]
        toks = tk(tu)
        exact = [n for n in names if n == tu]
        strong = [n for n in names if len(toks) >= 2 and all(x in tk(n) for x in toks)]
        def near(n):
            """التطابق الجزئي لا يُحتسب على كلمة قصيرة شائعة: يلزم رمز مميّز (6 محارف+) أو رمزان مشتركان."""
            nt = set(tk(n))
            sh = [x for x in toks if x in nt]
            return len(sh) >= 2 or any(len(x) >= 6 for x in sh)
        partial = [n for n in names if not strong and toks and near(n)]
        if exact or strong:
            res, m = 'match', (exact or strong)
            print(f"   ⚠ تطابق · {t} → {m[:2]}")
        elif partial:
            res, m = 'review', partial
            print(f"   ◐ تطابق جزئي باسم شائع — يحتاج تحقق يدوي · {t} → {m[:2]}")
        else:
            res, m = 'no_match', []
            print(f"   ✔ لا تطابق · {t}")
        hits.append({'target': t, 'match': m[:5], 'result': res})
    out = Path(f'{BRAIN}/archive'); out.mkdir(exist_ok=True)
    (out / 'ofac-screen-latest.json').write_text(json.dumps(
        {'utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
         'list': src, 'names': len(names),
         'rule_note': 'قاعدة 50%: تُعد الكيانات المملوكة 50% أو أكثر من كيان مُدرج مُدرجة حكمًا',
         'results': hits}, ensure_ascii=False, indent=1), encoding='utf-8')
    matches = [h for h in hits if h['result'] == 'match']
    reviews = [h for h in hits if h['result'] == 'review']
    print(f"  ✔ حُفظ: archive/ofac-screen-latest.json · تطابق: {len(matches)} · جزئي: {len(reviews)} · لا تطابق: {len(hits)-len(matches)-len(reviews)}")
    if matches:
        print("  ✘ مانع — تطابق إدراج صريح يحتاج قرارًا قبل النشر: " + " · ".join(h['target'] for h in matches))
        return 2
    if reviews:
        print("  ◐ تحذير — تطابق جزئي يحتاج تحققًا يدويًا")
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
