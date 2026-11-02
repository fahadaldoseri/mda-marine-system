#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار عقد علاقة الدفتر: موجب + خمس حالات منع فشل مغلق."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validators" / "check_ledger_links.py"


def row(code: str, date: str, *, target: str | None = None,
        evidence: str = "190-26", kind: str = "تحديث",
        title: str = "تحذير UKMTO 190-26") -> dict:
    return {
        "code": code,
        "date": date,
        "class": "بلاغ رسمي",
        "title": title,
        "source": "UKMTO",
        "source_excerpt": "UKMTO WARNING 190-26",
        "event_kind": kind,
        "update_of": target if kind == "تحديث" else None,
        "parent_id": target if kind == "فرع تابع" else None,
        "duplicate_of": target if kind == "تكرار" else None,
        "link_basis": "تسلسل رقمي من الجهة نفسها",
        "link_evidence": evidence,
        "link_status": "مرتبط",
        "counts_as_new": kind != "تكرار",
    }


def run_case(rows_by_day: dict[str, list[dict]]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix="ledger-link-contract-") as tmp:
        brain = pathlib.Path(tmp)
        daily = brain / "cumulative-2026" / "daily"
        daily.mkdir(parents=True)
        for day, rows in rows_by_day.items():
            (daily / f"{day}.json").write_text(
                json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8",
            )
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--date", "2026-11-02", "--brain", str(brain),
             "--site", str(brain / "site")],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return proc.returncode, proc.stdout


def check(name: str, condition: bool, detail: str = "") -> bool:
    if condition:
        print(f"  ✔ {name}")
        return True
    print(f"  ✘ {name} — {detail}")
    return False


def main() -> int:
    target = row("MN-2026-11-01-01", "2026-11-01", kind="جديد", target=None,
                 evidence="", title="تحذير UKMTO 190-26")
    good = row("MN-2026-11-02-01", "2026-11-02", target=target["code"], evidence="190-26")
    cases: list[tuple[str, int, dict[str, list[dict]], tuple[str, ...]]] = [
        (
            "الحالة الموجبة الحقيقية: دليل حرفي في حقول الصف المصدر",
            0,
            {"2026-11-01": [target], "2026-11-02": [good]},
            (),
        ),
        (
            "دليل مختلق يمنع",
            2,
            {"2026-11-01": [target], "2026-11-02": [row(good["code"], good["date"], target=target["code"], evidence="999-99")]},
            (good["code"], "999-99"),
        ),
        (
            "مكوّن دليل ناقص يمنع",
            2,
            {"2026-11-01": [target], "2026-11-02": [row(good["code"], good["date"], target=target["code"], evidence="190-26؛ مكوّن-غير-موجود")]},
            (good["code"], "مكوّن-غير-موجود"),
        ),
        (
            "هدف غير موجود يمنع",
            2,
            {"2026-11-02": [row(good["code"], good["date"], target="MN-NOT-FOUND", evidence="190-26")]},
            (),
        ),
        (
            "الإحالة الذاتية تمنع",
            2,
            {"2026-11-02": [row(good["code"], good["date"], target=good["code"], evidence="190-26")]},
            (),
        ),
        (
            "الدورة تمنع",
            2,
            {"2026-11-02": [
                row("MN-2026-11-02-01", "2026-11-02", target="MN-2026-11-02-02", evidence="190-26"),
                row("MN-2026-11-02-02", "2026-11-02", target="MN-2026-11-02-01", evidence="190-26"),
            ]},
            (),
        ),
    ]
    passed = 0
    for name, expected, fixture, required_text in cases:
        rc, output = run_case(fixture)
        ok = rc == expected
        if expected == 2 and required_text:
            ok = ok and all(piece in output for piece in required_text)
        if check(f"{name} (rc={rc})", ok, f"المتوقع {expected} والواقع {rc}; {output.strip()}"):
            passed += 1
    print(f"  نجح {passed} · فشل {len(cases) - passed}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
