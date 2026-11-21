#!/usr/bin/env python3
"""رقم الحادث ورقم البلاغ (قرار فهد 21 نوفمبر 2026، الصيغة أ).

1. البلاغ المرتبط بالدليل (update_of/parent_id/duplicate_of) يأخذ رقم حادث أصله ولاحقة تالية.
2. البلاغ غير المرتبط يأخذ رقم حادث جديدًا بتسلسل سنوي؛ و«لا واقعة» لا تأخذ رقمًا.
3. الرقم الصادر لا يُعاد ترقيمه؛ ورابط لاحق يخالفه يعطي تحذيرًا (3) لا تعديلًا.
4. واقعة بلا رقم، أو رقم مكرر، أو رمز محذوف من الدفتر = مخالفة مانعة (2).
5. البطاقة تعرض رقم البلاغ من تاريخ display_from فقط؛ قبله لا تتغير الصفحة.
6. السجل الحقيقي في المستودع يجتاز --check.
"""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
SITE = Path(os.environ.get("SITE_DIR") or B.parent / "site")
sys.path.insert(0, str(B / "tools"))
import assign_incident_ids as aii  # noqa: E402

FAILS = []


def expect(cond, msg):
    print(("  ✔ " if cond else "  ✘ ") + msg)
    if not cond:
        FAILS.append(msg)


def row(code, date, **kw):
    r = {"code": code, "date": date, "title": "t", "class": "بلاغ رسمي"}
    r.update(kw)
    return r


def make_root(days: dict) -> Path:
    root = Path(tempfile.mkdtemp())
    (root / "cumulative-2026" / "daily").mkdir(parents=True)
    (root / "appendices").mkdir()
    for date, rows in days.items():
        (root / "cumulative-2026" / "daily" / f"{date}.json").write_text(
            json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return root


DAYS = {
    "2026-11-17": [row("MN-2026-11-17-01", "2026-11-17"), row("MN-2026-11-17-02", "2026-11-17")],
    "2026-11-18": [row("MN-2026-11-18-01", "2026-11-18", update_of="MN-2026-11-17-01"),
                   {"code": "NI-2026-11-18", "date": "2026-11-18", "class": "no_incident"}],
    "2026-11-20": [row("MN-2026-11-20-01", "2026-11-20", duplicate_of="MN-2026-11-18-01"),
                   row("MN-2026-11-20-02", "2026-11-20")],
}


def run(root, *args):
    return aii.main([*args, "--root", str(root)])


def registry(root):
    return json.loads((root / "appendices" / "incident-id-map.json").read_text(encoding="utf-8"))


print("1-2) التعيين")
root = make_root(DAYS)
expect(run(root, "--apply") == 0, "--apply على دفتر سليم يرجع 0")
codes = registry(root)["codes"]
expect(codes["MN-2026-11-17-01"] == {"incident_id": "H-2026-0001", "report_id": "H-2026-0001/1"},
       "أول بلاغ = H-2026-0001/1")
expect(codes["MN-2026-11-17-02"]["incident_id"] == "H-2026-0002", "بلاغ غير مرتبط = حادث جديد H-2026-0002")
expect(codes["MN-2026-11-18-01"]["report_id"] == "H-2026-0001/2", "تحديث بعد يوم = البلاغ 2 من الحادث نفسه")
expect(codes["MN-2026-11-20-01"]["report_id"] == "H-2026-0001/3", "تكرار لتحديث بعد يومين = البلاغ 3 (سلسلة الأصل)")
expect(codes["MN-2026-11-20-02"]["incident_id"] == "H-2026-0003", "التسلسل السنوي يستمر")
expect("NI-2026-11-18" not in codes, "«لا واقعة» بلا رقم")
expect(registry(root).get("display_from") == aii.DISPLAY_FROM, "display_from محفوظ في السجل")

print("3) لا إعادة ترقيم")
before = registry(root)
expect(run(root, "--apply") == 0 and registry(root) == before, "تشغيل ثانٍ لا يغيّر السجل")
days2 = copy.deepcopy(DAYS)
days2["2026-11-20"][1]["parent_id"] = "MN-2026-11-17-02"
root2 = make_root(days2)
(root2 / "appendices" / "incident-id-map.json").write_text(json.dumps(before, ensure_ascii=False), encoding="utf-8")
expect(run(root2, "--apply") == 3, "رابط لاحق يخالف رقمًا صادرًا = تحذير 3")
expect(registry(root2)["codes"]["MN-2026-11-20-02"]["incident_id"] == "H-2026-0003", "والرقم الصادر لم يتغير")
days3 = copy.deepcopy(DAYS)
days3["2026-11-21"] = [row("MN-2026-11-21-01", "2026-11-21", update_of="MN-2026-11-17-02")]
root3 = make_root(days3)
(root3 / "appendices" / "incident-id-map.json").write_text(json.dumps(before, ensure_ascii=False), encoding="utf-8")
expect(run(root3, "--apply") == 0, "واقعة جديدة مرتبطة بحادث قديم")
c3 = registry(root3)["codes"]
expect(c3["MN-2026-11-21-01"]["report_id"] == "H-2026-0002/2", "تأخذ اللاحقة التالية للحادث القديم")
expect(all(c3[k] == v for k, v in before["codes"].items()), "ولا يتغير أي رقم صادر")

print("4) مخالفات مانعة")
root4 = make_root(DAYS)
expect(run(root4, "--check") == 2, "--check بلا سجل = 2 (وقائع بلا رقم)")
bad = copy.deepcopy(before)
bad["codes"]["MN-2026-11-17-02"]["report_id"] = "H-2026-0001/1"
bad["codes"]["MN-2026-11-17-02"]["incident_id"] = "H-2026-0001"
(root4 / "appendices" / "incident-id-map.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
expect(run(root4, "--check") == 2, "رقم بلاغ مكرر = 2")
gone = copy.deepcopy(before)
gone["codes"]["MN-2099-01-01-01"] = {"incident_id": "H-2099-0001", "report_id": "H-2099-0001/1"}
(root4 / "appendices" / "incident-id-map.json").write_text(json.dumps(gone, ensure_ascii=False), encoding="utf-8")
expect(run(root4, "--check") == 2, "رمز في السجل غائب عن الدفتر = 2")
fmt = copy.deepcopy(before)
fmt["codes"]["MN-2026-11-17-01"]["report_id"] = "H-2026-1/1"
(root4 / "appendices" / "incident-id-map.json").write_text(json.dumps(fmt, ensure_ascii=False), encoding="utf-8")
expect(run(root4, "--check") == 2, "صيغة غير معتمدة = 2")
days5 = copy.deepcopy(DAYS)
days5["2026-11-18"][0]["parent_id"] = "MN-2026-11-17-02"
root5 = make_root(days5)
expect(run(root5, "--apply") == 2, "حقلا علاقة بهدفين مختلفين = 2")

print("5) العرض في البطاقة")
sys.path.insert(0, str(SITE / "generator"))
try:
    import build_report as br
except Exception as exc:  # المولّد غير متاح خارج شجرة الموقع
    br = None
    expect(False, f"تعذر تحميل المولّد: {exc}")
if br is not None:
    site = Path(tempfile.mkdtemp())
    (site / "sources" / "reports").mkdir(parents=True)
    md = site / "sources" / "reports" / "x.md"
    reg = {"display_from": "2026-11-21", "codes": {
        "MN-2026-11-21-01": {"incident_id": "H-2026-0439", "report_id": "H-2026-0439/1"},
        "MN-2026-11-20-01": {"incident_id": "H-2026-0435", "report_id": "H-2026-0435/1"}}}
    (site / "sources" / "incident-id-map.json").write_text(json.dumps(reg), encoding="utf-8")
    chip = br._incident_chip({"code": "MN-2026-11-21-01", "date": "2026-11-21"}, md)
    expect('data-report-id="H-2026-0439/1"' in chip and ">H-2026-0439/1<" in chip, "يوم العرض: الشارة تحمل رقم البلاغ")
    expect(br._incident_chip({"code": "MN-2026-11-20-01", "date": "2026-11-20"}, md) == "",
           "قبل display_from: لا شارة (الصفحات المنشورة لا تتغير)")
    expect(br._incident_chip({"code": "MN-2026-11-21-09", "date": "2026-11-21"}, md) == "", "رمز بلا رقم: لا شارة")
    empty = Path(tempfile.mkdtemp()) / "sources" / "reports" / "y.md"
    expect(br._incident_chip({"code": "MN-2026-11-21-01", "date": "2026-11-21"}, empty) == "", "بلا سجل: لا شارة")

print("6) السجل الحقيقي")
expect(aii.main(["--check", "--root", str(B)]) in (0, 3), "brain/appendices/incident-id-map.json يجتاز --check")

print(f"\nالنتيجة: فشل {len(FAILS)}")
sys.exit(1 if FAILS else 0)
