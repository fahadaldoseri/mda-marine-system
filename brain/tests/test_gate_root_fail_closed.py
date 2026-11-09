#!/usr/bin/env python3
"""اختبار سلبي وموجب لفرع الفشل المغلق في اشتقاق جذر الموقع (بند المرحلة أ · خ-09).

يُثبت بلا شبكة وبلا تشغيل البوابة كاملة:
  1) لا جذر صريح ولا مرشّح موجود ⇒ **rc=2** ورسالة صريحة (فشل مغلق، لا مسار مُخمَّن).
  2) مرشّح موجود لكنه **بلا dist** ⇒ rc=2 (وجود المجلد لا يكفي).
  3) مرشّح موجود بـ dist ⇒ rc=0 ويُشتق الجذر الصحيح (إثبات موجب).
  4) جذر صريح صحيح (SITE) ⇒ rc=0 حتى لو أشارت المرساة إلى مسار آخر.
  5) جذر صريح **بلا dist** ⇒ rc=2: الصريح يُحترم ولا يُبحَث له بديل صامت.
  6) البوابة نفسها: تشغيل `tests/run_checks.sh` بمرساة بلا أي مرشّح ⇒ **rc=2** ولا تُشغَّل اختبارات.
الخروج: 0 سليم · 1 فشل.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parent.parent
RESOLVER = B / "tools" / "site_root.sh"
GATE = B / "tests" / "run_checks.sh"

fails: list[str] = []


def env_for(**over: str) -> dict:
    env = dict(os.environ)
    for key in ("SITE", "SITE_DIR", "SITE_CANDIDATES"):
        env.pop(key, None)
    env.update(over)
    return env


def probe(base: str, **over: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(RESOLVER), "--probe", base],
                          capture_output=True, text=True, timeout=120, env=env_for(**over))


def case(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✔ {name}")
    else:
        fails.append(f"{name}{' — ' + detail if detail else ''}")
        print(f"  ✘ {name}{' — ' + detail if detail else ''}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        no_dist = t / "site_no_dist"
        no_dist.mkdir()
        good = t / "site_ok"
        (good / "dist" / "reports").mkdir(parents=True)

        # 1) لا مرشّح موجود
        r = probe(tmp, SITE_CANDIDATES="/nonexistent-xyz")
        case("1) لا جذر ولا مرشّح ⇒ rc=2", r.returncode == 2, f"rc={r.returncode}")
        case("1) الرسالة صريحة ومغلقة", "فشل مغلق" in r.stdout and "dist" in r.stdout, r.stdout.strip()[:60])

        # 2) مرشّح بلا dist
        r = probe(tmp, SITE_CANDIDATES=str(no_dist))
        case("2) مرشّح بلا dist ⇒ rc=2", r.returncode == 2, f"rc={r.returncode}")

        # 3) مرشّح بـ dist
        r = probe(tmp, SITE_CANDIDATES=str(good))
        case("3) مرشّح بـ dist ⇒ rc=0", r.returncode == 0, f"rc={r.returncode}")
        case("3) الجذر المُشتق صحيح", r.stdout.strip() == f"OK {good}", r.stdout.strip()[:70])

        # 4) جذر صريح صحيح مع مرساة مضلِّلة
        r = probe(tmp, SITE=str(good), SITE_CANDIDATES="/nonexistent-xyz")
        case("4) SITE صريح صحيح ⇒ rc=0", r.returncode == 0, f"rc={r.returncode}")

        # 5) جذر صريح بلا dist
        r = probe(tmp, SITE=str(no_dist), SITE_CANDIDATES=str(good))
        case("5) SITE صريح بلا dist ⇒ rc=2", r.returncode == 2, f"rc={r.returncode}")

        # 6) البوابة نفسها تفشل مغلقًا قبل أي اختبار
        env = env_for(SITE_CANDIDATES="/nonexistent-xyz", HOME=tmp)
        g = subprocess.run(["bash", str(GATE)], capture_output=True, text=True, timeout=300, env=env)
        case("6) البوابة ⇒ rc=2", g.returncode == 2, f"rc={g.returncode}")
        case("6) البوابة لم تُشغّل اختبارات", "✘" in g.stdout and "✔" not in g.stdout, g.stdout.strip()[:80])

    if fails:
        print(f"  ✘ فشل الاختبار السلبي: {len(fails)} حالة")
        return 1
    print("  ✔ الفشل المغلق مُثبت: لا مسار مُخمَّن · لا dist لا يمرّ · والصريح يُحترم")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())