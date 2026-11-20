#!/usr/bin/env python3
"""عقد الفحص المسبق المبكر S015 (المقترح ٢، 20 نوفمبر 2026).

موجب: الشجرة الحالية تمرّ.
سالب G000: أرضية مرفوعة لأصل حاكم (نقص مصطنع) ← رمز 2 في الدقيقة الأولى.
سالب G049: صفحة مبنية فقد شريطها عدادات القطاعات ← رمز 2 في الدقيقة الأولى.
وعقد الربط: S015 يأتي بعد S010 مباشرة وقبل S020، وG000 وG049 باقيتان مانعتين في مكانهما.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
SCRIPT = B / "tools" / "early_preflight.sh"
FAILS = []


def expect(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAILS.append(msg)


def run(env_extra: dict, date: str) -> int:
    env = dict(os.environ, **env_extra)
    env.pop("D", None)
    return subprocess.run(["bash", str(SCRIPT), date], cwd=B, env=env, capture_output=True, text=True).returncode


def main() -> int:
    if not SCRIPT.is_file():
        print("  ✘ tools/early_preflight.sh غير موجود")
        return 1
    steps = json.loads((B / "runbook" / "runbook.json").read_text(encoding="utf-8"))["steps"]
    ids = [s["id"] for s in steps]
    expect("S015" in ids and ids.index("S015") == ids.index("S010") + 1 and ids.index("S015") < ids.index("S020"),
           "S015 بعد S010 مباشرة وقبل S020")
    by = {s["id"]: s for s in steps}
    expect(all(by[g].get("on_fail") == "stop" for g in ("S015", "G000", "G049")),
           "S015 وG000 وG049 كلها مانعة (on_fail=stop)")

    site = Path(os.environ.get("SITE_DIR") or B.parent / "site")
    built = sorted(p.stem for p in (site / "dist" / "reports").glob("[0-9]*-[0-9]*-[0-9]*.html")
                   if (B / "web" / "zones" / f"{p.stem}.json").is_file())
    if not built:
        print("  • تخطٍّ معلن: لا صفحة مبنية لاختبار G049 السالب")
        prev = None
    else:
        prev = built[-1]
    after = "9999-12-31"
    expect(run({"SITE": str(site)}, after) == 0, "موجب: الشجرة الحالية تمرّ")

    with tempfile.TemporaryDirectory() as d:
        floor = json.loads((B / "audit" / "asset-floor.json").read_text(encoding="utf-8"))
        path = sorted(floor["files"])[0]
        floor["files"][path]["lines"] = int(floor["files"][path].get("lines") or 0) + 100000
        fp = Path(d) / "floor.json"
        fp.write_text(json.dumps(floor, ensure_ascii=False), encoding="utf-8")
        expect(run({"SITE": str(site), "ASSET_FLOOR": str(fp)}, after) == 2,
               "سالب G000: نقص أصل حاكم يُكشف مبكرًا (رمز 2)")

        if prev:
            fake = Path(d) / "site"
            (fake / "dist" / "reports").mkdir(parents=True)
            shutil.copytree(site / "sources", fake / "sources")
            html = (site / "dist" / "reports" / f"{prev}.html").read_text(encoding="utf-8")
            tampered = re.sub(r'<span class="zs-p[^"]*">.*?</span>', "", html, flags=re.S)
            expect(tampered != html, "التلاعب المصطنع غيّر الصفحة فعلًا")
            (fake / "dist" / "reports" / f"{prev}.html").write_text(tampered, encoding="utf-8")
            expect(run({"SITE": str(fake)}, after) == 2,
                   "سالب G049: شريط بلا عدادات يُكشف مبكرًا (رمز 2)")
    print(f"الحصيلة: فشل {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
