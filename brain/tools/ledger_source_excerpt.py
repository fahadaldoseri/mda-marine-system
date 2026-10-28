#!/usr/bin/env python3
"""أصل نص كل واقعة — الخطوة 4.1 من الأمر التنفيذي (23 أكتوبر 2026).

لكل واقعة في دفتر اليوم: يبحث عن المقطع الأقرب من **الأصول المحفوظة** (`archive/originals/<date>/`)
والتغذيات (`feeds/feeds-<date>.md`)، ويكتبه في:
  · حقل `source_excerpt` داخل `cumulative-2026/daily/<date>.json`
  · ملف مستقل `archive/source-text/<date>/<رمز الواقعة>.txt`
إن لم يجد نصًا مطابقًا كتب ذلك صريحًا — لا يُخترع نص.

الاستعمال: python3 tools/ledger_source_excerpt.py --date 2026-10-23
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STOP = {'في', 'من', 'على', 'إلى', 'عن', 'مع', 'هذا', 'هذه', 'التي', 'الذي', 'بين', 'بعد', 'قبل', 'أو', 'و'}


def tokens(title: str):
    words = re.findall(r'[\u0621-\u064A]{3,}', title or '')
    return [w for w in words if w not in STOP][:8]


def load_corpus(date: str):
    parts = []
    for d in (ROOT / 'archive' / 'originals' / date, ROOT / 'feeds'):
        if not d.exists():
            continue
        pats = ['*.md', '*.txt'] if d.name != 'feeds' else [f'feeds-{date}*.md', f'feeds-{date}*.json']
        for pat in pats:
            for p in sorted(d.glob(pat)):
                try:
                    parts.append((p.name, p.read_text(encoding='utf-8')))
                except (OSError, UnicodeDecodeError):
                    pass
    return parts


def excerpt_for(title: str, corpus, width=700):
    toks = tokens(title)
    best, best_name, best_score = '', '', 0
    for name, text in corpus:
        for m in re.finditer(r'[^\n]{80,}', text):
            seg = m.group(0)
            score = sum(1 for t in toks if t in seg)
            if score > best_score:
                best, best_name, best_score = seg, name, score
    if best_score == 0:
        return None, None
    return best[:width].strip(), best_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    a = ap.parse_args()
    led = ROOT / 'cumulative-2026' / 'daily' / f'{a.date}.json'
    if not led.exists():
        print(f'  ✘ لا دفتر لهذا اليوم: {led}'); return 2
    events = json.loads(led.read_text(encoding='utf-8'))
    if isinstance(events, dict):
        events = events.get('events', [])
    corpus = load_corpus(a.date)
    print(f'  · الوقائع: {len(events)} · الأصول المقروءة: {len(corpus)} ملفًا')
    outdir = ROOT / 'archive' / 'source-text' / a.date
    outdir.mkdir(parents=True, exist_ok=True)
    found = 0
    written = 0
    for e in events:
        code = e.get('code', 'MN-?')
        if e.get('source_excerpt'):
            found += 1
        else:
            seg, src = excerpt_for(e.get('title', ''), corpus)
            if seg:
                e['source_excerpt'] = seg
                e['source_excerpt_from'] = src
                found += 1
            else:
                e['source_excerpt'] = 'لم يُعثر على نص مطابق في الأصول المحفوظة'
                e['source_excerpt_from'] = ''
        # ك-163 (طلب فهد 2026-10-24، البند 10): كان الخلل أن الوقائع ذات المقتطف
        # المحفوظ تُتخطّى بـcontinue، فيبقى مجلد أرشيف النص فارغًا مع رسالة نجاح.
        # الآن يُكتب ملف أصل لكل واقعة في كل تشغيل.
        (outdir / f'{code}.txt').write_text(
            f'الرمز: {code}\nالتاريخ: {e.get("date")}\nالعنوان: {e.get("title")}\n'
            f'المصدر: {e.get("source")}\nأصل النص من: {e.get("source_excerpt_from") or "—"}\n\n'
            + e['source_excerpt'] + '\n', encoding='utf-8')
        written += 1
    led.write_text(json.dumps(events, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'  ✔ أصل نص لكل واقعة: {found}/{len(events)} · ملفات أُصلحت: {written} في {outdir}')
    origins = sorted({e.get('source_excerpt_from') or '—' for e in events})
    print('  • أصول النصوص المستعملة: ' + ' · '.join(o[:60] for o in origins))
    missing = [e.get('code') for e in events if not e.get('source_excerpt_from')]
    if missing:
        print('  • بلا نص مطابق: ' + ' · '.join(missing[:8]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
