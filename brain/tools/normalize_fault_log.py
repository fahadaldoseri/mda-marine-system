#!/usr/bin/env python3
"""توحيد بنية سجل الأعطال وسجل التعلم: مخطط واحد · حالة صريحة لكل صف · إزالة الازدواج.
لا يُحذف أي سجل: الصفوف المكرّرة تُوسم بلاحقة (ب) · النسخ الأصلية تُؤرشف.
الاستخدام: python3 tools/normalize_fault_log.py [--apply]"""
import argparse, json, re, shutil, time
from collections import Counter
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
F = B / 'audit' / 'سجل-الأعطال-والثغرات.md'
L = B / 'memory' / 'learning-log.jsonl'
CANON = ['الرقم', 'التاريخ', 'المحور', 'العَرَض', 'السبب الجذري', 'الإصلاح', 'التشديد والحالة', 'الحالة']

CLOSED_RX = re.compile(r'مُغلق|مغلق|أُغلق|أغلق|مُصلح|مصلح|أُصلح|متحقَّق|مُتحقَّق|تحقّق|مُعاير|معاير|مطابق ✓|موثَّق|موثق')
OPEN_RX = re.compile(r'مفتوح|قيد|جزئي|مؤجل|لم يُصلح|لم يُغلق|بلا حاجز|يُصلح قبل|بانتظار')


def derive_status(cells: list[str]) -> str:
    """حالة مشتقة من نص السجل نفسه — لا حكم من الخارج."""
    blob = ' '.join(cells)
    if OPEN_RX.search(blob) and not CLOSED_RX.search(blob):
        return 'مفتوح'
    if CLOSED_RX.search(blob):
        return 'مفتوح (فيه عمل مُنجز)' if OPEN_RX.search(blob) else 'مغلق'
    return 'غير محدد'


def normalize_table(text: str):
    lines = text.splitlines()
    out, seen, fixed = [], Counter(), {'reorder': 0, 'merge': 0, 'dup': 0, 'status': Counter()}
    for line in lines:
        if not line.startswith('| ك-'):
            out.append(line)
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) == 6:          # (الرقم|العَرَض|السبب|الإصلاح|التاريخ|الحالة) → المخطط القانوني
            num, sym, root, fix, date, status = cells
            cells = [num, date, '—', sym, root, fix, status]
            fixed['reorder'] += 1
        elif len(cells) > 8:         # انقسام خلية بسبب شرطة عمودية داخل النص
            num = cells[0]
            merged = cells[0:7]
            merged[6] = ' '.join(cells[6:])
            cells = merged
            fixed['merge'] += 1
        num = cells[0]
        seen[num] += 1
        if seen[num] > 1:
            suffix = 'ب' if seen[num] == 2 else chr(ord('ب') + seen[num] - 2)
            cells[0] = f'{num}/{suffix}'
            fixed['dup'] += 1
        KNOWN = {'مغلق', 'مفتوح', 'مفتوح (فيه عمل مُنجز)', 'غير محدد'}
        if cells[-1] in KNOWN:            # الصف يحمل حالة صريحة مسبقًا: لا تُضاف ثانية (ثبات الأداة)
            status = cells[-1]
        else:
            status = derive_status(cells[1:])
            cells = cells + [status]
        fixed['status'][status] += 1
        out.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(out) + '\n', fixed


def normalize_learning(path: Path):
    STATUS_MAP = {
        'closed': 'مغلق', 'مغلق': 'مغلق', 'مُغلق بحاجز': 'مغلق', 'معتمد': 'مغلق',
        'مُصلح ومُتحقَّق': 'مغلق', 'مُصلح ومُعاير': 'مغلق',
        'candidate': 'مرشّح', 'confirmed': 'مؤكَّد', 'promoted': 'مُرقّى',
        'مفتوح': 'مفتوح', 'مفتوح بحاجز مُقترح': 'مفتوح', 'مفتوح — يُصلح قبل الدمج': 'مفتوح',
    }
    ents, counts = [], Counter()
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            counts['سطر غير قابل للقراءة'] += 1
            continue
        raw = d.get('status', '')
        norm = STATUS_MAP.get(raw.strip(), 'غير محدد')
        if raw.startswith('مُصلح —') or raw.startswith('مُتحقَّق —'):
            norm = 'مغلق'
        d['status_norm'] = norm
        if raw and raw != norm:
            d['status_raw'] = raw
        counts[norm] += 1
        ents.append(d)
    return ents, counts


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true'); a = ap.parse_args()
    stamp = time.strftime('%Y%m%d-%H%M%S')
    bak = B / 'audit' / 'backups' / f'normalize-{stamp}'
    bak.mkdir(parents=True, exist_ok=True)
    for src in (F, L):
        shutil.copy2(src, bak / src.name)
    print(f'  نسخة احتياطية: {bak}')
    text, fixed = normalize_table(F.read_text(encoding='utf-8'))
    ents, counts = normalize_learning(L)
    print(f'  الجدول: أُعيد ترتيب {fixed["reorder"]} · أُدمجت خلايا {fixed["merge"]} · وُسم مكرّر {fixed["dup"]}')
    print(f'  الحالات المشتقة: {dict(fixed["status"])}')
    print(f'  التعلم: {dict(counts)}')
    if a.apply:
        F.write_text(text, encoding='utf-8')
        L.write_text('\n'.join(json.dumps(e, ensure_ascii=False) for e in ents) + '\n', encoding='utf-8')
        print('  ✔ كُتب الملفان بالمخطط الموحّد')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())