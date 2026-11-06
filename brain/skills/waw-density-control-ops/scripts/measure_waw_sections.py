#!/usr/bin/env python3
"""قياس كثافة الجمل المبدوءة بـ«و» لكل قسم في ملف Markdown عربي.

الاستعمال:
  python3 measure_waw_sections.py --md <file.md> [--metric-module <style_metrics.py>]
      [--target 15] [--max 25] [--json logs/style-metrics-<DATE>.sections.json]
      [--section-filter <نص>] [--fail-over-target]

الخروج: 0 نجاح · 2 تجاوز سقف (أو هدف مع --fail-over-target) · 3 خطأ إدخال.
عند تمرير --metric-module يُستعمل منطق المشروع نفسه (تطابق تام مع البوابة).
"""
from __future__ import annotations
import argparse, importlib.util, json, pathlib, re, sys

ROOT_WAW_FALLBACK = {"و", "وهو", "وهي"}


def load_module(path: str | None):
    if not path:
        return None
    spec = importlib.util.spec_from_file_location("metric_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_metric(mod):
    if mod and hasattr(mod, "prose_lines") and hasattr(mod, "sentences") and hasattr(mod, "starts_with_waw"):
        return mod.prose_lines, mod.sentences, mod.starts_with_waw, False
    def prose_lines(text):
        for n, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s or s.startswith(("#", "|", ">", "-", "*", "```")):
                continue
            yield n, s
    def sentences(s):
        parts = re.split(r"(?<=[.؟!])\s+", s)
        return [p.strip() for p in parts if len(p.split()) >= 3]
    def starts_with_waw(sent):
        first = sent.split()[0].strip("«»\"'()[]")
        return first.startswith("و") and len(first) > 2 and first not in ROOT_WAW_FALLBACK
    return prose_lines, sentences, starts_with_waw, True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--metric-module")
    ap.add_argument("--target", type=float, default=15.0)
    ap.add_argument("--max", dest="ceiling", type=float, default=25.0)
    ap.add_argument("--json")
    ap.add_argument("--section-filter")
    ap.add_argument("--fail-over-target", action="store_true")
    a = ap.parse_args()
    p = pathlib.Path(a.md)
    if not p.exists():
        print("  ✘ الملف غير موجود:", a.md); return 3
    mod = load_module(a.metric_module)
    prose_lines, sentences, starts_with_waw, approx = make_metric(mod)
    if approx:
        print("  ⚠ لا وحدة قياس حاكمة — القاعدة المدمجة تقريبية، طابقها مع بوابة المشروع.")
    text = p.read_text(encoding="utf-8")
    rows = []
    for block in re.split(r"\n(?=## )", text):
        title = block.split("\n", 1)[0].lstrip("# ").strip()
        if not title or (a.section_filter and a.section_filter not in title):
            continue
        sents = waw = runs = long_ = 0
        for _n, line in prose_lines(block):
            run = 0
            for s in sentences(line):
                sents += 1
                if starts_with_waw(s):
                    waw += 1; run += 1
                    if run == 3: runs += 1
                else:
                    run = 0
                if len(s.split()) > 25: long_ += 1
        rows.append({"section": title, "sentences": sents, "waw": waw,
                     "pct": round(100 * waw / sents, 1) if sents else 0.0,
                     "runs3": runs, "long": long_})
    tot_s = sum(r["sentences"] for r in rows); tot_w = sum(r["waw"] for r in rows)
    overall = round(100 * tot_w / tot_s, 1) if tot_s else 0.0
    print(f"{'القسم':<44}{'جمل':>6}{'و':>5}{'النسبة':>8}")
    for r in sorted(rows, key=lambda x: -x["waw"]):
        print(f"{r['section'][:42]:<44}{r['sentences']:>6}{r['waw']:>5}{r['pct']:>7}%")
    print(f"{'الإجمالي':<44}{tot_s:>6}{tot_w:>5}{overall:>7}%")
    print(f"  الهدف {a.target}% · السقف {a.ceiling}%")
    over = [r for r in rows if r["pct"] > a.target]
    if over:
        print("  أقسام فوق الهدف: " + " · ".join(f"{r['section']} {r['pct']}% ({r['waw']}/{r['sentences']})" for r in over))
    if a.json:
        j = pathlib.Path(a.json); j.parent.mkdir(parents=True, exist_ok=True)
        j.write_text(json.dumps({"file": a.md, "overall_pct": overall, "sentences": tot_s, "waw": tot_w,
                                 "target": a.target, "max": a.ceiling, "sections": rows},
                                ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("  حُفظ:", j)
    # الأقسام صغيرة العيّنة (<10 جمل) لا تُستخدم للحكم على السقف
    solid = [r for r in rows if r["sentences"] >= 10]
    worst_solid = max((r["pct"] for r in solid), default=0.0)
    if overall > a.ceiling or worst_solid > a.ceiling:
        print(f"  ✘ تجاوز السقف (الإجمالي {overall}% · أسوأ قسم ≥10 جمل {worst_solid}%)"); return 2
    if a.fail_over_target and (over or overall > a.target):
        print("  ✘ تجاوز الهدف مع --fail-over-target"); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
