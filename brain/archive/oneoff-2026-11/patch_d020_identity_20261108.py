#!/usr/bin/env python3
"""ترقيع عقد D020: لا تدقيق بصري إلا على قناة تخدم بناءنا ببصمة مطابقة.

- أداة live_dom_audit: خيار --expect URL=SHA256 يمنع تدقيق صفحة جهة أخرى.
- خطوة D020: تقرأ القناة الأساسية من المانيفست عبر tools/channel_base.py،
  وتُمرّر بصمة كل صفحة من مخرج البناء.
"""
from __future__ import annotations

import json
import pathlib

BRAIN = pathlib.Path(__file__).resolve().parent.parent.parent

AUDIT = BRAIN / "tools" / "live_dom_audit.py"
MANIFEST = BRAIN / "runbook" / "runbook.json"

D020_CMD = (
    'B="$PWD"; export B SITE; bash tools/check_live.sh --compare {date}; rc=$?; '
    'if [ $rc -ne 0 ]; then exit $rc; fi; '
    'BASE="$(python3 "$B/tools/channel_base.py")"; '
    'test -n "$BASE" || { echo \'✘ لا قناة أساسية معلنة في المانيفست\'; exit 2; }; '
    'python3 "$B/tools/live_dom_audit.py" '
    '--url "$BASE/reports/{date}.html" '
    '--expect "$BASE/reports/{date}.html=$(sha256sum "$SITE/dist/reports/{date}.html" | cut -d\' \' -f1)" '
    '--url "$BASE/additions.html" '
    '--expect "$BASE/additions.html=$(sha256sum "$SITE/dist/additions.html" | cut -d\' \' -f1)" '
    '--url "$BASE/sources.html" '
    '--expect "$BASE/sources.html=$(sha256sum "$SITE/dist/sources.html" | cut -d\' \' -f1)" '
    '--json "logs/runbook/{date}/dom-audit.json"; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; '
    'exit ${w:-0}'
)


def patch_audit() -> None:
    t = AUDIT.read_text(encoding="utf-8")
    if "--expect" in t:
        print("   أداة التدقيق: شرط الهوية موجود مسبقًا")
        return

    t = t.replace(
        '    ap.add_argument("--json", default="")',
        '    ap.add_argument("--expect", action="append", default=[],\n'
        '                    help="URL=SHA256: لا يُدقَّق إلا ما يطابق بناءنا")\n'
        '    ap.add_argument("--json", default="")',
        1,
    )
    t = t.replace(
        "    shots = Path(a.shots) if a.shots else None\n"
        "    reports = [audit(u, shots, a.min_touch) for u in a.url]",
        "    shots = Path(a.shots) if a.shots else None\n"
        "    expects = {}\n"
        "    for item in a.expect:\n"
        "        if \"=\" in item:\n"
        "            u, s = item.rsplit(\"=\", 1)\n"
        "            expects[u.strip()] = s.strip()\n"
        "    identity_fail, urls = [], []\n"
        "    for u in a.url:\n"
        "        want = expects.get(u)\n"
        "        if not want:\n"
        "            urls.append(u)\n"
        "            continue\n"
        "        try:\n"
        "            with urllib.request.urlopen(u, timeout=45) as resp:\n"
        "                body = resp.read()\n"
        "            got = hashlib.sha256(body).hexdigest()\n"
        "        except Exception as exc:\n"
        "            identity_fail.append(f\"{u}: تعذّر جلب الصفحة للتحقق من الهوية ({str(exc)[:70]})\")\n"
        "            continue\n"
        "        if got == want:\n"
        "            urls.append(u)\n"
        "        else:\n"
        "            identity_fail.append(\n"
        "                f\"{u}: القناة لا تخدم بناءنا (بصمة {got[:12]} ≠ {want[:12]}) — لا يُدقَّق محتوى جهة أخرى\")\n"
        "    reports = [audit(u, shots, a.min_touch) for u in urls]",
        1,
    )
    if "import urllib.request" not in t:
        t = t.replace("import json", "import hashlib\nimport json\nimport urllib.request", 1)
    t = t.replace(
        "    for b in blocking:\n        print(f\"   ✘ {b}\")",
        "    blocking = identity_fail + blocking\n    for b in blocking:\n        print(f\"   ✘ {b}\")",
        1,
    )
    AUDIT.write_text(t, encoding="utf-8")
    print("   أداة التدقيق: شرط الهوية أُضيف")


def patch_manifest() -> None:
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for s in d.get("steps", []):
        if s.get("id") == "D020":
            s["command"] = ["bash", "-lc", D020_CMD]
            MANIFEST.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("   خطوة D020: تُدقّق القناة الأساسية بشرط بصمة")
            return
    print("   ✘ لم تُوجد خطوة D020")


if __name__ == "__main__":
    patch_audit()
    patch_manifest()