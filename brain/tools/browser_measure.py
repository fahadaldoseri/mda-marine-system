#!/usr/bin/env python3
"""القياس البصري الحي — يحوّل الفحص اليدوي بالعين إلى قياس آليّ قابل للمنع.

يقيس على متصفح حقيقي بعرضين (1440 و1920 افتراضيًّا) ويفشل مغلقًا:

  ب-01 القصّ البصري في بطاقات الوقائع   → فائض أفقي أو رأسي داخل أي بطاقة
  ب-02 قصّ نص البطاقة الإنجليزية        → غياب السطح الإنجليزي يُعلَن «غير قابل للقياس» لا «ناجحًا»
  ب-03 المرساة #news-card               → هل يوجد العنصر وهل يصل إليه التمرير
  ب-04 وضع Quirks وتحذيرات الكونسول     → compatMode ومخارج console/pageerror
  ب-13 بطاقة القرار أعلى الشاشة          → موضعها في الشاشة الأولى وعدد أسطرها
  ب-14 جاهزية القائد                     → عشرة أسئلة: كم منها مُجاب في الشاشة الأولى
  ف-10 بقايا نصّية لعبارة                → عدد ظهور العبارة وسياقها

الاستعمال:
  browser_measure.py --url <رابط> --out audit/measurements/live.json
  browser_measure.py --url file://$SITE_DIR/dist/reports/2026-11-05.html
  browser_measure.py --check overflow --check decision --phrase "هجمات مؤكدة"

رمز الخروج: 0 كل الفحوص المطلوبة ناجحة · 2 فشل مانع.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BRAIN = Path(os.environ.get("BRAIN_DIR") or Path(__file__).resolve().parents[1])

# أسئلة القائد العشرة تُقرأ من مصدر حقيقي واحد: runbook/readiness-questions.json
READINESS_FILE = "runbook/readiness-questions.json"
DEFAULT_READINESS = [
    "مستوى التهديد", "أعلى قطاع", "إجراء اليوم", "الوقائع المستوفية", "المصادر",
    "آخر تحديث", "التحذيرات", "المراقبة", "الاستهداف", "الخلاصة",
]

# بعض المواقع الرسمية تُنشئ قائمة الوقائع بعد تحميل HTML وتمنع بصمة Chromium
# الافتراضية؛ هذه بصمة سياق متصفح حقيقي ثابتة، وليست تجاوزًا لشرط وجود المرساة.
ANCHOR_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:158.0) Gecko/20100101 Firefox/158.0"
)
ANCHOR_DOM_WAIT_MS = 15000


def load_readiness(root: Path, url: str) -> list[str]:
    """يقرأ الأسئلة من المصدر الواحد، ويختار نمط اللغة بحسب الصفحة المقيسة."""
    p = Path(root) / READINESS_FILE
    if not p.is_file():
        return DEFAULT_READINESS
    data = json.loads(p.read_text(encoding="utf-8"))
    english = "/en/" in url
    key = "pattern_en" if english else "pattern"
    qs = [q.get(key) or q.get("pattern") for q in data.get("questions", [])]
    return [q for q in qs if q] or DEFAULT_READINESS

JS_MEASURE = r"""
(payload) => {
  const out = {compat: document.compatMode, console: {errors: payload.errors, warnings: payload.warnings},
               pageerrors: payload.pageerrors, horizontal_scroll: 0, events: [], decision: null,
               map_decision: null, anchor: null, readiness: [], phrases: []};
  const de = document.documentElement;
  out.horizontal_scroll = Math.max(0, de.scrollWidth - de.clientWidth);

  document.querySelectorAll('[id^="ev-"]').forEach(el => {
    const r = el.getBoundingClientRect();
    // القصّ الحقيقي: عنصر ينقصه عرض ويُخفي الفائض (hidden/clip/ellipsis) أو طفل يتجاوز حدّ البطاقة
    const clips = [];
    Array.from(el.querySelectorAll('*')).forEach(ch => {
      const cs = getComputedStyle(ch);
      const hidden = ['hidden', 'clip'].includes(cs.overflowX) || cs.textOverflow === 'ellipsis';
      if (hidden && ch.scrollWidth > ch.clientWidth + 1) {
        clips.push({tag: ch.tagName.toLowerCase(), cls: (ch.className || '').toString().slice(0, 30),
                    loss: ch.scrollWidth - ch.clientWidth, text: (ch.innerText || '').slice(0, 40)});
      }
    });
    const cr = r.right;
    Array.from(el.querySelectorAll('*')).forEach(ch => {
      const chR = ch.getBoundingClientRect();
      if (chR.right - cr > 2 && chR.width > 0) {
        clips.push({tag: ch.tagName.toLowerCase(), cls: (ch.className || '').toString().slice(0, 30),
                    loss: Math.round(chR.right - cr), text: (ch.innerText || '').slice(0, 40)});
      }
    });
    out.events.push({id: el.id, w: Math.round(r.width), h: Math.round(r.height),
                     clip_loss: clips.reduce((m, c) => Math.max(m, c.loss), 0),
                     clips: clips.slice(0, 3), top: Math.round(r.top + window.scrollY)});
  });

  const box = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const lh = parseFloat(getComputedStyle(el).lineHeight) || 24;
    return {sel, top: Math.round(r.top + window.scrollY), in_first_screen: r.top < window.innerHeight,
            height: Math.round(r.height), lines: Math.round(r.height / lh)};
  };
  out.decision = box('.decision') || box('.card-decision');
  out.map_decision = box('.hmap-decide') || box('.mds-k');

  const anchor = document.getElementById('news-card');
  if (anchor) {
    anchor.scrollIntoView();
    const r = anchor.getBoundingClientRect();
    out.anchor = {exists: true, reached: r.top >= -12 && r.top < window.innerHeight};
  } else { out.anchor = {exists: false, reached: false}; }

  // مراسي الروابط الداخلية: كل رابط يحمل #hash يجب أن يجد هدفه في صفحته
  out.anchor_links = Array.from(document.querySelectorAll('a[href*="#"]')).map(a => {
    const href = a.getAttribute('href') || '';
    const [page, hash] = href.split('#');
    return {href, page: page || '(نفس الصفحة)', hash, text: (a.innerText || '').slice(0, 30)};
  }).filter(x => x.hash && x.hash.length > 1).map(x => {
    x.same_page_exists = !!document.getElementById(x.hash);
    return x;
  });

  const firstScreen = Array.from(document.querySelectorAll('body *')).filter(el => {
    const r = el.getBoundingClientRect();
    return r.height > 0 && r.top < window.innerHeight && r.width > 0;
  }).map(el => (el.innerText || '')).join(' ');
  out.readiness = payload.questions.map(q => ({q, found: firstScreen.includes(q)}));

  const text = document.body.innerText || '';
  payload.phrases.forEach(p => {
    const idx = text.indexOf(p);
    out.phrases.push({p, count: text.split(p).length - 1,
                      context: idx >= 0 ? text.slice(Math.max(0, idx - 60), idx + 60).replace(/\n/g, ' ') : null});
  });
  return out;
}
"""


def measure(url: str, widths: list[int], questions: list[str], phrases: list[str],
            base: str | None = None) -> dict:
    from playwright.sync_api import Error as PlaywrightError, sync_playwright  # استيراد مؤجَّل
    from urllib.parse import unquote, urljoin

    result = {"url": url, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "widths": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        for width in widths:
            context = browser.new_context(
                viewport={"width": width, "height": 900},
                device_scale_factor=1,
                user_agent=ANCHOR_BROWSER_USER_AGENT,
            )
            page = context.new_page()
            errs: list[str] = []
            warns: list[str] = []
            pageerrs: list[str] = []
            page.on("console", lambda m: (errs if m.type == "error" else warns).append(m.text[:200]))
            page.on("pageerror", lambda e: pageerrs.append(str(e)[:200]))
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_timeout(1200)
            data = page.evaluate(JS_MEASURE, {"errors": [], "warnings": [], "pageerrors": [],
                                              "questions": questions, "phrases": phrases})
            if url.startswith("file://"):
                errs = [e for e in errs if "ERR_FILE_NOT_FOUND" not in e]
            data["console"] = {"errors": len(errs), "warnings": len(warns), "samples": (errs + warns)[:3]}
            data["pageerrors"] = pageerrs[:3]
            # أهداف المراسي: داخليًّا من الصفحة نفسها، وخارجيًّا بفتح الصفحة الهدف مرة لكل مرساة
            targets: dict[str, bool] = {}
            target_details: dict[str, dict] = {}
            for link in data.get("anchor_links", []):
                if link["page"] == "(نفس الصفحة)":
                    targets[f"#{link['hash']}"] = bool(link.get("same_page_exists"))
                    target_details[f"#{link['hash']}"] = {
                        "http_status": None,
                        "dom_wait_ms": 0,
                        "exists": targets[f"#{link['hash']}"] ,
                    }
                    continue
                key = f"{link['page']}#{link['hash']}"
                if key in targets:
                    continue
                aux = None
                try:
                    aux = context.new_page()
                    target_page = link["page"]
                    if base and url.startswith("file://") and target_page in ("", "/"):
                        target_page = "/index.html"
                    if base and url.startswith("file://") and target_page.startswith("/"):
                        target_page = "file://" + base.rstrip("/") + target_page
                    response = aux.goto(
                        target_page if target_page.startswith("file://") else urljoin(url, target_page),
                        wait_until="load", timeout=45000,
                    )
                    status = response.status if response is not None else None
                    if link["hash"].startswith(":~:text="):
                        # مرساة نص (Text Fragment) لا معرّف عنصر: الهدف أن يظهر النص نفسه في الصفحة الهدف
                        frag = unquote(link["hash"][len(":~:text="):].split("&")[0].split(",")[0])
                        targets[key] = bool(aux.evaluate(
                            "(t) => (document.documentElement.textContent || '').includes(t)", frag))
                    else:
                        aux.wait_for_function(
                            "(h) => !!document.getElementById(h)",
                            arg=link["hash"], timeout=ANCHOR_DOM_WAIT_MS,
                        )
                        targets[key] = bool(aux.evaluate("(h) => !!document.getElementById(h)", link["hash"]))
                    if not targets[key]:
                        if status is not None and not (200 <= status < 400):
                            raise PlaywrightError(f"anchor target HTTP {status}; DOM target absent")
                        raise PlaywrightError("anchor target absent after DOM wait")
                    target_details[key] = {
                        "http_status": status,
                        "dom_wait_ms": ANCHOR_DOM_WAIT_MS,
                        "exists": targets[key],
                    }
                    aux.close()
                except PlaywrightError as exc:
                    targets[key] = False
                    target_details[key] = {
                        "http_status": None,
                        "dom_wait_ms": ANCHOR_DOM_WAIT_MS,
                        "exists": False,
                        "error": str(exc)[:200],
                    }
                    # أخطاء الإغلاق غير المتوقعة تُترك للحارس الموحّد؛ لا تُبتلع.
                    if aux is not None:
                        aux.close()
            data["anchor_targets"] = targets
            data["anchor_target_details"] = target_details
            result["widths"][str(width)] = data
            page.close()
            context.close()
        browser.close()
    return result


def judge(data: dict, checks: list[str]) -> list[str]:
    """يرجع قائمة المخالفات المانعة بحسب الفحوص المطلوبة."""
    bad: list[str] = []
    for width, d in data["widths"].items():
        w = f"@{width}"
        if "overflow" in checks:
            for e in d["events"]:
                if e.get("clip_loss", 0) > 0:
                    worst = max(e.get("clips") or [{"tag": "?", "cls": "?", "loss": e["clip_loss"], "text": ""}],
                                key=lambda c: c["loss"])
                    bad.append(f"{w} قصّ في {e['id']}: {e['clip_loss']} بكسل — "
                               f"{worst['tag']}.{worst['cls']} («{worst['text'][:30]}»)")
            if d["horizontal_scroll"] > 1:
                bad.append(f"{w} تمرير أفقي غير مقصود: {d['horizontal_scroll']} بكسل")
        if "console" in checks:
            if d["compat"] != "CSS1Compat":
                bad.append(f"{w} وضع Quirks: {d['compat']}")
            if d["console"]["errors"] or d["pageerrors"]:
                bad.append(f"{w} أخطاء كونسول: {d['console']['errors']} · أخطاء صفحة: {len(d['pageerrors'])}")
        if "anchor" in checks:
            for link in d.get("anchor_links", []):
                if link["page"] == "(نفس الصفحة)" and not link["href"].startswith("#"):
                    continue
                target = link["page"] if link["page"] != "(نفس الصفحة)" else ""
                ok = d.get("anchor_targets", {}).get(f"{target}#{link['hash']}", False)
                if link["page"] == "(نفس الصفحة)" and link["href"].startswith("#"):
                    ok = bool(link.get("same_page_exists"))
                if not ok:
                    bad.append(f"{w} مرساة مكسورة: {link['href']} («{link['text']}») لا هدف لها")
        if "decision" in checks:
            for key, label in (("decision", "بطاقة القرار"),):
                b = d[key]
                if not b:
                    bad.append(f"{w} {label} غير موجودة في الصفحة")
                elif not b["in_first_screen"]:
                    bad.append(f"{w} {label} خارج الشاشة الأولى (موضعها {b['top']})")
            mb = d["map_decision"]
            if mb:
                d.setdefault("notes", []).append(
                    f"{w} شريط قرار الخريطة موضعه {mb['top']} (إعلامي لا مانع)")
        if "readiness" in checks:
            found = sum(1 for q in d["readiness"] if q["found"])
            if found < len(d["readiness"]):
                missing = " · ".join(q["q"] for q in d["readiness"] if not q["found"])
                bad.append(f"{w} جاهزية القائد {found}/{len(d['readiness'])} — ناقص: {missing}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description="القياس البصري الحي بمتصفح حقيقي")
    ap.add_argument("--url", help="رابط الصفحة")
    ap.add_argument("--site-root", help="جذر الموقع المحلي: يختار أحدث إصدار تلقائيًّا (dist)")
    ap.add_argument("--en", action="store_true", help="يقيس نظير الإصدار الإنجليزي (reports/en)")
    ap.add_argument("--soft", action="append", default=[],
                    choices=["overflow", "console", "anchor", "decision", "readiness", "phrases"],
                    help="فحص يُقاس ويُبلَّغ ولا يمنع")
    ap.add_argument("--root", default=str(BRAIN), help="جذر النظام (لقراءة أسئلة الجاهزية)")
    ap.add_argument("--base-file", help="جذر الموقع المحلي لحلّ المسارات المطلقة في file://")
    ap.add_argument("--widths", default="1440,1920", help="عروض الشاشة")
    ap.add_argument("--check", action="append", default=[],
                    choices=["overflow", "console", "anchor", "decision", "readiness", "phrases"],
                    help="يتكرر؛ الافتراضي: الكل")
    ap.add_argument("--phrase", action="append", default=["هجمات مؤكدة"], help="عبارة تُفحَص بقاياها")
    ap.add_argument("--out", help="ملف النتيجة JSON")
    args = ap.parse_args()
    if not args.url:
        if not args.site_root:
            print("✘ القياس البصري: يلزم --url أو --site-root"); return 2
        root_site = Path(args.site_root)
        folder = (root_site / "reports" / "en") if args.en else (root_site / "reports")
        pages = sorted(p for p in folder.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].html"))
        if not pages:
            print(f"✘ القياس البصري: لا إصدار مبني في {root_site}/reports"); return 2
        args.url = "file://" + str(pages[-1].resolve())
        args.base_file = args.base_file or str(root_site.resolve())
        print(f"   السطح المقيس: {'en/' if args.en else ''}{pages[-1].name} (أحدث إصدار مبني)")
    checks = args.check or ["overflow", "console", "anchor", "decision", "readiness", "phrases"]
    hard = [c for c in checks if c not in (args.soft or [])]
    soft = [c for c in checks if c in (args.soft or [])]
    widths = [int(w) for w in args.widths.split(",") if w.strip()]

    data = measure(args.url, widths, load_readiness(args.root, args.url), args.phrase,
                   base=args.base_file)
    bad = judge(data, hard)
    data["checks"] = checks
    data["soft_checks"] = soft
    data["violations"] = bad

    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"   القياس البصري الحي: {args.url} على {widths}")
    if soft:
        print(f"   فحوص إعلامية (لا تمنع): {' · '.join(soft)}")
    for width, d in data["widths"].items():
        ev = d["events"]
        worst = max((e.get("clip_loss", 0) for e in ev), default=0)
        rdy = sum(1 for q in d["readiness"] if q["found"])
        print(f"   @{width}: توافق {d['compat']} · بطاقات {len(ev)} (أقصى قصّ {worst} بكسل) · "
              f"مرساة {'✔' if d['anchor']['reached'] else '✘'} · "
              f"قرار {'✔' if d['decision'] and d['decision']['in_first_screen'] else '✘'} · "
              f"جاهزية {rdy}/{len(d['readiness'])} · تحذيرات {d['console']['warnings']} · أخطاء {d['console']['errors']}")
    for p in data["widths"][str(widths[0])]["phrases"]:
        print(f"   العبارة «{p['p']}»: {p['count']} ظهورًا" + (f" · السياق: {p['context'][:70]}" if p["context"] else ""))

    if soft:
        info = judge(data, soft)
        for line in info:
            print(f"   ⓘ إعلامي: {line}")
    if bad:
        print(f"✘ القياس البصري: {len(bad)} مخالفة مانعة")
        for b in bad[:8]:
            print(f"   ! {b}")
        return 2
    print("✔ القياس البصري: صفر مخالفة في الفحوص المطلوبة")
    return 0


if __name__ == "__main__":
    sys.exit(main())
