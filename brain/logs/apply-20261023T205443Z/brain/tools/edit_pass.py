#!/usr/bin/env python3
"""تحرير لغوي آلي لكل قسم — الخطوة 4 من الأمر التنفيذي (23 أكتوبر 2026).

يقرأ التقرير، يقسمه أقسامًا على العناوين `## `، ثم يرسل كل قسم إلى النموذج المدمج مع:
مختصر الكتابة (13 قاعدة) + المعجم (اكتب/لا تكتب) + قائمة المنع الواحدة + مطالبة المحرر.
المخرج: نص مُحرَّر + جدول تغييرات بفئات (أسلوب · بنية · مفردة · ترقيم · ترجمة حرفية).
**كل قسم يُفحص بـ`preserve_check.py`**: إن تغيّر رقم أو رمز أو اسم لاتيني أو رابط أو لفظ إسناد أو بنية عنوان/جدول،
يُرفض تعديل القسم كله ويُسجَّل السبب. ولا يُطبَّق على التقرير إلا بـ`--apply`.

الاستعمال:
  python3 tools/edit_pass.py --report reports/2026-10-23-sectioned.md            # تجربة جافة
  python3 tools/edit_pass.py --report reports/2026-10-23-sectioned.md --apply     # يكتب المُحرَّر في مكانه
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE = 'manus-node'
CLIENT = str(ROOT / 'tools' / 'llm.mjs')
CATEGORIES = ('أسلوب', 'بنية', 'مفردة', 'ترقيم', 'ترجمة حرفية')


def read(p: Path) -> str:
    return p.read_text(encoding='utf-8') if p.exists() else ''


def build_system() -> str:
    brief = read(ROOT / 'sections' / '20-writing-brief.md')
    lex = read(ROOT / 'sections' / '20-lexicon.md')
    ed = read(ROOT / 'appendices' / 'editor-prompt.md')
    rules = json.loads(read(ROOT / 'appendices' / 'writing-rules.json') or '{}')
    fc = json.loads(read(ROOT / 'appendices' / 'forbidden-coinages.json') or '{}')
    bans = []
    for e in rules.get('manual_only', []):
        if isinstance(e, dict) and e.get('dont'):
            bans.append(f"«{e['dont']}» ← «{e.get('do', '')}»")
    for e in fc.get('entries', []):
        if isinstance(e, dict) and e.get('term'):
            bans.append(f"«{e['term']}» ← «{e.get('replacement', '')}»")
    return (
        ed + '\n\n' + brief + '\n\n' + lex + '\n\n'
        + 'قائمة المنع الواحدة (ممنوع ← الصواب):\n- ' + '\n- '.join(bans[:80])
        + '\n\nقيود مطلقة: لا تغيّر أي رقم، ولا أي اسم لاتيني، ولا أي رمز (MN-… أو EST-…)، ولا أي رابط، '
          'ولا أي وصف يقين أو نسبة إلى جهة، ولا ترتيب العناوين ولا صفوف الجداول. '
          'التحرير لغوي وترقيمي وأسلوبي فقط، والمعنى يبقى كما هو حرفيًا.'
    )


SCHEMA = {
    'type': 'object',
    'properties': {
        'revised': {'type': 'string'},
        'changes': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'before': {'type': 'string'},
                    'after': {'type': 'string'},
                    'category': {'type': 'string', 'enum': list(CATEGORIES)},
                    'why': {'type': 'string'},
                },
                'required': ['before', 'after', 'category', 'why'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['revised', 'changes'],
    'additionalProperties': False,
}


def split_sections(text: str):
    """يقسّم التقرير إلى (عنوان، نص) على العناوين من مستوى `## `."""
    lines = text.splitlines()
    out, cur_title, cur = [], None, []
    for ln in lines:
        if ln.startswith('## '):
            if cur_title is not None:
                out.append((cur_title, '\n'.join(cur).strip('\n')))
            cur_title, cur = ln, [ln]
        else:
            cur.append(ln)
    if cur_title is not None:
        out.append((cur_title, '\n'.join(cur).strip('\n')))
    return out


def run_batch(texts, system, model, workers, tmpdir):
    """نداء واحد لكل قسم عبر `llm.mjs batch`. صفوف المخرج: {index, input, output, error}."""
    tmpdir.mkdir(parents=True, exist_ok=True)
    inp, out, sch = tmpdir / 'items.jsonl', tmpdir / 'out.jsonl', tmpdir / 'schema.json'
    inp.write_text('\n'.join(json.dumps(t, ensure_ascii=False) for t in texts) + '\n', encoding='utf-8')
    sch.write_text(json.dumps(SCHEMA, ensure_ascii=False), encoding='utf-8')
    cmd = [NODE, CLIENT, 'batch', '--input', str(inp), '--out', str(out),
           '--template', 'حرّر هذا القسم تحريرًا لغويًا فقط، وأعد JSON:\n{input}',
           '--system', system, '--schema', str(sch),
           '--model', model, '--workers', str(workers), '--max-tokens', '6000']
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print('  ✘ فشل النداء:', (p.stderr or p.stdout).strip()[:300])
        return None
    rows = []
    for line in out.read_text(encoding='utf-8').split('\n'):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def preserved(before: str, after: str, tmp: Path):
    """يستدعي preserve_check.py: 0 محفوظ · 2 تغيّرت حقائق أو بنية."""
    bp, ap = tmp / 'before.txt', tmp / 'after.txt'
    bp.write_text(before, encoding='utf-8')
    ap.write_text(after, encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'preserve_check.py'), str(bp), str(ap)],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stdout or '').strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out-dir', default=str(ROOT / 'audit'))
    ap.add_argument('--model', default='gpt-5-mini')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--min-chars', type=int, default=300)
    a = ap.parse_args()

    rep = Path(a.report)
    text = rep.read_text(encoding='utf-8')
    sections = split_sections(text)
    idxs = [i for i, (_, body) in enumerate(sections) if len(body) >= a.min_chars]
    print(f'  · الأقسام: {len(sections)} · المرسلة للتحرير: {len(idxs)} · النموذج: {a.model}')
    if not idxs:
        print('  ✘ لا أقسام للتحرير'); return 1

    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')
    tmp = Path('/tmp/edit-pass'); tmp.mkdir(parents=True, exist_ok=True)
    rows = run_batch([sections[i][1] for i in idxs], build_system(), a.model, a.workers, tmp)
    if rows is None:
        return 1

    accepted, rejected, changes, errors = {}, [], [], 0
    for r in rows:
        if r.get('error'):
            errors += 1; continue
        try:
            data = json.loads(r['output'])
        except (OSError, json.JSONDecodeError):
            errors += 1; continue
        pos = r.get('index')
        if not isinstance(pos, int) or pos < 0 or pos >= len(idxs):
            errors += 1; continue
        idx = idxs[pos]
        before = sections[idx][1]
        after = (data.get('revised') or '').strip('\n')
        ch = [c for c in (data.get('changes') or []) if c.get('before') and c.get('after') and c.get('category') in CATEGORIES]
        if not after or after == before:
            continue
        ok, msg = preserved(before, after, tmp)
        if not ok:
            rejected.append({'section': sections[idx][0], 'reason': msg.splitlines()[-1][:200] if msg else 'تغيّرت حقائق'})
            continue
        accepted[idx] = after
        changes += [dict(c, section=sections[idx][0].lstrip('# ').strip()) for c in ch]

    # ── المخرجات ──
    outdir = Path(a.out_dir); outdir.mkdir(parents=True, exist_ok=True)
    md = outdir / f'edit-pass-{stamp}.md'
    by_cat = {}
    for c in changes:
        by_cat[c['category']] = by_cat.get(c['category'], 0) + 1
    L = [f'# التحرير اللغوي الآلي — {stamp} UTC', '',
         f'- التقرير: `{rep}`',
         f'- النموذج: **{a.model}** (مدمج في Manus)',
         f'- الأقسام: **{len(sections)}** · محرَّرة ومقبولة: **{len(accepted)}** · مرفوضة لحفظ الحقائق: **{len(rejected)}** · أخطاء نداء: **{errors}**',
         f'- التغييرات: **{len(changes)}** · ' + ' · '.join(f'{k}: {v}' for k, v in sorted(by_cat.items())), '']
    if rejected:
        L += ['## أقسام رُفض تعديلها (حفظ الحقائق)', '']
        for r in rejected:
            L.append(f'- {r["section"]} — السبب: {r["reason"]}')
        L.append('')
    for c in changes:
        L.append(f'- **[{c["category"]}]** {c["section"]}: «{c["before"][:90]}» ← «{c["after"][:90]}»'
                 + (f' — {c.get("why","")}' if c.get('why') else ''))
    md.write_text('\n'.join(L) + '\n', encoding='utf-8')
    (outdir / f'edit-pass-{stamp}.jsonl').write_text(
        '\n'.join(json.dumps(c, ensure_ascii=False) for c in changes) + '\n', encoding='utf-8')

    # ── حقول العلامة ──
    date = re.search(r'(\d{4}-\d{2}-\d{2})', rep.name)
    date = date.group(1) if date else stamp[:10]
    (ROOT / 'logs').mkdir(exist_ok=True)
    (ROOT / 'logs' / f'edit-pass-{date}.json').write_text(json.dumps({
        'date': date, 'model': a.model, 'sections': len(sections), 'edited': len(accepted),
        'rejected': len(rejected), 'errors': errors, 'changes': len(changes), 'by_category': by_cat,
        'applied': bool(a.apply), 'report': str(rep), 'stamp': stamp,
    }, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    # ── مرشحات المعجم (الخطوة 7) ──
    cand = {}
    for c in changes:
        if c['category'] in ('مفردة', 'ترجمة حرفية'):
            k = (c['before'].strip()[:60], c['after'].strip()[:60])
            cand[k] = cand.get(k, 0) + 1
    reps = {k: v for k, v in cand.items() if v >= 2}
    if reps:
        lp = ROOT / 'appendices' / 'lexicon-candidates.md'
        t = lp.read_text(encoding='utf-8')
        for (b, af), n in sorted(reps.items(), key=lambda x: -x[1]):
            if f'| {b} |' not in t:
                t += f'| {b} | {af} | {n} | {date} |\n'
        lp.write_text(t, encoding='utf-8')
        print(f'  ✔ مرشحات المعجم: {len(reps)} (تنتظر اعتماد المالك)')

    if a.apply and accepted:
        lines = text.splitlines()
        rebuilt, cur, buf = [], None, []
        for ln in lines:
            if ln.startswith('## '):
                if cur is not None:
                    rebuilt.append((cur, buf))
                cur, buf = ln, [ln]
            else:
                buf.append(ln)
        if cur is not None:
            rebuilt.append((cur, buf))
        out_lines = []
        for i, (title, body) in enumerate(rebuilt):
            out_lines.append(accepted[i] if i in accepted else '\n'.join(body).strip('\n'))
        rep.write_text('\n\n'.join(out_lines) + '\n', encoding='utf-8')
        print(f'  ✔ طُبِّق على {rep} ({len(accepted)} قسمًا)')

    print(f'  ✔ الأقسام المقبولة: {len(accepted)} · المرفوضة: {len(rejected)} · التغييرات: {len(changes)} · أخطاء: {errors}')
    print(f'  ✔ التقرير: {md}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
