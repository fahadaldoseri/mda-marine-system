#!/usr/bin/env python3
"""أرقام المصادر الثلاثة — مصدر واحد للحقيقة (ح-3 · قرار صاحب القرار 2026-10-23).

أرقام منفصلة، تُولَّد كلها من بيانات التشغيل ولا تُكتب يدويًا في أي ملف:
  • معتمدة  = عدد المصادر في السجل المعتمد (appendices/sources-manifest.json).
  • مرصودة آليًا = عدد المصادر التي بلغها الفحص الآلي في هذا التشغيل.
  • ناجحة   = عدد المصادر التي أعادت محتوى صالحًا في هذا التشغيل.
  • مرجعية يدويًا = قائمة المصادر المستثناة من الفحص الآلي في الحالة.

الاستخدام:
  python3 tools/source_counts.py --date 2026-10-23            # JSON
  python3 tools/source_counts.py --date 2026-10-23 --line     # سطر عربي جاهز
  python3 tools/source_counts.py --date 2026-10-23 --write    # يكتب السطر في متن التقرير وحقول الواجهة
  python3 tools/source_counts.py --date 2026-10-23 --check    # يتحقق من تطابق كل المواضع (مانع)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
SENT_OPEN = "<!-- مصادر-تلقائي -->"
SENT_CLOSE = "<!-- /مصادر-تلقائي -->"


def approved_count() -> int:
    m = json.loads((B / "appendices" / "sources-manifest.json").read_text(encoding="utf-8"))
    return int(m["approved_source_count"])


def feeds_state(date: str) -> dict:
    p = B / "feeds" / f"feeds-{date}.status.json"
    if not p.exists():
        return {"checked": 0, "ok": 0, "failed": 0, "reasons": {}, "failed_names": [], "present": False}
    d = json.loads(p.read_text(encoding="utf-8"))
    failed = d.get("failed_feeds") or []
    failed_n = d.get("failed") if isinstance(d.get("failed"), int) else len(failed)
    manual_present = "manual_reference" in d
    manual = d.get("manual_reference") or []
    reasons: dict[str, list[str]] = {}
    names: list[str] = []
    for f in failed:
        name = (f.get("name") or f.get("source") or str(f.get("num", ""))).strip()
        reason = (f.get("block_reason") or f.get("reason") or "سبب غير مسجّل").strip()
        reasons.setdefault(reason, []).append(name)
        names.append(name)
    return {"checked": int(d.get("checked") or 0), "ok": int(d.get("ok") or 0),
            "failed": failed_n, "manual_reference": manual,
            "manual_reference_present": manual_present,
            "reasons": reasons, "failed_names": names, "present": True}


def counts(date: str) -> dict:
    fs = feeds_state(date)
    manual = fs.get("manual_reference") or []
    return {"date": date, "approved": approved_count(), "checked": fs["checked"], "ok": fs["ok"],
            "failed": fs["failed"], "manual_reference": manual,
            "manual_reference_present": fs.get("manual_reference_present", False),
            "manual_reference_count": len(manual), "failed_names": fs["failed_names"],
            "reasons": fs["reasons"], "feeds_status_file": fs["present"]}


def reason_label(block_reason: str) -> str:
    """تصنيف عربي موجز لسبب التعذّر — لا نصوص تقنية خام في متن التقرير (ك-135)."""
    r = (block_reason or "").lower()
    if any(k in r for k in ("403", "401", "429", "forbidden", "حجب", "cloudflare", "captcha",
                            "تحقق بشري", "attention required", "blocked page")):
        return "حجب المصدر"
    if any(k in r for k in ("timeout", "مهلة", "timed out", "connection", "اتصال", "ssl", "tls",
                            "reset", "refused", "dns", "eof", "closed connection")):
        return "عطل اتصال مؤقت"
    return "تغذية معطوبة"


def channels_declared() -> dict:
    """القنوات المُعلنة (مصدر واحد للحقيقة) — تُقرأ من tools/source_channels.py."""
    sys.path.insert(0, str(B / "tools"))
    import source_channels  # noqa: WPS433
    ch = source_channels.channels()
    return {"rss": sorted(ch["rss"]), "manual": sorted(ch["browser"]), "proxy": sorted(ch["proxy"])}


def identity_ar(c: dict) -> str:
    """هوية العدّاد: المعتمد = المسار الآلي + المرجعية اليدوية (+ البديل). أي فرق = مانع."""
    ch = channels_declared()
    parts = [f"{c['approved']} معتمدة = {len(ch['rss'])} بالمسار الآلي + {len(ch['manual'])} بالمرجعية اليدوية"]
    if ch["proxy"]:
        parts.append(f"{len(ch['proxy'])} بمسار رسمي بديل")
    return "المصادر: " + " + ".join(parts)


def line_ar(c: dict) -> str:
    txt = (f"{identity_ar(c)} · {c['ok']} ناجحة")
    if c["failed"]:
        # (و) كل مصدر متعذّر باسمه وسببه، لا أسماء مختصرة ولا أسباب مجمّعة
        pairs = []
        for r, ns in c["reasons"].items():
            for n in ns:
                pairs.append(f"{n.replace('حساب ', '').replace(' على X', '')} — {reason_label(r)}")
        if c.get("manual_reference_present"):
            txt += f" · {c['failed']} متعذّر: " + " · ".join(pairs)
        else:
            txt += f" · تعذّر {c['failed']}: " + " · ".join(pairs)
    if c.get("manual_reference_present"):
        manual_n = int(c.get("manual_reference_count") or len(c.get("manual_reference") or []))
        return txt + f" · {manual_n} مرجعية تُراجع يدويًا."
    return txt + "."


def report_path(date: str) -> Path:
    return B / "reports" / f"{date}-sectioned.md"


def faults_line(date: str) -> str:
    """سطر الإفصاح الآلي عن الأعطال المعروفة (قرار ح-4) — يُولَّد من العلامة والقائمة، لا يُكتب يدويًا."""
    mp = B / "logs" / f"pipeline-{date}.json"
    if not mp.exists():
        return ""
    sys.path.insert(0, str(B / "tools"))
    from known_faults import classify_component, degraded_components
    mark = json.loads(mp.read_text(encoding="utf-8"))
    parts: list[str] = []
    for comp, st, text, items in degraded_components(mark):
        r = classify_component(comp, st, text, items)
        label = {"feeds": "التغذيات", "ofac": "فحص العقوبات", "originals": "الأصول الرسمية",
                 "ledger_merge": "دمج الدفتر", "builtin_llm": "المراجعة الآلية",
                 "attachment": "إرفاق الملف"}.get(comp, comp)
        if r["allowed"]:
            parts.append(f"{label}: {r.get('reason_ar_full') or r['reason_ar']}")
        else:
            parts.append(f"{label}: عطل غير مسموح — يمنع التسليم")
    if not parts:
        return ""
    return "تشغيل منقوص مُفصح: " + " · ".join(parts) + "."


def inject(date: str, c: dict) -> tuple[bool, str]:
    """يكتب سطر الأرقام وسطر الإفصاح داخل قسم «ما لم يُحسم» (ظاهر في PDF) لا في الملحق وحده.

    الكتابة متكررة بلا تكرار: أي سطر مُولَّد سابقًا يبدأ بـ«- المصادر:» أو
    «- تشغيل منقوص مُفصح:» يُستبدل. لا وسوم تعليق في المتن — وسم التعليق ظهر نصًّا
    للقارئ في بناء الموقع (ك-135)، فاستُبدل ببادئة نصية ثابتة.
    """
    p = report_path(date)
    if not p.exists():
        return False, f"لا نص تقرير: {p}"
    t = p.read_text(encoding="utf-8")
    fl = faults_line(date)
    gen = [f"- {line_ar(c)}"] + ([f"- {fl}"] if fl else [])
    # إزالة النسخ المُولَّدة سابقًا في كل الملف، سواء كانت بنقطة أو بلا نقطة.
    t = re.sub(r"^-?\s*(?:المصادر:|تشغيل منقوص مُفصح:).*\n?", "", t, flags=re.M)
    if c.get("manual_reference_present"):
        manual_n = int(c.get("manual_reference_count") or len(c.get("manual_reference") or []))
        summary = (f"- إجمالي المصادر المعتمدة: {c['approved']} · المرصودة آليًا: {c['checked']} · "
                   f"الناجحة: {c['ok']} · المتعذّر: {c['failed']} · المرجعية اليدوية: {manual_n}.\n")
        t = re.sub(r"^- إجمالي المصادر المعتمدة:.*\n?", summary, t, flags=re.M)
    t = re.sub(r"^.*<!--\s*/?مصادر-تلقائي\s*-->.*\n?", "", t, flags=re.M)
    m = re.search(r"^##\s+ما لم يُحسم\s*$", t, re.M)
    if not m:
        return False, "قسم «ما لم يُحسم» غير موجود — لا يُكتب الرقم في مكان غير معتمد"
    nxt = re.search(r"^##\s+", t[m.end():], re.M)
    end = m.end() + (nxt.start() if nxt else len(t[m.end():]))
    body = t[m.end():end].strip("\n")
    body = re.sub(r"\n{3,}", "\n\n", body)
    # لا أسطر فارغة محقونة (البند ط): فاصل واحد ثابت بين المتن والسطور المُولَّدة
    t = t[:m.end()] + ("\n\n" + body if body else "") + "\n\n" + "\n".join(gen) + "\n" + t[end:]
    p.write_text(t, encoding="utf-8")
    return True, str(p)


def write_meta(date: str, c: dict) -> tuple[bool, str]:
    p = B / "web" / "meta" / f"{date}.json"
    if not p.exists():
        return False, f"لا ملف واجهة: {p}"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["sources_approved"] = c["approved"]
    d["sources_checked"] = c["checked"]     # مرصودة آليًا في هذا التشغيل (لا المعتمدة)
    d["sources_ok"] = c["ok"]
    d["sources_failed"] = c["failed"]
    d["sources_manual_reference"] = c.get("manual_reference") or []
    d["sources_manual_reference_count"] = int(c.get("manual_reference_count") or 0)
    if isinstance(d.get("notice"), str):
        old_notice = d["notice"]
        tail_match = re.search(r"(البلاغات المنقولة.*)$", old_notice)
        tail = tail_match.group(1) if tail_match else ""
        manual_n = int(c.get("manual_reference_count") or len(c.get("manual_reference") or []))
        d["notice"] = (f"نسخة ويب من التقرير اليومي. المصادر المعتمدة {c['approved']} مصدرًا؛ "
                        f"{c['checked']} مرصودة آليًا، {c['ok']} ناجحة، {c['failed']} متعذّر، "
                        f"و{manual_n} مرجعية تُراجع يدويًا."
                        + (f" {tail}" if tail else ""))
    d["sources_line"] = line_ar(c)
    if isinstance(d.get("source_reliability"), dict):
        d["source_reliability"]["checked"] = c["checked"]
        d["source_reliability"]["approved"] = c["approved"]
        d["source_reliability"]["ok"] = c["ok"]
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return True, str(p)


def check(date: str, c: dict) -> list[str]:
    """يتحقق من تطابق كل المواضع الظاهرة — أي اختلاف مخالفة مانعة."""
    bad: list[str] = []
    # الثابت الملزم (البند هـ): المصادر المرصودة آليًا = ناجحة + متعذّرة.
    if c["checked"] != c["ok"] + c["failed"]:
        bad.append(f"الثابت مفحوصة = ناجحة + متعذّرة مخالف: {c['checked']} ≠ {c['ok']} + {c['failed']}")
    # هوية القنوات (ك-212): كل مصدر معتمد له قناة واحدة، والمجموع = المعتمد.
    ch = channels_declared()
    flat = ch["rss"] + ch["manual"] + ch["proxy"]
    dup = sorted({n for n in flat if flat.count(n) > 1})
    if dup:
        bad.append(f"مصادر في أكثر من قناة: {dup}")
    declared = len(set(flat))
    if declared != c["approved"]:
        bad.append(f"مجموع قنوات المصادر {declared} لا يساوي المعتمد {c['approved']} — مصدر بلا قناة")
    if c.get("manual_reference_present") and len(ch["manual"]) != len(c.get("manual_reference") or []):
        bad.append(f"قائمة المرجعية اليدوية في ملف الحالة {len(c.get('manual_reference') or [])} "
                   f"تخالف إعلان القنوات {len(ch['manual'])} — أعد تشغيل فحص التغذيات")
    md = report_path(date)
    if md.exists() and line_ar(c).split("·")[0].strip() not in md.read_text(encoding="utf-8"):
        bad.append(f"متن التقرير لا يحمل سطر الأرقام المعتمد: {line_ar(c)}")
    mp = B / "web" / "meta" / f"{date}.json"
    if mp.exists():
        d = json.loads(mp.read_text(encoding="utf-8"))
        for k, v in (("sources_approved", c["approved"]), ("sources_checked", c["checked"]),
                     ("sources_ok", c["ok"])):
            if d.get(k) != v:
                bad.append(f"{mp.name}: {k} = {d.get(k)} والمصدر الحقيقي {v}")
        if c.get("manual_reference_present") and d.get("sources_manual_reference") != c.get("manual_reference"):
            bad.append(f"{mp.name}: قائمة المرجعية اليدوية لا تطابق ملف الحالة")
        if c.get("manual_reference_present") and d.get("sources_line") != line_ar(c):
            bad.append(f"{mp.name}: sources_line لا يطابق السطر المولّد")
    hp = Path(f"{B.parent}/seawatch/dist/index.html")
    if hp.exists():
        h = hp.read_text(encoding="utf-8")
        if f"{c['approved']} مصدرًا مفحوصًا" in h:
            bad.append("الرئيسية تقول «مصدرًا مفحوصًا» عن العدد المعتمد — خلط بين المعتمدة والمفحوصة")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--line", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    c = counts(a.date)

    if a.write:
        ok1, m1 = inject(a.date, c)
        ok2, m2 = write_meta(a.date, c)
        print(f"  {'✔' if ok1 else '✘'} متن التقرير: {m1}")
        print(f"  {'✔' if ok2 else '✘'} ملف الواجهة: {m2}")
        print(f"  · {line_ar(c)}")
        return 0 if (ok1 and ok2) else 2
    if a.check:
        bad = check(a.date, c)
        if bad:
            for x in bad:
                print(f"  ✘ {x}")
            print(f"النتيجة: {len(bad)} اختلافًا في أرقام المصادر — مانع")
            return 2
        print(f"  ✓ أرقام المصادر متطابقة في كل المواضع · {line_ar(c)}")
        return 0
    if a.line:
        print(line_ar(c))
        return 0
    print(json.dumps(c, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validators"))
    from _guard import run
    run(main)
