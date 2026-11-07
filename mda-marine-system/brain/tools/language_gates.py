#!/usr/bin/env python3
"""بوابات اللغة المتدرجة — الخطوة 4.3 من الأمر التنفيذي (23 أكتوبر 2026).

تُشغَّل داخل بوابة التسليم بعد إصلاح الصياغة الآلي وقبل بصمة النص:
  1) `validators/check_orthography.py` — الإملاء والنحو والترقيم (ط13أ).
  2) `tools/style_metrics.py`        — نسبة الجمل المبدوءة بـ«و» والمقاييس الأسلوبية.
وتقارن النتائج بعتبات `appendices/language-gates.json`، وتكتب ملفي القياس في `logs/`،
وتكتب تنبيهًا في `logs/alerts/` إن صارت نسبة «و» أسوأ من الوسيط. التدريج من التاريخ نفسه:
تنبيهي (رمز 1) حتى `advisory_until`، ومانع (رمز 2) من `enforce_from`.
"""
import argparse
import json
import statistics
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_cfg():
    return json.loads((ROOT / 'appendices' / 'language-gates.json').read_text(encoding='utf-8'))


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--md', default=None)
    a = ap.parse_args()
    md = Path(a.md) if a.md else ROOT / 'reports' / f'{a.date}-sectioned.md'
    if not md.exists():
        print(f'  ✘ لا تقرير: {md}'); return 2
    cfg = load_cfg()
    g = cfg['gates']
    logs = ROOT / 'logs'; logs.mkdir(exist_ok=True)
    ortho_j = logs / f'orthography-{a.date}.json'
    style_j = logs / f'style-metrics-{a.date}.json'

    rc_o, out_o = run([sys.executable, str(ROOT / 'validators' / 'check_orthography.py'), str(md), '--json', str(ortho_j)])
    rc_s, out_s = run([sys.executable, str(ROOT / 'tools' / 'style_metrics.py'), str(md), '--json', str(style_j)])
    def first(x):
        if isinstance(x, list):
            return x[0] if x else {}
        return x if isinstance(x, dict) else {}

    ortho = first(json.loads(ortho_j.read_text(encoding='utf-8'))) if ortho_j.exists() else {}
    style = first(json.loads(style_j.read_text(encoding='utf-8'))) if style_j.exists() else {}

    ortho_n = int(ortho.get('total', 0) or 0)
    waw = float(style.get('waw_pct', 0) or 0)
    banned = sum(int(v) for v in (style.get('banned') or {}).values()) if isinstance(style.get('banned'), dict) else int(style.get('banned') or 0)
    leaks = sum(int(style.get(k, 0) or 0) for k in ('dangling', 'space_before', 'double_letters'))

    fails = []
    if ortho_n > g['orthography_errors_max']:
        fails.append(f'إملاء/نحو: {ortho_n} > {g["orthography_errors_max"]}')
    if banned > g['banned_terms_max']:
        fails.append(f'ألفاظ ممنوعة: {banned} > {g["banned_terms_max"]}')
    if leaks > g['internal_phrases_max']:
        fails.append(f'عبارات داخلية: {leaks} > {g["internal_phrases_max"]}')
    if waw > g['waw_sentence_pct_max']:
        fails.append(f'جمل تبدأ بـ«و»: {waw}% > {g["waw_sentence_pct_max"]}%')

    print(f'  · الإملاء والنحو: {ortho_n} خطأ · ألفاظ ممنوعة: {banned} · عيوب ترقيم/تسرّب: {leaks}')
    if isinstance(style.get('banned'), dict) and style['banned']:
        top = sorted(style['banned'].items(), key=lambda x: -x[1])[:6]
        print('    أكثرها: ' + ' · '.join(f'{k}×{v}' for k, v in top))
    if style.get('waw_runs3'):
        print(f'    تتابع ثلاثي مبدوء بـ«و»: {style["waw_runs3"]} · جمل طويلة: {style.get("long", 0)}')
    print(f'  · الجمل المبدوءة بـ«و»: {waw}% (السقف {g["waw_sentence_pct_max"]}% · الهدف {cfg["targets"]["waw_sentence_pct"]}%)')
    mon = cfg.get('monitoring', {}).get('waw_sentence_pct', {})
    tgt = mon.get('target', cfg['targets']['waw_sentence_pct'])
    state = 'داخل الهدف' if waw <= tgt else ('بين الهدف والسقف' if waw <= g['waw_sentence_pct_max'] else 'فوق السقف')
    print(f'  · بند مراقبة «و» لكل تقرير: {waw}% · الهدف {tgt}% · السقف {g["waw_sentence_pct_max"]}%'
          f' · الحالة: {state} · السجل: logs/style-metrics-{a.date}.json')
    if fails:
        for f in fails:
            print(f'  ✘ {f}')
    else:
        print('  ✔ لا مخالفة لغوية')

    # ── تنبيه تراجع نسبة «و» ──
    hist = []
    for p in sorted(logs.glob('style-metrics-*.json'))[-cfg['alerts']['median_days'] - 1:-1]:
        try:
            v = json.loads(p.read_text(encoding='utf-8'))
            x = float(first(v).get('waw_pct', 0) or 0)
            if x:
                hist.append(x)
        except (OSError, json.JSONDecodeError):
            pass
    if hist and waw:
        med = statistics.median(hist)
        worse = (waw - med) / med * 100 if med else 0
        if worse > cfg['alerts']['waw_worse_than_median_pct']:
            ad = ROOT / cfg['alerts']['dir']; ad.mkdir(parents=True, exist_ok=True)
            (ad / f'waw-{a.date}.md').write_text(
                f'# تنبيه: تراجع أسلوبي\n\n- التاريخ: {a.date}\n- نسبة الجمل المبدوءة بـ«و»: {waw}%\n'
                f'- وسيط آخر {len(hist)} أيام: {med}%\n- مقدار التراجع: {worse:.1f}%\n'
                f'- القناة: ملف محلي فقط، ولا يُرسل على تلغرام.\n', encoding='utf-8')
            print(f'  ⚠ تنبيه: نسبة «و» أسوأ من الوسيط ({med}%) بمقدار {worse:.1f}% → logs/alerts/')

    today = date.fromisoformat(a.date)
    enforce = today >= date.fromisoformat(cfg['enforce_from'])
    if fails:
        if enforce:
            print('  ✘ بوابات اللغة مانعة اليوم (من %s) — يوقف التسليم' % cfg['enforce_from'])
            return cfg['enforce_exit_code']
        print('  • تنبيهي حتى %s — لا يوقف التسليم' % cfg['advisory_until'])
        return cfg['advisory_exit_code']
    return 0


if __name__ == '__main__':
    sys.exit(main())
