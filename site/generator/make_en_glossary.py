#!/usr/bin/env python3
"""يشتقّ مدخلات المعجم الإنجليزية آليًا من ذاكرة الترجمة، ويحصر ما يحتاج صياغة يدوية.

الاستعمال: python3 generator/make_en_glossary.py --date 2026-10-29 [--apply]
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import i18n_en as T  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
GL = ROOT / "sources" / "i18n" / "en" / "glossary.json"


def year_violation(key: str, value: str) -> bool:
    """هل تحمل القيمةُ سنةَ المفتاح؟

    ك-596: قاعدة الاشتقاق تأخذ أول جملة من مفتاح أطول، وقد تُسند إلى وحدة
    تاريخية ترجمةَ جزء آخر من الجملة. الحالة المقيسة: «آخر تحديث سبتمبر 2026»
    أُسند إليها «For public information» — ترجمة عبارة أخرى — فصار المفتاح
    يُترجم بلا سنة، وأوقف مسار الترجمة بفقد الرقم (حارس ك-592).
    القاعدة: كل سنة في المفتاح يجب أن تظهر في القيمة؛ وإلا فالمدخل مرفوض.
    """
    want = set(re.findall(r"\b20\d{2}\b", key))
    if not want:
        return False
    have = set(re.findall(r"\b20\d{2}\b", value or ""))
    return not want.issubset(have)


def prune(d: dict) -> list[str]:
    """يحذف من المعجم كل مدخل يخالف قاعدة السنة، ويعيد قائمة المفاتيح المحذوفة."""
    ent = d.get("entries", {})
    bad = [k for k, v in ent.items() if isinstance(v, str) and year_violation(k, v)]
    for k in bad:
        ent.pop(k, None)
        d.get("_derived", {}).pop(k, None)
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--prune", action="store_true", help="حذف مدخلات مخالفة لقاعدة السنة وحدها")
    a = ap.parse_args()
    if a.prune:
        d = json.loads(GL.read_text(encoding="utf-8"))
        bad = prune(d)
        GL.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"   ✔ حُذف {len(bad)} مدخلًا مخالفًا لقاعدة السنة")
        for k in bad:
            print(f"      · {k[:110]}")
        return 0
    tm = T.build_tm(a.date)
    gl = T.load_glossary()
    page = (ROOT / "dist" / "reports" / f"{a.date}.html").read_text(encoding="utf-8")
    _, missing, total = T.translate_page(page, a.date, tm, gl)
    miss = sorted(set(missing))
    keys = sorted(set(tm) | set(gl), key=len, reverse=True)
    derived: dict[str, str] = {}
    hard: list[str] = []
    for m in miss:
        n = T.norm(m)
        if n in tm or n in gl:
            continue
        suf = [k for k in keys if k.endswith(n) and 0 < len(k) - len(n) <= 40]
        if suf:
            k = min(suf, key=len)
            pref_ar = k[: -len(n)].strip()
            pref_en = gl.get(pref_ar) or tm.get(pref_ar) or ""
            val = tm.get(k) or gl.get(k) or ""
            if pref_en and val.startswith(pref_en):
                derived[n] = val[len(pref_en):].strip()
                continue
        pre = [k for k in keys if k.startswith(n) and 0 < len(k) - len(n) <= 80]
        if pre:
            k = min(pre, key=len)
            val = tm.get(k) or gl.get(k) or ""
            sentence = re.split(r"(?<=[.!؟])\s", val)[0]
            if sentence:
                derived[n] = sentence
                continue
        hard.append(n)
    # ك-596: لا يُقبل اشتقاق يُسقط سنة المفتاح، فيبقى النص «يحتاج يدويًا» بدل
    # أن يُقيَّد ترجمةً خاطئة تُلوّث المعجم وتوقف البناء لاحقًا.
    rejected = [k for k, v in derived.items() if year_violation(k, v)]
    for k in rejected:
        derived.pop(k, None)
        hard.append(k)
    print(f"   عقود النصوص: {total} · ناقص: {len(miss)} · مشتق آليًا: {len(derived)} · يحتاج يدويًا: {len(hard)}")
    if rejected:
        print(f"   ✘ رُفض {len(rejected)} اشتقاقًا مخالفًا لقاعدة السنة:")
        for k in rejected:
            print(f"      · {k[:110]}")
    for h in hard:
        print(f"      · {h[:110]}")
    if a.apply and derived:
        d = json.loads(GL.read_text(encoding="utf-8"))
        dropped = prune(d)
        if dropped:
            print(f"   ✔ حُذف {len(dropped)} مدخلًا قائمًا مخالفًا لقاعدة السنة")
        d.setdefault("entries", {}).update(derived)
        d.setdefault("_derived", {}).update({k: "اشتقاق آلي بمحاذاة ذاكرة الترجمة" for k in derived})
        GL.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"   ✔ أُضيف {len(derived)} مدخلًا مشتقًا إلى المعجم")
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
