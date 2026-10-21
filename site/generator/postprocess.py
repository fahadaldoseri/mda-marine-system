"""postprocess.py — طبقة إصلاح مخرجات الموقع (تعمل قبل النشر، وتبقى دائمة).

تعالج ما رصده التدقيق التصميمي على الصفحات المبنية:
  ص1  قوس زائد في كود التنسيق يُسقط ما بعده من قواعد.
  ص2  غياب قاعدة اتجاه النصوص اللاتينية والإحداثيات (.ltr) فتظهر مقلوبة.
  ص3  وسوم اتجاه مقطّعة تُلفّ جزءًا من الرمز فقط، فيظهر «26/10/18» مقلوبًا.
  ص4  علامات نجوم Markdown متبقية تظهر نصًّا خامًا للقارئ.
  ص5  مستويات ثقة إنجليزية في اللوحة الشهرية.
  ص6  جداول عريضة بلا معلم وصول ولا مفاتيح.
  ص7  شارات بلا ألوان في الوضع النهاري.
  ص8  وسوم شارات فارغة تترك فراغًا.

الدالة idempotent: تشغيلها مرتين يعطي الناتج نفسه.
"""
from __future__ import annotations

import re

STYLE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.S)
CODE = re.compile(r"(<(?:style|script)[^>]*>.*?</(?:style|script)>)", re.S)
LATIN_PIECE = r"[A-Za-z0-9][A-Za-z0-9.]*"

LTR_RULE = (
    "\n/* اتجاه النصوص اللاتينية والإحداثيات — يمنع انقلابها في السياق العربي */\n"
    ".ltr{direction:ltr;unicode-bidi:isolate}\n"
)

DAYLIGHT_BADGES = """
/* ألوان الشارات في الوضع النهاري (نفس منطق ألوان نسخة الطباعة) */
@media screen{
  body.daylight .st-badge.s-stable,body.daylight .chg.c-closed .chg-tag,body.daylight .conf.c-high,
  body.daylight .tag.t-confirm{color:#14603f;background:#edfaf3;border-color:#7cc4a0}
  body.daylight .st-badge.s-active,body.daylight .kstrip.k-confirm,body.daylight .cls-banner.c-sensitive
    {color:#7a1d1a;background:#fff1f0;border-color:#c77973}
  body.daylight .conf.c-med,body.daylight .kstrip.k-suspect,body.daylight .chg.c-reclassified .chg-tag,
  body.daylight .cls-banner.c-restricted,body.daylight .tag.t-suspect{color:#7c5000;background:#fff7e6;border-color:#c9a24f}
  body.daylight .conf.c-low,body.daylight .kstrip.k-inter,body.daylight .chg.c-new .chg-tag
    {color:#1d4f87;background:#edf4ff;border-color:#8bb1dd}
  body.daylight .chg.c-ongoing .chg-tag{color:#31465c;background:#f6f8fb;border-color:#b8c4d1}
  body.daylight .ev-code{color:#31465c;background:#f2f5f9;border-color:#c4d0dd}
}
"""

LEGEND_NUM = """
/* رقم المعلّم: نص داكن على معلّم فاتح، ومقلوب في الوضع النهاري */
body:not(.daylight) .lg-num{color:#04120f}
body.daylight .lg-num{color:#ffffff}
"""

TRUST_AR = {"high": "عالية", "medium": "متوسطة", "low": "منخفضة"}


def _outside_code(html: str, fn):
    return "".join(p if CODE.match(p) else fn(p) for p in CODE.split(html))


def _drop_stray_braces(css: str):
    """يحذف الأقواس المغلقة التي لا يقابلها فتح، فلا تُسقط ما بعدها."""
    out, depth, i, removed = [], 0, 0, 0
    in_str, in_com = None, False
    while i < len(css):
        c, nxt = css[i], css[i:i + 2]
        if in_com:
            out.append(c)
            if nxt == "*/":
                out.append("/")
                i += 2
                in_com = False
                continue
        elif in_str:
            out.append(c)
            if c == "\\":
                out.append(css[i + 1:i + 2])
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif nxt == "/*":
            out.append(nxt)
            i += 2
            in_com = True
            continue
        elif c in "\"'":
            in_str = c
            out.append(c)
        elif c == "{":
            depth += 1
            out.append(c)
        elif c == "}":
            if depth == 0:
                removed += 1
            else:
                depth -= 1
                out.append(c)
        else:
            out.append(c)
        i += 1
    return "".join(out), removed


def _merge_ltr(part: str) -> str:
    """يدمج وسوم الاتجاه المقطّعة في وسم واحد يلفّ الرمز كاملًا."""
    prev = None
    while prev != part:
        prev = part
        part = re.sub(r'</span>([/\-.:])<span class="ltr">', r"\1", part)
        part = re.sub(r'<span class="ltr">([^<]*)</span>((?:[/\-.:]' + LATIN_PIECE + r')+)',
                      r'<span class="ltr">\1\2</span>', part)
        part = re.sub(r'((?<![A-Za-z0-9])(?:' + LATIN_PIECE + r'[/\-.:])+)<span class="ltr">([^<]*)</span>',
                      r'<span class="ltr">\1\2</span>', part)
    return part


def _tables(part: str) -> str:
    """يضيف معلم وصول ومفاتيح لكل حاوية جدول قابلة للتمرير.

    الحاوية نفسها هي منطقة التمرير، فيجب أن تقبل التركيز بلوحة المفاتيح.
    والتلميح يُضاف للجداول العريضة فقط (أكثر من 5 أعمدة).
    """
    def one(m):
        holder = m.group(0)
        tbl = re.search(r"<table.*?</table>", holder, re.S).group(0)
        wide = len(re.findall(r"<th\b", tbl)) > 5
        label = "جدول يحتاج تمريرًا أفقيًا" if wide else "جدول"
        if 'tabindex=' not in holder.split(">", 1)[0]:
            holder = re.sub(r'<div class="(tbl-wrap|tbl-scroll)"',
                            lambda x: f'<div class="{x.group(1)}" tabindex="0" role="region" aria-label="{label}"',
                            holder, count=1)
        if wide and 'class="tbl-hint"' not in holder:
            holder = ('<span class="tbl-hint">اسحب الجدول أفقيًا لرؤية بقية الأعمدة</span>'
                      + holder)
        return holder
    return re.sub(r'<div class="(?:tbl-wrap|tbl-scroll)"[^>]*>\s*<table.*?</table>', one, part, flags=re.S)


def _stars(part: str) -> str:
    part = re.sub(r"\*\*([^*<>]{1,120}?)\*\*", r"<strong>\1</strong>", part)
    part = re.sub(r"<strong>\*\*([؛.\s]*)</strong>", r"\1", part)
    return part.replace("**", "")


def _trust(part: str) -> str:
    for en, ar in TRUST_AR.items():
        part = part.replace(f"<td>{en}</td>", f"<td>{ar}</td>")
    return part


def _empty_tags(part: str) -> str:
    part = re.sub(r'\s*<span class="sp-tag sp-code"></span>', "", part)
    part = re.sub(r'\s*<div class="sp-meta">\s*<span></span>\s*</div>', "", part)
    return re.sub(r'<span class="tag[^"]*"></span>', "", part)


def sanitize(html: str) -> str:
    """يطبّق كل إصلاحات المخرجات على صفحة واحدة."""
    removed = 0

    def css_fix(css: str) -> str:
        nonlocal removed
        css, n = _drop_stray_braces(css)
        removed += n
        return css

    html = STYLE.sub(lambda m: m.group(1) + css_fix(m.group(2)) + m.group(3), html)

    def body_fix(part: str) -> str:
        part = _merge_ltr(part)
        part = _stars(part)
        part = _trust(part)
        part = _tables(part)
        return _empty_tags(part)

    html = _outside_code(html, body_fix)

    # قاعدة الاتجاه + ألوان الشارات النهارية تُضاف مرة واحدة قبل نهاية آخر كتلة أنماط
    def inject_rules(css: str) -> str:
        add = ""
        if not re.search(r"\.ltr\s*\{", css):
            add += LTR_RULE
        if ".st-badge.s-stable" not in css and "daylight" in css:
            add += DAYLIGHT_BADGES
        if ".lg-num" not in css:
            add += LEGEND_NUM
        return css + add

    blocks = list(STYLE.finditer(html))
    if blocks:
        last = blocks[-1]
        html = html[:last.start(2)] + inject_rules(last.group(2)) + html[last.end(2):]

    if removed:
        html = html.replace("<!-- postprocess:stray-braces -->", "", 1)
    return html


def run(dist_root) -> dict:
    """يطبّق الإصلاح على كل صفحات مجلد النشر. يعيد إحصاءً مختصرًا."""
    from pathlib import Path

    dist = Path(dist_root)
    stats = {"pages": 0, "changed": 0}
    for p in sorted(dist.rglob("*.html")):
        t = p.read_text(encoding="utf-8")
        n = sanitize(t)
        stats["pages"] += 1
        if n != t:
            p.write_text(n, encoding="utf-8")
            stats["changed"] += 1
    return stats