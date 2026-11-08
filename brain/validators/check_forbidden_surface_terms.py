#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حاجز ألفاظ الأسطح — يمنع تسرب البنود المانعة إلى مخرجات القارئ.

مصدر الحكم الوحيد هو appendices/style-blacklist.json؛ لا يكتب هذا المدقق في
القائمة ولا يخففها. يفحص المصدر (المتن والواجهة) ومصادر الموقع والصفحة المبنية،
ويفشل مغلقًا عند غياب ملف أو قائمة أو عند وجود أي لفظ مانع.

الخروج: 0 مطابق · 2 منع/مدخل ناقص · 70 انهيار المدقق.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DEFAULT_BRAIN = Path(os.environ.get("BRAIN_DIR") or BASE)
DEFAULT_SITE = Path(os.environ.get("SITE_DIR") or (Path.home() / "seawatch"))
REQUIRED_TERM = "نافذة"


def load_blocking_terms(brain: Path) -> list[str]:
    db_path = brain / "appendices" / "style-blacklist.json"
    if not db_path.is_file():
        raise ValueError(f"قائمة المنع مفقودة: {db_path}")
    try:
        db = json.loads(db_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"قائمة المنع غير قابلة للقراءة: {db_path}: {exc}") from exc
    terms = [str(item.get("term") or "").strip() for item in db.get("blocking", [])]
    terms = sorted({term for term in terms if term})
    if not terms:
        raise ValueError("قائمة المنع فارغة — لا يمكن اعتماد الأسطح")
    return terms


def surface_paths(brain: Path, site: Path, date_iso: str) -> list[tuple[str, Path]]:
    core = [
        ("المتن المصدر", brain / "reports" / f"{date_iso}-sectioned.md"),
        ("ملف الواجهة المصدر", brain / "web" / "meta" / f"{date_iso}.json"),
        ("المتن المنسوخ", site / "sources" / "reports" / f"{date_iso}-sectioned.md"),
        ("ملف الواجهة المنسوخ", site / "sources" / "meta" / f"{date_iso}.json"),
        ("صفحة التقرير", site / "dist" / "reports" / f"{date_iso}.html"),
    ]
    optional = [
        ("صفحة التقرير الإنجليزية", site / "dist" / "reports" / "en" / f"{date_iso}.html"),
        ("صفحة الإضافات", site / "dist" / "additions.html"),
        ("صفحة المصادر", site / "dist" / "sources.html"),
        ("الصفحة الرئيسية", site / "dist" / "index.html"),
    ]
    return core + [item for item in optional if item[1].is_file()]


def scan(brain: Path, site: Path, date_iso: str, required_terms: list[str]) -> dict:
    blocking = load_blocking_terms(brain)
    violations: list[dict] = []
    missing_required = sorted(set(required_terms) - set(blocking))
    if missing_required:
        violations.append({
            "kind": "blacklist-contract",
            "terms": missing_required,
            "reason": "اللفظ المطلوب بقاؤه مانعًا غير موجود في القائمة السوداء",
        })
    for label, path in surface_paths(brain, site, date_iso):
        if not path.is_file():
            violations.append({
                "kind": "missing-surface",
                "surface": label,
                "path": str(path),
                "reason": "سطح مطلوب مفقود — فشل مغلق",
            })
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            violations.append({
                "kind": "unreadable-surface",
                "surface": label,
                "path": str(path),
                "reason": f"تعذرت القراءة — فشل مغلق: {exc}",
            })
            continue
        for term in blocking:
            count = text.count(term)
            if count:
                violations.append({
                    "kind": "blacklist",
                    "surface": label,
                    "path": str(path),
                    "term": term,
                    "count": count,
                })
    return {
        "date": date_iso,
        "brain": str(brain),
        "site": str(site),
        "surfaces": len(surface_paths(brain, site, date_iso)),
        "blocking_terms": len(blocking),
        "violations": violations,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="منع الألفاظ المانعة في أسطح التقرير")
    ap.add_argument("--date", required=True, help="تاريخ الإصدار YYYY-MM-DD")
    ap.add_argument("--brain", default=str(DEFAULT_BRAIN))
    ap.add_argument("--site", default=str(DEFAULT_SITE))
    ap.add_argument("--term", action="append", default=None,
                    help="لفظ يجب أن يبقى مانعًا (يمكن تكراره؛ الافتراضي: نافذة)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    required = a.term if a.term is not None else [REQUIRED_TERM]
    result = scan(Path(a.brain).resolve(), Path(a.site).resolve(), a.date, required)
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["violations"]:
        print(f"منع: حارس الألفاظ المانعة — {len(result['violations'])} مخالفة")
        for item in result["violations"]:
            if item["kind"] == "blacklist":
                print(f"  ✗ [{item['surface']}] {item['term']} ×{item['count']} — {item['path']}")
            else:
                print(f"  ✗ [{item['kind']}] {item.get('reason', '')} — {item.get('path', '')}")
    else:
        print(f"مطابق: حارس الألفاظ المانعة — {result['surfaces']} أسطح · "
              f"{result['blocking_terms']} ألفاظ مانعة · 0 مخالفة")
    return 2 if result["violations"] else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from _guard import run
    except ModuleNotFoundError:  # بيئة بلا الحارس الموحّد: فشل مغلق برمز main نفسه
        def run(fn):
            raise SystemExit(fn())
    run(main)
