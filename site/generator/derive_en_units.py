#!/usr/bin/env python3
"""اشتقاق الوحدات الإنجليزية من المتن الإنجليزي الحاكم وتسجيلها في المعجم.

المبدأ الجديد (2026-11-03): النسخة الإنجليزية هي **الأصل**، والمتن الإنجليزي
`sources/i18n/en/<DATE>-sectioned.en.md` هو مصدر النص الإنجليزي. فعندما تبقى
وحدة عربية في الصفحة المترجمة، لا يُترجمها النموذج ولا تُخمَّن، بل تُشتق من
مقابلها في المتن الإنجليزي بمحاذاة الجُمل، ثم تُقيَّد في المعجم الحاكم.

الاستعمال:
    python3 generator/derive_en_units.py --date 2026-11-02            # فحص
    python3 generator/derive_en_units.py --date 2026-11-02 --apply    # كتابة
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import i18n_en  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
AR_MD = ROOT.parent / "brain-marine-news" / "reports"
I18N = ROOT / "sources" / "i18n" / "en"


def sentences(s: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.؟!؛])\s+|\s+·\s+", s) if p.strip()]


def words(s: str) -> list[str]:
    return [w for w in re.split(r"\s+", s.strip()) if w]


def build_pairs(date: str):
    ar = (AR_MD / f"{date}-sectioned.md").read_text(encoding="utf-8").splitlines()
    en = (I18N / f"{date}-sectioned.en.md").read_text(encoding="utf-8").splitlines()
    A = [x for x in ar if x.strip()]
    E = [x for x in en if x.strip()]
    if len(A) != len(E):
        raise SystemExit(f"محاذاة غير ممكنة: عربي={len(A)} إنجليزي={len(E)}")
    return list(zip(A, E))


def build_pairs_history(date: str, back: int = 14):
    """أزواج اليوم المطلوب + أزواج الأيام السابقة.

    الأسطح المنشورة (صفحة الإضافات والرئيسية والأرشيف) تعرض نصوصًا من أيام
    سابقة. فإذا بقيت وحدة منها بلا ترجمة، تُشتقّ من متن يومها نفسه بدل أن
    تفشل الحزمة أو تُترجم تخمينًا. (ك-478: تجميد الاشتقاق على يوم واحد.)
    """
    import datetime as _dt
    d0 = _dt.date.fromisoformat(date)
    pairs: list[tuple[str, str]] = []
    for k in range(back + 1):
        d = (d0 - _dt.timedelta(days=k)).isoformat()
        try:
            pairs.extend(build_pairs(d))
        except SystemExit:
            continue
        except FileNotFoundError:
            continue
    if not pairs:
        raise SystemExit("محاذاة غير ممكنة: لا يوم قابل للمحاذاة")
    return pairs


TOKEN_RE = re.compile(r"\d[\d.,:/–\-]*[A-Za-z]{0,3}|\b[A-Z]{2,}\b|[A-Za-z]{2,}-\d+|\d+-\d+")


def tokens(s: str) -> set[str]:
    """الرموز القابلة للتحقق: الأرقام والمعرّفات وأسماء الجهات اللاتينية."""
    out = set()
    for t in TOKEN_RE.findall(s):
        t = t.strip().lower()
        if not t:
            continue
        digits = re.sub(r"[^\d]", "", t)
        out.add(digits if digits else t)
    return {x for x in out if x}


def verified(unit_ar: str, en: str) -> bool:
    """لا يُقبل اشتقاق يخالف أرقام الوحدة أو معرّفاتها (فشل مغلق)."""
    tu, te = tokens(unit_ar), tokens(en)
    if not tu:
        return bool(te) or bool(en.strip())
    missing = {x for x in tu if x not in te}
    # تُقبل الزيادة الطفيفة في أرقام الجملة الإنجليزية، ولا يُقبل نقص رقم عربي
    return not missing


def derive(unit: str, pairs) -> str | None:
    """يشتقّ النص الإنجليزي لوحدة عربية من المتن الإنجليزي بمحاذاة الجُمل."""
    nu = i18n_en.norm(unit)
    if not nu:
        return None
    su = sentences(unit)
    if not su:
        return None
    for a, e in pairs:
        na = i18n_en.norm(a)
        if nu not in na:
            continue
        sa, se = sentences(a), sentences(e)
        if len(sa) != len(se) or not sa:
            continue
        # موضع أول جملة من الوحدة داخل جمل السطر العربي
        start = None
        for j, aj in enumerate(sa):
            naj = i18n_en.norm(aj)
            if i18n_en.norm(su[0]) and i18n_en.norm(su[0]) in naj:
                start = j
                break
            if naj.endswith(nu) or nu.endswith(naj):
                start = j
                break
        if start is None:
            continue
        # تحقّق أن بقية جمل الوحدة تقابل الجمل التالية نفسها
        for k, uk in enumerate(su[1:], start=1):
            idx = start + k
            if idx >= len(sa):
                return None
            if i18n_en.norm(uk) != i18n_en.norm(sa[idx]):
                return None
        out = list(se[start:])
        # اقتطاع الجملة الأولى إذا كانت الوحدة تبدأ من نهاية الجملة العربية
        first_ar, first_unit = sa[start], su[0]
        if i18n_en.norm(first_unit) != i18n_en.norm(first_ar):
            wa, wu, we = words(first_ar), words(first_unit), words(se[start])
            drop = max(0, len(wa) - len(wu))
            if len(we) > drop:
                out[0] = " ".join(we[drop:])
        res = " ".join(out).strip()
        if res and not i18n_en.ARABIC.search(res) and verified(unit, res):
            return res
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    src = ROOT / "dist" / "reports" / f"{a.date}.html"
    pages = [ROOT / "dist" / "reports" / f"{a.date}.html", ROOT / "dist" / "additions.html"]
    pages = [p for p in pages if p.exists()]
    if not pages:
        print(f"تعذّر: لا صفحة عربية مبنية ليوم {a.date}")
        return 2
    tm, gl = i18n_en.build_tm(a.date), i18n_en.load_glossary()
    uniq: list[str] = []
    total = 0
    for pg in pages:
        _, miss, tot = i18n_en.translate_page(pg.read_text(encoding="utf-8"), a.date, tm, gl)
        total += tot
        uniq.extend(miss)
        print(f"   {pg.name}: عقود {tot} · ناقص {len(set(miss))}")
    uniq = sorted(set(uniq))
    print(f"   عقود النصوص: {total} · وحدات بلا ترجمة: {len(uniq)}")
    if not uniq:
        print("   ✔ لا وحدة ناقصة")
        return 0

    pairs = build_pairs_history(a.date)
    print(f"   أزواج المحاذاة المتاحة (اليوم + 14 يومًا سابقة): {len(pairs)} سطرًا")
    derived: dict[str, str] = {}
    failed: list[str] = []
    for u in uniq:
        en = derive(u, pairs)
        (derived.__setitem__(u, en) if en else failed.append(u))

    for k, v in derived.items():
        print(f"   ✔ اشتُقّت: {k[:70]}  →  {v[:70]}")
    for k in failed:
        print(f"   ✘ تعذّر اشتقاقها: {k[:110]}")
    if a.json:
        pathlib.Path(a.json).write_text(
            json.dumps({"derived": derived, "failed": failed}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    if a.apply and derived:
        P = I18N / "glossary.json"
        d = json.loads(P.read_text(encoding="utf-8"))
        ent = d.setdefault("entries", {})
        for k, v in derived.items():
            ent[k] = v
        d["updated"] = a.date
        P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"   ✔ كُتبت {len(derived)} وحدة في المعجم")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
