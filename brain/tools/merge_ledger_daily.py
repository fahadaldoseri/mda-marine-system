#!/usr/bin/env python3
"""دمج ملفات اليوم في الدفتر التراكمي + بناء خريطة رموز الأحداث.

المشكلة التي يحلّها (مكتشفة 13 أكتوبر 2026): التقرير اليومي يكتب ملفًا في
`cumulative-2026/daily/<التاريخ>.json`، لكن **لا شيء يدمجه** في الدفتر التراكمي،
ولا توجد خريطة تربط رموز التقرير (MN-...) بمعرّفات الدفتر (EV-...). النتيجة: انقطاع
الذاكرة التراكمية، وعدم إمكانية إسناد أي إشارة إلى حدث سابق.

إصلاحات 19 أكتوبر 2026 (بنود 10 و11 و12 و13 من التدقيق المستقل):
  · قائمة سجلات واحدة (`events`) بدل تخزين القائمة نفسها مرتين.
  · إعادة بناء الأقسام الرأسية القابلة للحساب من السجلات، ووسم كل قسم تاريخي
    لا يُعاد بناؤه آليًا بـ`_state: point_in_time` و`_as_of` صريحين.
  · تمييز «المضاف في هذه الجولة» عن «إجمالي المضاف منذ التجميد».
  · تسجيل حالة الدمج داخل الدفتر ليقرأها بيان الخط (العلامة) ولا يدّعي نجاحًا بلا دمج.

الاستخدام: python3 tools/merge_ledger_daily.py
المخرجات: cumulative-2026/event-ledger-master.json + appendices/event-code-map.json
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
import datetime
import hashlib
import json
from collections import Counter
from pathlib import Path

B = Path(f'{BRAIN}')
FROZEN = B / 'cumulative-2026' / 'event-ledger-sectioned-2026-02-28-to-2026-10-11.json'
MASTER = B / 'cumulative-2026' / 'event-ledger-master.json'
CODEMAP = B / 'appendices' / 'event-code-map.json'
SOURCES_MANIFEST = B / 'appendices' / 'sources-manifest.json'
DAILY = B / 'cumulative-2026' / 'daily'
DAILY_FILES = sorted(DAILY.glob('*.json'))
DAILY_FILE_NAMES = {f.name for f in DAILY_FILES}
# تاريخ الجولة هو أحدث ملف يومي متاح؛ لا يُقرأ من نطاق عام أو من متغير غير معرّف.
DATE = max((f.stem for f in DAILY_FILES), default='')

# الرموز المُسنَدة لوقائع سابقة بأثر رجعي في إصدار 13 أكتوبر — تُربط صراحةً بمعرّفات الدفتر
ALIASES = {
    'MN-2026-10-11-02': {
        'event_id': 'EV-2026-10-11-148-5ced58be',
        'note': 'نفس الواقعة: إصابة ناقلة بمسيّرة قرب مرسى صحار (UKMTO #165) — رُمِّزت بأثر رجعي في إصدار 13 أكتوبر.',
    },
    'MN-2026-10-04-01': {
        'event_id': 'EV-2026-10-04-141-90fecee1',
        'note': 'تنازع رموز: إصدار 12 أكتوبر استخدم الرمز نفسه بمعنى «تراجع الحركة إلى 4 عمليات عبور»، وإصدار 13 أكتوبر بمعنى «إصابة ناقلة بلغم في المضيق». الرمز يُمنح مرة واحدة ومعناه ثابت.',
    },
}
MONTHS = {2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو', 7: 'يوليو',
          8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'}
CLASS_MAP = {'هجوم': 'confirmed_effect_or_attack', 'قرصنة': 'piracy', 'سطو مسلح': 'armed_robbery',
             'نشاط مشبوه': 'suspicious_activity', 'حادث': 'unresolved_incident',
             'ملاحي': 'navigation_or_technical', 'تقني': 'navigation_or_technical'}
CONF_MAP = {'عالية': 'high', 'متوسطة': 'medium', 'منخفضة': 'low'}

# أقسام تاريخية نصّية: لا تُعاد بناؤها آليًا من السجلات، فتُوسَم بتاريخها بدل أن تبدو حديثة
POINT_IN_TIME_AS_OF = {
    'imo_summary': '2026-10-09',
    'numeric_indicators': '2026-10-11',
    'threat_assessment': '2026-10-11',
    'geographic_summary': '2026-10-11',
    'sections': '2026-10-11',
}


def label(date_str):
    y, m, d = (int(x) for x in date_str.split('-'))
    return f'{d} {MONTHS.get(m, m)}'


def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


frozen = load_json(FROZEN)
# سجل الجولة السابقة: أساس حساب «ما تغيّر في هذه الجولة» (بند 12 — لا خلط بين المضاف اليومي والإجمالي)
prev_master = load_json(MASTER) if MASTER.exists() else {}
prev_codes = {r.get('display_code') for r in (prev_master.get('events') or []) if r.get('display_code')}
prev_merged_utc = (prev_master.get('merge_log') or {}).get('merged_utc', '')
# قائمة سجلات واحدة: `events` — المفتاح المكرر `records` أُزيل (بند 10)
records = list(frozen.get('events') or frozen.get('records') or [])
# ── عطل ك-75: الدمج كان تراكميًا لا استبداليًا، فكل جولة تُضيف سجلات اليوم نفسه
#    برموز جديدة فيتضخم الدفتر وتكسر العدّادات. القاعدة: الدمج استبدال بالتاريخ
#    واسم الملف اليومي معًا — يُزال ما جاء منه ثم يُعاد إدراجه مرة واحدة.
_before = len(records)
_kept, _removed = [], 0
for _r in records:
    same_file = (_r.get('merged_from') or '') in DAILY_FILE_NAMES
    same_date = bool(DATE) and str(_r.get('date_start') or '') == DATE
    if same_file or same_date:
        _removed += 1
    else:
        _kept.append(_r)
if _removed:
    print(f"  · استبدال: أُزيل {_removed} سجلًا سابقًا لنفس التاريخ قبل إعادة الإدراج")
records = _kept
by_id = {r['event_id']: r for r in records}
max_seq = {}
for r in records:
    parts = r['event_id'].split('-')
    try:
        max_seq[r.get('date_start')] = max(max_seq.get(r.get('date_start'), 0), int(parts[3]))
    except Exception:
        pass

added, aliased, skipped, source_files = [], [], [], []
for f in DAILY_FILES:
    file_added = 0
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
            'report_sections': ['سجل الأحداث'],
            'merged_from': f.name,
            'merged_utc': (by_id.get(locals().get('rec', {}).get('event_id') or '', {}).get('merged_utc') or utcnow()),
        }
        records.append(rec)
        by_id[rec['event_id']] = rec
        added.append(f"{code} → {rec['event_id']}")
        file_added += 1
    if file_added:
        source_files = [sf for sf in source_files if (sf or {}).get('file') != f.name]
        source_files.append({'file': f.name, 'added': file_added})

records.sort(key=lambda r: (r.get('date_start') or '', r.get('event_id') or ''))
dates = [r.get('date_start') for r in records if r.get('date_start')]

# تعارض رموز: رمز واحد لسجلين مختلفين = مخالفة تُسجَّل (الرمز يُمنح مرة واحدة ومعناه ثابت)
code_counts = Counter(r['display_code'] for r in records if r.get('display_code'))
code_conflicts = [{'code': c, 'events': [r['event_id'] for r in records if r.get('display_code') == c]}
                  for c, n in sorted(code_counts.items()) if n > 1]

master = dict(frozen)
master['events'] = records
master.pop('records', None)
master['period_end'] = max(dates)
master['document_id'] = 'marine-events-ledger-master'
master['title'] = f"دفتر الأحداث التراكمي — من {master.get('period_start')} إلى {master.get('period_end')}"
master['schema_note'] = 'قائمة السجلات الوحيدة هي `events`. أُزيل المفتاح المكرر `records` في 19 أكتوبر 2026 (بند 10 من التدقيق المستقل).'

# ── إعادة بناء الأقسام الرأسية القابلة للحساب (بند 11) ──────────────────────────
counts = dict(master.get('counts') or {})
counts.update({
    'total_records': len(records),
    'by_month': dict(sorted(Counter(r.get('date_start', '')[:7] for r in records if r.get('date_start')).items())),
    'by_evidence_status': dict(sorted(Counter(r.get('evidence_status', 'غير مصنّف') for r in records).items())),
    'by_classification': dict(sorted(Counter(r.get('classification') or 'غير مصنّف' for r in records).items())),
    'by_area_top10': dict(Counter(r.get('location') or 'غير محدّد' for r in records).most_common(10)),
    '_rebuilt_utc': utcnow(),
})
master['counts'] = counts

src_audit = dict(master.get('source_audit') or {})
prev_approved = src_audit.get('approved_source_count')
try:
    approved = int(load_json(SOURCES_MANIFEST)['approved_source_count'])
except (OSError, json.JSONDecodeError, KeyError, ValueError):
    approved = prev_approved or 0
src_audit['approved_source_count'] = approved
src_audit['approved_source_count_source'] = 'appendices/sources-manifest.json (مصدر واحد للحقيقة)'
if prev_approved and prev_approved != approved:
    src_audit['approved_source_count_note'] = f'كان {prev_approved} وصار {approved} بموجب ملف المصدر الواحد.'
src_audit['unique_source_strings_in_ledger'] = len({s for r in records for s in (r.get('sources') or []) if s})
src_audit['_rebuilt_utc'] = utcnow()
master['source_audit'] = src_audit

rebuilt_keys, point_in_time = ['counts', 'source_audit'], []
for key, as_of in POINT_IN_TIME_AS_OF.items():
    block = master.get(key)
    if isinstance(block, dict):
        block['_state'] = 'point_in_time'
        block['_as_of'] = as_of
        block['_rebuild_note'] = ('نصّ تاريخي لا يُعاد بناؤه آليًا من السجلات — '
                                  'يُحدَّث يدويًا عند كل مراجعة، ويبقى وسمه صريحًا حتى ذلك الحين.')
        master[key] = block
        point_in_time.append({'key': key, 'as_of': as_of})
master['vertical_rebuild'] = {
    'rebuilt_utc': utcnow(),
    'rebuilt_keys': rebuilt_keys,
    'point_in_time_keys': point_in_time,
    'rule': 'كل قسم رأسي إمّا مُعاد بناؤه من السجلات، أو موسوم بتاريخه (`_state: point_in_time` + `_as_of`). لا قسم يبدو حديثًا بلا سند.',
}

# ── حالة الدمج: مضاف هذه الجولة مقابل إجمالي المضاف (بند 12) ─────────────────────
merged_from_frozen = [r for r in records if r.get('merged_from')]
current_codes = {r['display_code'] for r in records if r.get('display_code')}
added_this_run = sorted(current_codes - prev_codes)
removed_this_run = sorted(prev_codes - current_codes)
master['merge_log'] = {
    'merged_utc': utcnow(),
    'frozen_source': FROZEN.name,
    'records_total': len(records),
    'records_from_daily_files': len(merged_from_frozen),
    'added_this_run': added_this_run,
    'added_this_run_count': len(added_this_run),
    'removed_this_run': removed_this_run,
    'added_this_run_files': source_files,
    'added_total_since_frozen': len(merged_from_frozen),
    'added_total_since_frozen_codes': len(current_codes),
    'previous_merged_utc': prev_merged_utc,
    'aliased': aliased,
    'skipped': skipped,
    'code_conflicts': code_conflicts,
    'note': 'added_this_run = ما أضافته هذه الجولة فقط · added_total_since_frozen = كل ما دخل الدفتر بعد التجميد.',
}
MASTER.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding='utf-8')

codes = {r['display_code']: {'event_id': r['event_id'], 'date_start': r.get('date_start'),
                             'title': r.get('description', '')[:90]}
         for r in records if r.get('display_code')}
unmapped = sorted(set(ALIASES) - set(codes) - {k for k, v in ALIASES.items() if v['event_id'] in by_id})
code_map = {'generated_utc': utcnow(),
            'master': str(MASTER.relative_to(B)), 'records_total': len(records),
            'codes': codes, 'aliases': ALIASES, 'unmapped': unmapped,
            'code_conflicts': code_conflicts,
            'rule': 'الرمز يُمنح مرة واحدة، ومعناه ثابت، ويُسجَّل في هذه الخريطة عند أول ظهور؛ ويُدمج ملف اليوم في الدفتر كل صباح.'}
CODEMAP.write_text(json.dumps(code_map, ensure_ascii=False, indent=2), encoding='utf-8')

print(f"  ✔ الدفتر الجامع: {MASTER.relative_to(B)} — {len(records)} سجلًا (نطاق {master['period_start']} → {master['period_end']})")
print(f"  ✔ قائمة سجلات واحدة (`events`) — أُزيل المفتاح المكرر `records`")
print(f"  ✔ مضاف هذه الجولة: {len(added_this_run)}" + (f" — {added_this_run}" if added_this_run else ' (لا جديد)'))
print(f"  ✔ إجمالي المضاف منذ التجميد: {len(merged_from_frozen)} سجلًا ({len(current_codes)} رمزًا في الخريطة)")
if removed_this_run:
    print(f"  ⚠ مسحوب في هذه الجولة: {removed_this_run}")
print(f"  ✔ رموز مثبّتة بأثر رجعي: {len(aliased)}" + (f" — {aliased}" if aliased else ''))
if code_conflicts:
    print(f"   ✘ تعارض رموز: {code_conflicts}")
print(f"  ✔ أقسام مُعاد بناؤها: {', '.join(rebuilt_keys)} · لقطات تاريخية موسومة: {', '.join(k['key'] for k in point_in_time)}")
print(f"  ✔ خريطة الرموز: {CODEMAP.relative_to(B)} — {len(codes)} رمزًا · غير مُسنَد: {unmapped or 'لا شيء'}")
print(f"  · توزيع أكتوبر: {dict(Counter(r['date_start'] for r in records if r['date_start'].startswith('2026-10')))}")
