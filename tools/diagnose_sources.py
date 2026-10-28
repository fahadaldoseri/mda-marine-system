#!/usr/bin/env python3
"""تشخيص شامل لكل مصادر القائمة المعتمدة — مسح حي مباشر.

يقيس لكل مصدر: مسار التغذية (إن وُجد) وحداثتها، وقراءة الصفحة المباشرة،
ثم يصنّف المسار الفعلي ويقارنه بالمعلن، ويكتب تقريرًا عربيًا قابلًا للتدقيق.

الاستعمال:
    python3 tools/diagnose_sources.py [--out DIR] [--json PATH]

المبدأ: لا يُعدّ مصدر «يعمل» إلا إذا أمكن قراءة مادته فعليًا بأحد المسارات،
ولا يُعدّ «حديثًا» إلا إذا كان عمر أحدث مادة مقيسًا داخل الحدّ المعتمد.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import gzip
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / 'appendices' / 'source-reliability-40.json'
SOURCES_MD = ROOT / 'sections' / '10-sources.md'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

STALE_DAYS = 14          # حدّ التقادم المعتمد (ك-117)
MIN_PAGE_CHARS = 1500    # أقلّ نص مقروء يعني أن الصفحة ليست هيكلًا فارغًا

BROWSER_HOSTS = ('x.com', 'twitter.com')
TELEGRAM_HOSTS = ('t.me',)


def load_register() -> list[dict]:
    rows = json.loads(REGISTER.read_text(encoding='utf-8'))
    out = []
    for row in rows:
        out.append({
            'num': int(row[0]), 'name': row[1], 'url': row[2], 'type': row[3],
            'reliability': row[4], 'credibility': int(row[5]), 'basis': row[6],
        })
    return out


def load_feeds() -> dict[int, list[dict]]:
    """يقرأ جدول التغذيات من القسم الرسمي في sections/10-sources.md."""
    feeds: dict[int, list[dict]] = {}
    grab = False
    for line in SOURCES_MD.read_text(encoding='utf-8').splitlines():
        if line.startswith('## تغذيات RSS'):
            grab = True
            continue
        if grab and line.startswith('## '):
            break
        if not grab:
            continue
        m = re.match(r'^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(\S+)\s*\|$', line.strip())
        if m:
            feeds.setdefault(int(m.group(1)), []).append(
                {'name': m.group(2), 'url': m.group(3)})
    return feeds


def fetch(url: str, timeout: int = 18) -> dict:
    request = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml,*/*',
        'Accept-Language': 'ar,en;q=0.8', 'Accept-Encoding': 'gzip',
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=CTX) as response:
            raw = response.read(400000)
            if response.headers.get('Content-Encoding') == 'gzip':
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            return {'status': response.status, 'body': raw.decode('utf-8', 'ignore'),
                    'error': None, 'tls': 'unverified' if url.startswith('https://') else 'n/a'}
    except urllib.error.HTTPError as error:
        return {'status': error.code, 'body': '', 'error': f'HTTP {error.code}', 'tls': 'n/a'}
    except Exception as error:  # noqa: BLE001 — تصنيف موحّد لأي خطأ شبكي
        return {'status': None, 'body': '', 'error': type(error).__name__, 'tls': 'n/a'}


def parse_age(value: str) -> int | None:
    text = (value or '').strip()
    if not text:
        return None
    for parser in (email.utils.parsedate_to_datetime,
                   lambda t: dt.datetime.fromisoformat(t.replace('Z', '+00:00'))):
        try:
            stamp = parser(text)
            if stamp:
                if not stamp.tzinfo:
                    stamp = stamp.replace(tzinfo=dt.timezone.utc)
                return (dt.datetime.now(dt.timezone.utc) - stamp).days
        except Exception:
            continue
    return None


def measure_feed(url: str) -> dict:
    result = fetch(url)
    body = result['body']
    items = len(re.findall(r'<(item|entry)(?:\s[^>]*)?>', body, re.I))
    dates = re.findall(r'<(?:pubDate|updated|published|dc:date)\b[^>]*>([^<]{6,60})</', body, re.I)
    ages = [a for a in (parse_age(d) for d in dates) if a is not None]
    newest = min(ages) if ages else None
    return {'url': url, 'status': result['status'], 'items': items,
            'latest_age_days': newest, 'error': result['error']}


def visible_chars(html: str) -> int:
    text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', html, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    return len(re.sub(r'\s+', ' ', text).strip())


def classify(source: dict, feed: dict | None, page: dict) -> dict:
    """يصنّف المصدر إلى حالة واحدة واضحة مع مسار فعلي وإجراء مقترح."""
    host = re.sub(r'^www\.', '', (source['url'].split('/')[2] if '://' in source['url'] else ''))
    status = page['status']
    chars = visible_chars(page['body']) if page['body'] else 0

    # عطل ك-119: المطابقة النصية الجزئية صنّفت مضيفين كاذبين (ajnet.me كأنه t.me وsynmax.com كأنه x.com).
    def host_is(value, candidates):
        return any(value == c or value.endswith('.' + c) for c in candidates)

    if host_is(host, BROWSER_HOSTS):
        if status == 404:
            return {'state': 'مسار مكسور', 'path': '—', 'action': 'تصحيح المُعرّف أو حذف المصدر'}
        return {'state': 'متصفح إلزامي', 'path': 'متصفح', 'action': 'يُفتح بمتصفح في كل تشغيل'}
    if host_is(host, TELEGRAM_HOSTS):
        return {'state': 'معاينة عامة', 'path': 't.me/s', 'action': 'تُقرأ بالمعاينة العامة'}
    if feed and feed['status'] == 200 and feed['items'] > 0:
        age = feed['latest_age_days']
        if age is None:
            return {'state': 'تغذية بلا تواريخ', 'path': 'تغذية', 'action': 'يُراجع مسار التواريخ في التغذية'}
        if age > STALE_DAYS:
            return {'state': f'تغذية متقادمة ({age} يومًا)', 'path': 'تغذية',
                    'action': 'تغيير مسار التغذية أو تقييد المصدر بالمتصفح'}
        return {'state': f'يعمل آليًا · حديث ({age} يومًا)', 'path': 'تغذية', 'action': 'لا إجراء'}
    if feed and feed['status'] == 200 and feed['items'] == 0:
        if status == 200 and chars >= MIN_PAGE_CHARS:
            return {'state': 'تغذية فارغة · الصفحة تُقرأ', 'path': 'صفحة', 'action': 'تُقرأ الصفحة بدل التغذية'}
        if status == 200:
            return {'state': 'تغذية فارغة · صفحة هيكلية', 'path': 'متصفح',
                    'action': 'يُراجع مسار الوصول أو يُرفع للمتصفح'}
        return {'state': 'تغذية فارغة · الصفحة محجوبة', 'path': '—',
                'action': 'إصلاح المسار أو إعادة تقييم المصدر'}
    if status == 200 and chars >= MIN_PAGE_CHARS:
        return {'state': 'صفحة تُقرأ آليًا', 'path': 'صفحة', 'action': 'لا إجراء'}
    if status == 200:
        return {'state': 'صفحة هيكلية (تحتاج متصفح)', 'path': 'متصفح', 'action': 'يُرفع للمتصفح'}
    if status in (401, 402, 403):
        return {'state': f'محجوب آليًا ({status})', 'path': '—',
                'action': 'لا يُتجاوز الحجب — مسار متصفح أو استبعاد'}
    if status == 404:
        return {'state': 'مسار مكسور (404)', 'path': '—', 'action': 'تصحيح الرابط في السجل'}
    if status is None:
        return {'state': f'خطأ شبكي ({page["error"]})', 'path': '—', 'action': 'إعادة الفحص ثم قرار'}
    return {'state': f'حالة غير مصنّفة ({status})', 'path': '—', 'action': 'مراجعة يدوية'}


def diagnose_one(source: dict, feeds: dict[int, list[dict]]) -> dict:
    registered = feeds.get(source['num'], [])
    feed_results = [measure_feed(f['url']) for f in registered] if registered else []
    page = fetch(source['url'])
    feed = None
    if feed_results:
        working = [f for f in feed_results if f['status'] == 200 and f['items'] > 0]
        if working:
            feed = min(working, key=lambda f: (f['latest_age_days'] if f['latest_age_days'] is not None else 10 ** 6))
        else:
            feed = feed_results[0]
    verdict = classify(source, feed, page)
    return {**source, 'feed_registered': len(registered), 'feeds': feed_results,
            'page_status': page['status'], 'page_chars': visible_chars(page['body']) if page['body'] else 0,
            'page_error': page['error'], **verdict}



def write_report(results: list[dict], out_dir: Path, stamp: str) -> Path:
    """يكتب تقريرًا عربيًا قابلًا للتدقيق لكل مصدر."""
    groups: dict[str, list[dict]] = {}
    for row in results:
        groups.setdefault(row['state'].split(' (')[0], []).append(row)
    needs = [r for r in results if r['action'] != 'لا إجراء']
    lines = [
        f"# تشخيص المصادر الشامل — {stamp}",
        "",
        f"مسح حي مباشر لكل مصادر القائمة المعتمدة ({len(results)} مصدرًا) بمسارين: التغذية والصفحة، "
        "ثم تصنيف المسار الفعلي ومقارنته بالمعلن. الأداة: `tools/diagnose_sources.py` · البيانات الخام: "
        f"`docs/source-diagnosis-{stamp}.json`.",
        "",
        "## الخلاصة التنفيذية",
        "",
        f"- **{len(groups.get('يعمل آليًا · حديث', [])) + len(groups.get('صفحة تُقرأ آليًا', []))}** مصدرًا تُقرأ مادته آليًا الآن (تغذية حديثة أو صفحة مباشرة).",
        f"- **{len(groups.get('متصفح إلزامي', [])) + len(groups.get('معاينة عامة', []))}** مصدرًا يحتاج مسار متصفح أو معاينة عامة (حجب آلي أو بنية صفحة).",
        f"- **{len(groups.get('محجوب آليًا', [])) + len(groups.get('مسار مكسور (404)', [])) + len(groups.get('خطأ شبكي', []))}** مصدرًا محجوبًا أو معطوبًا من هذه البيئة — قيد معروف لا يُتجاوز بحماية المواقع.",
        f"- **{len(groups.get('تغذية متقادمة', []))}** تغذية تردّ 200 لكن أحدث مادة فيها أقدم من الحدّ المعتمد (14 يومًا).",
        f"- **{len(groups.get('تغذية فارغة · صفحة هيكلية', [])) + len(groups.get('صفحة هيكلية (تحتاج متصفح)', []))}** مصدرًا واجهته هيكلية فارغة آليًا.",
        f"- يحتاج إجراءً صريحًا: **{len(needs)}** مصدرًا.",
        "",
        "## توزيع الفئات",
        "",
        "| الفئة | العدد |",
        "|---|---:|",
    ]
    for key in sorted(groups, key=lambda k: -len(groups[k])):
        lines.append(f"| {key} | {len(groups[key])} |")
    lines += ["", "## جدول التشخيص الكامل", "",
              "| # | المصدر | النوع | الموثوقية · المصداقية | الحالة المقيسة | المسار | الإجراء |",
              "|---:|---|---|---|---|---|---|"]
    for row in sorted(results, key=lambda r: r['num']):
        lines.append(
            f"| {row['num']} | [{row['name']}]({row['url']}) | {row['type']} | "
            f"{row['reliability']} · {row['credibility']} | {row['state']} | {row['path']} | {row['action']} |")
    lines += ["", "## ما يحتاج إجراءً", ""]
    for row in sorted(needs, key=lambda r: r['num']):
        detail = (f"صفحة: {row['page_status']} · {row['page_chars']} حرف مقروء"
                  if row['page_status'] else f"خطأ: {row['page_error']}")
        feed = row['feeds'][0] if row['feeds'] else None
        feed_txt = (f" · تغذية: {feed['status']} · {feed['items']} عنصر · عمر أحدث مادة "
                    f"{feed['latest_age_days']} يومًا") if feed else " · بلا تغذية مسجّلة"
        lines.append(f"- **{row['num']}. {row['name']}** — {row['state']} ({detail}{feed_txt}) → **{row['action']}**")
    lines += ["", "## حدود المنهج", "",
              "- التصنيف يقيس **إمكانية القراءة الفعلية** لا وجود الرابط فقط: تغذية تردّ 200 بمادة قديمة لا تُعدّ عملًا.",
              "- الحجب 401/402/403 لا يُتجاوز: يُسجَّل قيدًا معروفًا ويُقترح مسار متصفح أو استبعاد.",
              "- مطابقة المضيف دقيقة (المضيف نفسه أو نطاق فرعي له) — لا مطابقة نصية جزئية تُنتج تصنيفًا كاذبًا (ك-119).",
              ""]
    target = out_dir / f"تشخيص-المصادر-الشامل-{stamp}.md"
    target.write_text("\n".join(lines), encoding='utf-8')
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=str(ROOT / 'docs'))
    parser.add_argument('--json', default='')
    args = parser.parse_args()

    sources = load_register()
    feeds = load_feeds()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda s: diagnose_one(s, feeds), sources))

    order = {'مسار مكسور': 0, 'خطأ شبكي': 1, 'محجوب آليًا': 2, 'صفحة هيكلية (تحتاج متصفح)': 3}
    def severity(r):
        return (order.get(r['state'].split(' (')[0], 9), -r['credibility'])
    results.sort(key=severity)

    buckets: dict[str, list[dict]] = {}
    for r in results:
        key = r['state'].split(' (')[0]
        buckets.setdefault(key, []).append(r)

    json_path = Path(args.json) if args.json else ROOT / 'docs' / f'source-diagnosis-{stamp}.json'
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"═══ تشخيص {len(results)} مصدرًا · {sum(len(v) for v in feeds.values())} تغذية ═══")
    for key in sorted(buckets, key=lambda k: order.get(k, 9)):
        print(f"  {len(buckets[key]):>3} · {key}")
    problems = [r for r in results if r['action'] != 'لا إجراء']
    print(f"  يحتاج إجراءً: {len(problems)}")
    for r in problems[:14]:
        print(f"    {r['num']:>3} {r['name'][:38]:40} {r['state'][:34]:36} → {r['action'][:44]}")
    report = write_report(results, Path(args.out), stamp)
    print(f"  ✔ حفظ: {json_path}")
    print(f"  ✔ تقرير: {report}")
    return 0


if __name__ == '__main__':
    sys.exit(main())