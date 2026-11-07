#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حصاد المفردات ودفعة القرار — من واقع القراءة لا من الخيال.

ثلاثة مصادر حصاد فقط:
  1) السجل الحاكم: بنود بحالة «بانتظار قرار المالك» أو «مراقب».
  2) حاصد البوابة: check_style.suggest() على إصدار اليوم (ألفاظ ثقيلة/مطلقة جديدة).
  3) الأرشيف: العبارات المتكررة (appendices/libraries/recurring-phrases.md)
     والرموز غير المعرَّفة (appendices/libraries/terminology-gaps.md).

الأوامر
-------
  --build [--date D] [--limit N]     يحسب دفعة القرار؛ لا يكتب بلا --write/--out
  --write | --apply                 يكتب دفعة القرار إلى logs/vocab-review-<D>.md
  --out PATH                        يكتب دفعة القرار إلى PATH (خيار كتابة صريح)
  --decide "اللفظ" --status approved|watch|rejected [--plain "بديل1|بديل2"] [--note "…"]
                                     يسجّل قرار المالك ويبني البوابة آليًا
  --impact "اللفظ"                   أثر اللفظ: أين ورد وكم مرة

رموز الخروج: 0 نجاح · 2 خطأ · 70 انهيار.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import traceback
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REGISTRY = BASE / "appendices" / "simplified-vocabulary.json"
BLACKLIST = BASE / "appendices" / "style-blacklist.json"
REPORTS = BASE / "reports"
RECURRING = BASE / "appendices" / "libraries" / "recurring-phrases.md"
GAPS = BASE / "appendices" / "libraries" / "terminology-gaps.md"
LOGS = BASE / "logs"
DECISIONS = LOGS / "vocabulary-decisions.jsonl"
TODAY = date.today().isoformat()


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def check_style_module():
    spec = importlib.util.spec_from_file_location("cs_vocab", BASE / "validators" / "check_style.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def registry_terms(reg: dict) -> set[str]:
    return {str(e.get("term") or "").strip() for e in reg.get("entries", [])}


def known_terms() -> set[str]:
    """كل ما حُكم عليه أو يُرصد بالفعل — لا يعود إلى الدفعة."""
    out = registry_terms(load_json(REGISTRY))
    try:
        bl = load_json(BLACKLIST)
        out |= {str(i.get("term") or "").strip() for i in bl.get("blocking", [])}
        out |= {str(i.get("term") or "").strip() for i in bl.get("watch", [])}
        out |= {str(i.get("id") or "").strip() for i in bl.get("patterns", [])}
    except (OSError, json.JSONDecodeError):
        pass
    return {x for x in out if x}


def official_terms() -> set[str]:
    try:
        g = load_json(BASE / "appendices" / "glossary-standard.json")
        return {str(k).strip() for k in (g.get("symbols") or {})}
    except (OSError, json.JSONDecodeError):
        return set()


def corpus_stats(term: str) -> dict:
    """أين ورد اللفظ فعلًا: عدد الإصدارات والمرات، وهل ورد في عنوان."""
    files, total, in_head, samples = [], 0, [], []
    for f in sorted(REPORTS.glob("*-sectioned.md")):
        t = f.read_text(encoding="utf-8")
        n = t.count(term)
        if n:
            files.append(f.stem.replace("-sectioned", ""))
            total += n
            for line in t.splitlines():
                if term in line:
                    if line.lstrip().startswith("#"):
                        in_head.append(f.stem.replace("-sectioned", ""))
                    elif len(samples) < 2:
                        samples.append(line.strip()[:110])
                    break
    return {"files": files, "count": total, "headings": sorted(set(in_head)), "samples": samples}


def harvest(date_str: str, limit: int) -> list[dict]:
    reg = load_json(REGISTRY)
    known = known_terms()
    off = official_terms()
    items: list[dict] = []
    seen: set[str] = set()

    def add(term: str, source: str, replacement: str = "", note: str = "", force: bool = False):
        term = (term or "").strip()
        if not term or term in seen:
            return
        if not force and (term in known or term in off):
            return
        seen.add(term)
        st = corpus_stats(term)
        items.append({
            "term": term, "source": source, "replacement": replacement, "note": note,
            "files": st["files"], "count": st["count"], "headings": st["headings"],
            "official": term in off, "samples": st["samples"],
        })

    # 1) السجل: المعلّق والمراقب أولًا
    for e in reg.get("entries", []):
        if e.get("status") in ("proposed", "watch"):
            add(str(e.get("term")), f"السجل الحاكم — حالة {e.get('status')}",
                " · ".join(e.get("plain") or []), str(e.get("reason") or ""), force=True)

    # 2) حاصد البوابة على إصدار اليوم (أو آخر إصدار)
    report = REPORTS / f"{date_str}-sectioned.md"
    if not report.exists():
        cands = sorted(REPORTS.glob("*-sectioned.md"))
        report = cands[-1] if cands else None
    if report and report.exists():
        try:
            for c in check_style_module().suggest(str(report)) or []:
                add(str(c.get("term")), f"حاصد البوابة على {report.name}", "", str(c.get("reason") or ""))
        except (AttributeError, KeyError, OSError, TypeError, ValueError) as exc:  # لا نُسقط الدفعة بسبب الحاصد
            print(f"  ! تعذّر تشغيل حاصد البوابة: {exc}", file=sys.stderr)

    # 3) الأرشيف: العبارات المتكررة
    if RECURRING.exists():
        for line in RECURRING.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|") or "---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3 or cells[0] in ("العبارة", ""):
                continue
            add(cells[0], f"مكتبة العبارات المتكررة — ظهرت في {cells[1]} من {cells[2]} إصدارًا")

    # 4) الرموز غير المعرَّفة
    if GAPS.exists():
        for line in GAPS.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|") or "---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3 or cells[0] in ("المصطلح", "") or "الإجمالي" in line:
                continue
            add(cells[0], f"فجوات التعريف — ظهر {cells[2]} مرة في {cells[3] if len(cells) > 3 else '؟'} إصدارًا")

    items.sort(key=lambda x: (0 if "السجل الحاكم" in x["source"] else 1, -x["count"]))
    return items[:limit]


def build(date_str: str, limit: int, write: bool = False, out_path: str | None = None) -> int:
    items = harvest(date_str, limit)
    lines = [
        f"# دفعة قرار المفردات — {date_str}", "",
        "**المصدر:** حصاد آلي من السجل الحاكم + حاصد البوابة + الأرشيف. لا بند من الذاكرة.",
        f"**عدد البنود:** {len(items)} · **السجل الحاكم:** `appendices/simplified-vocabulary.json`", "",
        "## كيف تُقرأ «الأثر»",
        "«الأثر» يقيس ما يحدث فعلًا لو مُنع اللفظ: عدد المرات في كل الإصدارات، وهل يرد في عنوان.",
        "اللفظ الذي يرد في عنوان أو في اسم رسمي يحتاج قرارًا واعيًا، لأن منعه يوقف التسليم.", "",
        "| # | اللفظ | المصدر | السياق الحقيقي | الأثر (مرات · إصدارات) | في عنوان؟ | البديل المقترح |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, it in enumerate(items, 1):
        ctx = (it["samples"][0] if it["samples"] else "—").replace("|", "/")
        lines.append(f"| {i} | `{it['term']}` | {it['source']} | {ctx} | {it['count']} · {len(it['files'])} | "
                     f"{'نعم (' + '، '.join(it['headings']) + ')' if it['headings'] else 'لا'} | "
                     f"{it['replacement'] or '—'} |")
    lines += ["", "## أمر القرار (انسخه وعدّله)", "```"]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it['term']} → ( ) مانع   ( ) مراقب   ( ) لا يُدرج      البديل: {it['replacement'] or '___'}")
    lines += ["```", "",
              "## تنفيذ القرار", "```bash",
              'python3 tools/vocab_review.py --decide "اللفظ" --status approved --plain "البديل" --note "قرار المالك — DATE"',
              "```"]
    rendered = "\n".join(lines) + "\n"
    if write or out_path:
        out = Path(out_path) if out_path else LOGS / f"vocab-review-{date_str}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"  ✔ كُتبت الدفعة: {out} · {len(items)} بندًا")
    else:
        print("  ↷ قراءة فقط: لم تُكتب الدفعة. استخدم --write/--apply أو --out PATH للكتابة.")
        print(f"  · نتيجة الحصاد: {len(items)} بندًا")
    for it in items[:6]:
        print(f"   · {it['term']}  ({it['count']} مرة في {len(it['files'])} إصدارًا)"
              + ("  ← وارد في عنوان" if it["headings"] else ""))
    return 0


def decide(term: str, status: str, plain: str, note: str) -> int:
    reg = load_json(REGISTRY)
    alts = [p.strip() for p in (plain or "").split("|") if p.strip()]
    found = None
    for e in reg.get("entries", []):
        if str(e.get("term") or "").strip() == term:
            found = e
            break
    if found is None:
        found = {"term": term, "plain": alts or ["—"], "status": status,
                 "since": TODAY, "reason": note or "قرار المالك",
                 "source": "دفعة قرار المفردات — tools/vocab_review.py"}
        reg.setdefault("entries", []).append(found)
    prev = found.get("status")
    found["status"] = status
    if alts:
        found["plain"] = alts
    found["decided"] = {"by": "صاحب القرار", "date": TODAY, "note": note or "", "from": prev}
    if status == "approved":
        found.setdefault("since", TODAY)
        if not str(found.get("reason") or "").strip():
            found["reason"] = note or "قرار المالك"
    reg["updated"] = TODAY
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    LOGS.mkdir(exist_ok=True)
    with DECISIONS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": TODAY, "term": term, "from": prev, "to": status,
                             "plain": alts, "note": note, "by": "صاحب القرار"},
                            ensure_ascii=False) + "\n")

    r = subprocess.run([sys.executable, str(BASE / "tools" / "build_vocab_gate.py"), "--apply"],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        return 2
    print(f"  ✔ سُجّل القرار: «{term}» {prev or '—'} ← {status}"
          + (f" · البديل: {' · '.join(alts)}" if alts else ""))
    return 0


def impact(term: str) -> int:
    st = corpus_stats(term)
    print(f"  اللفظ: {term}")
    print(f"  المرات: {st['count']} · الإصدارات: {len(st['files'])}"
          + (f" ({'، '.join(st['files'][:8])})" if st['files'] else ""))
    print(f"  في عنوان: {'نعم — ' + '، '.join(st['headings']) if st['headings'] else 'لا'}")
    for s in st["samples"]:
        print(f"   · {s}")
    print(f"  معرَّف رسميًا في بنك التعريفات: {'نعم' if term in official_terms() else 'لا'}")
    return 0


def fail(msg: str, code: int = 2) -> None:
    print(f"  ✘ {msg}", file=sys.stderr)
    sys.exit(code)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="حصاد المفردات ودفعة القرار (الوضع الافتراضي قراءة فقط؛ --decide يكتب السجل الحاكم)"
    )
    ap.add_argument("--build", action="store_true", help="حساب دفعة القرار")
    ap.add_argument("--write", "--apply", dest="write", action="store_true",
                    help="كتابة دفعة القرار إلى logs/vocab-review-<date>.md")
    ap.add_argument("--out", metavar="PATH", help="كتابة دفعة القرار إلى PATH")
    ap.add_argument("--date", default=TODAY)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--decide", metavar="اللفظ")
    ap.add_argument("--status", choices=["approved", "watch", "rejected", "proposed"])
    ap.add_argument("--plain", default="", help="البدائل مفصولة بـ |")
    ap.add_argument("--note", default="")
    ap.add_argument("--impact", metavar="اللفظ")
    a = ap.parse_args()

    if a.out and (a.decide or a.impact):
        fail("--out متاح مع حصاد الدفعة فقط")
    if a.write and (a.decide or a.impact):
        fail("--write/--apply متاحان مع حصاد الدفعة فقط")

    if a.impact:
        return impact(a.impact)
    if a.decide:
        if a.status not in ("approved", "watch", "rejected", "proposed"):
            fail("يجب تحديد الحالة: --status approved|watch|rejected|proposed")
        return decide(a.decide, a.status, a.plain, a.note)
    return build(a.date, a.limit, a.write, a.out)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(70)
