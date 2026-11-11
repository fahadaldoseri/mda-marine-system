import pathlib
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد الموقع الدائم لمركز الوعي بالمجال البحري.

الاستخدام:
  python3 generator/build_site.py [--site-root /path/to/site] [--check]

يعيد استخدام المولّد الحالي (build_report.py + blocks.py + map_gulf.py + monthly_dashboard.py)
ويبني مجلد النشر dist/ كاملًا:
  dist/index.html                     الرئيسية والأرشيف
  dist/reports/<YYYY-MM-DD>.html      التقارير اليومية
  dist/reports/cumulative-2026.html   السجل التراكمي
  dist/reports/monthly-2026-10.html   اللوحة الشهرية
  dist/manus-routes.json              بيان المسارات
  dist/favicon.svg

قاعدة المصادر: كل تقرير يومي يحتاج زوجًا: sources/reports/<التاريخ>-sectioned.md
و sources/meta/<التاريخ>.json. أي زوج ناقص يُسجَّل ويُتجاوز بلا إسقاط البناء.
"""
# ── مسارات النظام: محمولة (تُقرأ من BRAIN_DIR / SITE_DIR، والافتراضي جذر الشجرة) ──
import os as _os
import shutil
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[1]

CRITICAL_FAIL: list[str] = []


def _tree(_env, _base, *_names):
    """جذر الشجرة المجاورة: من متغيّر البيئة أو من مجلد شقيق."""
    _v = _os.environ.get(_env)
    if _v:
        return _Path(_v)
    for _n in _names:
        _c = _base.parent / _n
        if _c.is_dir():
            return _c
    return _base.parent / _names[0]
def _canonical_brain():
    """جذر الدماغ القانوني: قياس واحد عبر brain_root، ولا يُقبل الأرشيف (ك-571)."""
    _v = _os.environ.get("BRAIN_DIR")
    if _v and _Path(_v).is_dir():
        return _Path(_v)
    import sys as _sys
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from brain_root import brain_root as _br  # noqa: E402
    return _br()


BRAIN = _canonical_brain()

import argparse
import json
import re
import sys
from datetime import date
from html import escape as esc
from pathlib import Path

_LOCK_TOOLS = _Path(_os.environ.get("BRAIN_DIR", str(BRAIN))) / "tools"
sys.path.insert(0, str(_LOCK_TOOLS))
try:
    from build_lock import BuildLock, BuildLockBusy, default_lock_path
except Exception as _lock_exc:  # fail closed: direct builds must never bypass the lock
    raise SystemExit(f"توقف البناء: تعذّر تحميل قفل البناء المشترك: {_lock_exc}") from _lock_exc

# الاسم المعتمد للتقرير اليومي (قرار صاحب القرار — 18 أكتوبر 2026)
from daily_title import DAILY_TITLE, DAILY_PLACEHOLDERS, normalize_daily_title  # noqa: E402

SOURCES_MANIFEST = Path(f'{BRAIN}/appendices/sources-manifest.json')
THREAT_SCALE = BRAIN / "appendices" / "threat-scale.json"


def approved_source_count(fallback: int = 40) -> int:
    """عدد المصادر المعتمد — مصدر واحد للحقيقة (بند 8 من تدقيق 19 أكتوبر 2026)."""
    try:
        return int(json.loads(SOURCES_MANIFEST.read_text(encoding='utf-8'))['approved_source_count'])
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return fallback


# نمط عنوان يومي عام: بادئة معتمدة، وربما تاريخ عربي ملحق بها.
# الإصلاح الجذري (ك-595): كان التمييز بقائمة ثابتة، فعنوان مثل
# «التقرير اليومي لأمن الملاحة والأوضاع الراهنة في المنطقة — 29 أكتوبر 2026»
# يُعامل عنوانًا مخصّصًا، فيحتاج ترجمة في المعجم ويُسقط بناء الإصدارات القديمة.
_DAILY_PREFIXES = "|".join(re.escape(x) for x in DAILY_PLACEHOLDERS)
DAILY_PLACEHOLDER_RE = re.compile(
    rf"^\s*(?:{_DAILY_PREFIXES})"
    rf"(?:\s*[—–-]\s*\d{{1,2}}\s+[\u0600-\u06FF]+\s+\d{{4}})?\s*$"
)


def daily_headline(meta: dict) -> str:
    """عنوان الإصدار اليومي المعتمد، مع احترام أي عنوان مخصّص غير عام."""
    return normalize_daily_title(meta.get("headline") or meta.get("subtitle"))


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_report  # noqa: E402
from display_format import format_release_version, format_update_label  # noqa: E402
import monthly_dashboard  # noqa: E402
import site_chrome  # noqa: E402

AR_MONTHS = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
             7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="8" fill="#04120f"/>
<path d="M16 5l8 3.4v6.9c0 5-3.3 8.7-8 10.3-4.7-1.6-8-5.3-8-10.3V8.4z" fill="none" stroke="#22c3b6" stroke-width="1.8" stroke-linejoin="round"/>
<path d="M16 14v6" stroke="#22c3b6" stroke-width="1.8" stroke-linecap="round"/>
<path d="M12.8 16.4h6.4" stroke="#22c3b6" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""


def ar_date(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return f"{d} {AR_MONTHS[m]} {y}"
    except Exception:
        return iso


def _risk_catalog() -> tuple[dict, dict]:
    """يقرأ سلم الخطر الحاكم؛ الملف المفقود أو غير الصالح يمنع البناء."""
    try:
        raw = json.loads(THREAT_SCALE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"سلم الخطر الحاكم غير قابل للقراءة: {THREAT_SCALE}: {exc}") from exc
    by_token, by_label = {}, {}
    for level in raw.get("levels") or []:
        token = str(level.get("token") or "").strip().lower()
        ar = str(level.get("ar") or "").strip()
        if not token or not ar or token in by_token:
            raise ValueError("سلم الخطر الحاكم ناقص أو يحوي رمزًا مكررًا")
        by_token[token] = level
        for label in (ar, level.get("en"), level.get("jmic")):
            if label:
                by_label[str(label).strip().lower()] = token
    if not by_token:
        raise ValueError("سلم الخطر الحاكم فارغ")
    return by_token, by_label


def risk_of(meta: dict):
    dc = meta.get("decision_card") or {}
    kind = str(dc.get("risk_kind") or "").strip().lower()
    label = str(dc.get("risk") or meta.get("threat_level") or "").strip()
    by_token, by_label = _risk_catalog()
    label_kind = by_label.get(label.lower()) if label else None
    if kind:
        if kind not in by_token:
            raise ValueError(f"risk_kind خارج سلم الخطر الحاكم: «{kind}» — يُمنع البناء")
        if label and not label_kind:
            raise ValueError(f"مستوى الخطر خارج سلم الخطر الحاكم: «{label}» — يُمنع البناء")
        # بعض الإصدارات القديمة حملت رمزًا لونيًا قديمًا؛ لا نُسقطها إلى med،
        # بل نستخدم المستوى العربي الحاكم إن كان معروفًا.
        if label_kind and label_kind != kind:
            kind = label_kind
    else:
        if not label or not label_kind:
            raise ValueError("ينقص مستوى خطر معتمد أو risk_kind — يُمنع البناء")
        kind = label_kind
    return label or str(by_token[kind].get("ar") or ""), kind


RESTRICTED_CLASSES = {"مقيّد", "حساس"}


def is_restricted(meta) -> bool:
    """الإصدار المقيّد أو الحساس لا يُنشر على الموقع العام."""
    return str((meta or {}).get("classification", "عام")).strip() in RESTRICTED_CLASSES


def discover(site_root: Path):
    """يجمع أزواج التقارير اليومية من مجلد المصادر."""
    reports, warnings = [], []
    meta_dir = site_root / "sources" / "meta"
    rep_dir = site_root / "sources" / "reports"
    for md in sorted(rep_dir.glob("*-sectioned.md")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", md.name)
        if not m:
            continue
        iso = m.group(1)
        meta_path = meta_dir / f"{iso}.json"
        if not meta_path.exists():
            warnings.append(f"تقرير بلا ملف واجهة: {md.name}")
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            warnings.append(f"ملف واجهة غير صالح {meta_path.name}: {e}")
            continue
        reports.append({"iso": iso, "md": md, "meta": meta})
    reports.sort(key=lambda r: r["iso"], reverse=True)
    return reports, warnings


def _flat(value) -> str:
    """حقول أهم الأخبار المتعلقة بالأمن البحري قد تكون نصًّا أو قائمة نقاط — تُسطَّح للعرض المختصر."""
    if isinstance(value, list):
        return " · ".join(str(x).strip() for x in value if str(x).strip())
    return (value or "").strip()


def build_reports(site_root: Path, dist: Path, reports, warnings):
    out_dir = dist / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    built = []
    for r in reports:
        target = out_dir / f"{r['iso']}.html"
        try:
            # غير الأحدث يُوسم أرشيفيًا على الشاشة بدل شارة «قديم» المنذرة
            _meta = dict(r["meta"], screen_archived=(r is not reports[0]))
            _, count = build_report.build(r["md"], target, _meta)
        except Exception as e:  # ك-316: تقرير يومي ساقط = فشل مغلق
            import traceback as _tb, pathlib as _pl, datetime as _dt
            _log = _pl.Path("logs/runbook") / f"fail-{_dt.date.today().isoformat()}.log"
            _log.parent.mkdir(parents=True, exist_ok=True)
            with _log.open("a", encoding="utf-8") as _fh:
                _fh.write(f"\n=== تقرير {r['iso']} ===\n{_tb.format_exc()}\n")
            CRITICAL_FAIL.append(f"تقرير {r['iso']}: {e}")
            warnings.append(f"فشل بناء {r['iso']}: {e}")
            continue
        html = target.read_text(encoding="utf-8")
        html = site_chrome.inject(html, active="report", note=f"إصدار {ar_date(r['iso'])}")
        target.write_text(html, encoding="utf-8")
        risk, kind = risk_of(r["meta"])
        built.append({
            "iso": r["iso"], "label": r["meta"].get("date_label") or ar_date(r["iso"]),
            "risk": risk, "risk_kind": kind,
            "headline": daily_headline(r["meta"]),
            "lede": _flat(r["meta"].get("lede")),
            "changed": _flat((r["meta"].get("decision_card") or {}).get("changed")),
            "action": _flat((r["meta"].get("decision_card") or {}).get("action")),
            "changed_list": [str(x).strip() for x in ((r["meta"].get("decision_card") or {}).get("changed") or [])
                             if str(x).strip()] if isinstance((r["meta"].get("decision_card") or {}).get("changed"), list)
                            else [],
            "version": r["meta"].get("version") or "", "window": r["meta"].get("window") or "",
            "sources": r["meta"].get("sources_checked") or "", "cited": r["meta"].get("sources_cited") or "",
            "generated": r["meta"].get("generated_label") or "",
            "sections": count, "size": target.stat().st_size,
        })
    return built


def build_cumulative(site_root: Path, dist: Path, warnings):
    md = site_root / "sources" / "reports" / "cumulative.md"
    meta_p = site_root / "sources" / "meta" / "cumulative.json"
    if not (md.exists() and meta_p.exists()):
        warnings.append("مصدر السجل التراكمي غير متاح، تُجاوز الصفحة")
        return None
    target = dist / "reports" / "cumulative-2026.html"
    try:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        meta["screen_archived"] = "none"  # سجل تراكمي: بلا شارة عمر
        _, count = build_report.build(md, target, meta)
    except Exception as e:
        warnings.append(f"فشل بناء السجل التراكمي: {e}")
        return None
    html = site_chrome.inject(target.read_text(encoding="utf-8"), active="cumulative",
                              note="سجل تراكمي 28 فبراير – 11 أكتوبر 2026")
    target.write_text(html, encoding="utf-8")
    return {"size": target.stat().st_size, "sections": count}


def build_monthly(site_root: Path, dist: Path, warnings):
    ledger = site_root / "sources" / "ledger.json"
    if not ledger.exists():
        warnings.append("دفتر الأحداث غير متاح، تُجاوَز اللوحة الشهرية")
        return None
    target = dist / "reports" / "monthly-2026-10.html"
    try:
        info = monthly_dashboard.build(str(ledger), str(target), "لوحة المؤشرات الشهرية — أمن الملاحة 2026")
    except Exception as e:
        warnings.append(f"فشل بناء اللوحة الشهرية: {e}")
        return None
    html = site_chrome.inject(target.read_text(encoding="utf-8"), active="monthly",
                              note="لوحة مبنية من دفتر الأحداث التراكمي")
    target.write_text(html, encoding="utf-8")
    return info


def build_about(site_root: Path, dist: Path, warnings):
    """صفحة «عن المنصة» — مقر الإفصاح الحاكم المنقول من تذييل الرئيسية (م-29).

    المحتوى في sources/about.md ويُبنى بالمسار نفسه الذي تبني به بقية الصفحات،
    فلا نص إفصاح مكتوب داخل المولّد ولا سقوط له عند تغيير التخطيط.
    """
    md = site_root / "sources" / "about.md"
    meta_p = site_root / "sources" / "meta" / "about.json"
    if not (md.exists() and meta_p.exists()):
        warnings.append("مصدر «عن المنصة» غير متاح، تُجاوز الصفحة")
        return 0
    target = dist / "about.html"
    try:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        meta["screen_archived"] = "none"
        _, count = build_report.build(md, target, meta)
    except Exception as e:
        CRITICAL_FAIL.append(f"صفحة عن المنصة: {e}")
        warnings.append(f"فشل بناء صفحة «عن المنصة»: {e}")
        return 0
    html = site_chrome.inject(target.read_text(encoding="utf-8"), active="about",
                              note="عن المنصة")
    target.write_text(html, encoding="utf-8")
    return count


def _additions_decision_context(meta: dict) -> str:
    """سياق القرار الذي يبقى ظاهرًا داخل بطاقة الأخبار في صفحة الإضافات."""
    threat_zones = meta.get("threat_zones") or {}
    if not isinstance(threat_zones, dict):
        threat_zones = {}
    top_zone = str(threat_zones.get("top_zone") or "").strip()
    level = str(threat_zones.get("overall") or meta.get("threat_level") or "").strip()
    sector = " — ".join(value for value in (top_zone, level) if value)

    counter = threat_zones.get("counter") or {}
    qualifying = ""
    if isinstance(counter, dict) and counter.get("qualifying") is not None:
        qualifying = str(counter["qualifying"])
        if counter.get("total") is not None:
            qualifying += f' / {counter["total"]}'

    decision = meta.get("decision_card") or {}
    raw_action = decision.get("action") if isinstance(decision, dict) else ""
    if isinstance(raw_action, list):
        action = next((str(value).strip() for value in raw_action if str(value).strip()), "")
    else:
        action = str(raw_action or "").strip()

    cells = (("أعلى قطاع", sector), ("الوقائع المؤهلة", qualifying), ("إجراء اليوم", action))
    items = "".join(
        f'<li><span class="mds-k">{label}</span><span class="mds-v">{esc(value)}</span></li>'
        for label, value in cells if value
    )
    return f'<ul class="hmap-decide additions-decision-context">{items}</ul>' if items else ""


def build_additions(site_root: Path, dist: Path, reports, warnings):
    """صفحة «إضافات» — قرار المالك 2026-10-28: المجموعة المزاحة من التقرير اليومي تُنشر هنا.

    المصدر نفسه: متن أحدث إصدار. الأقسام تأتي من سياسة الأقسام (additions_sections) التي
    يقرأها المولّد، فلا تُخفَّض صلاحية أي حارس ولا تُفقد بيانات.
    """
    if not reports:
        warnings.append("تعذّر بناء «إضافات»: لا إصدار منشور")
        return 0
    r = reports[0]
    meta = dict(r["meta"])
    decision_context = _additions_decision_context(meta)
    # صفحة عرض فقط: تُكتم بطاقات التقرير ويبقى متن الأقسام المزاحة.
    # لا تُحذف بيانات الكتل (hypotheses/indicators/gaps/timeline وغيرها):
    # build_report يحتاجها ليعرض الجداول والبطاقات التي نُقلت إلى «إضافات».
    # الخريطة تُبنى مع وقائع التوزيع الجغرافي المنقول، فتبقى في «إضافات».
    for k in ("decision_card", "hero_kpis", "notice", "threat_level",
              "event_keys", "glossary", "classification"):
        meta.pop(k, None)
    meta["title"] = "إضافات"
    meta["headline"] = "إضافات"
    _label = r["meta"].get("date_label") or ar_date(r["iso"])
    meta["subtitle"] = f"المجموعة المنقولة من التقرير اليومي — إصدار {_label}"
    meta["lede"] = ("الأقسام التفصيلية التي كانت داخل التقرير اليومي. متن التقرير اليومي في صفحته، "
                    "وهذه الصفحة مرجعها الدائم المحدَّث مع كل إصدار.")
    meta["date_label"] = _label
    meta["footer_note"] = ("هذه الصفحة مرجع دائم للإصدار الحالي. البيانات نفسها في دفتر الأحداث، "
                           "والتقرير اليومي في صفحته وفي PDF.")
    target = dist / "additions.html"
    try:
        _, count = build_report.build(r["md"], target, meta, mode="additions")
    except Exception as e:
        CRITICAL_FAIL.append(f"صفحة إضافات: {e}")
        warnings.append(f"فشل بناء صفحة إضافات: {e}")
        return 0
    html = target.read_text(encoding="utf-8")
    if decision_context:
        card_start = html.find('id="news-card"')
        card_end = html.find("</section>", card_start) if card_start >= 0 else -1
        if card_end < 0:
            CRITICAL_FAIL.append("صفحة إضافات: بطاقة الأخبار غير موجودة لإدراج سياق القرار")
            warnings.append("فشل بناء صفحة إضافات: بطاقة الأخبار غير موجودة لإدراج سياق القرار")
            return 0
        html = html[:card_end] + decision_context + html[card_end:]
    html = site_chrome.inject(html, active="additions", note=f"إضافات إصدار {ar_date(r['iso'])}")
    target.write_text(html, encoding="utf-8")
    return count


REGISTRY_YEARS = ("2026", "2027", "2028")


def clean_text(s) -> str:
    """تنظيف نص للعرض: بلا وسوم Markdown وبلا فراغات مكررة."""
    t = str(s or "")
    t = re.sub(r"[*_`>#]+", "", t)
    return re.sub(r"\s+", " ", t).strip()


def row_summary(r: dict) -> str:
    """ملخص الصف من حقل `lede` الحقيقي (م-03).

    دالة اشتقاق مستقلة عن دالة تطبيع العنوان اليومي، حتى لا يمسّ الإصلاح
    مسار الترجمة الإنجليزية الذي يعتمد `daily_headline`.
    """
    t = clean_text(r.get("lede")) or clean_text(r.get("headline"))
    # ك-627: جملة «ويظل … أعلى القطاعات …» تتكرر حرفيًا في صفوف السجل فيمنعها
    # حارس «قالب جملة متكرر أكثر من مرتين». تُسقَط من صفوف الرئيسية (تفصيلها في
    # صفحة التقرير)، ويُصدَّر الملخص بتاريخ الصف فلا يتطابق صفّان نصًّا.
    import re as _re
    t = _re.sub(r"ويظل\s+.+?أعلى القطاعات عند مستوى[^.]+\.[\s]*", "", t or "").strip()
    _label = clean_text(r.get("label"))
    if _label:
        t = f"{_label} — {t}" if t else _label
    if len(t) > 170:
        cut = t[:170]
        if " " in cut:
            cut = cut[: cut.rfind(" ")]
        t = cut.rstrip("،,. ") + "…"
    return t


def reports_rows(items, hidden_after=None) -> str:
    """صفوف إصدارات: التاريخ · التصنيف الملوّن · الملخص الحقيقي."""
    out = []
    for i, r in enumerate(items):
        cls = "ar-row" + (" ar-extra" if hidden_after is not None and i >= hidden_after else "")
        out.append(
            f'<li class="{cls}"><a class="ar-link" href="/reports/{r["iso"]}.html">'
            f'<span class="ar-date">{esc(r["label"])}</span>'
            f'<span class="ar-risk rk-{esc(r["risk_kind"])}">{esc(r["risk"])}</span>'
            f'<span class="ar-note">{esc(row_summary(r))}</span>'
            f'</a></li>'
        )
    return "".join(out)


def month_title(iso: str) -> str:
    """عنوان قائمة الشهر بصيغة «أكتوبر 2026» بدل «أرشيف الإصدارات» (م-01 د)."""
    try:
        y, m = iso.split("-")[0], int(iso.split("-")[1])
        return f"{AR_MONTHS[m]} {y}"
    except (IndexError, KeyError, ValueError):
        return ""


def reports_index(reports) -> list:
    """فهرس مدمج يتيح التنقّل بين الأشهر بلا إعادة بناء ولا استعلام شبكي."""
    return [{"d": r["iso"], "l": r["label"], "k": r["risk_kind"],
             "r": r["risk"], "s": row_summary(r)} for r in reports]


def months_registry(reports, active: str) -> str:
    """السجل: سنوات ثم أشهر (م-01 ج) — اشتقاق آلي من الإصدارات، والفارغ معطّل."""
    have: dict = {}
    for r in reports:
        key = r["iso"][:7]
        have[key] = have.get(key, 0) + 1
    blocks = []
    for y in REGISTRY_YEARS:
        months = []
        for i in range(1, 13):
            name = AR_MONTHS[i]
            key = f"{y}-{i:02d}"
            n = have.get(key, 0)
            if n:
                cur = ' aria-current="true"' if key == active else ""
                months.append(f'<li><button type="button" class="mo" data-month="{key}"{cur}>'
                              f'{name}<span class="n">{n}</span></button></li>')
            else:
                months.append(f'<li><span class="mo is-empty" aria-disabled="true">{name}</span></li>')
        total = sum(have.get(f"{y}-{i:02d}", 0) for i in range(1, 13))
        open_attr = " open" if total else ""
        label = f"{y} · {total} إصدارًا" if total else f"{y} · لا إصدارات"
        blocks.append(f'<li class="yr-item{"" if total else " is-empty"}"><details{open_attr}>'
                      f'<summary class="yr">{label}</summary>'
                      f'<ul class="months">{"".join(months)}</ul></details></li>')
    return f'<ul class="registry">{"".join(blocks)}</ul>'


def build_index(dist: Path, reports, notfound: bool = False):
    latest = reports[0] if reports else None
    ledger_total = ledger_count(dist)
    month_events = ledger_month_count(dist, latest["iso"][:7] if latest else "")
    _active_month = latest["iso"][:7] if latest else ""
    month_rows = reports_rows([r for r in reports if r["iso"][:7] == _active_month],
                              hidden_after=8) or '<li class="ar-empty">لا توجد تقارير في هذا الشهر.</li>'
    month_label = month_title(latest["iso"]) if latest else "الإصدارات"
    registry_html = months_registry(reports, _active_month)
    reports_json = json.dumps(reports_index(reports), ensure_ascii=False, separators=(",", ":"))
    month_has_more = len([r for r in reports if r["iso"][:7] == _active_month]) > 8
    rows = reports_rows(reports)

    if latest:
        chg = latest.get("changed_list") or [latest.get("changed") or ""]
        chg_items = "".join(f"<li>{esc(x)}</li>" for x in [c for c in chg if c][:3])
        meta_bits = [
            f"فترة التغطية {esc(latest['window'])}" if latest.get("window") else "",
            f"{esc(str(latest['sources']))} مصدرًا مفحوصًا في ذلك التشغيل" if latest.get("sources") else "",
            f"{esc(str(latest['cited']))} مُستشهدًا" if latest.get("cited") else "",
            f"آخر تحديث {esc(format_update_label(latest['generated']))}" if latest.get("generated") else "",
        ]
        _ver = format_release_version(latest["version"]) if latest.get("version") else ""
        status_bar = (
            '<div class="statusbar">'
            f'<span class="sb-risk rk-{esc(latest.get("risk_kind") or "med")}">مستوى التهديد: {esc(latest["risk"])}</span>'
            f'<span class="sb-date">{esc(latest["label"])}</span>'
            + (f'<span class="sb-code">رقم الإصدار {esc(_ver)}</span>' if _ver else "")
            + f'<a class="sb-open" href="/reports/{latest["iso"]}.html">التقرير الحالي ←</a></div>'
        )
        _lede = clean_text(latest.get("lede")) or clean_text(latest.get("headline"))
        hero_card = f"""<article class="hero-card">
      <h2>أهم الأخبار المتعلقة بالأمن البحري</h2>
      <p class="hc-lede">{esc(_lede[:260])}</p>
      <ul class="hc-changes">{chg_items}</ul>
      <p class="hc-action"><b>الإجراء المطلوب:</b> {esc(latest['action'] or '—')}</p>
      <p class="hc-meta">{' · '.join(b for b in meta_bits if b)}</p>
      <a class="hc-open" href="/reports/{latest['iso']}.html">افتح التقرير كاملًا ←</a>
    </article>"""
    else:
        hero_card = '<div class="hero-card"><h2>لا يوجد إصدار بعد</h2></div>'
        status_bar = ""

    return f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="مركز الوعي بالمجال البحري: تقارير أمن الملاحة اليومية في مضيق هرمز والخليج العربي وبحر العرب والبحر الأحمر.">
<meta name="keywords" content="الأمن البحري, أمن الملاحة, مركز الوعي بالمجال البحري, مضيق هرمز, الخليج العربي, تقرير أمني بحري يومي">
{site_chrome.social_meta("مركز الوعي بالمجال البحري — تقارير أمن الملاحة", "منصة دائمة لتقارير أمن الملاحة: إصدار يومي بمؤشراته وخرائطه، ولوحة شهرية مبنية من دفتر أحداث تراكمي، وسجل تاريخي للمقارنة.", "/")}
<meta name="theme-color" content="#040810">
{site_chrome.icon_links()}
<link rel="alternate" type="application/rss+xml" title="تغذية الإصدارات اليومية" href="/feed.xml">
<title>مركز الوعي بالمجال البحري — تقارير أمن الملاحة</title>
<link rel="stylesheet" href="{build_report.FONT_LINK}">
<style>
{site_chrome.SITE_CSS}{site_chrome.MOBILE_NAV_CSS}
:root{{--bg:#040810;--panel:#0b1524;--panel2:#0f1d33;--line:#1b2b45;--ink:#e9f0f9;--ink2:#b9c8dc;
--muted:#7f95ae;--accent:#22c3b6;--accent-ink:#04120f;--danger:#ff5d52;--warn:#ffb02e;--ok:#33d07a;--info:#4d9dff}}
body.daylight{{--bg:#eef3f9;--panel:#ffffff;--panel2:#f5f8fc;--line:#d3dded;--ink:#0d1a2b;--ink2:#33475e;
--muted:#4f657c;--accent:#0b7a72;--accent-ink:#ffffff;--danger:#c2352c;--warn:#a86b00;--ok:#1d7a4c;--info:#1d5fa8}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);line-height:1.7;
font-family:"IBM Plex Sans Arabic",system-ui,Tahoma,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:20px 20px 10px}}
h1{{font-size:28px;margin:0 0 6px;line-height:1.35;text-align:center}}
.lede{{color:var(--muted);margin:0 0 16px;font-size:14px;max-width:78ch;margin-inline:auto;
text-align:justify;text-justify:inter-word}}
/* ── شريط الحالة (م-20): المستوى بلونه + التاريخ + الرقم في أول شاشة ── */
.statusbar{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:var(--panel);
border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:0 0 14px}}
.statusbar .sb-risk{{font-size:14px;font-weight:700;border:1px solid currentColor;border-radius:99px;padding:2px 12px}}
.statusbar .sb-date{{font-family:"IBM Plex Mono",monospace;font-size:14px;color:var(--ink);text-align:center}}
.statusbar .sb-code{{font-size:12.5px;color:var(--muted)}}
.statusbar .sb-open{{margin-inline-start:auto;color:var(--accent);font-size:13.5px;font-weight:600;text-decoration:none}}
.statusbar .sb-open:hover{{border-bottom:1px solid var(--accent)}}
@media(min-width:901px){{.statusbar{{position:sticky;top:62px;z-index:40}}}}
/* ── السجل: سنوات ثم أشهر (م-01 ج) ── */
.registry{{list-style:none;margin:0;padding:0}}
.yr-item{{border-bottom:1px solid var(--line)}}
.yr-item:last-child{{border-bottom:0}}
.yr{{cursor:pointer;padding:11px 2px;font-size:14.5px;font-weight:600;color:var(--ink2);text-align:right}}
.yr-item.is-empty .yr{{color:var(--muted)}}
.months{{list-style:none;margin:0 0 10px;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:6px}}
.months .mo{{display:flex;align-items:center;justify-content:space-between;gap:6px;width:100%;
background:transparent;border:1px solid var(--line);border-radius:9px;padding:8px 10px;
color:var(--ink2);font:inherit;font-size:13.5px;cursor:pointer;text-align:right;min-height:40px}}
.months .mo:hover{{border-color:var(--accent);color:var(--ink)}}
.months .mo[aria-current="true"]{{background:var(--accent);border-color:var(--accent);color:var(--accent-ink);font-weight:700}}
.months .mo .n{{font-family:"IBM Plex Mono",monospace;font-size:12px;opacity:.85}}
.months .mo.is-empty{{color:var(--muted);opacity:.55;cursor:default;border-style:dashed}}
.ar-extra{{display:none}}
.ar.open .ar-extra{{display:block}}
.more{{margin-top:12px;background:transparent;border:1px solid var(--line);border-radius:10px;
color:var(--ink2);font:inherit;font-size:13.5px;padding:9px 14px;cursor:pointer;min-height:40px}}
.more:hover{{border-color:var(--accent);color:var(--ink)}}
.hero-card{{display:block;background:linear-gradient(150deg,var(--panel2),var(--panel));border:1px solid var(--line);
border-radius:14px;padding:22px;color:inherit;margin:0 0 22px}}
.hc-top{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}}
.hc-tag{{font-size:13px;background:var(--accent);color:var(--accent-ink);padding:3px 10px;border-radius:99px;font-weight:700}}
.hc-risk{{font-size:12.5px;border:1px solid var(--line);padding:3px 10px;border-radius:99px}}
.hc-code{{font-size:12.5px;color:var(--muted)}}
.hc-code b{{color:var(--ink2);font-family:"IBM Plex Mono",monospace}}
.hero-card h2{{margin:0 0 8px;font-size:20px}}
.hc-meta{{color:var(--muted);font-size:13px;margin:0 0 14px}}
.hc-changes{{border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:0 0 12px}}
.hc-changes b{{color:var(--ink2);font-size:14px}}
.hc-changes ul{{margin:8px 0 0;padding-inline-start:20px}}
.hc-changes li{{font-size:14.5px;color:var(--ink2);margin:0 0 6px}}
.hc-action{{color:var(--muted);font-size:14px;margin:0 0 14px}}
.hc-action b{{color:var(--ink2)}}
.hc-open{{display:inline-block;color:var(--accent);font-size:13.5px;font-weight:600;
text-decoration:none;border-bottom:1px solid transparent;padding:6px 2px}}
.hc-open:hover,.hc-open:focus-visible{{border-bottom-color:var(--accent)}}
.hc-open:focus-visible{{outline:2px solid var(--accent);outline-offset:3px;border-radius:4px}}
.grid{{display:grid;grid-template-columns:1.15fr .85fr;gap:22px;align-items:start}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px}}
.card h3{{margin:0 0 6px;font-size:17px}}
.card p.hint{{color:var(--muted);font-size:13px;margin:0 0 14px}}
.pref-row{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 0;border-bottom:1px solid var(--line);flex-wrap:wrap}}
.pref-row:last-child{{border-bottom:0}}
.pref-row span{{font-size:14px;color:var(--ink2)}}
.seg{{display:flex;border:1px solid var(--line);border-radius:10px;overflow:hidden}}
.seg button{{background:transparent;border:0;color:var(--ink2);padding:7px 13px;cursor:pointer;font:inherit;font-size:13.5px}}
.seg button.on{{background:var(--accent);color:var(--accent-ink);font-weight:700}}
.cont{{display:none;background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:14px;margin:0 0 22px}}
.cont.on{{display:block}}
.cont a{{color:var(--accent);text-decoration:none;font-weight:600}}
.cont .ct{{color:var(--muted);font-size:12.5px;display:block;margin-top:4px}}
ul.ar{{list-style:none;margin:0;padding:0}}
.ar-row{{border-bottom:1px solid var(--line)}}
.ar-row:last-child{{border-bottom:0}}
.ar-link{{display:grid;grid-template-columns:1fr auto;gap:6px 12px;padding:13px 2px;text-decoration:none;color:inherit}}
.ar-link:hover .ar-date{{color:var(--accent)}}
.ar-date{{font-weight:600;font-size:15px}}
.ar-risk{{font-size:13px;border:1px solid var(--line);border-radius:99px;padding:2px 10px;align-self:start}}
.ar-note{{grid-column:1/-1;color:var(--muted);font-size:13px}}
.rk-high{{color:var(--danger);border-color:var(--danger)}}
.rk-med{{color:var(--warn);border-color:var(--warn)}}
.rk-low{{color:var(--ok);border-color:var(--ok)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:0 0 22px}}
.tile{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}}
.tile b{{display:block;font-size:22px;font-family:"IBM Plex Mono",monospace}}
.tile span{{color:var(--muted);font-size:13px}}
.foot-note{{color:var(--muted);font-size:13px;margin:26px 0 0;border-top:1px solid var(--line);padding-top:14px}}
@media print{{body{{background:#fff;color:#000}}.wrap{{padding:0}}
.cont,.hero-card .hc-open{{display:none!important}}
.card,.hero-card,.tile{{border-color:#bbb;background:#fff;break-inside:avoid}}
.ar-link{{color:#000}}.ar-note,.hc-meta,.tile span{{color:#333}}}}
</style>
</head>NF_CSS_PLACEHOLDER<body>
PREFS_EARLY_PLACEHOLDER
NAV_PLACEHOLDER
<div class="wrap" role="main" id="main" tabindex="-1">
  <script type="application/json" id="reports-index">{reports_json}</script>
  {status_bar}
  <h1>مركز الوعي بالمجال البحري</h1>
  <p class="lede">إصدار يومي لأمن الملاحة بمؤشراته وخرائطه، ولوحة شهرية مبنية من دفتر أحداث تراكمي، وسجل تاريخي للمقارنة. <a href="/about.html">الوصف الكامل في صفحة «عن المنصة»</a>.</p>

  {hero_card}

  <div class="tiles">
    <div class="tile"><b>{len(reports)}</b><span>إصدار يومي منشور</span></div>
    <div class="tile"><b>{ledger_total or "—"}</b><span>سجل في الدفتر التراكمي</span></div>
    <div class="tile"><b>{approved_source_count()}</b><span>مصدرًا معتمدًا في السجل</span></div>
    <div class="tile"><b>{month_events or "—"}</b><span>واقعة مصنّفة في الشهر الجاري</span></div>
  </div>

  <div class="grid">
    <section class="card" id="month-card">
      <h3 id="month-title">{month_label}</h3>
      <p class="hint">إصدارات الشهر المختار. آخر ثمانية إصدارات افتراضيًا، وزر العرض يُظهر الشهر كاملًا. مفتاح اللون يبيّن مستوى التهديد المسجل في أهم الأخبار المتعلقة بالأمن البحري.</p>
      <ul class="ar" id="month-rows">{month_rows}</ul>
      <button type="button" class="more" id="show-all"{"" if month_has_more else " hidden"}>عرض كل إصدارات الشهر</button>
    </section>
    <div class="side">
      <section class="card" id="archive">
        <h3>السجل</h3>
        <p class="hint">اختر السنة ثم الشهر. الأشهر الباهتة بلا إصدارات، والقائمة تُبنى آليًا من الإصدارات المنشورة.</p>
        {registry_html}
      </section>
    </div>
  </div>

</div>
NOTFOUND_PLACEHOLDER
FOOT_PLACEHOLDER
PREFS_LATE_PLACEHOLDER
<script>
(function(){{
var LS=window.localStorage;
function get(k,d){{try{{return LS.getItem(k)||d;}}catch(e){{return d;}}}}
function set(k,v){{try{{LS.setItem(k,v);}}catch(e){{}}}}
function paintTheme(){{
  var light=document.body.classList.contains('daylight');
  document.querySelectorAll('#p-theme button').forEach(function(b){{
    b.classList.toggle('on', (b.getAttribute('data-theme')==='light')===light);
  }});
  var sb=document.getElementById('sn-theme'); if(sb) sb.textContent = light?'المظهر: نهاري':'المظهر: ليلي';
}}
function paintScale(){{
  var s=parseFloat(get('mn-scale','1'));
  document.querySelectorAll('[data-scale]').forEach(function(b){{
    b.classList.toggle('on', parseFloat(b.getAttribute('data-scale'))===s);
  }});
}}
document.querySelectorAll('#p-theme button').forEach(function(b){{
  b.addEventListener('click',function(){{
    var light=b.getAttribute('data-theme')==='light';
    document.body.classList.toggle('daylight',light); set('mn-theme',light?'light':'dark'); paintTheme();
  }});
}});
document.querySelectorAll('[data-scale]').forEach(function(b){{
  b.addEventListener('click',function(){{
    var s=parseFloat(b.getAttribute('data-scale')); set('mn-scale',s);
    document.body.style.zoom=(s===1?'':s); paintScale();
  }});
}});
paintTheme(); paintScale();
/* ── السجل: تبديل الشهر داخل الصفحة بلا إعادة تحميل (م-01 د) ── */
var AR_M=['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'];
var IDX=[];
try{{IDX=JSON.parse(document.getElementById('reports-index').textContent)||[];}}catch(e){{IDX=[];}}
function monthLabel(k){{var p=k.split('-');return AR_M[parseInt(p[1],10)-1]+' '+p[0];}}
function rowHtml(o,extra){{
  return '<li class="ar-row'+(extra?' ar-extra':'')+'"><a class="ar-link" href="/reports/'+o.d+'.html">'
    +'<span class="ar-date">'+o.l+'</span>'
    +'<span class="ar-risk rk-'+o.k+'">'+o.r+'</span>'
    +'<span class="ar-note">'+o.s+'</span></a></li>';
}}
function renderMonth(k){{
  var list=document.getElementById('month-rows'), t=document.getElementById('month-title'),
      more=document.getElementById('show-all');
  if(!list) return;
  var items=IDX.filter(function(o){{return o.d.slice(0,7)===k;}});
  list.classList.remove('open');
  list.innerHTML=items.length?items.map(function(o,i){{return rowHtml(o,i>=8);}}).join('')
                              :'<li class="ar-empty">لا توجد تقارير في هذا الشهر.</li>';
  if(t) t.textContent=monthLabel(k);
  if(more) more.hidden=items.length<=8;
  document.querySelectorAll('.mo[data-month]').forEach(function(b){{
    b.setAttribute('aria-current', b.getAttribute('data-month')===k ? 'true' : 'false');
  }});
}}
document.querySelectorAll('.mo[data-month]').forEach(function(b){{
  b.addEventListener('click',function(){{renderMonth(b.getAttribute('data-month'));}});
}});
var more=document.getElementById('show-all');
if(more) more.addEventListener('click',function(){{
  document.getElementById('month-rows').classList.add('open'); more.hidden=true;
}});
}})();
</script>
MOBILE_NAV_JS_PLACEHOLDER
</body></html>""".replace("MOBILE_NAV_JS_PLACEHOLDER", site_chrome.MOBILE_NAV_JS) \
   .replace("PREFS_EARLY_PLACEHOLDER", site_chrome.PREFS_EARLY) \
   .replace("NF_CSS_PLACEHOLDER", NF_STYLE) \
   .replace("NOTFOUND_PLACEHOLDER", notfound_panel(reports, notfound)) \
   .replace("NAV_PLACEHOLDER", site_chrome.nav_html("home")) \
   .replace("FOOT_PLACEHOLDER", site_chrome.foot_html("الرئيسية")) \
   .replace("PREFS_LATE_PLACEHOLDER", site_chrome.PREFS_LATE)


def site_base(dist: Path) -> str:
    """نطاق الموقع المنشور. غيابه أو فساده يوقف البناء: لا نطاق احتياطي وهمي."""
    cfg_p = dist.parent / "sources" / "site.json"
    site = ""
    if cfg_p.exists():
        try:
            site = str(json.loads(cfg_p.read_text(encoding="utf-8")).get("base_url") or "").strip().rstrip("/")
        except json.JSONDecodeError as e:
            raise SystemExit(f"توقف البناء: ملف sources/site.json غير صالح ({e})")
    if not site:
        raise SystemExit("توقف البناء: base_url مفقود في sources/site.json؛ لا يُبنى الموقع بنطاق احتياطي وهمي.")
    if not site.startswith("https://") or "example" in site:
        raise SystemExit(f"توقف البناء: base_url غير صالح ({site})؛ يجب رابطًا عامًا يبدأ بـ https://")
    return site


def ledger_count(dist: Path) -> int:
    """عدد سجلات الدفتر التراكمي — يُقرأ ولا يُكتب يدويًا في الصفحة."""
    f = dist.parent / "sources" / "ledger.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        ev = d.get("events") if isinstance(d, dict) else d
        return len(ev) if isinstance(ev, list) else 0
    except Exception:
        return 0


def ledger_month_count(dist: Path, month: str) -> int:
    """عدد الوقائع المصنّفة في الشهر الجاري من دفتر الأحداث (البطاقة الرابعة)."""
    if not month:
        return 0
    f = dist.parent / "sources" / "ledger.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        ev = d.get("events") if isinstance(d, dict) else d
        if not isinstance(ev, list):
            return 0
        n = 0
        for e in ev:
            if not isinstance(e, dict):
                continue
            ds = str(e.get("date") or e.get("iso") or e.get("event_date") or "")[:7]
            if ds == month:
                n += 1
        return n
    except Exception:
        return 0


def _enrich_feed_xml(xml: str) -> str:
    """ك-252: pubDate لكل عنصر وlastBuildDate للقناة في تغذية RSS."""
    import re as _re
    from datetime import datetime, timezone
    from email.utils import format_datetime
    if not xml or "<item>" not in xml:
        return xml
    def _pub(m):
        try:
            dt = datetime.fromisoformat(m.group(2)).replace(tzinfo=timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc)
        return m.group(0) + f"<pubDate>{format_datetime(dt)}</pubDate>"
    xml = _re.sub(r'(<guid[^>]*>mn-(\d{4}-\d{2}-\d{2})[^<]*</guid>)', _pub, xml)
    if "lastBuildDate" not in xml:
        xml = xml.replace("<channel>", f"<channel><lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>", 1)
    return xml


def build_feed(dist: Path, reports):
    """تغذية RSS للإصدارات اليومية، لمتابعة الموقع دون زيارة يدوية."""
    from xml.sax.saxutils import escape as xesc
    site = site_base(dist)
    items = []
    for r in reports:
        link = f"{site}/reports/{r['iso']}.html"
        desc = r["changed"] or r["headline"] or ""
        items.append(
            "  <item>\n"
            f"    <title>{xesc(r['label'])} — مستوى التهديد: {xesc(r['risk'])}</title>\n"
            f"    <link>{link}</link>\n"
            f"    <guid isPermaLink=\"false\">mn-{r['iso']}</guid>\n"
            f"    <description>{xesc(desc)}</description>\n"
            "  </item>"
        )
    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
           "<rss version=\"2.0\"><channel>\n"
           "  <title>مركز الوعي بالمجال البحري — تقارير أمن الملاحة</title>\n"
           f"  <link>{site}/</link>\n"
           "  <description>إصدار يومي لأمن الملاحة في مضيق هرمز والخليج العربي وبحر العرب والبحر الأحمر</description>\n"
           "  <language>ar</language>\n"
           + ("\n".join(items) if items else "") + "\n</channel></rss>\n")
    (dist / "feed.xml").write_text(_enrich_feed_xml(xml), encoding="utf-8")
    return len(items)


def build_routes(dist: Path, reports):
    routes = [{"path": "/", "title": "الرئيسية والأرشيف"}]
    for r in reports:
        routes.append({"path": f"/reports/{r['iso']}.html", "title": f"تقرير {r['label']}"})
    routes.append({"path": "/reports/:date", "title": "تقرير يومي"})
    routes.append({"path": "/reports/monthly-2026-10.html", "title": "اللوحة الشهرية"})
    routes.append({"path": "/reports/cumulative-2026.html", "title": "السجل التراكمي"})
    routes.append({"path": "/sources.html", "title": "المصادر والمراجع"})
    routes.append({"path": "/additions.html", "title": "إضافات"})
    routes.append({"path": "/about.html", "title": "عن المنصة"})
    (dist / "manus-routes.json").write_text(
        json.dumps({"routes": routes}, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(routes)


def known_paths(reports):
    """المسارات المنشورة فعليًا: تُستخدم في صفحة «غير موجودة» وفي خريطة الموقع."""
    ks = ["/", "/reports/cumulative-2026.html", "/reports/monthly-2026-10.html", "/sources.html", "/additions.html"]
    ks += [f"/reports/{r['iso']}.html" for r in reports]
    return ks


def notfound_panel(reports, visible: bool = False) -> str:
    """لوحة «الصفحة غير موجودة» + فاحص مسار في المتصفح.

    الاستضافة تعيد صفحة الرئيسية لأي مسار غير معروف (soft-404)، فيعرض هذا الفاحص
    اللوحة الصحيحة للزائر. رمز الاستجابة يبقى 200 لأن التوصيل ثابت بلا خادم.
    """
    ks = known_paths(reports)
    names = {"/": "الرئيسية والأرشيف", "/reports/cumulative-2026.html": "السجل التراكمي",
             "/reports/monthly-2026-10.html": "اللوحة الشهرية", "/sources.html": "المصادر والمراجع",
             "/additions.html": "إضافات", "/about.html": "عن المنصة"}
    names.update({f"/reports/{r['iso']}.html": f"التقرير اليومي — {r['label']}" for r in reports})
    items = "".join(f'<li><a href="{k}"><span class="nf-t">{esc(names.get(k, k))}</span>'
                    f'<span class="nf-p">{k}</span></a></li>' for k in ks)
    keys = ",".join(f'"{k}":1' for k in ks)
    hid = "" if visible else " hidden"
    script = ""
    if not visible:
        script = (
            "<script>(function(){var K={" + keys + "};"
            r"var p=location.pathname.replace(/\/index\.html$/,'/');"
            "if(!K[p]){var nf=document.getElementById('nf404');"
            "var w=document.querySelector('.wrap');"
            "if(nf){if(w){w.setAttribute('hidden','');}nf.removeAttribute('hidden');"
            "document.title='الصفحة غير موجودة — مركز الوعي بالمجال البحري';}}})();</script>"
        )
    return (
        f'<section class="card nf" id="nf404"{hid}>'
        "<h1>الصفحة غير موجودة</h1>"
        "<p>الرابط المطلوب لا يقابل صفحة منشورة على هذا الموقع. هذه الروابط المتاحة الآن:</p>"
        f'<ul class="nf-list">{items}</ul>'
        '<p><a class="nf-back" href="/">العودة إلى الرئيسية والأرشيف</a></p></section>' + script
    )


NF_STYLE = """<style>
.nf{max-width:760px;margin:26px auto}
.nf h1{font-size:30px;margin:6px 0 10px}
.nf-list{list-style:none;padding:0;margin:14px 0;display:grid;gap:8px}
.nf-list a{display:flex;justify-content:space-between;align-items:baseline;gap:14px;padding:10px 14px;
  border:1px solid var(--line,#2b3b4e);border-radius:8px;text-decoration:none;color:inherit;min-height:44px}
.nf-t{font-weight:600}
.nf-p{font-family:"IBM Plex Mono",monospace;font-size:12.5px;color:var(--muted,#7f95ae);direction:ltr;
  unicode-bidi:isolate;overflow-wrap:anywhere}
.nf-list a:hover{border-color:var(--accent,#2fd6c3)}
.nf-back{display:inline-block;margin-top:6px;font-weight:700;text-decoration:none;color:var(--accent,#2fd6c3)}
</style>"""


def build_sitemap(dist: Path, reports) -> int:
    site = site_base(dist)
    urls = known_paths(reports)
    last = reports[0]["iso"] if reports else ""
    body = "".join(
        f"  <url><loc>{site}{u}</loc>" + (f"<lastmod>{last}</lastmod>" if last else "") + "</url>\n"
        for u in urls
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")
    (dist / "sitemap.xml").write_text(xml, encoding="utf-8")
    return len(urls)


def build_robots(dist: Path) -> None:
    site = site_base(dist)
    (dist / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site}/sitemap.xml\n", encoding="utf-8")


def build_notfound(dist: Path, reports) -> None:
    html = build_index(dist, reports, notfound=True).replace(
        '<div class="wrap" role="main" id="main" tabindex="-1">', '<div class="wrap" role="main" id="main" tabindex="-1" hidden>', 1).replace(
        "<title>مركز الوعي بالمجال البحري — تقارير أمن الملاحة</title>",
        "<title>الصفحة غير موجودة — مركز الوعي بالمجال البحري</title>")
    (dist / "404.html").write_text(html, encoding="utf-8")


ARCHIVE_INDEX_STYLE = """
  :root{--bg:#050a12;--panel:#0c1626;--line:#1c2c47;--tx:#e8eef7;--mut:#9fb2cc;--acc:#4cc3ff}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--tx);font-family:system-ui,"Segoe UI",Tahoma,sans-serif;line-height:1.7}
  .wrap{max-width:960px;margin:0 auto;padding:28px 18px 64px}
  h1{font-size:1.5rem;margin:0 0 6px}
  .sub{color:var(--mut);font-size:.95rem;margin:0 0 22px}
  ul{list-style:none;margin:0;padding:0;display:grid;gap:10px}
  li a{display:grid;grid-template-columns:120px 1fr;gap:12px;align-items:baseline;
       text-decoration:none;color:inherit;background:var(--panel);border:1px solid var(--line);
       border-radius:12px;padding:12px 14px}
  li a:hover{border-color:var(--acc)}
  .d{color:var(--mut);font-variant-numeric:tabular-nums;font-size:.92rem}
  .t{font-size:1rem}
  .back{display:inline-block;margin-top:26px;color:var(--acc);text-decoration:none}
  @media(max-width:520px){li a{grid-template-columns:1fr}.d{font-size:.85rem}}
"""


def _site_nav(dist: Path) -> str:
    """ترويسة الموقع نفسها من الصفحة الرئيسية المبنية — لا نسخة موازية تتباعد مع الوقت."""
    home = dist / "index.html"
    if home.is_file():
        m = re.search(r"<header\b[^>]*>.*?</header>", home.read_text(encoding="utf-8"), re.S)
        if m and "site-nav" in m.group(0):
            return m.group(0)
    return ('<nav class="site-nav" aria-label="التنقل"><a href="/">الرئيسية</a>'
            '<a href="/reports/">الأرشيف</a><a href="/sources.html">المصادر</a>'
            '<a href="/additions.html">الإضافات</a></nav>')


def build_reports_index(dist: Path, reports) -> int:
    """فهرس مسار /reports/ — يمنع 404 على مسار الأرشيف ويسرد كل الإصدارات المنشورة."""
    rows = []
    for r in reports:
        iso = r["iso"]
        meta = r.get("meta") or {}
        title = esc(daily_headline(meta) or "إصدار يومي")
        rows.append(f'<li><a href="/reports/{iso}.html">'
                    f'<span class="d">{ar_date(iso)}</span>'
                    f'<span class="t">{title}</span></a></li>')
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>أرشيف الإصدارات اليومية — مركز الوعي بالمجال البحري</title>
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="referrer" content="no-referrer">
<link rel="stylesheet" href="{build_report.FONT_LINK}">
<style>{ARCHIVE_INDEX_STYLE}</style>
</head>
<body>
{_site_nav(dist)}
<div class="wrap">
  <h1>أرشيف الإصدارات اليومية</h1>
  <p class="sub">{len(rows)} إصدارًا منشورًا · الأحدث أولًا بحسب ترتيب السجل</p>
  <ul>
{chr(10).join(rows)}
  </ul>
  <a class="back" href="/">العودة إلى الصفحة الرئيسية ←</a>
</div>
</body>
</html>
"""
    (dist / "reports").mkdir(parents=True, exist_ok=True)
    (dist / "reports" / "index.html").write_text(html, encoding="utf-8")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-root", default=str(HERE.parent))
    ap.add_argument("--check", action="store_true", help="فحص المخرجات بعد البناء")
    ap.add_argument("--allow-restricted", action="store_true",
                    help="يسمح بنشر إصدار مقيّد أو حساس على الموقع العام (ممنوع افتراضيًا)")
    a = ap.parse_args()

    site_root = Path(a.site_root).resolve()
    dist = site_root / "dist"
    (dist / "reports").mkdir(parents=True, exist_ok=True)
    warnings = []
    # ── أصول الهوية (م-28): الشعار والأيقونات وصورة المشاركة ──
    (dist / "assets").mkdir(parents=True, exist_ok=True)
    for _a in ("logo-official.png", "logo-header.png", "icon-32.png", "icon-180.png",
               "icon-512.png", "og-1200x630.png"):
        _src = site_root / "assets" / _a
        if _src.is_file():
            shutil.copy2(_src, dist / "assets" / _a)
        else:
            warnings.append(f"أصل هوية مفقود: {_a}")

    reports, w = discover(site_root)
    warnings += w
    if not a.allow_restricted:
        kept, blocked = [], []
        for r in reports:
            (blocked if is_restricted(r["meta"]) else kept).append(r)
        for r in blocked:
            warnings.append(f"لم يُنشر إصدار مقيّد أو حساس: {r['iso']} — يبقى داخل المحادثة فقط")
        if blocked and not kept:
            raise SystemExit("توقف البناء: كل الإصدارات مقيّدة أو حساسة، ولا يُنشر منها شيء على الموقع العام.")
        reports = kept
    built = build_reports(site_root, dist, reports, warnings)
    cum = build_cumulative(site_root, dist, warnings)
    mon = build_monthly(site_root, dist, warnings)

    # صفحة «المصادر والمراجع» — مرجع دائم في الشريط العلوي
    try:
        import build_sources
        build_sources.build(dist)
    except Exception as e:
        CRITICAL_FAIL.append(f"صفحة المصادر والمراجع: {e}")
        warnings.append(f"تعذّر بناء صفحة المصادر والمراجع: {e}")
    n_about = build_about(site_root, dist, warnings)
    n_add = build_additions(site_root, dist, reports, warnings)  # ك-227: يحتاج سجل الإصدار الأم (meta+md) لا قائمة البناء
    (dist / "index.html").write_text(build_index(dist, built), encoding="utf-8")
    n_archive = build_reports_index(dist, built)
    (dist / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    n_feed = build_feed(dist, built)
    n_routes = build_routes(dist, built)
    n_sitemap = build_sitemap(dist, built)
    build_robots(dist)
    build_notfound(dist, built)

    # قسم «التقارير الخاصة» — يُبنى آليًا من sources/special
    n_sp_items = 0
    try:
        import build_special
        _, n_sp_items = build_special.build_all(dist)
    except Exception as e:  # لا يُسقط بناء الموقع بسبب قسم فرعي
        CRITICAL_FAIL.append(f"التقارير الخاصة: {e}")
        warnings.append(f"تعذّر بناء صفحة التقارير الخاصة: {e}")

    # طبقة إصلاح المخرجات — تعمل على كل صفحة مبنية قبل النشر (idempotent)
    try:
        try:
            import postprocess
        except ImportError:  # عند التشغيل من جذر المشروع
            from generator import postprocess
        st = postprocess.run(dist)
        print(f"طبقة الإصلاح: {st['changed']} من {st['pages']} صفحة عُدّلت")
    except Exception as e:  # لا تُسقط البناء، لكن تُعلن في التنبيهات
        CRITICAL_FAIL.append(f"طبقة الإصلاح: {e}")
        warnings.append(f"تعذّر تشغيل طبقة الإصلاح: {e}")

    print(f"الرئيسية: {len(built)} إصدار · السجل التراكمي: {'نعم' if cum else 'لا'} · "
          f"اللوحة الشهرية: {'نعم' if mon else 'لا'} · المسارات: {n_routes} · التغذية: {n_feed} · "
          f"خريطة الموقع: {n_sitemap} · robots: نعم · 404: نعم · التقارير الخاصة: {n_sp_items} · "
          f"فهرس الأرشيف: {n_archive}")
    for w_ in warnings:
        print(f"تنبيه: {w_}")

    if a.check:
        pages = sorted(p for p in dist.rglob("*.html"))
        missing = []
        escaped = []
        for p in pages:
            t = p.read_text(encoding="utf-8")
            if "site-nav" not in t:
                missing.append(p.name)
            if len(t) < 3000:
                missing.append(p.name + " (صغير)")
            if "&lt;" in t:
                escaped.append(f"{p.name} ({t.count('&lt;')})")
        print(f"فحص: {len(pages)} صفحة، بلا ترويسة أو غير مكتملة: {missing or 'لا شيء'}")
        print(f"فحص الوسوم المهرَّبة (تظهر للقارئ نصًّا): {escaped or 'لا شيء'}")
        # فحص سياسة عرض رموز الأحداث (2+5): الرمز الكامل في قسم الوقائع فقط
        try:
            import subprocess as _sp
            _r = _sp.run([sys.executable, f"{BRAIN}/validators/check_code_policy.py",
                          str(dist)], capture_output=True, text=True)
            _line = [l for l in _r.stdout.splitlines() if "النتيجة" in l]
            print(f"فحص سياسة الرموز: {(_line[-1].strip() if _line else _r.stdout.strip()[-80:])}")
        except Exception as _e:
            print(f"تنبيه: تعذر فحص سياسة الرموز ({_e})")
        bad = [p.name for p in pages if not (dist / "manus-routes.json").exists()]
        if bad:
            print("تنبيه: بيان المسارات مفقود")
        return 0 if not (missing or escaped) else 1
    return 0


def _build_en_editions() -> None:
    """يبني نسخ الإصدارات الإنجليزية عند وجود ترجمة معتمدة."""
    try:
        import build_report_en
        for _f in sorted(pathlib.Path("sources/i18n/en").glob("*-sectioned.en.md")):
            build_report_en.build(_f.name.split("-sectioned")[0])
    except Exception as _e:  # ك-316: النسخة الإنجليزية مخرج منشور = فشل مغلق
        CRITICAL_FAIL.append(f"النسخة الإنجليزية: {_e}")
        print("   تنبيه: لم تُبنَ نسخة إنجليزية:", _e)




# ── إصلاح ك-252 (2026-10-28): pubDate لكل عنصر وlastBuildDate للقناة في تغذية RSS ──
def _enrich_feed():
    import re as _re, time as _time
    from email.utils import format_datetime
    from datetime import datetime, timezone
    from pathlib import Path as _P
    outs = list(_P(__file__).resolve().parent.parent.glob("dist/feed.xml")) + \
           list(_P(__file__).resolve().parent.parent.glob("dist/**/feed.xml"))
    for f in outs:
        xml = f.read_text(encoding="utf-8")
        if "lastBuildDate" in xml and "<pubDate>" in xml:
            continue
        def _pub(m):
            iso = m.group(2)
            try:
                dt = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
            except Exception:
                dt = datetime.now(timezone.utc)
            return m.group(0) + f"<pubDate>{format_datetime(dt)}</pubDate>"
        xml = _re.sub(r'(<guid[^>]*>mn-(\d{4}-\d{2}-\d{2})[^<]*</guid>)', _pub, xml)
        if "lastBuildDate" not in xml:
            xml = xml.replace("<channel>", f"<channel><lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>", 1)
        f.write_text(xml, encoding="utf-8")
        print(f"تغذية RSS: أُضيف pubDate وlastBuildDate ({f.name})")




# ك-316/ك-319: كتلة التشغيل في نهاية الملف لتصل إلى كل الدوال المعرّفة بعده،
# ولتُشغّل إثراء التغذية (pubDate · lastBuildDate) الذي كان كودًا ميتًا غير قابل للوصول.
def _verify_map_contract() -> None:
    """حارس عقد قسم الخريطة على الصفحات المبنية — فشل مغلق يمنع النشر."""
    try:
        sys.path.insert(0, str(_Path(__file__).resolve().parent))
        import check_map_contract as _cmc
    except Exception as _e:
        CRITICAL_FAIL.append(f"حارس عقد الخريطة غير قابل للاستيراد: {_e}")
        return
    dist_reports = _ROOT / "dist" / "reports"
    meta_dir = _ROOT / "sources" / "meta"
    checked = 0
    for meta_p in sorted(meta_dir.glob("*.json")):
        try:
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
        except Exception:
            continue
        mp = meta.get("map") or {}
        if not (mp.get("points") or mp.get("caption")):
            continue
        page = dist_reports / f"{meta_p.stem}.html"
        if not page.exists():
            continue
        bad = _cmc.verify(page.read_text(encoding="utf-8"), meta)
        checked += 1
        if bad:
            print(f"✘ حارس عقد الخريطة ({meta_p.stem}): " + " · ".join(bad[:4]))
            CRITICAL_FAIL.extend(f"خريطة {meta_p.stem}: {x}" for x in bad)
    if not checked:
        CRITICAL_FAIL.append("حارس عقد الخريطة: لم تُفحص أي صفحة خريطة")
    else:
        print(f"✔ حارس عقد الخريطة: فُحصت {checked} صفحة دون مخالفة" if not CRITICAL_FAIL
              else f"حارس عقد الخريطة: فُحصت {checked} صفحة مع مخالفات")


def _finalize_build() -> None:
    _verify_map_contract()
    _build_en_editions()
    try:
        _enrich_feed()
    except Exception as _e:
        CRITICAL_FAIL.append(f"تغذية RSS: {_e}")


def _run_build() -> int:
    _rc = main()
    _finalize_build()
    if _rc == 0 and CRITICAL_FAIL:
        print("✘ فشل مغلق: أقسام منشورة لم تُبنَ — " + " · ".join(CRITICAL_FAIL[:4]))
        _rc = 2
    return _rc


def _run_with_build_lock() -> int:
    _lock_path = Path(_os.environ.get("MARINE_BUILD_LOCK_PATH", str(default_lock_path(BRAIN))))
    _lock = BuildLock(_lock_path, stale_after=3600)
    if _os.environ.get("MARINE_BUILD_LOCK_HELD") == "1":
        try:
            _lock.assert_owned_by_self_or_parent()
        except BuildLockBusy as _exc:
            print(f"✘ رُفض البناء: {_exc}")
            return 73
        return _run_build()
    try:
        with _lock:
            return _run_build()
    except BuildLockBusy as _exc:
        print(f"✘ رُفض البناء الثاني: {_exc}")
        return 73


if __name__ == "__main__":
    sys.exit(_run_with_build_lock())
