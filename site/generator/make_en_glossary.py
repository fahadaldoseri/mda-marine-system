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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
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
    print(f"   عقود النصوص: {total} · ناقص: {len(miss)} · مشتق آليًا: {len(derived)} · يحتاج يدويًا: {len(hard)}")
    for h in hard:
        print(f"      · {h[:110]}")
    if a.apply and derived:
        d = json.loads(GL.read_text(encoding="utf-8"))
        d.setdefault("entries", {}).update(derived)
        d.setdefault("_derived", {}).update({k: "اشتقاق آلي بمحاذاة ذاكرة الترجمة" for k in derived})
        GL.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"   ✔ أُضيف {len(derived)} مدخلًا مشتقًا إلى المعجم")
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
