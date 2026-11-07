#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار بوابة نظافة أسطح الإصدار والإضافات.

كل حالة تكتب HTML مصغرًا داخل tempfile، ثم تشغّل البوابة الحقيقية عبر CLI.
الموجب يخرج 0، والسالب يخرج 2 ويذكر سبب المنع، وفي النهاية يطبع الاختبار
جدول الحالات ثم «نجح N · فشل 0» عند النجاح.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "validators" / "check_surface_hygiene.py"


def clean_report(extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="ar"><head>
<style>.internal {{ content: 'Z1 MN-2026-11-03-01 A/1'; }}</style>
<script>const internal = 'EST-2026-11-03-01';</script>
</head><body>
<div hidden><code>Z2 BF-2026-11-03-01 IMO-2026-11-03-01 F/6</code></div>
<h2>مستوى التهديد</h2>
<section><p>المستوى العام منخفض مع متابعة يومية للوقائع.</p></section>
<a href="/additions.html">أهم الأخبار</a>
{extra}
</body></html>"""


def clean_additions(extra: str = "") -> str:
    return f"""<!doctype html><html lang="ar"><body>
<h2>أهم الأخبار المتعلقة بالأمن البحري</h2>
<p>خبر موثق وتفاصيل متابعة مهنية.</p>
{extra}
</body></html>"""


def run_gate(report: Path, additions: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--report",
            str(report),
            "--additions",
            str(additions),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_case(
    root: Path,
    report_html: str,
    additions_html: str,
) -> subprocess.CompletedProcess[str]:
    report = root / "report.html"
    additions = root / "additions.html"
    report.write_text(report_html, encoding="utf-8")
    additions.write_text(additions_html, encoding="utf-8")
    return run_gate(report, additions)


def main() -> int:
    passed = 0
    failed = 0
    rows: list[tuple[str, str, int, int]] = []

    def check(
        rule: str,
        polarity: str,
        result: subprocess.CompletedProcess[str],
        expected: int,
        needle: str = "",
    ) -> None:
        nonlocal passed, failed
        output = result.stdout + result.stderr
        good = result.returncode == expected and (not needle or needle in output)
        if good:
            passed += 1
            print(f"  ✔ {rule} | {polarity} | رمز الخروج {result.returncode}")
        else:
            failed += 1
            print(
                f"  ✘ {rule} | {polarity} | المتوقع {expected} والواقع {result.returncode}"
            )
            print("    المخرج:", output.strip())
        rows.append((rule, polarity, result.returncode, expected))

    with tempfile.TemporaryDirectory(prefix="surface-hygiene-") as directory:
        root = Path(directory)

        # موجب مشترك: السطح نظيف، والرموز الداخلية محصورة في CSS/JS وكتلة مخفية.
        result = run_case(root, clean_report(), clean_additions())
        for rule in (
            "تكرار عنوان h2",
            "الرموز الداخلية",
            "النصوص البديلة",
            "طول قسم مستوى التهديد",
            "عنوان تتبع الوقائع",
            "موضع أهم الأخبار",
        ):
            check(rule, "موجب — سطح نظيف", result, 0)

        result = run_case(
            root,
            clean_report("<h2>قسم مكرر</h2><h2>قسم مكرر</h2>"),
            clean_additions(),
        )
        check("تكرار عنوان h2", "سالب — عنوان مكرر", result, 2, "مكرر")

        result = run_case(
            root,
            clean_report("<p>Z1 · A/1 · B/2 · C/3 · D/4 · E/5 · F/6</p>"),
            clean_additions(),
        )
        check("الرموز الداخلية", "سالب — وسم قطاع ودرجة إسناد ظاهران", result, 2, "رمز داخلي")

        result = run_case(
            root,
            clean_report("<p>MN-2026-11-03-01 · EST-2026-11-03-01</p>"),
            clean_additions(),
        )
        check(
            "الرموز الداخلية",
            "سالب — رمز سجل ورمز تقدير في متن مستوى التهديد",
            result,
            2,
            "متن «مستوى التهديد»",
        )

        result = run_case(
            root,
            clean_report("<h2>سجل الأحداث</h2><p>MN-2026-11-03-01 · EST-2026-11-03-01</p>"),
            clean_additions(),
        )
        check(
            "الرموز الداخلية",
            "موجب — رمز السجل في موضعه المصمَّم خارج قسم التهديد",
            result,
            0,
        )

        result = run_case(
            root,
            clean_report(
                "<p>الترجمة غير مدرجة في الدفتر · "
                "لا تتوفر إحداثيات قابلة للرسم</p>"
            ),
            clean_additions(),
        )
        check("النصوص البديلة", "سالب — نص بديل ظاهر", result, 2, "نص بديل")

        result = run_case(
            root,
            clean_report("<p>النصان الكاملان غير متاحين في المواد الحالية</p>"),
            clean_additions(),
        )
        check("النصوص البديلة", "موجب — إفصاح مشروع عن معلومة غائبة", result, 0)

        long_body = " ".join(f"كلمة{i}" for i in range(1, 112))
        result = run_case(
            root,
            clean_report(
                f'<section><h2>مستوى التهديد</h2><p>{long_body}</p></section>'
            ),
            clean_additions(),
        )
        check("طول قسم مستوى التهديد", "سالب — 111 كلمة", result, 2, "111")

        production_site = Path(
            os.environ.get("SITE_DIR", str(ROOT.parent / "seawatch"))
        )
        result = run_gate(
            production_site / "dist" / "reports" / "2026-11-07.html",
            production_site / "dist" / "additions.html",
        )
        check(
            "طول قسم مستوى التهديد",
            "موجب — الإصدار المبني لا يتجاوز السقف",
            result,
            0,
        )

        result = run_case(
            root,
            clean_report(),
            clean_additions("<h2>تتبع الوقائع</h2>"),
        )
        check("عنوان تتبع الوقائع", "سالب — عنوان محظور", result, 2, "تتبع الوقائع")

        result = run_case(
            root,
            clean_report("<h2>أهم الأخبار المتعلقة بالأمن البحري</h2>"),
            clean_additions(),
        )
        check("موضع أهم الأخبار", "سالب — حاضر في صفحة الإصدار", result, 2, "صفحة الإصدار")

        missing_report = root / "missing-report.html"
        additions = root / "additions.html"
        additions.write_text(clean_additions(), encoding="utf-8")
        result = run_gate(missing_report, additions)
        check("مدخلات البوابة", "سالب — ملف مفقود", result, 2, "الملف غير موجود")

        empty_report = root / "empty-report.html"
        empty_report.write_text("", encoding="utf-8")
        result = run_gate(empty_report, additions)
        check("مدخلات البوابة", "سالب — ملف فارغ", result, 2, "الملف فارغ")

    print("\nجدول الحالات:")
    print("  القاعدة | الحالة | رمز الخروج | المتوقع")
    for rule, polarity, actual, expected in rows:
        print(f"  {rule} | {polarity} | {actual} | {expected}")
    print(f"نجح {passed} · فشل {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
