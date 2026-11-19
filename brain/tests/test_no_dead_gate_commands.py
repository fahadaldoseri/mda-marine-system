"""حارس الأوامر الميتة: لا فحص يُكتب بعد أمر خروج فلا يُنفَّذ أبدًا (2026-11-19).

العطلان المقيسان:
- أمر B010 في runbook.json كان ينتهي بـ`; rc=$?; exit $rc && python3 tests/test_map_location_term.py ...`
  فاختباران لا يُنفَّذان قط، والخطوة تبدو أنها تفحصهما.
- `tools/final_gate.sh` كان يستدعي «ترجمة الشيفرة» بعد `exit "$WORST"`، فلا تعمل البوابة.

القاعدة: لا شيء بعد `exit` في أمر خطوة، ولا خطوة بعد آخر `exit` في بوابة التسليم.
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
# خروج غير مشروط على مستوى الجملة (بعد «;» أو في البداية، لا بعد then أو || أو &&)
# يتبعه أمر غير «fi» = ذيل لا يُنفَّذ.
EXIT_THEN = re.compile(r"(?:^|;)\s*exit\s+\"?\$\{?\w+:?-?\w*\}?\"?\s*(?:&&|\|\||;)\s*(?!fi\b)\S")


def dead_tails(command: str) -> list[str]:
    return [m.group(0) for m in EXIT_THEN.finditer(command)]


def test_detector_catches_the_b010_pattern():
    assert dead_tails('a; rc=$?; exit $rc && python3 t.py')
    assert dead_tails('a; exit "$rc"; python3 t.py')
    assert not dead_tails('a && python3 t.py; rc=$?; exit $rc')
    assert not dead_tails('a; rc=$?; exit "$rc"')
    assert not dead_tails('if [ $w -gt 1 ]; then exit $w; fi; b')
    assert not dead_tails('[ $rc -eq 0 ] || exit $rc; b')
    assert dead_tails('a; rc=$?; exit $rc ; python3 - <<PY')


# ذيل ميت مقيس ينتظر قرار المالك، لا يُفعَّل خفية: ذيل G054 (check_published_counters.py)
# يُرجع 2 على تقريري 2026-11-12 و2026-11-18 المنشورين (قيس 2026-11-19)، فتفعيله يمنع النشر.
# كل مدخل هنا مؤرخ ومسبَّب، وأي ذيل ميت جديد خارجها يُسقط الاختبار.
PENDING_OWNER_DECISION: dict[str, str] = {}  # G054 فُعِّل بقرار المالك 2026-11-19 بعد إصلاح الأرقام


def test_no_manifest_command_has_code_after_exit():
    manifest = json.loads((ROOT / "runbook" / "runbook.json").read_text(encoding="utf-8"))
    bad = []
    for step in manifest.get("steps", []):
        for part in step.get("command") or []:
            if isinstance(part, str) and dead_tails(part) and step.get("id") not in PENDING_OWNER_DECISION:
                bad.append(step.get("id"))
    assert not bad, f"أوامر بعد exit لا تُنفَّذ في الخطوات: {bad}"


def test_final_gate_has_no_step_after_last_exit():
    lines = (ROOT / "tools" / "final_gate.sh").read_text(encoding="utf-8").splitlines()
    last_exit = max(i for i, line in enumerate(lines) if line.strip().startswith('exit "$WORST"'))
    after = [line for line in lines[last_exit + 1:] if re.match(r"\s*(step|step_strict)\s", line)]
    assert not after, f"خطوات بعد آخر exit في final_gate.sh: {after}"
