#!/usr/bin/env python3
"""حارس الحتمية في مترجم الإنجليزية (2026-11-19).

العطل المقيس: `make_translator` كان يرتب المفاتيح بـ`key=len` فقط، فتبقى المفاتيح
المتساوية الطول بترتيب المجموعة، وهو يتغير مع بذرة التجزئة في كل عملية Python.
فبناءان من الشيفرة والمدخلات نفسها أعطيا 12 صفحة إنجليزية مختلفة، منها ملاحظة
«و1 بنود أخرى في قسم <a>ما تغيّر</a>» تُترجم مرة «What changed section» ومرة
«Recommendations section» بحسب البذرة. فما تجتازه البوابة ليس بالضرورة ما يُنشر.

الحالة الموجبة: الترجمة نفسها مهما كان ترتيب إدخال المفاتيح، والعقدة المقطوعة عند
«قسم» تُترجم بلا تخمين لاسم القسم.
الحالة السالبة: العبارة الكاملة باسم القسم تبقى على مدخلها المعجمي.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def default_site() -> Path:
    configured = os.environ.get("SITE_DIR")
    if configured:
        return Path(configured).resolve()
    for candidate in (ROOT.parent / "seawatch", ROOT.parent / "site"):
        if candidate.is_dir():
            return candidate.resolve()
    return (ROOT.parent / "seawatch").resolve()


SITE = default_site()
sys.path.insert(0, str(SITE / "generator"))
import i18n_en as I18N  # noqa: E402

A = "و1 بنود أخرى في قسم «التوصيات»."
B = "و1 بنود أخرى في قسم «ما تغيّر»."
GL = {A: "and 1 more item in the Recommendations section.",
      B: "and 1 more item in the What changed section."}


def _translate(order: list[str], text: str) -> str:
    gl = {k: GL[k] for k in order}
    tr = I18N.make_translator({}, gl)
    return tr(text) if callable(tr) else tr[0](text)


def test_equal_length_keys_do_not_depend_on_hash_seed() -> None:
    """ترتيب المجموعة يتغير مع PYTHONHASHSEED، فتُشغَّل عمليات مستقلة ببذور مختلفة."""
    import subprocess
    assert len(A) == len(B)
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); import i18n_en as I; "
        "tr = I.make_translator({}, {sys.argv[2]: 'a', sys.argv[3]: 'b'}); "
        "print(tr('و1 بنود أخرى في'))"
    )
    outs = set()
    for seed in range(8):
        env = dict(os.environ, PYTHONHASHSEED=str(seed))
        res = subprocess.run([sys.executable, "-c", code, str(SITE / "generator"), A, B],
                             capture_output=True, text=True, env=env, check=True)
        outs.add(res.stdout.strip())
    assert len(outs) == 1, f"الترجمة تغيّرت مع بذرة التجزئة: {outs}"


def test_split_note_does_not_guess_the_section() -> None:
    out = I18N.localize_patterns("و1 بنود أخرى في قسم")
    assert out == "and 1 more item under"
    assert I18N.localize_patterns("و3 بنود أخرى في قسم") == "and 3 more items under"


def test_full_note_keeps_its_glossary_entry() -> None:
    assert _translate([A, B], B) == GL[B]
    assert _translate([B, A], A) == GL[A]


if __name__ == "__main__":
    test_equal_length_keys_do_not_depend_on_hash_seed()
    test_split_note_does_not_guess_the_section()
    test_full_note_keeps_its_glossary_entry()
    print("✔ مترجم الإنجليزية حتمي")
