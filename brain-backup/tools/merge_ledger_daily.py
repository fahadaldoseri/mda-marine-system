#!/usr/bin/env python3
"""دمج ملفات اليوم في الدفتر التراكمي + بناء خريطة رموز الأحداث.

المشكلة التي يحلّها (مكتشفة 13 أكتوبر 2026): التقرير اليومي يكتب ملفًا في
`cumulative-2026/daily/<التاريخ>.json`، لكن **لا شيء يدمجه** في الدفتر التراكمي،
ولا توجد خريطة تربط رموز التقرير (MN-...) بمعرّفات الدفتر (EV-...). النتيجة: انقطاع
الذاكرة التراكمية، وعدم إمكانية إسناد أي إشارة إلى حدث سابق.

الاستخدام: python3 tools/merge_ledger_daily.py
المخرجات: cumulative-2026/event-ledger-master.json + appendices/event-code-map.json
"""
import hashlib, json, datetime
from collections import Counter
from pathlib import Path

B = Path('/home/ubuntu/brain-marine-news')
FROZEN = B / 'cumulative-2026' / 'event-ledger-sectioned-2026-02-28-to-2026-10-11.json'
MASTER = B / 'cumulative-2026' / 'event-ledger-master.json'
CODEMAP = B / 'appendices' / 'event-code-map.json'
DAILY = B / 'cumulative-2026' / 'daily'

# الرموز المُسنَدة لوقائع سابقة بأثر رجعي في إصدار 13 أكتوبر — تُربط صراحةً بمعرّفات الدفتر
ALIASES = {
    'MN-2026-10-11-02': {
        'event_id': 'EV-2026-10-11-148-5ced58be',
        'note': 'نفس الواقعة: إصابة ناقلة بمسيّرة قرب مرسى صحار (UKMTO #165) — رُمِّزت بأثر رجعي في إصدار 13 أكتوبر.',
    },
    'MN-2026-10-04-01': {
        'event_id': 'EV-2026-10-04-141-90fecee1',
        'note': 'تنازع رموز: إصدار 12 أكتوبر استخدم الرمز نفسه بمعنى «تراجع الحركة إلى 4 عبورات»، وإصدار 13 أكتوبر بمعنى «إصابة ناقلة بلغم في المضيق». الرمز يُمنح مرة واحدة ومعناه ثابت.',
    },
}
MONTHS = {2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو', 7: 'يوليو',
          8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'}
CLASS_MAP = {'هجوم': 'confirmed_effect_or_attack', 'قرصنة': 'piracy', 'سطو مسلح': 'armed_robbery',
             'نشاط مشبوه': 'suspicious_activity', 'حادث': 'unresolved_incident',
             'ملاحي': 'navigation_or_technical', 'تقني': 'navigation_or_technical'}
CONF_MAP = {'عالية': 'high', 'متوسطة': 'medium', 'منخفضة': 'low'}

def label(date_str):
    y, m, d = (int(x) for x in date_str.split('-'))
    return f'{d} {MONTHS.get(m, m)}'

def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

frozen = load_json(FROZEN)
records = list(frozen.get('events') or frozen.get('records') or [])
by_id = {r['event_id']: r for r in records}
max_seq = {}
for r in records:
    parts = r['event_id'].split('-')
    try:
        max_seq[r.get('date_start')] = max(max_seq.get(r.get('date_start'), 0), int(parts[3]))
    except Exception:
        pass

added, aliased, skipped = [], [], []
for f in sorted(DAILY.glob('*.json')):
    for ev in load_json(f):
        code = ev.get('code')
        if not code:
            skipped.append(f'{f.name}: سجل بلا رمز')
            continue
        if code in ALIASES:                                   # رمز موجود بأثر رجعي → يُثبت على سجله
            tid = ALIASES[code]['event_id']
            if tid in by_id:
                by_id[tid]['display_code'] = code
                by_id[tid].setdefault('code_note', ALIASES[code]['note'])
                aliased.append(f'{code} → {tid}')
            continue
        if any(r.get('display_code') == code for r in records):  # مدمج مسبقًا (لا تكرار)
            continue
        date = ev.get('date') or ev.get('date_start')
        max_seq[date] = max_seq.get(date, 0) + 1
        h = hashlib.sha256((code + ev.get('title', '')).encode()).hexdigest()[:8]
        rec = {
            'event_id': f'EV-{date}-{max_seq[date]:03d}-{h}',
            'display_code': code,
            'date_start': date,
            'date_label': label(date),
            'location': ev.get('area', ''),
            'classification': ev.get('class', ev.get('classification', '')),
            'evidence_status': CLASS_MAP.get(ev.get('class', ''), 'unresolved_incident'),
            'confidence_level': CONF_MAP.get(ev.get('confidence', ''), 'medium'),
            'confidence': ev.get('confidence', ''),
            'description': ev.get('title', ''),
            'operational_effect': ev.get('effect', ''),
            'sources': [ev.get('source', '')] if ev.get('source') else [],
            'source_count': 1 if ev.get('source') else 0,
            'deduplication_note': 'مُدمج من ملف اليوم التراكمي — لا تكرار مع سجلات سابقة',
            'report_sections': ['الوقائع الجديدة'],
            'merged_from': f.name,
            'merged_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        records.append(rec)
        by_id[rec['event_id']] = rec
        added.append(f"{code} → {rec['event_id']}")

records.sort(key=lambda r: (r.get('date_start') or '', r.get('event_id') or ''))
dates = [r.get('date_start') for r in records if r.get('date_start')]
master = dict(frozen)
master['events'] = records
master['records'] = records
master['period_end'] = max(dates)
master['document_id'] = 'marine-events-ledger-master'
master['title'] = f"دفتر الأحداث التراكمي — من {master.get('period_start')} إلى {master.get('period_end')}"
master['merge_log'] = {'merged_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       'frozen_source': FROZEN.name, 'records_total': len(records),
                       'added': added, 'aliased': aliased, 'skipped': skipped}
MASTER.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding='utf-8')

codes = {r['display_code']: {'event_id': r['event_id'], 'date_start': r.get('date_start'),
                             'title': r.get('description', '')[:90]}
         for r in records if r.get('display_code')}
unmapped = sorted(set(ALIASES) - set(codes) - {k for k, v in ALIASES.items() if v['event_id'] in by_id})
code_map = {'generated_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'master': str(MASTER.relative_to(B)), 'records_total': len(records),
            'codes': codes, 'aliases': ALIASES, 'unmapped': unmapped,
            'rule': 'الرمز يُمنح مرة واحدة، ومعناه ثابت، ويُسجَّل في هذه الخريطة عند أول ظهور؛ ويُدمج ملف اليوم في الدفتر كل صباح.'}
CODEMAP.write_text(json.dumps(code_map, ensure_ascii=False, indent=2), encoding='utf-8')

print(f"  ✔ الدفتر الجامع: {MASTER.relative_to(B)} — {len(records)} سجلًا (نطاق {master['period_start']} → {master['period_end']})")
print(f"  ✔ سجلات مضافة: {len(added)}" + (f" — {added}" if added else ''))
print(f"  ✔ رموز مثبّتة بأثر رجعي: {len(aliased)}" + (f" — {aliased}" if aliased else ''))
print(f"  ✔ خريطة الرموز: {CODEMAP.relative_to(B)} — {len(codes)} رمزًا · غير مُسنَد: {unmapped or 'لا شيء'}")
print(f"  · توزيع أكتوبر: {dict(Counter(r['date_start'] for r in records if r['date_start'].startswith('2026-10')))}")