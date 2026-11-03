#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار حاجز أرضية الأصول الحاكمة (ك-483) — سلوك حقيقي على مجلد مؤقت.

الحالات المقيسة:
  1) تأسيس الأرضية ثم فحص الحالة نفسها ⇒ 0
  2) قصّ أسطر من أصل ⇒ 2 (وهذا ما كان يمرّ بلا مانع قبل الحاجز)
  3) نموّ الأصل ⇒ 0، وترتفع الأرضية معه
  4) نقص مقبول صراحةً بلا سبب ⇒ 2 · وبسبب مسجَّل ⇒ 0 ويُدوَّن في السجل
  5) حذف أصل مسجَّل ⇒ 2
الرمز: 0 كل الحالات صحيحة · 1 خلل في الاختبار.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

BRAIN = pathlib.Path(__file__).resolve().parent.parent
VALIDATOR = BRAIN / "validators" / "check_asset_floor.py"
PASS, FAIL = 0, 0


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"  ✔ {msg}")


def bad(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  ✘ {msg}")


def run(cfg: pathlib.Path, floor: pathlib.Path, *extra: str) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(VALIDATOR), "--config", str(cfg), "--floor", str(floor), *extra],
        cwd=BRAIN, capture_output=True, text=True, timeout=300,
    )
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="asset-floor-"))
    try:
        cfg = tmp / "assets.txt"
        floor = tmp / "floor.json"
        asset = tmp / "SKILL.md"
        cfg.write_text(
            f"GLOB {tmp}/*/SKILL.md\nEXCLUDE **/__pycache__/**\n", encoding="utf-8",
        )
        skill_dir = tmp / "demo-skill"
        skill_dir.mkdir()
        asset = skill_dir / "SKILL.md"
        asset.write_text("".join(f"سطر {i}\n" for i in range(20)), encoding="utf-8")

        rc, _ = run(cfg, floor, "--update")
        (ok if rc == 0 else bad)(f"تأسيس الأرضية ⇒ {rc} (المتوقع 0)")

        rc, out = run(cfg, floor)
        (ok if rc == 0 else bad)(f"فحص بلا تغيير ⇒ {rc} (المتوقع 0)")

        original = asset.read_text(encoding="utf-8")
        asset.write_text("".join(original.splitlines(keepends=True)[:-5]), encoding="utf-8")
        rc, out = run(cfg, floor)
        if rc == 2 and "نقص" in out:
            ok("قصّ 5 أسطر ⇒ 2 مع إعلان النقص")
        else:
            bad(f"قصّ 5 أسطر لم يُمنع: rc={rc}")

        asset.write_text(original, encoding="utf-8")
        rc, _ = run(cfg, floor)
        (ok if rc == 0 else bad)(f"الإعادة إلى الأصل ⇒ {rc} (المتوقع 0)")

        asset.write_text(original + "سطر إضافي\n", encoding="utf-8")
        rc, _ = run(cfg, floor, "--update")
        raised = json.loads(floor.read_text(encoding="utf-8"))["files"][asset.as_posix()]["lines"]
        (ok if rc == 0 and raised == 21 else bad)(f"النموّ ⇒ {rc} والأرضية صارت {raised} (المتوقع 0 و21)")

        asset.write_text(original, encoding="utf-8")
        rc, _ = run(cfg, floor)
        (ok if rc == 2 else bad)(f"نقص بعد ارتفاع الأرضية ⇒ {rc} (المتوقع 2)")

        rc, _ = run(cfg, floor, "--accept", "demo-skill/SKILL.md")
        (ok if rc == 2 else bad)(f"قبول نقص بلا سبب ⇒ {rc} (المتوقع 2)")

        rc, out = run(cfg, floor, "--accept", "demo-skill/SKILL.md", "--reason", "حذف مثال مكرر بقرار مالك")
        rec = json.loads(floor.read_text(encoding="utf-8"))["files"][asset.as_posix()]
        logged = rec.get("accepted_reductions", [])
        if rc == 0 and logged and "قرار مالك" in logged[-1].get("reason", ""):
            ok("قبول نقص بسبب مسجَّل ⇒ 0 والقرار مدوَّن في السجل")
        else:
            bad(f"قبول النقص لم يُدوَّن: rc={rc} · السجل={logged}")

        rc, _ = run(cfg, floor)
        (ok if rc == 0 else bad)(f"فحص بعد قبول مسجَّل ⇒ {rc} (المتوقع 0)")

        asset.unlink()
        rc, out = run(cfg, floor)
        (ok if rc == 2 and "مفقود" in out else bad)(f"حذف أصل مسجَّل ⇒ {rc} (المتوقع 2 مع «مفقود»)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"  الحصيلة: نجح {PASS} · فشل {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
