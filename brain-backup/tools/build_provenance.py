#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يبني سجل المصدرية وسجل التناقضات من الأصول المحفوظة في archive/originals/<اليوم>/manifest.json
ويخرج: audit/provenance-<case>.json/.md و audit/discrepancies-<case>.json/.md
البصمات والأحجام تُقرأ من البيان لا تُكتب يدويًا.
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]
BRAIN = _Path(_os.environ.get("BRAIN_DIR") or _ROOT)
import datetime as dt
import hashlib
import json
from pathlib import Path

DAY = '2026-10-16'
CASE = '2026-10-13-14'
BASE = Path(f'{BRAIN}')
ARCH = BASE / 'archive/originals' / DAY
OUT = BASE / 'audit'
OUT.mkdir(exist_ok=True)

# ---------- المصادر (تُربط بالأصول المحفوظة بالمعرّف) ----------
SOURCES = [
    dict(sid='S-01', art='mpa-release-pdf', pub='هيئة الموانئ والملاحة بسنغافورة (MPA)',
         title='Two Singapore-Registered Vessels Struck in Strait of Hormuz — MEDIA RELEASE',
         kind='بيان رسمي (PDF)', grade='A/1', method='تنزيل مباشر من نطاق MPA الرسمي',
         quotes=['two Singapore-registered container vessels, GFS PRIDE and GFS GISELLE, were reportedly struck by unknown projectiles while transiting the Strait of Hormuz on 13 and 14 October 2026 (Singapore Time), respectively.',
                 'GFS PRIDE sustained damage and a fire on board, and has since sunk. All 21 crew members were safely evacuated. No injuries have been reported.',
                 'GFS GISELLE sustained hull damage and has since arrived under its own propulsion at a safe anchorage. All 22 crew members are safe, with no injuries reported.',
                 'There are no Singaporeans on board both vessels.'],
         use='أساس الواقعة: الهوية، العلم، الطواقم، الغرق، الأضرار'),
    dict(sid='S-02', art='mpa-release-page', pub='هيئة الموانئ والملاحة بسنغافورة (MPA)',
         title='صفحة البيان على الموقع الرسمي', kind='بيان رسمي (HTML)', grade='A/1',
         method='تنزيل مباشر', quotes=['النص نفسه المنشور في ملف PDF'],
         use='مطابقة نص البيان المنشور مع ملفه الأصلي'),
    dict(sid='S-03', art='navarea9-373-26', pub='NAVAREA IX — المكتب الهيدروغرافي الباكستاني',
         title='NAVAREA IX 373/26 — STRAIT OF HORMUZ — SHIP SUNK',
         kind='تحذير ملاحي رسمي', grade='A/1', method='تنزيل ملف التحذير الرسمي',
         quotes=["COMMERCIAL VESSEL 'GFS PRIDE' REPORTED SUNK WITH FLOATING CONTAINERS IN 26-16.8N 056-08.6E APPROXIMATELY 4NM NORTHWEST RAS SHAYKH MASUD",
                 'CANCEL NAVAREA IX 371/26'],
         use='موضع الغرق وزمن التحذير (14 OCT 1045 UTC) وإلغاء التحذير السابق'),
    dict(sid='S-04', art='navarea9-370-26', pub='NAVAREA IX — المكتب الهيدروغرافي الباكستاني',
         title='NAVAREA IX 370/26 — GULF OF OMAN',
         kind='تحذير ملاحي رسمي', grade='A/1', method='تنزيل ملف التحذير الرسمي',
         quotes=['MV CAPE DAO EARLIER INVOLVED IN A SECURITY INCIDENT ON 23 SEP 26 REPORTED SINKING IN 24-44.2N 056-47.7E'],
         use='موضع غرق CAPE DAO وربط 23 سبتمبر بالغرق'),
    dict(sid='S-05', art='navarea9-372-26', pub='NAVAREA IX — المكتب الهيدروغرافي الباكستاني',
         title='NAVAREA IX 372/26 — GULF OF OMAN',
         kind='تحذير ملاحي رسمي', grade='A/1', method='تنزيل ملف التحذير الرسمي',
         quotes=['OIL TANKER (PETRO DOLPHIN) REPORTED INVOLVED IN SECURITY INCIDENT ON 12 OCT 26 DRIFTING IN 24-30.36N 057-27.11E APPROXIMATELY 50 NM NORTHEAST SUHAR PORT'],
         use='حالة PETRO DOLPHIN وموضعها'),
    dict(sid='S-06', art='navarea9-warnings', pub='NAVAREA IX — المكتب الهيدروغرافي الباكستاني',
         title='جدول التحذيرات السارية (NAVAREA IX WARNINGS)',
         kind='فهرس رسمي', grade='A/1', method='تنزيل مباشر',
         quotes=['372/26 GULF OF OMAN 140750 UTC OCT 26 SECURITY INCIDENT',
                 '373/26 STRAIT OF HORMUZ 141045 UTC OCT 2026 SHIP SUNK',
                 '370/26 GULF OF OMAN 131520 UTC OCT 2026 SECURITY INCIDENT'],
         use='إثبات زمن إصدار كل تحذير وترتيبه'),
    dict(sid='S-07', art='navarea9-364-26', pub='NAVAREA IX — المكتب الهيدروغرافي الباكستاني',
         title='NAVAREA IX 364/26 — IN-FORCE LIST', kind='تحذير ملاحي رسمي', grade='A/1',
         method='تنزيل ملف التحذير الرسمي', quotes=['قائمة التحذيرات السارية حتى 10 أكتوبر 2026'],
         use='حالة التحذيرات السارية قبل نافذة الحادث'),
    dict(sid='S-08', art='ukmto-recent-rendered', pub='UKMTO (هيئة التجارة البحرية البريطانية)',
         title='Recent Incidents — النص المعروض للبلاغات #162–#173',
         kind='بلاغات رسمية (استخراج من صفحة حيّة)', grade='A/2',
         method='عرض الصفحة في متصفح حقيقي ثم استخراج النص المعروض (الصفحة تُبنى بجافاسكربت)',
         quotes=['#170 — 13 October 2026 — container ship struck by an unknown projectile within the Strait of Hormuz',
                 '#171 — 13 October 2026 — tanker struck by an unknown projectile within the Strait of Hormuz',
                 '#172 — 14 October 2026 — 50,000 tonne Container ship struck inbound, minor damage, continued',
                 '#173 — 14 October 2026 — 19,000 tonne Container ship struck outbound, minor damage, continued'],
         use='تسلسل البلاغات الرسمية ونوع السفن؛ وربطها بواقعتي GFS'),
    dict(sid='S-09', art='ukmto-recent', pub='UKMTO', title='Recent Incidents — نسخة HTML الخام',
         kind='صفحة غير محتوية على البيانات', grade='A/2', method='تنزيل مباشر',
         quotes=['الصفحة تُبنى بجافاسكربت: النسخة الخام لا تحوي أي بلاغ'],
         use='إثبات أن البلاغات لا تُلتقط إلا بالعرض الحيّ — قيد على الأرشفة الآلية'),
    dict(sid='S-10', art='ukmto-json', pub='UKMTO', title='بيانات الصفحة (Next.js data)',
         kind='هيكل تقني', grade='A/2', method='تنزيل مباشر',
         quotes=['لا يحوي البلاغات؛ لا نقطة بيانات عامة مكشوفة'],
         use='قيد استطلاعي: لا يمكن سحب البلاغات آليًا بلا متصفح'),
    dict(sid='S-11', art='jmic', pub='JMIC (Combined Maritime Forces)',
         title='صفحة JMIC', kind='صفحة جهة شريكة', grade='B/2', method='تنزيل مباشر',
         quotes=['لا نص حادث مطابق في هذه الصفحة'],
         use='فحص جهة شريكة — لا يسند شيئًا في هذه الواقعة'),
    dict(sid='S-12', art='imo-whatsnew', pub='المنظمة البحرية الدولية (IMO)',
         title="IMO — What's New", kind='صفحة رسمية', grade='A/2', method='تنزيل مباشر',
         quotes=['لا قيد مطابق للواقعتين في الصفحة الرئيسية'],
         use='فحص رسمي — يستكمل لاحقًا من سجل GISIS'),
    dict(sid='S-13', art='navarea9-mirror', pub='Sea Lagom (طرف ثالث)',
         title='NAVAREA IX mirror', kind='مرآة غير رسمية', grade='C/3', method='تنزيل مباشر',
         quotes=['يُستخدم للمطابقة فقط'],
         use='مطابقة النصوص؛ لا يُعتمد للتحقق'),
    dict(sid='S-14', art='navarea9-pak', pub='NAVAREA IX — المكتب الهيدروغرافي الباكستاني',
         title='صفحة NAVAREA IX الرئيسية', kind='صفحة خدمة رسمية', grade='A/1',
         method='تنزيل مباشر', quotes=['فهرس التحذيرات والملاحة'],
         use='الوصول إلى أصل التحذيرات'),
]

# ---------- الوقائع المسندة ----------
CLAIMS = [
    dict(cid='C-01', claim='إصابة «GFS PRIDE» و«GFS GISELLE» بمقذوفات غير محددة المصدر أثناء عبور مضيق هرمز',
         srcs=['S-01', 'S-02'], status='مؤكد رسميًا'),
    dict(cid='C-02', claim='«GFS PRIDE» غرقت بعد ضرر وحريق، وأُجلي طاقمها وعدده 21 بلا إصابات',
         srcs=['S-01'], status='مؤكد رسميًا'),
    dict(cid='C-03', claim='«GFS GISELLE» تضرر بدنها ووصلت بقوة دفعها إلى مرسى آمن، وطاقمها 22 بلا إصابات',
         srcs=['S-01'], status='مؤكد رسميًا'),
    dict(cid='C-04', claim='موضع غرق «GFS PRIDE»: 26-16.8N 056-08.6E، نحو 4 أميال بحرية شمال غرب رأس الشيخ مسعود، وتحذير 14 أكتوبر 1045 UTC',
         srcs=['S-03', 'S-06'], status='مؤكد رسميًا'),
    dict(cid='C-05', claim='«CAPE DAO» غرقت في 24-44.2N 056-47.7E بخليج عُمان بعد إصابة أمنية في 23 سبتمبر',
         srcs=['S-04', 'S-06'], status='مؤكد رسميًا'),
    dict(cid='C-06', claim='«PETRO DOLPHIN» (ناقلة نفط) انجرافها في 24-30.36N 057-27.11E نحو 50 ميلًا شمال شرق ميناء صحار بعد حادثة 12 أكتوبر',
         srcs=['S-05', 'S-06'], status='مؤكد رسميًا'),
    dict(cid='C-07', claim='بلاغ UKMTO #170 (13 أكتوبر): إصابة سفينة حاويات بمقذوف غير معروف في المضيق',
         srcs=['S-08'], status='رسمي — بلا وقت حادث (TBC)'),
    dict(cid='C-08', claim='بلاغ UKMTO #171 (13 أكتوبر): إصابة ناقلة بمقذوف غير معروف في المضيق',
         srcs=['S-08'], status='رسمي — بلا اسم سفينة'),
    dict(cid='C-09', claim='بلاغا UKMTO #172/#173 (14 أكتوبر): سفينتا حاويات (50,000 طن داخلة و19,000 طن خارجة) بضرر طفيف وواصلتا العبور',
         srcs=['S-08'], status='رسمي — بلا اسم سفينة'),
    dict(cid='C-10', claim='تسلسل هجمات مركّز في المضيق وخليج عُمان خلال 10–14 أكتوبر (بلاغات #162 إلى #173)',
         srcs=['S-08'], status='رسمي — يلزم تحويله إلى معدل كمّي'),
]

# ---------- التناقضات ----------
DISCREPANCIES = [
    dict(did='D-01', topic='أساس التاريخ: توقيت سنغافورة مقابل UTC',
         a='بيان MPA: الإصابة في 13 و14 أكتوبر (Singapore Time)',
         b='تقريرنا: إصابة PRIDE في 13 أكتوبر 16:40 UTC',
         analysis='توقيت سنغافورة = UTC+8؛ فـ«13 أكتوبر بتوقيت سنغافورة» يقع بين 12 أكتوبر 16:00 UTC و13 أكتوبر 16:00 UTC. لا يمكن إثبات 16:40 UTC من الأصل الرسمي.',
         status='محلول جزئيًا (فارق التوقيت) · الوقت الدقيق غير مثبت',
         action='طلب زمن الحادث من UKMTO #170 أو استكماله من MPA'),
    dict(did='D-02', topic='هوية بلاغَي UKMTO #172/#173 مقابل سفينتي GFS',
         a='#172/#173: سفينتا حاويات بضرر طفيف «واصلتا العبور»',
         b='بيان MPA: «GFS GISELLE» تضرر بدنها ووصلت مرسى آمنًا بقوة دفعها',
         analysis='يمكن أن تُطابق GISELLE أحد البلاغين، ويبقى البلاغ الثاني لسفينة ثالثة غير مسمّاة. أما «GFS PRIDE» فغرقت ولا يطابق وصف «واصلت العبور».',
         status='غير محسوم — خطر إسناد مزدوج',
         action='عدم ربط #172/#173 آليًا برموز واقعتي GFS قبل تأكيد UKMTO أو MPA'),
    dict(did='D-03', topic='علم «GFS GISELLE»',
         a='بيان MPA: سفينتان مسجلتان في سنغافورة (تشمل GISELLE)',
         b='جدول هوية السفن في موقعنا: علم «غير معلنة» لـGISELLE',
         analysis='الأصل الرسمي A/1 يحسم العلم: سنغافورة.',
         status='محلول — يُصحّح في الجدول'),
    dict(did='D-04', topic='زمن غرق «GFS PRIDE»',
         a='NAVAREA IX 373/26 صدر 14 أكتوبر 1045 UTC بعد الغرق',
         b='تقريرنا: الغرق 14 أكتوبر مع إصابة 13 أكتوبر 16:40 UTC',
         analysis='لا وثيقة رسمية لدينا تثبت ساعة الغرق ولا ساعة الإصابة.',
         status='غير محسوم',
         action='إضافة «زمن غير مثبت» في التقرير بدل الساعة'),
    dict(did='D-05', topic='موقع إصابة «GFS GISELLE»',
         a='UKMTO #172/#173: داخل مضيق هرمز',
         b='تقريرنا: قبالة ساحل عُمان (ميل واحد / ستة أميال)',
         analysis='اختلاف جغرافي جوهري؛ الأصلان لا يسمّيان السفينة، فلا يمكن الجزم.',
         status='غير محسوم',
         action='طلب موضع من UKMTO أو سلطة العلم'),
    dict(did='D-06', topic='وحدة قياس الحمولة',
         a='UKMTO: 19,000 طن و50,000 طن',
         b='جدولنا: 2,824 و4,350 وحدة مكافئة (TEU) وأبعاد السفينتين',
         analysis='لا تتكافأ الوحدات (حمولة ساكنة/إزاحة مقابل TEU)؛ المساواة بينهما خطأ منهجي.',
         status='تنبيه منهجي',
         action='إضافة وحدة القياس ومرجعها عند كل رقم حمولة'),
    dict(did='D-07', topic='حالة طاقم «PETRO DOLPHIN»',
         a='NAVAREA IX 372/26: انجراف فقط، بلا ذكر حالة الطاقم',
         b='دفتر أحداثنا: «مفقودان» في مرسى صحار',
         analysis='الأصل الرسمي لا يسند فقدان أفراد.',
         status='غير محسوم',
         action='استكمال من IMO GISIS أو UKMTO'),
    dict(did='D-08', topic='بلاغ UKMTO #171 (ناقلة) مقابل «AL SAADIYAT»',
         a='#171: ناقلة أُصيبت في المضيق يوم 13 أكتوبر',
         b='تقريرنا: «AL SAADIYAT» أُصيبت أثناء عبور داخل المضيق في 13 أكتوبر',
         analysis='التوافق الزمني والنوعي قوي، لكن UKMTO لا يسمّي السفينة.',
         status='مُرجَّح لا مؤكد',
         action='تسمية الربط «مُرجَّح» في التقرير'),
    dict(did='D-09', topic='تحذير NAVAREA IX 371/26 الملغى',
         a='373/26 يلغي 371/26 (تحذير 13 أكتوبر)',
         b='371/26 لم يعد منشورًا في جدول التحذيرات',
         analysis='فقدان أثر أصلي يوثّق الحالة قبل الغرق.',
         status='فجوة توثيق',
         action='طلب النسخة من الأرشيف أو من المكتب الهيدروغرافي'),
    dict(did='D-10', topic='خطر العدّ المزدوج للوقائع',
         a='تقريرنا سجّل «سفينة حاويات 50,000 طن» كواقعة مستقلة بلا اسم',
         b='بيان MPA يسمّي سفينتين فقط',
         analysis='قد يكون الرقم نفسه واقعة مسمّاة؛ العدّ المزدوج يضخّم المؤشرات.',
         status='خطر قائم',
         action='تسوية كل بند بلا اسم مع البلاغ الرسمي قبل أي عدّ'),
]

REQUIREMENTS = [
    'زمن حادث UKMTO #170 و#171 بالدقيقة (UTC) — طلب من UKMTO.',
    'تسمية السفن في بلاغَي #172/#173 — طلب من UKMTO أو MPA.',
    'قيد الحادثة الرسمي في IMO GISIS للواقعتين (رقم القيد وتاريخه).',
    'نسخة NAVAREA IX 371/26 (الملغى) من الأرشيف الهيدروغرافي.',
    'موضع إصابة «GFS GISELLE» الدقيق (باب المندب؟ لا — المضيق أو ساحل عُمان).',
    'بيان الحمولة الرسمي لسفينتي GFS (مالك الحمولة/المؤمّن).',
    'حالة طاقم «PETRO DOLPHIN» ومصير المفقودين من مصدر رسمي.',
]


def load_manifest():
    recs = json.loads((ARCH / 'manifest.json').read_text(encoding='utf-8'))
    by_id = {}
    for r in recs:
        if r.get('status') == 'saved':
            by_id[r['id']] = r
    # بصمة ملف النص المستخرج من UKMTO (أصل مستخرج لا ملف منشور)
    p = ARCH / 'ukmto-recent-rendered.txt'
    if p.exists():
        b = p.read_bytes()
        by_id['ukmto-recent-rendered'] = {'url': 'https://www.ukmto.org/recent-incidents',
                                          'file': p.name, 'bytes': len(b),
                                          'sha256': hashlib.sha256(b).hexdigest(),
                                          'retrieved_utc': '2026-10-16T00:31:00Z',
                                          'content_type': 'text/plain'}
    return by_id


def md_table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)]
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out)


def main():
    man = load_manifest()
    src_rows, src_json = [], []
    for s in SOURCES:
        a = man.get(s['art'], {})
        row = dict(sid=s['sid'], publisher=s['pub'], title=s['title'], kind=s['kind'],
                   grade=s['grade'], method=s['method'], url=a.get('url', '—'),
                   retrieved_utc=a.get('retrieved_utc', '—'),
                   sha256=a.get('sha256', '—'), bytes=a.get('bytes', 0),
                   local_file=str(ARCH / a.get('file', '—')) if a.get('file') else '—',
                   quotes=s['quotes'], used_for=s['use'])
        src_json.append(row)
        src_rows.append([s['sid'], s['pub'], s['kind'], s['grade'],
                         (a.get('sha256', '—') or '—')[:16], a.get('bytes', 0), s['use']])
    claims_json = [dict(cid=c['cid'], claim=c['claim'], sources=c['srcs'], status=c['status'])
                   for c in CLAIMS]
    disc_json = [dict(**d) for d in DISCREPANCIES]

    prov = dict(case=CASE, generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                archive_day=DAY, sources=src_json, claims=claims_json,
                collection_requirements=REQUIREMENTS)
    (OUT / f'provenance-{CASE}.json').write_text(json.dumps(prov, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / f'discrepancies-{CASE}.json').write_text(json.dumps(disc_json, ensure_ascii=False, indent=1), encoding='utf-8')

    md = [f'# سجل المصدرية — واقعتا «GFS PRIDE» و«GFS GISELLE» (13–14 أكتوبر 2026)', '',
          f'**يوم الأرشفة:** {DAY} · **عدد الأصول المحفوظة:** {len(src_json)} · **تاريخ التوليد (UTC):** {prov["generated_utc"]}',
          '', 'كل صف يحمل بصمة SHA-256 ووقت التقاط؛ الأصل محفوظ محليًا في `archive/originals/'
          + DAY + '/`، ويمكن لأي طرف ثالث إعادة التنزيل ومطابقة البصمة.', '',
          '## 1) المصادر', '', md_table(
              ['المعرّف', 'الجهة', 'النوع', 'التصنيف', 'SHA-256', 'بايت', 'ما استُخدم منه'],
              src_rows), '', '## 2) الوقائع المسندة', '',
          md_table(['المعرّف', 'الواقعة', 'المصادر', 'الحالة'],
                   [[c['cid'], c['claim'], ' · '.join(c['srcs']), c['status']] for c in CLAIMS]),
          '', '## 3) متطلبات الاستطلاع', '']
    md += [f'{i}. {r}' for i, r in enumerate(REQUIREMENTS, 1)]
    (OUT / f'provenance-{CASE}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')

    md2 = [f'# سجل التناقضات — واقعتا «GFS PRIDE» و«GFS GISELLE» (13–14 أكتوبر 2026)', '',
           f'**عدد البنود:** {len(disc_json)} · **تاريخ التوليد (UTC):** {prov["generated_utc"]}', '',
           'سجل حيّ: كل بند يبقى مفتوحًا حتى يُحسم بأصل رسمي، ولا يُسقط منه شيء.', '',
           md_table(['#', 'الموضوع', 'الرواية (أ)', 'الرواية (ب)', 'التحليل', 'الحالة', 'الإجراء'],
                    [[d['did'], d['topic'], d['a'], d['b'], d['analysis'], d['status'], d.get('action', '—')]
                     for d in disc_json])]
    (OUT / f'discrepancies-{CASE}.md').write_text('\n'.join(md2) + '\n', encoding='utf-8')

    print(f'  سجل المصدرية: {len(src_json)} مصدرًا · {len(CLAIMS)} واقعة مسندة')
    print(f'  سجل التناقضات: {len(disc_json)} بندًا')
    print(f'  {OUT}/provenance-{CASE}.md')
    print(f'  {OUT}/discrepancies-{CASE}.md')


if __name__ == '__main__':
    main()