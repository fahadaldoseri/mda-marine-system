import unittest
#!/usr/bin/env python3
"""كل أمر في المانيفست يستدعي سكربتًا موجودًا بخيارات موجودة في نصه (D060 كان يمرّر --check إلى أداة لا تعرفه).
الاستعمال: python3 tests/test_manifest_commands.py    رمز 0 سليم · 2 خلل"""
import json
import os
import re
import sys
from pathlib import Path

B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)
m = json.loads((B / "runbook" / "runbook.json").read_text(encoding="utf-8"))
bad = []
n = 0
for s in m["steps"]:
    cmd = " ".join(s.get("command") or [])
    for part in re.split(r";|&&", cmd):
        mm = re.search(r'(?:python3|bash)\s+"?(?:\$B/)?((?:tools|validators|tests)/[\w./-]+)"?(.*)', part)
        if not mm:
            continue
        path, rest = mm.group(1), mm.group(2)
        n += 1
        f = B / path
        if not f.is_file():
            bad.append(f"{s['id']}: السكربت غير موجود {path}")
            continue
        src = f.read_text(encoding="utf-8", errors="ignore")
        for fl in sorted(set(re.findall(r"(?<![\w-])(--[a-z][\w-]*)", rest))):
            if fl not in src:
                bad.append(f"{s['id']}: الخيار {fl} غير معرَّف في {path}")
for b in bad:
    print("✘", b)
if not bad:
    print(f"✔ {n} استدعاء سكربت في المانيفست: كلها موجودة وخياراتها معرَّفة")
sys.exit(2 if bad else 0)

class TestCommandShape(unittest.TestCase):
    """ALL_COMMANDS_ARE_ARGV_V1: كل أمر خطوة قائمة argv نصية، وبلا تاريخ مثبَّت."""

    def test_shape_and_date(self):
        import json, pathlib, re
        rb = json.loads(pathlib.Path("runbook/runbook.json").read_text(encoding="utf-8"))
        for s in rb["steps"]:
            c = s.get("command")
            self.assertIsInstance(c, list, f"{s['id']}: الأمر ليس قائمة argv")
            self.assertTrue(all(isinstance(x, str) and x for x in c), f"{s['id']}: عنصر أمر غير نصي")
            self.assertNotIn(";", c[0], f"{s['id']}: العنصر الأول اسم برنامج لا سطر شل")
            self.assertNotIn(" ", c[0], f"{s['id']}: العنصر الأول اسم برنامج بلا مسافات")
            joined = " ".join(c)
            self.assertIsNone(re.search(r"20\d\d-\d\d-\d\d", joined),
                              f"{s['id']}: تاريخ مثبَّت في الأمر بدل {{date}}")


if __name__ == "__main__":
    unittest.main()

