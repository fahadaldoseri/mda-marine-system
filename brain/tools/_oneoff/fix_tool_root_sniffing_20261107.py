#!/usr/bin/env python3
"""إصلاح جذري: توحيد اشتقاق جذر brain في الأدوات الحيّة على الوحدة القانونية.

يستبدل دوال `_brain_root()` التي كانت تتخطّف مجلدًا باسم `brain-marine-news`
بنداء `canonical_brain_root` (قياس المانيفست · فشل مغلق)، ويصلح الأدوات التي
تبني قوائم جذور بالأسماء. لا يمسّ سكربتات `_oneoff` التاريخية.
الاستخدام: python3 tools/_oneoff/fix_tool_root_sniffing_20261107.py [--apply]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

BRAIN = pathlib.Path(__file__).resolve().parents[2]

NEW_FN = '''def _brain_root():
    """جذر brain القانوني بالقياس (runbook/runbook.json) — فشل مغلق."""
    import sys as _sys
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'tools'))
    from brain_root import canonical_brain_root
    return canonical_brain_root(_Path(__file__).resolve().parents[1])
'''

TARGETS = [
    'tools/closure_round.py',
    'tools/normalize_fault_log.py',
    'tools/rotate_webhook_secret.py',
    'validators/check_closure.py',
]

FN_RX = re.compile(r'def _brain_root\(\):.*?\n(?=\S)', re.S)


def patch_function_files(apply: bool) -> list[str]:
    changed = []
    for rel in TARGETS:
        p = BRAIN / rel
        text = p.read_text(encoding='utf-8')
        if 'canonical_brain_root' in text:
            continue
        new, n = FN_RX.subn(NEW_FN, text, count=1)
        if n != 1:
            print(f'   ✘ {rel}: لم يُطابق نمط الدالة')
            continue
        if apply:
            p.write_text(new, encoding='utf-8')
        changed.append(rel)
    return changed


def patch_gate_verdict(apply: bool) -> bool:
    p = BRAIN / 'tools' / 'gate_verdict.py'
    text = p.read_text(encoding='utf-8')
    if 'canonical_brain_root' in text:
        return False
    old = '_root("BRAIN_DIR", pathlib.Path(__file__).resolve().parents[1].parent, "brain-marine-news", "brain")'
    new = ('canonical_brain_root(pathlib.Path(__file__).resolve().parents[1])')
    if old not in text:
        print('   ✘ tools/gate_verdict.py: لم يُطابق نداء الجذر')
        return False
    text = text.replace(old, new)
    imp = 'from brain_root import canonical_brain_root\n'
    if imp not in text:
        text = text.replace('import pathlib\n', 'import pathlib\nimport sys as _sys\n_sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n' + imp, 1)
    if apply:
        p.write_text(text, encoding='utf-8')
    return True


def patch_normalize_digits(apply: bool) -> bool:
    p = BRAIN / 'tools' / 'normalize_digits.py'
    text = p.read_text(encoding='utf-8')
    if 'canonical_brain_root' in text:
        return False
    old = ('ROOTS = [str(BASE / "brain-marine-news"), str(BASE / "seawatch")]\n'
           'if not Path(ROOTS[0]).exists():                          # عند التشغيل داخل نسخة مستنسخة\n'
           '    ROOTS = [str(HERE)] + ([str(HERE.parent / "site")] if (HERE.parent / "site").exists() else [])')
    new = ('sys.path.insert(0, str(HERE / "tools"))\n'
       'from brain_root import canonical_brain_root  # noqa: E402\n'
       '_BRAIN = canonical_brain_root(HERE)\n'
       '_SITE = next((str(c) for c in [HERE.parent / "seawatch", HERE.parent / "site"] if c.exists()), str(HERE.parent / "seawatch"))\n'
       'ROOTS = [str(_BRAIN), _SITE]')
    if old not in text:
        print('   ✘ tools/normalize_digits.py: لم يُطابق تعريف الجذور')
        return False
    text = text.replace(old, new, 1)
    if apply:
        p.write_text(text, encoding='utf-8')
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    fn = patch_function_files(a.apply)
    gv = patch_gate_verdict(a.apply)
    nd = patch_normalize_digits(a.apply)
    print(f'   دوال الجذر الموحّدة: {fn or "لا جديد"}')
    print(f'   gate_verdict: {"أُصلح" if gv else "لا جديد"} · normalize_digits: {"أُصلح" if nd else "لا جديد"}')
    if not a.apply:
        print('   (تجربة جافة)')
    return 0


if __name__ == '__main__':
    sys.exit(main())