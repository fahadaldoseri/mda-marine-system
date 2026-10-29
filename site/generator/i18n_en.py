#!/usr/bin/env python3
"""ترجمة صفحة إصدار عربية مبنية إلى إنجليزية مع الحفاظ على الوسم والهيئة حرفيًا.

المبدأ: النسخة الإنجليزية ليست إعادة بناء، بل نفس صفحة الإصدار العربية بوسمها
وأقسامها وخريطتها وبطاقاتها وزراها، مع استبدال النصوص الظاهرة بالإنجليزية. هذا
يضمن تطابق التصميم والأزرار والخريطة بين النسختين بلا استثناء.

المكوّنات:
- ذاكرة ترجمة (TM): محاذاة متن التقرير العربي مع ترجمته المعتمدة سطرًا بسطر.
- معجم واجهة (glossary.json): نصوص لا تأتي من المتن (بطاقات الوقائع · وسوم الحالة ·
  تسميات المؤشرات · مفاتيح الخريطة · عدّادات). ويسقط عليه معجم الشريط الحاكم.
- معالجة أنماط: التواريخ والعدّادات والمقاطع المقتطعة بعلامة «…».

الاستعمال:
  python3 generator/i18n_en.py --date 2026-10-29 --report
  python3 generator/i18n_en.py --date 2026-10-29 --out /tmp/en.html
"""
from __future__ import annotations
import os
import argparse, json, pathlib, re, sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
def _root(env: str, base: pathlib.Path, *names: str) -> pathlib.Path:
    """جذر الشجرة: من متغيّر البيئة أو من مجلد شقيق معتمد (قابلية النقل)."""
    v = os.environ.get(env)
    if v:
        return pathlib.Path(v)
    for n in names:
        if (base / n).is_dir():
            return base / n
    return base / names[0]


_HOME = pathlib.Path(__file__).resolve().parents[2]
BRAIN = _root("BRAIN_DIR", _HOME, "brain-marine-news", "brain")
AR_MD = BRAIN / "reports"
I18N = ROOT / "sources" / "i18n" / "en"
SKIP_TAGS = {"script", "style", "code"}
TR_ATTRS = ("title", "aria-label", "alt", "placeholder", "data-label")
ARABIC = re.compile(r"[\u0600-\u06FF]")
MONTHS = {
    "يناير": "January", "فبراير": "February", "مارس": "March", "أبريل": "April",
    "مايو": "May", "يونيو": "June", "يوليو": "July", "أغسطس": "August",
    "سبتمبر": "September", "أكتوبر": "October", "نوفمبر": "November", "ديسمبر": "December",
}
COUNT_WORD = {"بندًا": "items", "بنود": "items", "بند": "item", "واقعة": "incidents", "وقائع": "incidents",
              "مصدرًا": "sources", "مصادر": "sources", "سفينة": "vessel", "سفن": "vessels",
              "يومًا": "days", "أيام": "days", "رمزًا": "codes", "رموز": "codes", "حدثًا": "events",
              "أحداث": "events", "خريطة": "map", "خرائط": "maps"}
COUNTER = re.compile(r"^(\d+)\s+(" + "|".join(COUNT_WORD) + r")\b\s*(·?)$")


def norm(s: str) -> str:
    s = (s or "").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


def plain(md_line: str) -> str:
    s = md_line.strip()
    s = re.sub(r"^#{1,6}\s+", "", s)
    s = re.sub(r"^>\s*", "", s)
    s = re.sub(r"^[-*]\s+", "", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    if s.startswith("|"):
        s = " · ".join(c.strip() for c in s.strip("|").split("|"))
    return norm(s)


def build_tm(date: str) -> dict[str, str]:
    ar = (AR_MD / f"{date}-sectioned.md").read_text(encoding="utf-8")
    en = (I18N / f"{date}-sectioned.en.md").read_text(encoding="utf-8")
    A = [plain(x) for x in ar.splitlines() if x.strip()]
    E = [plain(x) for x in en.splitlines() if x.strip()]
    if len(A) != len(E):
        raise SystemExit(f"محاذاة غير ممكنة: عربي={len(A)} إنجليزي={len(E)}")
    tm = {a: e for a, e in zip(A, E) if a and a != e and ARABIC.search(a)}
    ar_rows = [x.strip() for x in ar.splitlines() if x.strip().startswith("|")]
    en_rows = [x.strip() for x in en.splitlines() if x.strip().startswith("|")]
    for al, el in zip(ar_rows, en_rows):
        for a, e in zip((norm(c) for c in al.strip("|").split("|")), (norm(c) for c in el.strip("|").split("|"))):
            if a and e and ARABIC.search(a):
                tm.setdefault(a, e)
    return tm


def chrome_glossary() -> dict[str, str]:
    import site_chrome  # استيراد مؤجّل

    src = pathlib.Path(site_chrome.__file__).read_text(encoding="utf-8")
    i = src.find("var I18N={ar:")
    if i < 0:
        return {}
    blk = src[i : src.find("})();", i)]
    def obj(tag: str) -> dict:
        j = blk.find("{", blk.find(f'"{tag}"'))
        if j < 0:
            return {}
        k = blk.find("}", j)
        try:
            return json.loads(blk[j : k + 1])
        except Exception:
            return {}
    ar_obj, en_obj = obj("ar"), obj("en")
    return {norm(k): v for k, v in ar_obj.items() if isinstance(v, str) and v.strip() and en_obj.get(k)}


def load_glossary() -> dict[str, str]:
    p = I18N / "glossary.json"
    gl: dict[str, str] = {}
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        gl = {norm(k): v for k, v in (d.get("entries") or {}).items()}
    gl.update(chrome_glossary())
    return gl


def localize_patterns(s: str) -> str | None:
    n = norm(s)
    m = re.fullmatch(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})", n)
    if m:
        return f"{m.group(1)} {MONTHS[m.group(2)]} {m.group(3)}"
    m = re.fullmatch(r"(" + "|".join(MONTHS) + r")\s+(\d{4})", n)
    if m:
        return f"{MONTHS[m.group(1)]} {m.group(2)}"
    m = COUNTER.match(n)
    if m:
        return f"{m.group(1)} {COUNT_WORD[m.group(2)]}" + (f" {m.group(3)}" if m.group(3) else "")
    return None


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.skip = 0
        self.units: list[str] = []
        self.parts: list[str] = []
        self.attrs_seen: list[str] = []

    def _attr(self, attrs) -> str:
        if not attrs:
            return ""
        out = []
        for k, v in attrs:
            if v is None:
                out.append(f" {k}")
            elif k in TR_ATTRS and ARABIC.search(v):
                self.attrs_seen.append(v)
                out.append(f' {k}="__ATTR{len(self.attrs_seen) - 1}__"')
            else:
                out.append(f' {k}="{v}"')
        return "".join(out)

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        self.parts.append(f"<{tag}{self._attr(attrs)}>")

    def handle_startendtag(self, tag, attrs):
        self.parts.append(f"<{tag}{self._attr(attrs)}/>")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip:
            self.parts.append(data)
            return
        self.parts.append("\u0000")
        self.units.append(data)

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")


def make_translator(tm: dict[str, str], gl: dict[str, str]):
    keys = sorted(set(tm) | set(gl), key=len, reverse=True)

    def lookup(t: str) -> str | None:
        if t in tm:
            return tm[t]
        if t in gl:
            return gl[t]
        pat = localize_patterns(t)
        if pat:
            return pat
        starts = [k for k in keys if k.startswith(t)]
        if starts:
            k = min(starts, key=len)
            return tm.get(k) or gl.get(k) or ''
        within = [k for k in keys if t.startswith(k)]
        if within:
            k = max(within, key=len)
            return tm.get(k) or gl.get(k) or ''
        return None

    def translate(u: str) -> str:
        n = norm(u)
        if not n or not ARABIC.search(n):
            return u
        direct = lookup(n)
        if direct is not None:
            return u.replace(n, direct)
        res, ok = u, True
        for part in re.split(r"(?<=[…·])\s*", u):
            p = norm(part)
            if not p or not ARABIC.search(p):
                continue
            hit = lookup(p)
            if hit is None:
                ok = False
                break
            res = res.replace(part, part.replace(p, hit))
        if ok:
            return res
        for k in keys:
            if k in res:
                res = res.replace(k, tm.get(k) or gl.get(k) or '')
        return res

    return translate



# ك-320: تصحيح تسميات الشريط الثابتة في النسخة الإنجليزية.
# سبب الإصلاح: المترجم النصي يترجم الحروف المفردة ترجمة خاطئة (ع ← Aden، أ ← issued)
# وبعض سمات أدوات التحكم تبقى عربية. تُثبَّت هنا صراحةً بعد الترجمة.
_CHROME_FIX = {
    'aria-label="تنقل Location"': 'aria-label="Site navigation"',
    'aria-label="تنقل الموقع"': 'aria-label="Site navigation"',
    'aria-label="اللغة / Language"': 'aria-label="Language"',
    'aria-label="حجم الخط"': 'aria-label="Text size"',
    'title="العربية"': 'title="Arabic"',
    'title="حجم عادي"': 'title="Normal size"',
    'title="حجم أكبر"': 'title="Larger size"',
    'title="أكبر حجم"': 'title="Largest size"',
    '>Aden</button>': '>AR</button>',
    '>issued</button>': '>A</button>',
    '>أ+</button>': '>A+</button>',
    '>أ++</button>': '>A++</button>',
    'title="A+"': 'title="Larger size"',
    'title="A++"': 'title="Largest size"',
    'خريطة ': 'Map of ',
}


def _fix_chrome(out: str) -> str:
    for a, b in _CHROME_FIX.items():
        out = out.replace(a, b)
    # ك-320 (تكملة): أي وسم إمكانية وصول يبقى عربيًا في النسخة الإنجليزية يُستبدل بنص إنجليزي صريح،
    # فلا تُقرأ واجهة إنجليزية عربيةَ على قارئ الشاشة.
    def _lbl(m):
        v = m.group(1)
        if "خريطة" in v:
            en = "Map of the region with incident locations"
        else:
            en = "Section"
        return 'aria-label="%s"' % en
    out = re.sub(r'aria-label="([^"]*[\u0600-\u06FF][^"]*)"', _lbl, out)
    return out


def translate_page(html_text: str, date: str, tm: dict[str, str], gl: dict[str, str]):
    tr = make_translator(tm, gl)
    c = _Collector()
    c.feed(html_text)
    units = [tr(t) for t in c.units]
    attrs = [tr(a) for a in c.attrs_seen]
    parts, k = [], 0
    for p in c.parts:
        if p == "\u0000":
            parts.append(units[k]); k += 1
        else:
            for i, a in enumerate(attrs):
                p = p.replace(f'__ATTR{i}__', a)
            parts.append(p)
    out = "".join(parts)
    head_end = out.find(">")
    head = out[: head_end + 1]
    head = re.sub(r'lang="[^"]*"', 'lang="en"', head) if 'lang=' in head else head[:-1] + ' lang="en">'
    head = re.sub(r'dir="[^"]*"', 'dir="ltr"', head) if 'dir=' in head else head[:-1] + ' dir="ltr">'
    head = head if 'data-lang="en"' in head else head[:-1] + ' data-lang="en">'
    out = head + out[head_end + 1 :]
    m = re.search(r"<body([^>]*)>", out)
    if m:
        a = m.group(1)
        if "class=" in a:
            a = re.sub(r'class="', 'class="lang-en ', a, count=1)
        else:
            a = a + ' class="lang-en"'
        out = out[: m.start(1)] + a + out[m.end(1):]
    out = re.sub(r"<title>.*?</title>", f"<title>Daily Maritime Security Report — {date} (English edition)</title>", out, flags=re.S)
    out = re.sub(r'<meta name="description" content="[^"]*"',
                 '<meta name="description" content="Daily Maritime Security Report — English edition, translated and governed against the Arabic source.">', out)
    remaining = [t for t in c.units if ARABIC.search(norm(tr(t))) and len(ARABIC.findall(tr(t))) > 2]
    out = _fix_chrome(out)
    return out, [norm(x) for x in remaining], len(c.units)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--src", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    src = pathlib.Path(a.src) if a.src else ROOT / "dist" / "reports" / f"{a.date}.html"
    if not src.exists():
        print(f"تعذّر: صفحة الإصدار العربية غير موجودة: {src}")
        return 2
    tm, gl = build_tm(a.date), load_glossary()
    page, missing, total = translate_page(src.read_text(encoding="utf-8"), a.date, tm, gl)
    print(f"   ذاكرة الترجمة: {len(tm)} · المعجم: {len(gl)} · عقود النصوص: {total}")
    uniq = sorted(set(missing))
    if uniq:
        print(f"   ✘ نصوص عربية بلا ترجمة: {len(uniq)}")
        for s in uniq[:60]:
            print(f"      · {s[:120]}")
    else:
        print("   ✔ لا نص عربي متبقٍّ في الصفحة المترجمة")
    if a.out:
        pathlib.Path(a.out).write_text(page, encoding="utf-8")
        print(f"   ✔ كُتب {a.out}")
    return 0 if not uniq else 1


if __name__ == "__main__":
    sys.exit(main())
