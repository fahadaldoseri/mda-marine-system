#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حاصد الألفاظ الجديدة — قاعدة دائمة تُنفَّذ قبل كل تسليم.

الغرض: كل إصدار يُفحص قبل التسليم (موقعًا أو PDF)، ويُسجَّل ما فيه من ألفاظ
ورموز تحتاج تعريفًا في مكتبة دائمة، لا في الذاكرة.

معيار الحصاد (حتمي، بلا تخمين):
  · رمز أو مصطلح أجنبي: رمز لاتيني في متن الإصدار أو قيم واجهته، غير معرَّف في
    وثائق النظام ولا في قواميس الإصدارات (تُستبعد روابط الويب).
  · عبارة مميّزة بلا تعريف: كل عبارة عربية تُبرز في المتن (**…**) ولا ترد في أي
    مكتبة مرجعية ولا في قاموس أي إصدار — أي أنها موضع احتمال لالتباس القارئ.

الخرج: appendices/libraries/new-terms-register.{json,md}
الحالة: «بانتظار مراجعة المالك» حتى تُدرَج أو تُستبعد بقرار.
"""
import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

B = Path(__file__).resolve().parents[1]
LIB = B / 'appendices' / 'libraries'
REG_JSON = LIB / 'new-terms-register.json'
REG_MD = LIB / 'new-terms-register.md'

LATIN_TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9.\-/]{1,14}')
BOLD = re.compile(r'\*\*(.+?)\*\*', re.S)
URL_SPAN = re.compile(r'https?://\S+')
ARABIC = re.compile(r'[\u0621-\u064A]')

STOP = set("""نافذة النافذة نوافذ فترات فترةالتي الذي الذين وهذا وهذه وكان وكانت وقد فقد لكن ولكن حيث بين بعد قبل
عند لدى خلال ضمن دون سوى إلا إذا كما أيضا أيضًا كذلك لذلك بينما حينما عندما أن إن بأن
هناك هنالك أكثر أقل جميع بعض كل معظم سائر بقية نحو حوالي قرابة مطلع منتصف نهاية بداية
يعد تعد يذكر تذكر يلاحظ تلاحظ يمكن سوف يتم تم جرى جرت ظل ظلت بقي بقيت ولا فإن وإن
العام العامة الخاص الخاصة الأخير الأخيرة الأول الأولى السابق السابقة المقبل الحالي
الجديد الجديدة المستمر المستمرة القائم القائمة الكامل الكاملة المذكور المذكورة
على إلى عن من في مع حتى منذ خلف أمام فوق تحت خلال عبر بلا عدم بدون فيها فيه منها منه
هذا هذه هؤلاء ذلك تلك التي والذي وهما وهم وهي وهو أنه أنها إليها إليه عليه عليها
تقرير التقرير اليومي الملاحة أمن الأوضاع الراهنة المنطقة مركز الوعي المجال البحري
بيانات مصادر المصادر موثوقية البند القسم الفقرة الجدول الخلاصة المؤشرات التوجيهات
""".split())

# كلمات تخصصية: وجودها في عبارة يعني أنها مصطلح مجال لا تسمية بنية.
MARKERS = set("""قائمة نظام مؤشر نمط فضاء سجل رمز تصنيف تأمين حطام إغلاق حظر مرسى
تأهب استهداف سطو قرصنة حصار عبور تكدس معايرة تحذير نشرة بلاغ إسناد احتمال ثقة
فرضية نقيض مصفوفة مسار خط سلامة تهديد خطر حماية دورية إنقاذ خفر سواحل ميناء رصيف
انجراف غرق جنوح اصطدام مقذوف لغم مسيّرة زورق قُطر سحب غاطسة طافية حاويات شحنة
""".split())

# كلمات إنجليزية عامة ليست رموزًا تخصصية.
EN_COMMON = {'press', 'releases', 'news', 'media', 'report', 'reports', 'page',
             'home', 'index', 'search', 'about', 'contact', 'login', 'sign',
             'read', 'more', 'view', 'site', 'html', 'www', 'http', 'https'}

KNOWN_DIRS = ['appendices', 'sections', 'watchlist', 'validators', 'tools']


def norm(text):
    """تطبيع عربي: بلا تشكيل ولا تطويل، والهمزات موحّدة."""
    text = re.sub(r'[\u064B-\u0652\u0640]', '', str(text))
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ى', 'ي')
    return re.sub(r'\s+', ' ', text).strip()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def library_terms():
    """كل ما هو معرَّف في مكتبات النظام وقواميس الإصدارات."""
    known = set()

    def add(value):
        if isinstance(value, str):
            known.add(norm(value))
        elif isinstance(value, (list, tuple, set)):
            for v in value:
                add(v)
        elif isinstance(value, dict):
            for k, v in value.items():
                add(k)
                add(v)

    for folder in KNOWN_DIRS:
        root = B / folder
        if not root.exists():
            continue
        for p in root.rglob('*'):
            if p.suffix.lower() not in ('.md', '.json', '.txt'):
                continue
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for m in BOLD.findall(text):
                for piece in re.split(r'[·،,؛:()/]', m):
                    add(piece)
            if p.suffix == '.json':
                add(read_json(p))
    for p in sorted((B / 'web' / 'meta').glob('2026-*.json')):
        add(read_json(p))
    return {t for t in known if t}


def known_latin(terms):
    known = set()
    for folder in KNOWN_DIRS:
        root = B / folder
        if not root.exists():
            continue
        for p in root.rglob('*'):
            if p.suffix.lower() not in ('.md', '.json', '.txt', '.py'):
                continue
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            known |= {t.upper() for t in LATIN_TOKEN.findall(text)}
    for p in sorted((B / 'web' / 'meta').glob('2026-*.json')):
        for key in ((read_json(p) or {}).get('glossary') or {}):
            known.add(str(key).upper())
    return known


def meta_values_only(raw):
    data = json.loads(raw) if raw.strip().startswith('{') else None
    if data is None:
        return raw
    out = []

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, str):
            out.append(node)

    walk(data)
    return '\n'.join(out)


def _prose_only(text):
    """بلا أسطر الجداول والعناوين: خلايا الجداول تسميات بنية لا مصطلحات."""
    keep = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|') or stripped.startswith('#'):
            continue
        keep.append(line)
    return '\n'.join(keep)


# كلمات تدل على جملة وصفية لا مصطلح: أفعال وروابط وحالات.
SENTENCE_WORDS = set("""صدر ورد لا بلا ولا لم لن غياب استمرار توسيع تحديث فرق محاولة إعلان
الرواية تصنيف مغلق مراجعة فرق في عدّ حطام طافية وغارقة غرق إصابة تضرر شرق غرب شمال
جنوب قرب بعد قبل خلال داخل خارج وفق حسب مقابل بشأن عن مع بين أيّ أي أن إن وقد وكان
قال قالت أعلن أعلنت وقع وقعت حدث حدثت يعد تعد يذكر تذكر بقي بقيت ظل ظلت""".split())


def _is_noise(piece):
    """جملة وصفية أو اسم سفينة أو عنوان واقعة — ليست مصطلحًا."""
    n = norm(piece)
    words = n.split()
    if len(words) > 3:
        return True
    if any(w in SENTENCE_WORDS for w in words):
        return True
    if re.search(r'«[^»]*[A-Za-z][^»]*»', piece):
        return True
    if re.search(r'MN-\d{4}', piece):
        return True
    if re.search(r'[A-Za-z]', piece):
        return True
    return False


def _split_bold(match):
    for piece in re.split(r'[·،,؛:()/]', match):
        piece = piece.strip(' .«»"\'')
        if not (4 <= len(piece) <= 48) or not ARABIC.search(piece):
            continue
        if any(ch.isdigit() for ch in piece) or '—' in piece:
            continue
        words = norm(piece).split()
        if len(words) < 2 or not any(w in MARKERS for w in words):
            continue
        if _is_noise(piece):
            continue
        yield piece


def _recurring_phrases():
    """عبارة تُبرز في ثلاثة إصدارات فأكثر = تسمية بنية، لا مصطلحًا جديدًا."""
    counter = Counter()
    for path in sorted((B / 'reports').glob('2026-*-sectioned.md')):
        text = _prose_only(path.read_text(encoding='utf-8', errors='ignore'))
        for match in BOLD.findall(text):
            for piece in _split_bold(match):
                counter[norm(piece)] += 1
    return {key for key, value in counter.items() if value >= 3}


def candidates(date):
    md = B / 'reports' / f'{date}-sectioned.md'
    meta = B / 'web' / 'meta' / f'{date}.json'
    if not md.exists() and not meta.exists():
        return None
    prose = md.read_text(encoding='utf-8', errors='ignore') if md.exists() else ''
    meta_text = meta_values_only(meta.read_text(encoding='utf-8', errors='ignore')) if meta.exists() else ''
    full = prose + '\n' + meta_text

    recurring = _recurring_phrases()
    phrases = []
    for match in BOLD.findall(_prose_only(prose)):
        for piece in _split_bold(match):
            if norm(piece) in recurring:
                continue
            phrases.append(piece)

    no_urls = URL_SPAN.sub(' ', prose + ' ' + meta_text)
    # اسم سفينة أو شركة أو رمز داخل علامات تنصيص: ليس رمزًا يحتاج تعريفًا.
    ship_ctx = re.compile(r'(?:سفينة|ناقلة|السفينة|الناقلة|سفن|ناقلات|شركة|بارجة|الواقعة)\s*«?\s*$')
    latin = []
    for t in LATIN_TOKEN.findall(no_urls):
        if '_' in t or '/' in t:
            continue
        clean = t.rstrip('.')
        if len(clean) < 3 or clean.lower() in EN_COMMON:
            continue
        idx = no_urls.find(t)
        before = no_urls[max(0, idx - 22):idx]
        if ship_ctx.search(before) or re.search(r'«\s*$', before):
            continue
        latin.append(clean)
    return prose, meta_text, full, phrases, latin


def harvest(date):
    got = candidates(date)
    if got is None:
        print(f"  ✘ لا مصدر للإصدار {date}")
        return 2
    prose, meta_text, full, phrases, latin = got

    bank = read_json(B / 'appendices' / 'glossary-standard.json') or {}
    bank_keys = set((bank.get('symbols') or {}).keys())
    known = library_terms()
    known_norm = {norm(t) for t in known}
    known_lat = known_latin(known)

    new_phrases = []
    for p in phrases:
        n = norm(p)
        if n in known_norm or n in STOP:
            continue
        if all(w in STOP for w in n.split()):
            continue
        if n not in [norm(x) for x in new_phrases]:
            new_phrases.append(p)

    new_latin = []
    for t in latin:
        if t.upper() in known_lat or t in new_latin:
            continue
        new_latin.append(t)

    register = read_json(REG_JSON) or {
        'note': 'مكتبة الألفاظ والرموز الجديدة — مرجع دائم يُغذّى آليًا قبل كل تسليم.',
        'updated': '', 'count': 0, 'terms': [],
    }
    register.setdefault('terms', [])
    seen = {t['term'] for t in register['terms']}
    added = []
    for term, kind in ([(p, 'عبارة مميّزة بلا تعريف') for p in new_phrases]
                       + [(t, 'رمز أو مصطلح أجنبي') for t in new_latin]):
        if term in seen:
            continue
        ctx = re.search(rf'.{{0,70}}{re.escape(term)}.{{0,70}}', full)
        register['terms'].append({
            'term': term, 'kind': kind, 'first_seen': date,
            'occurrences_in_edition': full.count(term),
            'context': re.sub(r'\s+', ' ', ctx.group(0).strip()) if ctx else '',
            'status': ('مُدرَج في بنك التعريفات' if term in bank_keys
                       else 'بانتظار مراجعة المالك'),
        })
        seen.add(term)
        added.append(term)

    register['updated'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    register['count'] = len(register['terms'])
    LIB.mkdir(parents=True, exist_ok=True)
    REG_JSON.write_text(json.dumps(register, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    lines = [
        '# مكتبة الألفاظ والرموز الجديدة',
        '',
        'مرجع دائم يُغذّى آليًا قبل كل تسليم. لا يُعتمد لفظ من الذاكرة؛ يُسجَّل هنا أولًا.',
        f'آخر تحديث: {register["updated"]} · المجموع: {register["count"]} بندًا.',
        '',
        'المعيار: عبارة عربية مميّزة في المتن ولا ترد في أي مكتبة أو قاموس، أو رمز أجنبي غير معرَّف.',
        '',
        '| اللفظ | الفئة | أول ورود | في الإصدار | الحالة |',
        '|---|---|---|---|---|',
    ]
    for t in sorted(register['terms'], key=lambda x: (x['first_seen'], x['term'])):
        lines.append(f"| `{t['term']}` | {t['kind']} | {t['first_seen']} | "
                     f"{t['occurrences_in_edition']} | {t['status']} |")
    lines += ['', '## سياق أول ورود (للمراجعة)', '']
    for t in sorted(register['terms'], key=lambda x: (x['first_seen'], x['term'])):
        if t.get('context'):
            lines.append(f"- **{t['term']}** — …{t['context']}…")
    REG_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f"  مكتبة الألفاظ الجديدة: +{len(added)} بندًا · المجموع {register['count']}")
    if added:
        print(f"   · نماذج: {', '.join(added[:12])}")
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    a = ap.parse_args()
    sys.exit(harvest(a.date))