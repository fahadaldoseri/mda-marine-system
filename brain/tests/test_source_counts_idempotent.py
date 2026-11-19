"""اختبار انحدار: كتابة أرقام المصادر في المتن متساوية القوى (2026-11-19).

العطل المقيس: `tools/source_counts.py --write` يُستدعى من `tests/run_checks.sh` على تقرير
اليوم الحقيقي (في G001 وفي بوابة التسليم وقبل الدفع). وكان كل استدعاء يزيد سطرًا فارغًا
تحت «## ما لم يُحسم» وتحت «## المصادر والمراجع»، لأن نمط العنوان `\\s*$` يبتلع الأسطر
الفارغة التالية فيبقيها، ولأن إزالة سطر «إجمالي الوقائع المرمزة» كانت تترك الفاصل المحقون
معه. فتغيّرت بصمة النص بعد تسجيلها (G042)، وخالف التقرير المودَع النص الذي اجتاز البوابة.
في تقرير 2026-11-19 تراكمت 11 سطرًا فارغًا بهذه الطريقة.

الحالة الموجبة: الكتابة الثانية والثالثة تعطيان البايتات نفسها التي أعطتها الأولى.
الحالة السالبة: نص بأسطر فارغة متراكمة يُطبَّع إلى فاصل واحد، ولا يضيع أي سطر غير فارغ.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATE = "2026-11-09"


def load_module():
    spec = importlib.util.spec_from_file_location("source_counts_idem", ROOT / "tools" / "source_counts.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


REPORT = (
    "## الخلاصة\n\nنص الخلاصة.\n\n"
    "## ما لم يُحسم\n\n\n\n\n| المسألة | الجهة |\n|---|---|\n| أ | ب |\n\n"
    "## حالة المصادر والإفصاح\nقديم.\n\n"
    "## المصادر والمراجع\n\n\n\n- مرجع رسمي.\n"
)


def build_tree(tmp: pathlib.Path) -> pathlib.Path:
    for sub in ("reports", "feeds", "web/meta", "cumulative-2026/daily", "appendices"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    report = tmp / "reports" / f"{DATE}-sectioned.md"
    report.write_text(REPORT, encoding="utf-8")
    (tmp / "web" / "meta" / f"{DATE}.json").write_text("{}", encoding="utf-8")
    (tmp / "feeds" / f"feeds-{DATE}.status.json").write_text(json.dumps({
        "date": DATE, "checked": 60, "ok": 59, "failed": 1, "items": 1800,
        "manual_reference": ["a", "b"], "stale": [],
        "failed_feeds": [{"num": 62, "name": "مصدر", "block_reason": "403"}],
    }, ensure_ascii=False), encoding="utf-8")
    (tmp / "cumulative-2026" / "daily" / f"{DATE}.json").write_text(json.dumps(
        [{"source": "UKMTO"}, {"source": "IMO"}], ensure_ascii=False), encoding="utf-8")
    return report


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _write(mod, report: pathlib.Path) -> str:
    c = mod.counts(DATE)
    ok, msg = mod.inject(DATE, c)
    assert ok, msg
    return _sha(report)


def test_repeated_write_is_byte_identical(tmp_path: pathlib.Path) -> None:
    mod = load_module()
    report = build_tree(tmp_path)
    mod.B = tmp_path
    mod.approved_count = lambda: 62
    first = _write(mod, report)
    second = _write(mod, report)
    third = _write(mod, report)
    assert first == second == third, "الكتابة المتكررة غيّرت بايتات المتن"


def test_accumulated_blank_lines_collapse_without_losing_content(tmp_path: pathlib.Path) -> None:
    mod = load_module()
    report = build_tree(tmp_path)
    mod.B = tmp_path
    mod.approved_count = lambda: 62
    before = [line for line in REPORT.splitlines() if line.strip()]
    _write(mod, report)
    text = report.read_text(encoding="utf-8")
    section = text.split("## ما لم يُحسم", 1)[1].split("\n## ", 1)[0]
    assert "\n\n\n" not in section, "بقيت أسطر فارغة متراكمة تحت «ما لم يُحسم»"
    for line in before:
        if line.startswith("قديم"):
            continue  # قسم الحالة يُولَّد من جديد عمدًا
        assert line in text, f"ضاع سطر من المتن: {line}"
    assert text.count("إجمالي الوقائع المرمزة:") == 1
