#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""صفحة «المصادر والمراجع» — مرجع دائم في الشريط العلوي.

الأقسام الثلاثة:
  1) حالة المصادر المفحوصة: بطاقة لكل مصدر من فحص التغذيات اليومي (رقمه · اسمه · حالته).
  2) المراجع الرسمية: روابط الجهات الرسمية المستخدمة في التقرير.
  3) الموثوقية والمصداقية: جدول الـ62 مصدرًا بدرجات الموثوقية (A–F) والمصداقية (1–6).

المصادر: sources/feeds-status.json (فحص التغذيات) و sources/source-reliability.md (سجل الموثوقية).
"""
import html
import json
import re
from pathlib import Path

import site_chrome as CH

try:
    import build_report as BR
except ImportError:  # عند التشغيل من جذر المشروع
    from generator import build_report as BR

SITE = Path(__file__).resolve().parents[1]

CSS = """
.sp-head{margin:18px 0 6px}
.sp-head h1{font-size:clamp(22px,3.4vw,32px);margin:0 0 8px}
.sp-head p{color:var(--ink2);font-size:14.5px;line-height:1.8;margin:0}
.sx-note{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:10px 14px;margin:14px 0;font-size:13.5px;color:var(--ink2)}
.sx-h2{font-size:17px;margin:26px 0 10px;padding-inline-start:10px;border-inline-start:3px solid var(--accent)}
.sx-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:9px;margin:10px 0}
.sx-card{background:var(--panel);border:1px solid var(--line);border-radius:11px;
  padding:9px 11px;display:flex;flex-direction:column;gap:5px;position:relative;overflow:hidden}
.sx-card::before{content:"";position:absolute;inset-inline-start:0;top:0;bottom:0;width:4px;background:var(--line)}
.sx-card.ok::before{background:#1f9d6b}
.sx-card.bad::before{background:#c8402f}
.sx-card.lim::before{background:#c99a2e}
.sx-card.none::before{background:#5a6b86}
.dx-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:9px;margin:10px 0 12px}
.dx-tile{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:10px 12px;text-align:center}
.dx-tile b{display:block;font-size:22px;line-height:1.25}
.dx-tile span{font-size:11.5px;color:var(--muted)}
.dx-ok b{color:#3fbf8f}.dx-lim b{color:#d8a83a}.dx-bad b{color:#e0604c}.dx-none b{color:#8fa2bd}
.sx-top{display:flex;align-items:center;gap:8px}
.sx-num{background:var(--bg);border:1px solid var(--line);border-radius:8px;
  min-width:26px;text-align:center;font-size:12.5px;padding:2px 6px;color:var(--ink2)}
.sx-name{font-size:13.5px;font-weight:600;line-height:1.5}
.sx-state{font-size:13px;color:var(--ink2);line-height:1.6}
.sx-legend{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;color:var(--ink2);margin:6px 0 0}
.sx-legend b{display:inline-block;width:10px;height:10px;border-radius:3px;margin-inline-end:5px}
.sx-refs{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:7px}
.sx-ref{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:8px 11px;font-size:13px;line-height:1.7;word-break:break-word}
.sx-ref a{color:var(--accent);text-decoration:none;display:inline-block;padding:3px 0;min-height:24px}
.sx-ref span{display:block;color:var(--ink2);font-size:13px;margin-top:3px}
.sx-tbl{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
.sx-tbl th,.sx-tbl td{border:1px solid var(--line);padding:7px 9px;text-align:start;vertical-align:top}
.sx-tbl th{background:var(--panel);font-size:12.5px}
.sx-tbl td.n{text-align:center;white-space:nowrap}
.sx-tbl td a{display:inline-block;padding:3px 0;min-height:24px}
.sx-tbl td.g{text-align:center;font-weight:700}
@media(max-width:760px){.sx-grid{grid-template-columns:1fr}.sx-tbl{display:block;overflow-x:auto}}
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ''), quote=True)


def short_error(err: str) -> str:
    """صياغة قصيرة مفهومة لسبب التعذّر."""
    low = err.lower()
    code = re.search(r'\b(403|404|405|429|500|503)\b', err)
    if '403' in err or '405' in err or 'forbidden' in low or 'not allowed' in low:
        return f"قيد حماية موثق · {code.group(1) if code else '403'}"
    if 'ssl' in low or 'certificate' in low:
        return "حجب على مستوى النقل (SSL)"
    if 'timed out' in low or 'timeout' in low:
        return "انتهت المهلة"
    if code:
        return f"خطأ شبكة · {code.group(1)}"
    return "تعذّر الجلب"


def source_cards(status: dict, rows: list) -> tuple:
    """بطاقة لكل مصدر من الـ40: حالة تغذيته من فحص اليوم، أو أنه بلا تغذية آلية."""
    feeds = status.get('checked_feeds') or status.get('feeds') or []
    manual_reference = {int(n) for n in (status.get('manual_reference') or [])
                        if str(n).isdigit()}
    by_num = {}
    for f in feeds:
        num = f.get('num')
        if isinstance(num, int):
            by_num.setdefault(num, []).append(f)
    cards, seen = [], set()
    # كل مصادر السجل (40) بترتيب أرقامها
    for r in rows:
        num = r['num']
        seen.add(num)
        group = by_num.get(num) or []
        if not group:
            cards.append({'num': num, 'name': r['name'], 'kind': 'none',
                          'state': ('مرجعية تُراجع يدويًا — لا تُفحص آليًا'
                                    if num in manual_reference
                                    else 'لا تغذية RSS — يُتابع بالمتصفح أو الأرشيف')})
            continue
        oks = [f for f in group if f.get('ok')]
        if oks:
            items = sum(int(f.get('items_count') or 0) for f in oks)
            vias = ', '.join(sorted({str(f.get('via') or '') for f in oks if f.get('via')}))
            state = f"نجح · {items} عنصرًا" + (f" · {vias}" if vias else "")
            cards.append({'num': num, 'name': r['name'], 'kind': 'ok', 'state': state})
        else:
            err = str(group[0].get('error') or group[0].get('block_reason') or '')
            cards.append({'num': num, 'name': r['name'], 'kind': 'bad',
                          'state': 'تعذّر — ' + short_error(err)})
    # مصادر في فحص اليوم ولا رقم لها في السجل
    for num, group in sorted(by_num.items()):
        if num in seen:
            continue
        oks = [f for f in group if f.get('ok')]
        cards.append({'num': num, 'name': group[0].get('name') or '',
                      'kind': 'ok' if oks else 'bad',
                      'state': f"نجح · {sum(int(f.get('items_count') or 0) for f in oks)} عنصرًا"
                               if oks else 'تعذّر — ' + short_error(str(group[0].get('error') or ''))})
    cards.sort(key=lambda c: c['num'] if isinstance(c['num'], int) else 999)
    return cards, status


def parse_reliability(md_path: Path) -> list:
    """جدول الموثوقية والمصداقية من سجل الـ62 مصدرًا."""
    if not md_path.exists():
        return []
    rows = []
    for line in md_path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 6 or cells[0].startswith('---') or cells[0] == '#':
            continue
        num = cells[0]
        if not num.isdigit():
            continue
        link = re.search(r'\[([^\]]+)\]\((https?://[^)]+)\)', cells[1])
        rows.append({
            'num': int(num),
            'name': link.group(1) if link else re.sub(r'\[|\]|\(.*?\)', '', cells[1]).strip(),
            'url': link.group(2) if link else '',
            'type': cells[2].replace('**', ''),
            'rel': cells[3].replace('**', ''),
            'cred': cells[4].replace('**', ''),
            'basis': cells[5].replace('**', ''),
        })
    return rows



def _diag_kind(state: str) -> str:
    if state.startswith('يعمل آليًا') or state.startswith('صفحة تُقرأ'):
        return 'ok'
    if state.startswith('متصفح') or state.startswith('معاينة'):
        return 'lim'
    if state.startswith('محجوب') or state.startswith('مسار مكسور') or state.startswith('خطأ شبكي'):
        return 'bad'
    return 'none'


def diagnosis_section(diag: list, esc) -> str:
    """قسم التشخيص الحي لكل المصادر — يُبنى من ملف التشخيص المنسوخ من النظام."""
    if not diag:
        return ''
    import datetime as _dt
    groups = {}
    for row in diag:
        groups.setdefault(_diag_kind(row.get('state', '')), []).append(row)
    labels = [('ok', 'يعمل آليًا'), ('lim', 'يحتاج متصفح/معاينة'),
              ('bad', 'محجوب أو معطوب'), ('none', 'يحتاج مراجعة مسار')]
    tiles = ''.join(
        f'<div class="dx-tile dx-{k}"><b>{len(groups.get(k, []))}</b><span>{lab}</span></div>'
        for k, lab in labels)
    needs = sorted([r for r in diag if r.get('action') and r['action'] != 'لا إجراء'],
                   key=lambda r: r['num'])
    if needs:
        body = '\n'.join(
            f'<tr><td class="n">{r["num"]}</td>'
            f'<td><a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["name"])}</a></td>'
            f'<td>{esc(r["state"])}</td><td>{esc(r["action"])}</td></tr>' for r in needs)
    else:
        body = '<tr><td colspan="4">كل المصادر تعمل بلا إجراء مطلوب.</td></tr>'
    stamp = _dt.datetime.utcnow().strftime('%Y-%m-%d')
    return f"""
  <h2 class="sx-h2">التشخيص الحي لكل المصادر ({len(diag)} مصدرًا · {stamp})</h2>
  <div class="dx-tiles">{tiles}</div>
  <div class="sx-note">التشخيص يقيس لكل مصدر مسار التغذية وحداثتها، وقراءة الصفحة المباشرة، ثم يصنّف المسار الفعلي.
  «يعمل آليًا» يعني قراءة المادة فعلًا داخل حدّ الحداثة المعتمد (14 يومًا). و«يحتاج متصفح» يعني أن الحجب أو بنية الصفحة تمنع القراءة الآلية.
  و«محجوب أو معطوب» قيد معروف لا يُتجاوز بحماية المواقع.</div>
  <table class="sx-tbl">
    <thead><tr><th>#</th><th>المصدر</th><th>الحالة المقيسة</th><th>الإجراء المطلوب</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
"""


def build(dist: Path, quiet: bool = False) -> dict:
    status_p = SITE / 'sources' / 'feeds-status.json'
    rel_p = SITE / 'sources' / 'source-reliability.md'
    status = {}
    if status_p.exists():
        try:
            status = json.loads(status_p.read_text(encoding='utf-8'))
        except Exception:
            status = {}
    rows = parse_reliability(rel_p)
    cards, status = source_cards(status, rows)
    diag_p = SITE / 'sources' / 'source-diagnosis.json'
    diag = []
    if diag_p.exists():
        try:
            diag = json.loads(diag_p.read_text(encoding='utf-8'))
        except Exception:
            diag = []

    checked = status.get('checked') or len(cards)
    ok_n = status.get('ok') or len([c for c in cards if c['kind'] == 'ok'])
    fail_n = status.get('failed') or len([c for c in cards if c['kind'] in ('bad', 'lim')])
    approved_n = status.get('approved') or len(rows)
    manual_n = len(status.get('manual_reference') or [])
    feeds_n = len(status.get('checked_feeds') or [])
    items_n = status.get('items') or 0
    stamp = status.get('date') or status.get('stamp') or ''
    ok_c = len([c for c in cards if c['kind'] == 'ok'])
    bad_c = len([c for c in cards if c['kind'] == 'bad'])
    none_c = len([c for c in cards if c['kind'] == 'none'])

    official = [r for r in rows if 'رسمي' in r['type']]

    def card_html(c):
        return (f'<div class="sx-card {c["kind"]}">'
                f'<div class="sx-top"><span class="sx-num">{esc(c["num"])}</span>'
                f'<span class="sx-name">{esc(c["name"])}</span></div>'
                f'<div class="sx-state">{esc(c["state"])}</div></div>')

    refs_html = '\n'.join(
        f'<div class="sx-ref"><a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["name"])}</a>'
        f'<span>{esc(r["type"])} · الموثوقية {esc(r["rel"])} · المصداقية {esc(r["cred"])}</span></div>'
        for r in official if r['url'])

    table_html = '\n'.join(
        f'<tr><td class="n">{r["num"]}</td>'
        f'<td><a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["name"])}</a></td>'
        f'<td>{esc(r["type"])}</td><td class="g">{esc(r["rel"])}</td>'
        f'<td class="g">{esc(r["cred"])}</td><td>{esc(r["basis"])}</td></tr>'
        for r in rows)

    doc = f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="المصادر والمراجع — مركز الوعي بالمجال البحري: حالة المصادر المفحوصة، والمراجع الرسمية، ودرجات الموثوقية والمصداقية.">
<meta name="theme-color" content="#040810">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<title>المصادر والمراجع — {esc(CH.BRAND)}</title>
<link rel="stylesheet" href="{BR.FONT_LINK}">
<style>{BR.DESIGN_TOKENS}{BR.STYLE}{BR.DAYLIGHT}{CSS}</style>
</head>
<body>
<div class="wrap" role="main">
  <header class="sp-head">
    <h1>المصادر والمراجع</h1>
    <p>مرجع دائم لكل ما بُني عليه التقرير اليومي. تُحذف هاتان القائمتان من نسخة الطباعة وPDF،
    فتبقىان هنا في الموقع للرجوع إليهما في أي وقت.</p>
  </header>

  <div class="sx-note">حالة آخر فحص للتغذيات{(' — ' + esc(stamp)) if stamp else ''}:
  المصادر: <b>{esc(approved_n)}</b> معتمدة · <b>{esc(checked)}</b> مرصودة آليًا ·
  <b>{esc(ok_n)}</b> ناجحة · <b>{esc(fail_n)}</b> متعذّر · <b>{esc(manual_n)}</b> مرجعية تُراجع يدويًا
  {('· تغذيات مفحوصة <b>' + esc(feeds_n) + '</b>') if feeds_n else ''}
  {('· عناصر مجمَّعة <b>' + esc(items_n) + '</b>') if items_n else ''}.
  والتعذّر يُسجَّل قيدًا معروفًا؛ وسياسة النظام تمنع تجاوز حماية المواقع.</div>

{diagnosis_section(diag, esc)}
  <h2 class="sx-h2">حالة المصادر المفحوصة</h2>
  <div class="sx-legend">
    <span><b style="background:#1f9d6b"></b>نجح الفحص ({ok_c})</span>
    <span><b style="background:#c8402f"></b>متعذّر ({bad_c})</span>
    <span><b style="background:#5a6b86"></b>لا تغذية RSS ({none_c})</span>
  </div>
  <div class="sx-note">الرمادي: مصدر مُدرج في سجل المصادر المعتمد ولا تغذية آلية له في فحص التغذيات اليومي؛
  ويُتابع بمسار آخر — فتح مباشر بالمتصفح، أو حفظ أصل رسمي، أو مراجعة يدوية. ولا يعني أنه غير مُتحقَّق منه.
  المصادر الموسومة «مرجعية تُراجع يدويًا» مستثناة من عداد الفحص الآلي ولا تُنتج عناصر وهمية.</div>
  <div class="sx-grid">
{chr(10).join(card_html(c) for c in cards) if cards else '<div class="sx-note">لا بيانات فحص بعد.</div>'}
  </div>

  <h2 class="sx-h2">المراجع الرسمية</h2>
  <div class="sx-refs">
{refs_html if refs_html else '<div class="sx-note">لا مراجع مسجّلة بعد.</div>'}
  </div>

  <h2 class="sx-h2">موثوقية المصادر ومصداقيتها</h2>
  <div class="sx-note">الموثوقية تقيس الجهة (A مطلق · B جيد · C متوسط · D غير موثوق · E غير مؤكد · F لا يمكن الحكم).
  والمصداقية تقيس درجة التصديق (1 مؤكد من مصدر آخر · 2 يُرجَّح · 3 يُحتمل · 4 مشكوك · 5 غير مُرجَّح · 6 لا يمكن الحكم).</div>
  <table class="sx-tbl">
    <thead><tr><th>#</th><th>المصدر</th><th>النوع</th><th>الموثوقية</th><th>المصداقية</th><th>الأساس</th></tr></thead>
    <tbody>
{table_html if table_html else '<tr><td colspan="6">لا سجل موثوقية بعد.</td></tr>'}
    </tbody>
  </table>
</div>
</body></html>
"""
    target = dist / 'sources.html'
    target.write_text(CH.inject(doc, 'sources', 'المصادر والمراجع — مرجع دائم'), encoding='utf-8')
    if not quiet:
        print(f"صفحة المصادر: {len(cards)} بطاقة · {len(official)} مرجعًا رسميًا · {len(rows)} مصدرًا في جدول الموثوقية")
    return {'cards': len(cards), 'refs': len(official), 'rows': len(rows), 'size': target.stat().st_size}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dist', default=str(SITE / 'dist'))
    a = ap.parse_args()
    print(build(Path(a.dist)))


if __name__ == '__main__':
    main()
