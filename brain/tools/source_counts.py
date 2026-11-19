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
import os
import re
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
from source_count_units import count_phrase

B = Path(__file__).resolve().parent.parent
SENT_OPEN = "<!-- مصادر-تلقائي -->"
SENT_CLOSE = "<!-- /مصادر-تلقائي -->"


def approved_count() -> int:
    m = json.loads((B / "appendices" / "sources-manifest.json").read_text(encoding="utf-8"))
    return int(m["approved_source_count"])


def registry_names() -> dict[int, str]:
    """أسماء التغذيات الحالية بأرقامها من sections/10-sources.md (المصدر الذي يقرؤه check_feeds).

    لقطة الفحص تحفظ الاسم وقت الجلب؛ وإذا عُدّل اسم في السجل بعدها (لفظ ممنوع مثلًا) أعاد
    `--write` الاسم القديم إلى المتن. الرقم ثابت، فالاسم يُقرأ من السجل الحالي.
    رقم بأكثر من اسم أو غائب عن السجل يبقى على اسم اللقطة.
    """
    src = B / "sections" / "10-sources.md"
    if not src.exists():
        return {}
    seen: dict[int, set[str]] = {}
    grab = False
    for ln in src.read_text(encoding="utf-8").splitlines():
        if ln.startswith("## تغذيات RSS"):
            grab = True
            continue
        if grab and ln.startswith("## "):
            break
        if grab:
            m = re.match(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(\S+)\s*\|$", ln.strip())
            if m:
                seen.setdefault(int(m.group(1)), set()).add(m.group(2))
    return {n: next(iter(v)) for n, v in seen.items() if len(v) == 1}


def feeds_state(date: str) -> dict:
    p = B / "feeds" / f"feeds-{date}.status.json"
    if not p.exists():
        return {"checked": 0, "ok": 0, "failed": 0, "items": 0,
                "reasons": {}, "failed_names": [], "present": False}
    d = json.loads(p.read_text(encoding="utf-8"))
    failed = d.get("failed_feeds") or []
    failed_n = d.get("failed") if isinstance(d.get("failed"), int) else len(failed)
    manual_present = "manual_reference" in d
    manual = d.get("manual_reference") or []
    reasons: dict[str, list[str]] = {}
    names: list[str] = []
    current = registry_names()
    for f in failed:
        num = f.get("num")
        name = (current.get(num) if isinstance(num, int) else None) or \
            (f.get("name") or f.get("source") or str(f.get("num", ""))).strip()
        reason = (f.get("block_reason") or f.get("reason") or "سبب غير مسجّل").strip()
        reasons.setdefault(reason, []).append(name)
        names.append(name)
    return {"checked": int(d.get("checked") or 0), "ok": int(d.get("ok") or 0),
            "failed": failed_n, "items": int(d.get("items") or 0), "manual_reference": manual,
            "manual_reference_present": manual_present,
            "reasons": reasons, "failed_names": names, "present": True}


def counts(date: str) -> dict:
    fs = feeds_state(date)
    manual = fs.get("manual_reference") or []
    return {"date": date, "approved": approved_count(), "checked": fs["checked"], "ok": fs["ok"],
            "items": fs.get("items", 0),
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
    """سطر الإفصاح مقسّم إلى جمل قصيرة (ك-458).

    بوابة الأسلوب تمنع أي جملة تتجاوز 35 كلمة، وسطر الإفصاح الواحد بلغ 42 كلمة.
    القسمة لا تُسقط معلومة: مقاطع السطر الثلاثة (الهوية · الفحص · المرجعية) صارت
    ثلاثة مقاطع منفصلة بنقطة، وكل مقطع داخل الحد المسموح.
    """
    parts = [identity_ar(c), f"الفحص: {c['ok']} ناجحة"]
    if c["failed"]:
        # (و) كل مصدر متعذّر باسمه وسببه، لا أسماء مختصرة ولا أسباب مجمّعة
        pairs = []
        for r, ns in c["reasons"].items():
            for n in ns:
                pairs.append(f"{n.replace('حساب ', '').replace(' على X', '')} — {reason_label(r)}")
        if c.get("manual_reference_present"):
            parts.append(f"{c['failed']} متعذّر: " + " · ".join(pairs))
        else:
            parts.append(f"تعذّر {c['failed']}: " + " · ".join(pairs))
    if c.get("manual_reference_present"):
        manual_n = int(c.get("manual_reference_count") or len(c.get("manual_reference") or []))
        parts.append(f"المرجعية اليدوية: {manual_n} يُفحص يدويًا")
    return ". ".join(parts) + "."


def report_path(date: str) -> Path:
    return B / "reports" / f"{date}-sectioned.md"


def feed_totals(date: str, c: dict, language: str) -> str:
    """جملة إجمالي التغذيات والعناصر مشتقة من ملف الحالة، لا من نص يدوي."""
    items = int(c["items"]) if "items" in c else int(feeds_state(date).get("items") or 0)
    manual = int(c.get("manual_reference_count") or len(c.get("manual_reference") or []))
    if language == "ar":
        return (f"المصادر المعتمدة {c['approved']}؛ فُحصت {c['checked']} تغذية، ونجحت {c['ok']}، "
                f"وتعذّر {c['failed']}، ومجموع العناصر المقروءة {items}؛ والمرجعية اليدوية {manual}.")
    if language == "en":
        return (f"Approved sources: {c['approved']}; {c['checked']} feeds were checked, "
                f"{c['ok']} succeeded, {c['failed']} failed, and {items} items were read; "
                f"{manual} under manual review.")
    raise ValueError(f"لغة إجمالي غير معتمدة: {language}")


def english_master_path(date: str) -> Path:
    """أصل الإنجليزية في المستودع أولًا؛ وجهة SITE_DIR بديل لعقود الاختبار المؤقتة فقط."""
    rel = Path("sources") / "i18n" / "en" / f"{date}-sectioned.en.md"
    candidates = [B.parent / "site", Path(os.environ["SITE_DIR"]) if os.environ.get("SITE_DIR") else None]
    roots = [root for root in candidates if root is not None]
    for root in roots:
        candidate = root / rel
        if candidate.is_file():
            return candidate
    return (roots[0] if roots else B.parent / "site") / rel


def _rewrite_feed_totals(text: str, date: str, c: dict, language: str) -> str:
    """يستبدل جمل الإجمالي القديمة فقط ويحافظ على بقية الجمل والمحتوى."""
    replacement = feed_totals(date, c, language)
    rewritten: list[str] = []
    for line in text.splitlines(keepends=True):
        ending = "\n" if line.endswith("\n") else ""
        body = line[:-1] if ending else line
        sentences = re.split(r"(?<=\.)\s+", body)
        for index, sentence in enumerate(sentences):
            lower = sentence.lower()
            if language == "ar":
                has_source = bool(re.search(r"تغذي|مصدر", sentence))
                has_checked = bool(re.search(r"فُ?حصت?", sentence))
                has_result = bool(re.search(r"نجحت|فشلت|تعذّر|تعذر", sentence))
            else:
                has_source = bool(re.search(r"feeds?|sources?", lower))
                has_checked = "checked" in lower
                has_result = bool(re.search(r"succeeded|failed", lower))
            if has_source and has_checked and has_result:
                bullet = re.match(r"^(\s*(?:[-*]\s+)?)", sentence)
                prefix = bullet.group(1) if bullet else ""
                sentences[index] = prefix + replacement
        rewritten.append(" ".join(sentences) + ending)
    text = "".join(rewritten)

    items = int(c["items"]) if "items" in c else int(feeds_state(date).get("items") or 0)
    if language == "ar":
        text = re.sub(r"(مجموع العناصر(?: المقروءة)?\s+)\d+(\s+عنصرًا)",
                      lambda m: f"{m.group(1)}{items}{m.group(2)}", text)
    else:
        text = re.sub(r"(\bTotal items read:\s*)\d+", lambda m: f"{m.group(1)}{items}", text,
                      flags=re.IGNORECASE)
        text = re.sub(r"(\btotal number of items was\s*)\d+",
                      lambda m: f"{m.group(1)}{items}", text, flags=re.IGNORECASE)
    return text


def sync_feed_totals(date: str, c: dict) -> list[str]:
    """يحدّث الإجمالي اليدوي في التقرير والأصل الإنجليزي الموجودين؛ لا يكتب إلى feeds/."""
    targets = [(report_path(date), "ar"), (english_master_path(date), "en")]
    touched: list[str] = []
    for path, language in targets:
        if not path.is_file():
            continue
        before = path.read_text(encoding="utf-8")
        after = _rewrite_feed_totals(before, date, c, language)
        if after != before:
            path.write_text(after, encoding="utf-8")
            touched.append(str(path))
    return touched


def ledger_events_line(date: str) -> str:
    """سطر إجمالي الوقائع وإسناداتها، مشتق من دفتر اليوم لا من كتابة التقرير."""
    p = B / "cumulative-2026" / "daily" / f"{date}.json"
    if not p.exists():
        return ""
    raw = json.loads(p.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else (raw.get("incidents") or [])
    counts: dict[str, int] = {}
    for row in rows:
        for name in re.split(r"[·,]", str(row.get("source", ""))):
            name = name.strip()
            if name:
                counts[name] = counts.get(name, 0) + 1
    if not rows or not counts:
        return ""
    details = "؛ ".join(
        f"{name} {count_phrase(n, i)}" for i, (name, n) in enumerate(counts.items())
    )
    return (f"إجمالي الوقائع المرمزة: {len(rows)} واقعة، بإجمالي {sum(counts.values())} إسنادًا. "
            f"المصادر المستخدمة وعدد الوقائع المنسوبة إليها: {details}.")


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
        r = classify_component(comp, st, text, items, today=date)
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
    el = ledger_events_line(date)
    gen = [f"- {line_ar(c)}"] + ([f"- {fl}"] if fl else [])
    # إزالة النسخ المُولَّدة سابقًا في كل الملف، سواء كانت بنقطة أو بلا نقطة.
    t = re.sub(r"^-?\s*(?:المصادر:|تشغيل منقوص مُفصح:).*\n?", "", t, flags=re.M)
    t = re.sub(r"^إجمالي الوقائع المرمزة:.*\n?", "", t, flags=re.M)
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
    # عطل (2026-10-30): كان سطر الإفصاح المولَّد يلتصق بالعنوان التالي فيصير جزءًا من قائمة
    # بلا فاصل، فيفسد العرض والطباعة. الفاصل الآن سطر فارغ واحد ثابت قبل ما يلي.
    t = (t[:m.end()] + ("\n\n" + body if body else "") + "\n\n" + "\n".join(gen)
         + "\n\n" + t[end:].lstrip("\n"))
    if el:
        sm = re.search(r"^##\s+المصادر والمراجع\s*$", t, re.M)
        if sm:
            t = t[:sm.end()] + "\n\n" + el + t[sm.end():]
        else:
            t = t.rstrip("\n") + "\n\n" + el + "\n"
    p.write_text(t, encoding="utf-8")
    inject_sources_state(date, c)
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
                        f"و{manual_n} يُفحص يدويًا."
                        + (f" {tail}" if tail else ""))
    d["sources_line"] = line_ar(c)
    if isinstance(d.get("source_reliability"), dict):
        d["source_reliability"]["checked"] = c["checked"]
        d["source_reliability"]["approved"] = c["approved"]
        d["source_reliability"]["ok"] = c["ok"]
    if isinstance(d.get("source_reliability"), dict):
        _st = json.loads((B / "feeds" / f"feeds-{date}.status.json").read_text(encoding="utf-8")) if (B / "feeds" / f"feeds-{date}.status.json").exists() else {}
        d["source_reliability"]["stale"] = len(_st.get("stale") or [])
        d["source_reliability"]["stale_days_limit"] = _st.get("stale_days_limit")
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
    state = feeds_state(date)
    items = int(c["items"]) if "items" in c else int(state.get("items") or 0)
    has_feed_state = bool(c.get("feeds_status_file", state.get("present")))
    if md.exists() and line_ar(c).split("·")[0].strip() not in md.read_text(encoding="utf-8"):
        bad.append(f"متن التقرير لا يحمل سطر الأرقام المعتمد: {line_ar(c)}")
    # كل جملة إجمالي داخل المتن تحمل الأرقام المعتمدة — لا موضع بلا رقابة
    # (عطل 2026-11-10: جملة الإفصاح في المتن بقيت على 51/9/1875 بينما الحالة 59/1/1851)
    if md.exists():
        text = md.read_text(encoding="utf-8")
        pairs = [(r"نجحت\s+(\d+)", c["ok"], "نجحت"),
                 (r"(\d+)\s*متعذّر", c["failed"], "متعذّر"),
                 (r"(\d+)\s*متعذر", c["failed"], "متعذّر")]
        if has_feed_state:
            pairs.append((r"مجموع العناصر(?:\s+المقروءة)?\s+(\d+)", items, "مجموع العناصر"))
        for pat, want, label in pairs:
            for found in re.findall(pat, text):
                if int(found) != int(want):
                    bad.append(f"جملة إجمالي الفحص في المتن تحمل رقمًا قديمًا: «{label} {found}» "
                               f"والمعتمد {want} — أعد توليد الأرقام")
        if re.search(r"فشلت\s+\d+", text):
            bad.append("المتن يستعمل «فشلت» بدل المصطلح المعتمد «متعذّر» في جملة إجمالي")
    en = english_master_path(date)
    if has_feed_state and en.is_file():
        text_en = en.read_text(encoding="utf-8")
        en_pairs = [
            (r"\b(\d+)\s+(?:feeds?|sources?)\s+were\s+checked\b", c["checked"], "checked"),
            (r"\b(\d+)\s+succeeded\b", c["ok"], "succeeded"),
            (r"\b(\d+)\s+failed\b", c["failed"], "failed"),
            (r"\bTotal items read:\s*(\d+)", items, "items read"),
            (r"\btotal number of items was\s*(\d+)", items, "items read"),
            (r"\b(\d+)\s+items were read\b", items, "items read"),
        ]
        for pat, want, label in en_pairs:
            for found in re.findall(pat, text_en, flags=re.IGNORECASE):
                if int(found) != int(want):
                    bad.append(f"جملة إجمالي الفحص بالنسخة الإنجليزية تحمل {label}={found}؛ المعتمد {want}")
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
        touched = sync_feed_totals(a.date, c)
        print(f"  {'✔' if ok1 else '✘'} متن التقرير: {m1}")
        print(f"  {'✔' if ok2 else '✘'} ملف الواجهة: {m2}")
        print(f"  ✔ إجماليات المتن/الأصل الإنجليزي من الحالة: {len(touched)} ملفًا محدّثًا")
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


def sources_state_section(date: str, c: dict) -> str:
    """قسم «حالة المصادر والإفصاح» — مُولَّد من ملف حالة التغذيات ومن العدّاد الحاكم.

    عطل (2026-11-01): كان القسم يُكتب يدويًا في متن التقرير فغاب في إصدار اليوم،
    وسقط فحص سطح الإضافات (G050) مغلقًا. الآن يُولَّد آليًا في كل تشغيل.
    """
    p = B / "feeds" / f"feeds-{date}.status.json"
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    items = int(d.get("items") or 0)
    limit = int(d.get("stale_days_limit") or 14)
    stale = [str(x) for x in (d.get("stale") or [])]
    manual = [str(x) for x in (d.get("manual_reference") or [])]
    attempts = d.get("failed_attempts") or []
    nums = []
    for a in attempts:
        n = a.get("num")
        if n is not None and str(n) not in nums:
            nums.append(str(n))

    def ar_list(xs):
        return "، ".join(xs)

    parts = [f"فُحصت **{c['checked']}/{c['checked']} تغذية** بجملة **{items} عنصرًا**."]
    parts = [f"فُحصت {c['checked']} تغذية من {c['checked']} تغذية.",
             f"بلغ مجموع العناصر المقروءة {items} عنصرًا."]
    if c["failed"] == 0:
        parts.append("نجحت التغذية على مستوى المصدر كله.")
    else:
        parts.append(f"تعذّرت {c['failed']} تغذية من أصل {c['checked']}.")
    if manual:
        parts.append(f"سُجلت مرجعية يدوية للمصدرين {ar_list(manual)} — العدد {len(manual)}.")
    if stale:
        parts.append(f"وُسمت مصادر متقادمة وفق حد {limit} يومًا: {ar_list(stale)} — العدد {len(stale)}؛ "
                     "لم يُستند إليها وحدها في إثبات واقعة جديدة.")
    if nums:
        parts.append(f"سُجل تعذر مساري المصدرين {ar_list(nums)} في محاولات فرعية، مع بقاء حالة التغذية "
                     "الكلية ناجحة عبر المسارات المعتمدة البديلة.")
    if not d.get("empty"):
        parts.append("لا تغذية فارغة، ولا يُخفى أي قيد عن القارئ.")
    return "## حالة المصادر والإفصاح\n" + "\n\n".join(parts)


def inject_sources_state(date: str, c: dict) -> tuple[bool, str]:
    """يكتب/يستبدل قسم «حالة المصادر والإفصاح» قبل «المصادر والمراجع» بلا تكرار."""
    p = report_path(date)
    if not p.exists():
        return False, f"لا نص تقرير: {p}"
    t = p.read_text(encoding="utf-8")
    block = sources_state_section(date, c)
    pat = re.compile(r"^##\s+حالة المصادر والإفصاح\s*$.*?(?=^##\s+المصادر والمراجع\s*$)", re.M | re.S)
    if pat.search(t):
        t = pat.sub(block + "\n\n", t, count=1)
    else:
        m = re.search(r"^##\s+المصادر والمراجع\s*$", t, re.M)
        if not m:
            return False, "قسم «المصادر والمراجع» غير موجود"
        t = t[:m.start()] + block + "\n\n" + t[m.start():]
    p.write_text(t, encoding="utf-8")
    return True, str(p)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validators"))
    from _guard import run
    run(main)
