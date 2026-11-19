#!/usr/bin/env python3
"""يولّد ملخص تلغرام (HTML) من `web/meta/<التاريخ>.json` وفق قالب `appendices/telegram-delivery.md` (القسم 4).

لا يرسل شيئًا. المخرج ملف نصي يمرّ بعدها على `telegram_send.py --validate-only` ثم الإرسال بأمر صريح.
الاستعمال: python3 tools/make_tg_digest.py --date YYYY-MM-DD [--out PATH] [--base-url URL]
المسارات: BRAIN_DIR و SITE_DIR تُحترمان.
رموز الخروج: 0 تم · 2 بيانات ناقصة أو الملخص فوق السقف.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

CAP = 900
MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
B = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parent.parent)
MANIFEST = B / "runbook" / "runbook.json"


def primary_channel_url():
    """عنوان القناة الأساسية من المانيفست — رابط القرّاء الرسمي."""
    try:
        doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    for ch in doc.get("publish_channels") or []:
        if ch.get("primary") and ch.get("enabled"):
            return str(ch.get("base_url") or ch.get("url") or "").rstrip("/")
    return ""


def site_base_url():
    primary = primary_channel_url()
    if primary:
        return primary
    for cand in (os.environ.get("SITE_DIR"), B.parent / "seawatch", B.parent / "site"):
        if cand and (Path(cand) / "sources" / "site.json").is_file():
            return json.loads((Path(cand) / "sources" / "site.json").read_text(encoding="utf-8")).get("base_url", "")
    return ""


def _third_person_unit():
    """وحدة أسلوب الغائب من مشروع الموقع (مصدر واحد لمعجم أفعال الأمر)."""
    import importlib.util
    for cand in (os.environ.get("SITE_DIR"), os.environ.get("SITE"), B.parent / "seawatch", B.parent / "site"):
        p = Path(cand) / "generator" / "third_person.py" if cand else None
        if p and p.is_file():
            spec = importlib.util.spec_from_file_location("site_third_person", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "to_masdar"):
                return mod
    return None


def action_line(text):
    """سطر «الإجراء المطلوب» بصيغة المصدر لا الأمر (قرار المالك، 19 نوفمبر 2026):
    «ارفعوا التأهب…» ← «رفع التأهب…». تغيب الوحدة = فشل مغلق، فلا تخرج رسالة بصيغة الأمر."""
    unit = _third_person_unit()
    if unit is None:
        raise SystemExit("✘ وحدة generator/third_person.py (to_masdar) غير موجودة — لا تُبنى الرسالة")
    return unit.to_masdar(clean(text))


def imperative_violations(text):
    unit = _third_person_unit()
    return unit.violations(text) if unit else []


def dtg(t):
    return f"{t.day:02d}{t.hour:02d}{t.minute:02d}Z"


def clean(text):
    """نص البند كاملًا بلا قصّ: الرسالة لا تقطع جملة في منتصفها بنقاط «…».
    ضبط الطول يجري بإسقاط التفاصيل ثم عدد البنود (انظر main) لا بقصّ الكلمات."""
    return re.sub(r"\s+", " ", text or "").strip()


def _hero_kpi_registry() -> dict[str, dict]:
    """Return the governing hero-card contract keyed by card id.

    The daily meta file is a derived surface and has used more than one
    presentation shape over time.  Labels therefore come from the governing
    registry when a derived card omits one; values remain data from the
    derived surface.
    """
    path = B / "appendices" / "card_registry.json"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    cards = ((registry.get("hero_kpis") or {}).get("cards") or [])
    return {
        str(card.get("id")): card
        for card in cards
        if isinstance(card, dict) and card.get("id")
    }


def _hero_kpi_items(meta: dict) -> list[dict]:
    """Normalize list and container forms emitted by the meta builders."""
    raw = meta.get("hero_kpis") or []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in ("cards", "items", "data"):
            nested = raw.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [
            {"id": key, **value}
            for key, value in raw.items()
            if isinstance(value, dict)
        ]
    return []


def _card_field(card: dict, registry_card: dict, keys: tuple[str, ...]):
    for source in (card, registry_card):
        for key in keys:
            value = source.get(key)
            if value is not None and str(value).strip():
                return value
    return ""


def _hero_kpi_line(card: dict, registry: dict[str, dict]) -> str:
    card_id = str(card.get("id") or "")
    contract = registry.get(card_id, {})
    label = _card_field(
        card,
        contract,
        ("label", "display_label", "title", "name", "caption", "key"),
    )
    value = _card_field(
        card,
        {},
        ("value", "current", "count", "total", "number", "amount"),
    )
    if not label:
        label = card_id or "مؤشر"
    return f"{label} {value}".strip()


def more_line(n):
    """سطر الوقائع الباقية بعبارة عربية سليمة بدل «(و1 غيرها …)» (فهد، 19 نوفمبر)."""
    if n == 1:
        return "وواقعة أخرى في التقرير الكامل."
    if n == 2:
        return "وواقعتان أخريان في التقرير الكامل."
    if 3 <= n <= 10:
        return f"و{n} وقائع أخرى في التقرير الكامل."
    return f"و{n} واقعة أخرى في التقرير الكامل."


def build(meta, date, base, detail=True, delivery_note="", max_items=3):
    cut = dt.datetime.strptime(meta["generated_label"], "%Y-%m-%dT%H:%M:%SZ")
    start = cut - dt.timedelta(hours=24)
    bh = cut + dt.timedelta(hours=3)
    event_keys = meta.get("event_keys") or []
    codes = {str(e["code"]): e for e in event_keys
             if isinstance(e, dict) and e.get("code")}
    lines = ["<b>مركز الوعي بالمجال البحري</b>", "",
             f"<b>{meta['title']}</b>",
             f"تقرير رقم: «{meta['version']}»",
             f"التاريخ: {cut.day} {MONTHS[cut.month - 1]} {cut.year}",
             f"الفترة: {dtg(start)}–{dtg(cut)} {MONTHS[cut.month - 1]} {cut.year}",
             f"الوقت: {cut.hour:02d}{cut.minute:02d}Z ({bh.hour:02d}{bh.minute:02d}C بتوقيت البحرين)", "",
             f"<b>مستوى التهديد:</b> {meta['threat_level']}", "", "<b>ما تغيّر عن التقرير السابق:</b>"]
    changes = meta.get("changes", [])[:3]
    for i, c in enumerate(changes[:max_items], 1):
        title = clean((codes.get(c["code"]) or {}).get("title") or c["text"])
        body = clean(c["text"])
        show_body = detail and body and body != title
        # نقطة في آخر البند الخالي من التفاصيل: كل بند جملة مستقلة، وإلا دمج مدقق
        # الأسلوب البنود الثلاثة في جملة واحدة تتجاوز 35 كلمة (G045، 19 نوفمبر).
        # الرمز بلا أقواس بعد كلمة عربية: القوس بعد رمز لاتيني في سطر عربي يُقلب في
        # تلغرام فيظهر «(MN-… 18/11/2026 ·» (لقطة فهد، 19 نوفمبر).
        lines += [f"{i}) {title}، الرمز {c['code']}" + (":" if show_body else ".")]
        if show_body:
            lines.append(body)
    if len(changes) > max_items:
        lines.append(more_line(len(changes) - max_items))
    registry = _hero_kpi_registry()
    kp = " · ".join(
        _hero_kpi_line(card, registry) for card in _hero_kpi_items(meta)[:3]
    )
    if kp:
        lines += ["", "<b>المؤشرات:</b>", kp]
    act = (meta.get("decision_card", {}).get("action") or [""])[0]
    lines += ["", "<b>الإجراء المطلوب:</b>", action_line(act)]
    if delivery_note:
        lines += ["", "<b>قناة التسليم:</b>", delivery_note]
    lines += ["", "<b>التقرير الكامل:</b>", f"{base.rstrip('/')}/reports/{date}.html"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--out")
    ap.add_argument("--base-url")
    a = ap.parse_args()
    mp = B / "web" / "meta" / f"{a.date}.json"
    if not mp.is_file():
        print(f"✘ لا بيانات إصدار: {mp}")
        return 2
    meta = json.loads(mp.read_text(encoding="utf-8"))
    need = ("title", "version", "generated_label", "threat_level", "changes")
    miss = [k for k in need if not meta.get(k)]
    base = a.base_url or site_base_url()
    delivery_note = ""
    publish_path = B / "logs" / f"publish-{a.date}.json"
    try:
        publish = json.loads(publish_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        publish = {}
    if publish.get("status") == "ok" and publish.get("channel") == "github-pages":
        report_url = str(publish.get("url") or "")
        if "/reports/" in report_url:
            base = report_url.split("/reports/", 1)[0]
        delivery_note = (
            "القناة الأساسية (منصة Manus) معطّلة مؤقتًا؛ "
            "أُرسل التقرير عبر القناة البديلة."
        )
    if miss or not base:
        print(f"✘ حقول ناقصة: {miss or ''} {'base_url' if not base else ''}")
        return 2
    for detail, max_items in ((True, 3), (False, 3), (False, 2), (False, 1)):
        text = build(meta, a.date, base, detail, delivery_note, max_items)
        visible = re.sub(r"<[^>]+>", "", text)
        if len(visible) <= CAP:
            break
    bad = imperative_violations(visible)
    if bad:
        print(f"✘ صيغة أمر في الرسالة: {' · '.join(bad)} — قاعدة المشروع أسلوب الغائب")
        return 2
    out = Path(a.out) if a.out else B / "logs" / f"tg-digest-{a.date}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"✔ {out} — {len(visible)} حرفًا (السقف {CAP})")
    return 0 if len(visible) <= CAP else 2


if __name__ == "__main__":
    sys.exit(main())
