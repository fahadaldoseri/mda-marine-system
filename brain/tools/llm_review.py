#!/usr/bin/env python3
"""ناقد لغوي ومصطلحي لمتن التقارير — يعمل بالنموذج المدمج في Manus (بلا مفاتيح خارجية).

يقرأ نصّاً عربياً، يفحص كل فقرة على قواعد اللغة العسكرية والمصطلحات المعتمدة،
ثم يكتب: ملف مراجعة Markdown + ملف JSONL للاستخدام الآلي.
لا يُعدّل النص تلقائياً؛ يُخرج ملاحظات ليُعتمد التعديل بعد المراجعة.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
NODE = 'manus-node'
CLIENT = str(ROOT / 'tools' / 'llm.mjs')

RULES = """أنت ناقد لغوي عسكري بحري خبير في العربية الفصحى المبسّطة.
افحص الفقرة المعطاة واذكر المخالفات **المادية** فقط. القواعد:
1) لغة عربية بسيطة ومباشرة موجّهة للقارئ؛ ممنوع الحشو والمصطلحات الأكاديمية غير الدارجة.
2) مصطلحات معتمدة: «وقائع أمنية جديدة» لا «هجمات» إلا بثبوت الهجوم؛ «نشرات استشارية»؛
   «مقذوفات من جهة غير معلومة»؛ «التكدس الملاحي»؛ «الأثر على العمل»؛ «ناقلة سوائب (سفينة شحن سائب)» لا «السائبة» وحدها.
3) ممنوع: «إنذار»، «السائبة» وحدها، «تحقيق» بمعنى فحص، «هجوم» بلا إسناد رسمي.
4) لا تُقدَّم الروايات غير المؤكدة كحقائق؛ يلزم وسمها: «رواية غير مؤكدة» أو «نقل إعلامي».
5) التوقيت مزدوج (UTC وتوقيت البحرين) عند ذكر وقت أو تاريخ.
6) لا تخترع بيانات، ولا تطلب معلومات غير موجودة في الفقرة.

قيود إلزامية تمنع الإنذارات الكاذبة:
- اذكر فقط كلمات موجودة حرفياً في الفقرة. لا تذكر كلمة غير موجودة.
- لا تعتبر غياب التوقيت مخالفة إلا إذا وردت في الفقرة ساعة أو تاريخ.
- «ناقلة السوائب» مقبولة بعد ورود الصيغة الكاملة مرة واحدة؛ لا تعلّق عليها.
- إذا أُسند الرقم أو الوصف إلى جهة رسمية بالاسم (المنظمة البحرية الدولية، UKMTO، هيئة الموانئ السنغافورية)
  فالإسناد كافٍ؛ لا تطلب مصدراً إضافياً.
- الحد الأقصى ثلاث ملاحظات للفقرة، وبالأهمية: عالية أو متوسطة فقط. إن لم توجد مخالفة مادية فاجعل المصفوفة فارغة.
أخرج النتيجة وفق المخطط المطلوب فقط، وبلا أي شرح إضافي."""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["سليم", "يحتاج تعديل"]},
        "violations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "kind": {"type": "string", "enum": ["مصطلح", "أسلوب", "دقة", "توقيت", "حشو"]},
                    "severity": {"type": "string", "enum": ["عالية", "متوسطة"]},
                    "suggestion": {"type": "string"},
                },
                "required": ["word", "kind", "severity", "suggestion"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdict", "violations"],
    "additionalProperties": False,
}


def _present(word: str, para: str) -> bool:
    """يتحقق أن الكلمة المشتكى منها موجودة فعلاً في الفقرة (بعد تجاهل علامات الترقيم)."""
    norm = lambda s: re.sub(r'[«»"\'،.:؛\-—–()\s]', '', s)
    return norm(word) and norm(word) in norm(para)


def paragraphs(text: str, limit: int):
    out = []
    for ln in text.split('\n'):
        s = ln.strip()
        if not s or s.startswith(('#', '|', '>', '---')):
            continue
        s = re.sub(r'^\d+\.\s*', '', s).replace('**', '')
        if len(s) < 25:
            continue
        out.append(s)
    return out[:limit]


def run_batch(items, model, workers, tmpdir):
    inp = tmpdir / 'items.jsonl'
    out = tmpdir / 'out.jsonl'
    sch = tmpdir / 'schema.json'
    inp.write_text('\n'.join(json.dumps(i, ensure_ascii=False) for i in items) + '\n', encoding='utf-8')
    sch.write_text(json.dumps(SCHEMA, ensure_ascii=False), encoding='utf-8')
    cmd = [NODE, CLIENT, 'batch', '--input', str(inp), '--out', str(out),
           '--template', 'افحص الفقرة التالية:\n{input}', '--system', RULES,
           '--schema', str(sch), '--schema-name', 'review', '--model', model,
           '--workers', str(workers), '--max-tokens', '3000', '--reasoning-effort', 'minimal']
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print('  ✘ فشل النداء:', (p.stderr or p.stdout).strip()[:300])
        return None
    print('  ' + (p.stderr.strip().split('\n')[-1] if p.stderr.strip() else 'تم'))
    rows = []
    for line in out.read_text(encoding='utf-8').split('\n'):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    ap.add_argument('--out-dir', default=str(ROOT / 'audit'))
    ap.add_argument('--model', default='gpt-5-mini')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int, default=40)
    a = ap.parse_args()

    text = Path(a.report).read_text(encoding='utf-8')
    items = paragraphs(text, a.limit)
    if not items:
        print('  ✘ لا فقرات للفحص'); return 1
    print(f'  · الفقرات المرسلة: {len(items)} · النموذج: {a.model}')

    tmpdir = Path('/tmp/llm-review')
    tmpdir.mkdir(parents=True, exist_ok=True)
    rows = run_batch(items, a.model, a.workers, tmpdir)
    if rows is None:
        return 1

    flagged, errors, ok = [], 0, 0
    for r in rows:
        if r.get('error'):
            errors += 1; continue
        try:
            data = json.loads(r['output'])
        except Exception:
            errors += 1; continue
        para = r['input']
        # ترشيح: تُقبل الملاحظة فقط إذا كانت الكلمة موجودة حرفياً في الفقرة (منع التخمين)
        clean = [v for v in (data.get('violations') or [])
                 if v.get('word') and _present(v['word'], para) and v.get('severity') in ('عالية', 'متوسطة')]
        if clean:
            flagged.append({'paragraph': para, 'verdict': data.get('verdict'), 'violations': clean})
        else:
            ok += 1

    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')
    outdir = Path(a.out_dir); outdir.mkdir(parents=True, exist_ok=True)
    md = outdir / f'llm-review-{stamp}.md'
    lines = [f'# مراجعة لغوية ومصطلحية آلية — {stamp} UTC', '',
             f'- النموذج: **{a.model}** (مدمج في Manus — بلا مفاتيح خارجية)',
             f'- الفقرات المفحوصة: **{len(items)}** · سليمة: **{ok}** · تحتاج تعديل: **{len(flagged)}** · أخطاء نداء: **{errors}**', '']
    for i, f in enumerate(flagged, 1):
        lines += [f'## فقرة {i}', f'> {f["paragraph"][:400]}', '']
        for v in f['violations']:
            lines.append(f'- **{v["word"]}** — {v.get("kind")} · أهمية {v.get("severity")} · المقترح: {v["suggestion"]}')
        lines.append('')
    md.write_text('\n'.join(lines), encoding='utf-8')
    (outdir / f'llm-review-{stamp}.jsonl').write_text(
        '\n'.join(json.dumps(x, ensure_ascii=False) for x in flagged) + '\n', encoding='utf-8')
    print(f'  ✔ سليمة: {ok} · تحتاج تعديل: {len(flagged)} · أخطاء: {errors}')
    print(f'  ✔ المراجعة: {md}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
