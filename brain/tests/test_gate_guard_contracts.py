#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""عقود اختبار للحراس التي كشفها gate_audit.

كل حالة تقيس منطق الحارس نفسه، لا مجرد وجود أمره في runbook:
حالة موجبة تمر، وحالة سالبة تمنع أو تُبلغ بالمخالفة. الحارس البصري مستثنى
من هذا الملف لأنه يحتاج متصفحًا حيًا؛ عقده المفتوح موثق في تقرير الفرز.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FAILURES: list[str] = []


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label: str, condition: bool) -> None:
    print(f"  {'✔' if condition else '✘'} {label}")
    if not condition:
        FAILURES.append(label)


def test_findings_closed() -> None:
    m = load("validators/check_findings_closed.py", "guard_findings_closed")
    with tempfile.TemporaryDirectory() as td:
        m.LIB = Path(td)
        reg = m.LIB / "findings-register.md"
        reg.write_text("| الحالة |\n|---|\n| مغلق |\n", encoding="utf-8")
        check("findings_closed موجب: سجل مغلق", m.open_findings() == (0, 1))
        reg.write_text("| الحالة |\n|---|\n| مفتوح |\n", encoding="utf-8")
        check("findings_closed سالب: سجل مفتوح", m.open_findings() == (1, 0))


def test_code_policy() -> None:
    m = load("validators/check_code_policy.py", "guard_code_policy")
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "good.html"
        bad = Path(td) / "bad.html"
        good.write_text("<main><section><h2>سجل الأحداث</h2>MN-2026-11-06-01</section></main>", encoding="utf-8")
        bad.write_text("<main><section><h2>بطاقة القرار</h2>MN-2026-11-06-01</section></main>", encoding="utf-8")
        check("code_policy موجب: الرمز داخل سجل الأحداث", m.check_file(good)["outside"] == 0)
        check("code_policy سالب: الرمز خارج سجل الأحداث", m.check_file(bad)["outside"] == 1)

        attribute_only = Path(td) / "attribute-only.html"
        attribute_only.write_text(
            '<main><section><h2>بطاقة القرار</h2>'
            '<span data-code="MN-2026-11-06-01">رمز مخفي في وسم</span>'
            '</section></main>',
            encoding="utf-8",
        )
        result = m.check_file(attribute_only)
        check(
            "code_policy سالب: رمز في وسم بلا نص مرئي لا يُسقط الحارس",
            result["outside"] == 1 and result["samples"],
        )


def test_ofac_coverage() -> None:
    m = load("validators/check_ofac_coverage.py", "guard_ofac_coverage")
    with tempfile.TemporaryDirectory() as td:
        m.SCREEN = Path(td) / "ofac.json"
        m.SCREEN.write_text(json.dumps({"results": [{"target": "VESSEL", "result": "no_match"}]}), encoding="utf-8")
        with patch.object(m, "from_report", lambda _date: ["VESSEL"]), patch.object(sys, "argv", ["guard", "--date", "2026-11-06"]):
            check("ofac_coverage موجب: نتيجة لا تطابق", m.main() == 0)
        m.SCREEN.write_text(json.dumps({"results": []}), encoding="utf-8")
        with patch.object(m, "from_report", lambda _date: ["VESSEL"]), patch.object(sys, "argv", ["guard", "--date", "2026-11-06"]):
            check("ofac_coverage سالب: سفينة بلا نتيجة", m.main() == 2)


def test_portable_paths() -> None:
    m = load("validators/check_portable_paths.py", "guard_portable_paths")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m.BRAIN, m.SITE = root / "brain", root / "site"
        m.BRAIN.mkdir(); m.SITE.mkdir()
        m.LITERALS = (m.BRAIN.as_posix(), m.SITE.as_posix())
        m.PAT = re.compile("|".join(re.escape(x) for x in m.LITERALS))
        (m.BRAIN / "good.py").write_text("ROOT = Path(__file__).resolve().parents[1]\n", encoding="utf-8")
        check("portable_paths موجب: جذر مشتق من الملف", m.scan() == [])
        # نبني المخالفة من الجذر المؤقت حتى يبقى الاختبار محمولًا وقابلًا لإعادة التشغيل.
        (m.BRAIN / "bad.py").write_text(f'ROOT = "{m.BRAIN.as_posix()}"\n', encoding="utf-8")
        check("portable_paths سالب: مسار مطلق في شيفرة", bool(m.scan()))


def test_numerals() -> None:
    m = load("validators/check_numerals.py", "guard_numerals")
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "good.txt"
        bad = Path(td) / "bad.txt"
        good.write_text("العدد 12\n", encoding="utf-8")
        # الحالة السالبة: أرقام عربية-هندية فعلية (٠١٢٣…) لا أرقام لاتينية مكرَّرة.
        bad.write_text("العدد \u0661\u0662\n", encoding="utf-8")
        check("numerals موجب: أرقام لاتينية", m.nums(good) == 0)
        check("numerals سالب: أرقام عربية هندية", m.nums(bad) > 0)


def test_skills_integrity() -> None:
    m = load("validators/check_skills_integrity.py", "guard_skills_integrity")
    with tempfile.TemporaryDirectory() as td:
        m.SK = Path(td) / "skills"
        m.REPO = Path(td) / "missing-repo"
        (m.SK / "demo").mkdir(parents=True)
        skill = m.SK / "demo" / "SKILL.md"
        skill.write_text("---\nname: demo\ndescription: d\n---\nالشاهد\n", encoding="utf-8")
        m.REQUIRED = [("demo/SKILL.md", "الشاهد", "قاعدة")]
        with patch.object(sys, "argv", ["guard"]):
            check("skills_integrity موجب: شاهد موجود", m.main() == 0)
        skill.write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        with patch.object(sys, "argv", ["guard"]):
            check("skills_integrity سالب: شاهد مفقود", m.main() == 2)


def test_libraries_skills() -> None:
    m = load("validators/check_libraries_skills.py", "guard_libraries_skills")
    with tempfile.TemporaryDirectory() as td:
        m.LIBS = Path(td) / "libraries"
        m.LIBS.mkdir()
        m.findings.clear()
        (m.LIBS / "clean.md").write_text("مكتبة سليمة\n", encoding="utf-8")
        m.check_libs()
        check("libraries_skills موجب: مكتبة قابلة للقراءة", not m.findings)
        m.findings.clear()
        (m.LIBS / "secret.json").write_text('{"chat_id": "-100123456789"}\n', encoding="utf-8")
        m.check_libs()
        check("libraries_skills سالب: سر محتمل في مكتبة", any(x[0] == "عائق" for x in m.findings))


def test_library_use() -> None:
    m = load("validators/check_library_use.py", "guard_library_use")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m.B = root
        m.BANK = root / "appendices" / "glossary-standard.json"
        m.GAPS = root / "appendices" / "libraries" / "terminology-gaps.md"
        (root / "appendices").mkdir()
        (root / "appendices" / "libraries").mkdir()
        (root / "reports").mkdir(); (root / "web" / "meta").mkdir(parents=True)
        (root / "reports" / "2026-11-06-sectioned.md").write_text("تقرير\n", encoding="utf-8")
        meta = root / "web" / "meta" / "2026-11-06.json"
        meta.write_text(json.dumps({"glossary": {"TERM": "تعريف"}}), encoding="utf-8")
        m.BANK.write_text(json.dumps({"symbols": {"TERM": "تعريف"}}), encoding="utf-8")
        with patch.object(sys, "argv", ["guard", "--date", "2026-11-06"]):
            check("library_use موجب: تعريف الإصدار في البنك", m.main() == 0)
        meta.write_text(json.dumps({"glossary": {"MISSING": "تعريف"}}), encoding="utf-8")
        with patch.object(sys, "argv", ["guard", "--date", "2026-11-06"]):
            check("library_use سالب: تعريف خارج البنك", m.main() == 1)


def test_telegram_delivery() -> None:
    m = load("validators/check_telegram_delivery.py", "guard_telegram_delivery")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m.ROOT = root
        m.SEND_LOG = root / "logs" / "telegram-sends.jsonl"
        m.SEND_LOG.parent.mkdir()
        m.SEND_LOG.write_text(json.dumps({"date": "2026-11-06", "decision": "sent"}) + "\n", encoding="utf-8")
        with patch.object(sys, "argv", ["guard", "--date", "2026-11-06", "--quiet"]):
            check("telegram_delivery موجب: سجل إرسال ناجح", m.main() == 0)
        m.SEND_LOG.unlink()
        with patch.object(sys, "argv", ["guard", "--date", "2026-11-06", "--quiet"]):
            check("telegram_delivery سالب: لا محاولة إرسال", m.main() == 1)


def test_source_route_coverage() -> None:
    m = load("validators/check_source_route_coverage.py", "guard_source_route_coverage")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m.B = root
        (root / "feeds").mkdir(); (root / "tools").mkdir()
        (root / "feeds" / "feeds-2026-11-06.status.json").write_text(
            json.dumps({"checked_feeds": [{"num": 1, "ok": True}], "manual_reference": []}), encoding="utf-8")
        (root / "tools" / "content_extractors.py").write_text("def extract():\n    return []\n", encoding="utf-8")
        m.approved = lambda: [1]
        m.routed = lambda: {1}
        m.manual = lambda: set()
        with patch.object(sys, "argv", ["guard", "--date", "2026-11-06"]):
            check("source_route_coverage موجب: المصدر له مسار ناجح", m.main() == 0)
        m.routed = lambda: set()
        with patch.object(sys, "argv", ["guard", "--date", "2026-11-06"]):
            check("source_route_coverage سالب: مصدر بلا مسار", m.main() == 1)


def _threat_fixture(root: Path) -> None:
    (root / "appendices").mkdir(parents=True)
    (root / "web" / "zones").mkdir(parents=True)
    (root / "web" / "meta").mkdir(parents=True)
    (root / "cumulative-2026" / "daily").mkdir(parents=True)
    (root / "reports").mkdir(parents=True)
    (root / "appendices" / "threat-scale.json").write_text(json.dumps({"levels": [{"ar": "منخفض"}]}), encoding="utf-8")
    (root / "appendices" / "zone-registry.json").write_text(json.dumps({"zones": [{"id": "z1", "ar": "الخليج"}]}), encoding="utf-8")
    (root / "web" / "zones" / "2026-11-06.json").write_text(json.dumps({
        "overall": {"level": "منخفض", "top_zone_id": "z1", "top_zone": "الخليج"},
        "zones": [{"id": "z1", "name": "الخليج", "level": "منخفض", "rank": 1, "basis": "واقعة E1", "qualifying_codes": ["E1"]}],
        "events": [{"code": "E1", "zone": "z1"}], "counter": 1}), encoding="utf-8")
    (root / "web" / "meta" / "2026-11-06.json").write_text(json.dumps({
        "threat_level": "منخفض", "decision_card": {"risk": "منخفض"}, "lede": "الخليج", "headline": "منخفض"}), encoding="utf-8")
    (root / "cumulative-2026" / "daily" / "2026-11-06.json").write_text(json.dumps([{"code": "E1"}]), encoding="utf-8")
    (root / "reports" / "2026-11-06-sectioned.md").write_text(
        "المستوى العام: منخفض\nالمستوى في الخليج: منخفض\n", encoding="utf-8")


def test_threat_consistency() -> None:
    m = load("validators/check_threat_consistency.py", "guard_threat_consistency")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _threat_fixture(root)
        check("threat_consistency موجب: مصدر الحكم متسق", m.check_all(root, "2026-11-06") == 0)
        meta = root / "web" / "meta" / "2026-11-06.json"
        data = json.loads(meta.read_text(encoding="utf-8")); data["threat_level"] = "مرتفع"; meta.write_text(json.dumps(data), encoding="utf-8")
        check("threat_consistency سالب: مستوى الواجهة مختلف", m.check_all(root, "2026-11-06") == 2)


def test_event_links() -> None:
    m = load("validators/check_event_links.py", "guard_event_links")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        m.BRAIN = root; m.DAILY = root / "daily"; m.FROZEN = root / "frozen.json"
        m.DAILY.mkdir()
        rows = [{"code": "E1"}, {"code": "E2", "update_of": "E1", "parent_id": "E1", "link_basis": "E1"}]
        (m.DAILY / "2026-11-06.json").write_text(json.dumps(rows), encoding="utf-8")
        with patch.object(sys, "argv", ["guard"]):
            check("event_links موجب: رابط له سند وهدف معروف", m.main() == 0)
        rows[1]["update_of"] = "MISSING"
        (m.DAILY / "2026-11-06.json").write_text(json.dumps(rows), encoding="utf-8")
        with patch.object(sys, "argv", ["guard"]):
            check("event_links سالب: هدف رابط غير معروف", m.main() == 2)


def test_project_skills() -> None:
    m = load("validators/check_project_skills.py", "guard_project_skills")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        surfaces = {name: root / name for name in ("brain", "server", "mirror", "mirror_brain")}
        for path in surfaces.values():
            (path / "demo").mkdir(parents=True)
            (path / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        args = ["--brain", str(surfaces["brain"]), "--server", str(surfaces["server"]),
                "--mirror", str(surfaces["mirror"]), "--mirror-brain", str(surfaces["mirror_brain"])]
        check("project_skills موجب: الأسطح الأربعة متطابقة", m.main(args) == 0)
        (surfaces["mirror"] / "demo" / "SKILL.md").write_text("منحرف\n", encoding="utf-8")
        check("project_skills سالب: سطح المرآة منحرف", m.main(args) == 2)


def test_map_note_counts() -> None:
    m = load("validators/check_map_note_counts.py", "guard_map_note_counts")
    points = [{"qualifying": True, "confirmation": "confirmed"}, {"qualifying": False, "confirmation": ""}]
    calc = m.compute(points)
    problems: list[str] = []
    ok = m.parse_segments("الحالات: مؤكد 1 · مرجّح 0 · غير مؤكد مؤهل 0 · غير مؤهل 1 · حالة غير محددة 0", m.AR_HINTS, "fixture", calc, problems)
    check("map_note_counts موجب: العدادات المعلنة مطابقة", ok and not problems)
    problems = []
    m.parse_segments("الحالات: مؤكد 2 · مرجّح 0 · غير مؤكد مؤهل 0 · غير مؤهل 1 · حالة غير محددة 0", m.AR_HINTS, "fixture", calc, problems)
    check("map_note_counts سالب: عداد مؤكد مختلف", bool(problems))


def test_vocab_chain() -> None:
    m = load("validators/check_vocab_chain.py", "guard_vocab_chain")
    blocks, warns = m.classify([("autoreplace", "قديم", "بديل")], {"ممنوع"})
    check("vocab_chain موجب: بديل لا يعيد لفظًا ممنوعًا", not blocks and not warns)
    blocks, _ = m.classify([("autoreplace", "ممنوع", "بديل ممنوع")], {"ممنوع"})
    check("vocab_chain سالب: البديل يعيد لفظًا ممنوعًا", bool(blocks))


def main() -> int:
    test_findings_closed()
    test_code_policy()
    test_ofac_coverage()
    test_portable_paths()
    test_numerals()
    test_skills_integrity()
    test_libraries_skills()
    test_library_use()
    test_telegram_delivery()
    test_source_route_coverage()
    test_threat_consistency()
    test_event_links()
    test_project_skills()
    test_map_note_counts()
    test_vocab_chain()
    print(f"الحصيلة: اختبارات ناجحة {30 - len(FAILURES)} · فاشلة {len(FAILURES)}")
    if FAILURES:
        print("الفاشل: " + " · ".join(FAILURES))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
