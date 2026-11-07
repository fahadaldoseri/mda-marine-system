#!/usr/bin/env python3
"""ترشيح بنود التغذيات قبل المعالجة (ط0) بالنموذج المدمج في Manus — بلا مفاتيح خارجية.

يقرأ بنوداً (سطر لكل بند أو مصفوفة JSON)، ويصنّف كل بند إلى ثلاثة مستويات:
«داخل النطاق» · «عند الصلة المباشرة» · «خارج النطاق»، مع المنطقة والتصنيف
وحالة التحقق المطلوبة، ثم يكتب JSONL + ملخصاً Markdown.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
NODE = 'manus-node'
CLIENT = str(ROOT / 'tools' / 'llm.mjs')

RULES = """أنت محلّل أمن بحري. نطاق العمل: الخليج العربي، مضيق هرمز، خليج عُمان، بحر العرب،
البحر الأحمر وباب المندب وخليج عدن عند الصلة المباشرة، المحيط الهندي والقرن الأفريقي.
لا يشمل النطاق: البحر الأسود، بحر البلطيق، آسيا والمحيط الهادئ، الأمريكتان، أوروبا، غرب أفريقيا.
قرار المستخدم المعتمد: البحر الأسود ليس منطقة مراقبة دائمة؛ أي بند عنه يُصنَّف «خارج النطاق» دائماً،
ولا يُدرج حتى في «عند الصلة المباشرة».
صنّف كل بند إلى أحد ثلاثة مستويات:
- «داخل النطاق»: تطوّر أمني بحري يمسّ السفينة أو العبور أو الرسو أو الطاقم أو الاتصال داخل النطاق مباشرة.
- «عند الصلة المباشرة»: الحادث خارج النطاق أو غير بحري صريح، لكنه يمسّ الملاحة في النطاق
  (توسّع صراع يهدد خطوط الملاحة، إجراءات على ميناء أو خط داخل النطاق، عقوبات على ناقلات تعمل في النطاق) — يُفحص بلا تنبيه.
- «خارج النطاق»: لا صلة بحرية بالنطاق.
واستخرج أيضاً: region (المنطقة الأقرب من قائمة النطاق أو «خارج النطاق»)،
category (هجوم أو قرصنة أو سطو مسلح أو نشاط مشبوه أو حادث بحري أو تشويش GNSS/AIS أو عقوبات أو نشرة رسمية أو غير ذلك)،
source_type (رسمي: UKMTO/IMO/NAVAREA/سنتكوم/هيئة موانئ — أو نقل إعلامي أو تغذية ثانوية)،
verify_with (الجهة الرسمية التي يُفحص عندها البند).
لا تخترع معلومات غير موجودة في البند؛ وإن كان غامضاً فاذكر ذلك في reason."""

SCHEMA = {
    "type": "object",
    "properties": {
        "scope": {"type": "string", "enum": ["داخل النطاق", "عند الصلة المباشرة", "خارج النطاق"]},
        "region": {"type": "string"},
        "category": {"type": "string"},
        "source_type": {"type": "string"},
        "verify_with": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["scope", "region", "category", "source_type", "verify_with", "reason"],
    "additionalProperties": False,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='ملف بنود: سطر لكل بند أو مصفوفة JSON')
    ap.add_argument('--out-dir', default=str(ROOT / 'audit'))
    ap.add_argument('--model', default='gpt-5-mini')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()

    raw = Path(a.input).read_text(encoding='utf-8').strip()
    if raw.startswith('['):
        items = json.loads(raw)
    else:
        items = [l.strip() for l in raw.split('\n')
                 if l.strip() and not l.strip().startswith(('#', '|', '>', '---')) and len(l.strip()) >= 15]
    if not items:
        print('  ✘ لا بنود'); return 1

    tmp = Path('/tmp/llm-triage'); tmp.mkdir(parents=True, exist_ok=True)
    (tmp / 'items.jsonl').write_text('\n'.join(json.dumps(i, ensure_ascii=False) for i in items) + '\n', encoding='utf-8')
    (tmp / 'schema.json').write_text(json.dumps(SCHEMA, ensure_ascii=False), encoding='utf-8')
    cmd = [NODE, CLIENT, 'batch', '--input', str(tmp / 'items.jsonl'), '--out', str(tmp / 'out.jsonl'),
           '--template', 'صنّف البند التالي:\n{input}', '--system', RULES,
           '--schema', str(tmp / 'schema.json'), '--schema-name', 'triage', '--model', a.model,
           '--workers', str(a.workers), '--max-tokens', '3000', '--reasoning-effort', 'minimal']
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print('  ✘ فشل النداء:', (p.stderr or p.stdout).strip()[:300]); return 1

    rows, inside, related, outside, errors = [], [], [], [], 0
    for line in (tmp / 'out.jsonl').read_text(encoding='utf-8').split('\n'):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get('error'):
            errors += 1; continue
        try:
            d = json.loads(r['output'])
        except Exception:
            errors += 1; continue
        rec = {'item': r['input'], **d}
        rows.append(rec)
        {'داخل النطاق': inside, 'عند الصلة المباشرة': related}.get(d.get('scope'), outside).append(rec)

    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')
    outdir = Path(a.out_dir); outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f'llm-triage-{stamp}.jsonl').write_text(
        '\n'.join(json.dumps(x, ensure_ascii=False) for x in rows) + '\n', encoding='utf-8')
    md = outdir / f'llm-triage-{stamp}.md'
    lines = [f'# ترشيح التغذيات (ط0) — {stamp} UTC', '',
             f'- النموذج: **{a.model}** (مدمج في Manus) · البنود: **{len(items)}** · '
             f'داخل النطاق: **{len(inside)}** · عند الصلة المباشرة: **{len(related)}** · '
             f'خارج النطاق: **{len(outside)}** · أخطاء: **{errors}**', '',
             '## بنود داخل النطاق (تُمرَّر للتحقق الرسمي)', '']
    for r in inside:
        lines.append(f'- **{r.get("region")}** · {r.get("category")} · {r.get("source_type")} · يُفحص عند: {r.get("verify_with")}\n  > {r["item"][:220]}')
    lines += ['', '## بنود عند الصلة المباشرة (تُفحص بلا تنبيه)', '']
    for r in related:
        lines.append(f'- **{r.get("region")}** · {r.get("category")} · يُفحص عند: {r.get("verify_with")}\n  > {r["item"][:220]}')
    lines += ['', '## بنود خارج النطاق (تُستبعد ولا تُنبَّه)', '']
    for r in outside:
        lines.append(f'- {r.get("region")} · {str(r.get("reason"))[:120]}\n  > {r["item"][:160]}')
    md.write_text('\n'.join(lines), encoding='utf-8')
    print(f'  ✔ داخل النطاق: {len(inside)} · عند الصلة المباشرة: {len(related)} · خارج النطاق: {len(outside)} · أخطاء: {errors}')
    print(f'  ✔ الملخص: {md}')
    return 0


if __name__ == '__main__':
    sys.exit(main())