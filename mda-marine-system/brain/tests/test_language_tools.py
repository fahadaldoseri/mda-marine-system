#!/usr/bin/env python3
"""اختبارات دائمة لأدوات محور اللغة (أمر 23 أكتوبر 2026).

تثبت الحفظ اللغوي، وتستخرج مراحل التدريج من إعداد البوابة نفسه، وتثبت أن
المخالفة بعد تاريخ الإنفاذ تعيد رمز المنع بدل الاعتماد على يوم تقرير بعينه.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

B = Path(__file__).resolve().parent.parent
FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f'  {"✔" if ok else "✘"} {name}' + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def preserved(before: str, after: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as td:
        bp, ap = Path(td) / "b.txt", Path(td) / "a.txt"
        bp.write_text(before, encoding="utf-8")
        ap.write_text(after, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(B / "tools" / "preserve_check.py"), str(bp), str(ap)],
            capture_output=True,
            text=True,
        )
        return r.returncode == 0, (r.stdout or "").strip()


def language_gate(date_arg: str, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(B / "tools" / "language_gates.py"),
            "--date",
            date_arg,
            "--md",
            str(report),
        ],
        capture_output=True,
        text=True,
        cwd=B,
    )


# 1) حارس الحفظ
ok, why = preserved(
    "وصلت الناقلة إلى 26°12.34N وحمولتها 15 ألف طن.",
    "وصلت الناقلة إلى 26°12.34N وحمولتها 16 ألف طن.",
)
check("الحارس يرفض تغيير رقم", not ok, why)
ok, _ = preserved(
    "وصلت الناقلة 26°12.34N وفق بلاغ UKMTO.",
    "بلغت الناقلة 26°12.34N وفق بلاغ UKMTO.",
)
check("الحارس يقبل تحريرًا لغويًا آمنًا", ok)
ok, _ = preserved("أفادت UKMTO بمشاهدة قارب مسيّر.", "أفادت UKMTO بمشاهدة زورق مسيّر.")
check("الحارس يقبل استبدال مفردة", ok)

# 2) تدريج بوابة اللغة: التواريخ والرموز من الإعداد لا من تقرير اليوم.
# ك-485: النص «النظيف» كان تقريرًا قديمًا (2026-11-01) سبق قواعد لاحقة فصار مخالفًا،
# فأسقط الاختبار بلا علاقة بالبوابة. الأرضية الآن أحدث تقرير — وهو التقرير الذي مُرّر
# فعلًا من بوابات اللغة في الجولة نفسها.
rep_clean = sorted((B / "reports").glob("*-sectioned.md"))[-1]
rep_advisory = B / "reports" / "2026-10-23-sectioned.md"
cfg = json.loads((B / "appendices" / "language-gates.json").read_text(encoding="utf-8"))
advisory_until = date.fromisoformat(cfg["advisory_until"])
enforce_from = date.fromisoformat(cfg["enforce_from"])
advisory_rc = int(cfg["advisory_exit_code"])
enforce_rc = int(cfg["enforce_exit_code"])

if rep_clean.exists() and rep_advisory.exists():
    pre_enforcement_date = (advisory_until - timedelta(days=1)).isoformat()
    r = language_gate(pre_enforcement_date, rep_advisory)
    check(
        f"بوابة اللغة قبل advisory_until تعيد {advisory_rc}",
        r.returncode == advisory_rc,
        f"أعادت {r.returncode}",
    )

    # ك-485: النص «النظيف» القديم كُتب قبل قواعد أحدث، فأصبح مخالفًا وأسقط اختبار التنظيف
    # بلا علاقة بالبوابة. فتُهيَّأ هنا نسخة مؤقتة مطابقة للقواعد النافذة، ويبقى الاختبار
    # يقيس البوابة الحقيقية لا أرضية قديمة. وتُحدَّث القائمة أدناه مع كل قاعدة لاحقة.
    STALE_RULES = (
        ("الموضع", "الموقع"),                     # قاعدة المالك: الموقع لا الموضع (2026-11-03)
        ("غير محددة المصدر", "جهات غير معلومة"),   # قاعدة الإسناد (2026-11-02)
    )
    with tempfile.TemporaryDirectory() as td:
        clean = Path(td) / "language-gate-clean.md"
        clean_text = rep_clean.read_text(encoding="utf-8")
        for old, new in STALE_RULES:
            clean_text = clean_text.replace(old, new)
        clean.write_text(clean_text, encoding="utf-8")
        r = language_gate(enforce_from.isoformat(), clean)
        detail = next(
            (ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip().startswith("✘")),
            "",
        )
        check(
            f"بوابة اللغة من enforce_from على متن نظيف تعيد 0",
            r.returncode == 0,
            f"أعادت {r.returncode}" + (f" · {detail}" if detail else ""),
        )

        bad = Path(td) / "language-gate-negative.md"
        bad.write_text(clean_text + "\n\nعمليات عبور.\n", encoding="utf-8")
        r = language_gate(enforce_from.isoformat(), bad)
        check(
            f"بوابة اللغة من enforce_from على مخالفة تعيد {enforce_rc}",
            r.returncode == enforce_rc,
            f"أعادت {r.returncode}",
        )
else:
    check("تقارير اختبار تدريج اللغة موجودة", False, "لا ملف نظيف أو تنبيهي")

# 3) التحرير بلا --apply لا يكتب في التقرير
if rep_advisory.exists():
    h0 = hashlib.sha256(rep_advisory.read_bytes()).hexdigest()
    r = subprocess.run(
        [
            sys.executable,
            str(B / "tools" / "edit_pass.py"),
            "--report",
            str(rep_advisory),
            "--out-dir",
            str(B / "audit"),
            "--workers",
            "2",
            "--min-chars",
            "100000",
        ],
        capture_output=True,
        text=True,
        cwd=B,
    )
    h1 = hashlib.sha256(rep_advisory.read_bytes()).hexdigest()
    check("التحرير التجريبي لا يغيّر التقرير", h0 == h1)
    check("التحرير التجريبي يعيد رمز نجاح أو تحذير", r.returncode in (0, 1), f"رمز {r.returncode}")

print(f'\n  الحصيلة: {"كل الاختبارات نجحت" if not FAILS else str(len(FAILS)) + " فشل: " + " · ".join(FAILS)}')
sys.exit(1 if FAILS else 0)
