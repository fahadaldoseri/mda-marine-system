"""اختبار انحدار: جملة إجمالي الفحص تُشتق من حالة التغذيات الحاكمة (ك-593 · ك-594).

العطل الذي يحرسه هذا الاختبار: متن اليوم حمل أرقامًا متخالفة عن الفحص نفسه —
سطر الإفصاح «59 ناجحة · 1 متعذّر» مقابل جملة إجمالي قديمة «نجحت 51 · وفشلت 9 ·
1875 عنصرًا» — والماستر الإنجليزي حمل القياس القديم نفسه، فرفض حارس التماثل النشر.
الإصلاح الجذري: مصدر واحد (feeds/feeds-<date>.status.json) يغذّي المتنين معًا.

الحالة الموجبة: حالة تغذيات مغايرة للأرقام المكتوبة ⇒ تُعاد الكتابة للأرقام الحاكمة.
الحالة السالبة: قياس حاكم مخالف لسطر المتن ⇒ الحارس يمنع.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("source_counts_mod", ROOT / "tools" / "source_counts.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def build_tree(tmp: pathlib.Path, ar_line: str, en_line: str, state: dict) -> None:
    (tmp / "reports").mkdir(parents=True, exist_ok=True)
    (tmp / "feeds").mkdir(parents=True, exist_ok=True)
    (tmp / "web" / "meta").mkdir(parents=True, exist_ok=True)
    site_en = tmp / "site" / "sources" / "i18n" / "en"
    site_en.mkdir(parents=True, exist_ok=True)
    (tmp / "reports" / "2026-11-09-sectioned.md").write_text(ar_line + "\n", encoding="utf-8")
    (site_en / "2026-11-09-sectioned.en.md").write_text(en_line + "\n", encoding="utf-8")
    (tmp / "feeds" / "feeds-2026-11-09.status.json").write_text(
        json.dumps(state, ensure_ascii=False), encoding="utf-8")


def governed_state(ok: int = 59, failed: int = 1, items: int = 1851) -> dict:
    return {
        "date": "2026-11-09",
        "checked": ok + failed,
        "ok": ok,
        "failed": failed,
        "items": items,
        "manual_reference": ["a", "b"],
        "failed_feeds": [{"num": 62, "name": "حساب @Yemenarmyeng على X"}],
        "stale": [],
    }


def test_sync_rewrites_stale_totals_in_both_masters(tmp_path: pathlib.Path) -> None:
    mod = load_module()
    ar = "استُشهد في هذا المتن بـ14 مصدرًا مسمّى. فُحصت 60 تغذية، نجحت 51 منها، وفشلت 9، وبلغ مجموع العناصر 1875 عنصرًا. هذا عداد للفحص."
    en = "The text cites 14 named sources. 60 feeds were checked, 51 succeeded, 9 failed, and the total number of items was 1875."
    build_tree(tmp_path, ar, en, governed_state())

    mod.B = tmp_path
    mod.os.environ["SITE_DIR"] = str(tmp_path / "site")
    c = {"approved": 62, "checked": 60, "ok": 59, "failed": 1, "reasons": {"timeout": ["حساب @Yemenarmyeng على X"]},
         "manual_reference_present": True, "manual_reference": ["a", "b"], "manual_reference_count": 2}

    touched = mod.sync_feed_totals("2026-11-09", c)
    assert len(touched) == 2, touched
    ar_body = (tmp_path / "reports" / "2026-11-09-sectioned.md").read_text(encoding="utf-8")
    en_body = (tmp_path / "site" / "sources" / "i18n" / "en" / "2026-11-09-sectioned.en.md").read_text(encoding="utf-8")
    assert mod.feed_totals("2026-11-09", c, "ar") in ar_body
    assert mod.feed_totals("2026-11-09", c, "en") in en_body
    assert "نجحت 51 منها" not in ar_body and "1875" not in ar_body
    assert "51 succeeded" not in en_body and "1875" not in en_body
    assert "1851" in ar_body and "1851" in en_body


def test_check_blocks_divergent_totals(tmp_path: pathlib.Path) -> None:
    mod = load_module()
    ar = "- المصادر: 62 معتمدة = 60 بالمسار الآلي + 2 بالمرجعية اليدوية. الفحص: 59 ناجحة. 1 متعذّر: @Yemenarmyeng — عطل اتصال مؤقت. المرجعية اليدوية: 2 يُفحص يدويًا.\nفُحصت 60 تغذية، نجحت 51 منها، وفشلت 9، وبلغ مجموع العناصر 1875 عنصرًا."
    build_tree(tmp_path, ar, "nothing here", governed_state())
    mod.B = tmp_path
    mod.os.environ["SITE_DIR"] = str(tmp_path / "site")
    c = {"approved": 62, "checked": 60, "ok": 59, "failed": 1, "reasons": {"timeout": ["حساب @Yemenarmyeng على X"]},
         "manual_reference_present": True, "manual_reference": ["a", "b"], "manual_reference_count": 2}
    bad = mod.check("2026-11-09", c)
    joined = " | ".join(bad)
    assert "جملة إجمالي الفحص" in joined, joined


if __name__ == "__main__":
    sys.exit("شغّله عبر pytest")
