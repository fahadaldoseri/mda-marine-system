#!/usr/bin/env python3
"""فحص صحة معنى الترجمة بالعكس لوقائع 17–23 أكتوبر 2026.

يستخرج الحقول من الأصل الإنجليزي ومن الكتلة العربية بنداءين منفصلين، ثم يشغّل
meaning_compare.py ويحفظ الأدلة الخام خارج المستودع. لا يعدّل أي تقرير.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
NODE = "manus-node"
CLIENT = str(ROOT / "tools" / "llm.mjs")
COMPARE = ROOT / "tools" / "meaning_compare.py"
DEFAULT_OUT = Path("/home/ubuntu/language-fix-01/reverse-check")
DATES = [f"2026-10-{d:02d}" for d in range(17, 24)]

# These two prompts are deliberately kept verbatim from the execution order.
SOURCE_SYSTEM = '''Extract the following JSON from the English text about a maritime security event. Use only what is explicitly written. "numbers": every numeral as a string. "names": ships, bodies, and places in Latin letters. "attributed_to": the body that made the statement or claim. "certainty": official_confirmed | official_unconfirmed | media_report | one_sided_claim | estimate | none. "attribution": none | named_by_official | claimed_by_party | alleged_by_media. "event_type": attack | advisory | warning | military_interaction | piracy | suspicious_activity | incident_update | background | market_indicator | other. Output JSON only.'''
ARABIC_SYSTEM = '''استخرج من النص العربي التالي عن واقعة أمن ملاحي JSON بالمخطط نفسه تمامًا. استعمل ما كُتب صراحة فقط. اكتب الأسماء بالأحرف اللاتينية كما هي معروفة (UKMTO, IRGC, IMO…). المخرج JSON فقط.'''

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "event_type": {"type": "string", "enum": ["attack", "advisory", "warning", "military_interaction", "piracy", "suspicious_activity", "incident_update", "background", "market_indicator", "other"]},
        "certainty": {"type": "string", "enum": ["official_confirmed", "official_unconfirmed", "media_report", "one_sided_claim", "estimate", "none"]},
        "attribution": {"type": "string", "enum": ["none", "named_by_official", "claimed_by_party", "alleged_by_media"]},
        "attributed_to": {"type": "string"},
        "numbers": {"type": "array", "items": {"type": "string"}},
        "names": {"type": "array", "items": {"type": "string"}},
        "location": {"type": "string"},
        "time": {"type": "string"},
    },
    "required": ["event_type", "certainty", "attribution", "attributed_to", "numbers", "names", "location", "time"],
    "additionalProperties": False,
}

@dataclass
class Event:
    code: str
    date: str
    text: str
    record: dict[str, Any]
    source_path: Path | None = None
    source_text: str | None = None
    source_reason: str = ""


def _strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return html.unescape(raw)


def _latin_only(raw: str) -> str:
    """Keep English source lines and discard Arabic editorial annotations."""
    raw = _strip_html(raw)
    out: list[str] = []
    for line in raw.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        arabic = len(re.findall(r"[\u0600-\u06ff]", line))
        latin = len(re.findall(r"[A-Za-z]", line))
        # Mixed source lines such as a URL/date are still useful; predominantly
        # Arabic editorial prose is not an English original.
        if latin >= 3 and (arabic == 0 or latin >= arabic * 2):
            out.append(line)
    return "\n".join(out).strip()


def _looks_like_english_original(path: Path, raw: str) -> bool:
    if path.name in {"manifest.json", "status.json"} or path.suffix.lower() not in {".txt", ".md", ".html"}:
        return False
    text = _latin_only(raw)
    words = re.findall(r"[A-Za-z]{2,}", text)
    if len(text) < 160 or len(words) < 25:
        return False
    # Feed markdown is a title/index catalogue, not an English source body.
    if "feeds" in path.parts and sum(1 for x in text.splitlines() if x.startswith("- ")) > 8:
        return False
    return True


def discover_english_sources(root: str | Path, date: str | None = None) -> list[Path]:
    """Return locally saved text-like files that contain a real English source.

    The daily JSON files are also inspected for an explicit English-original
    field, but the current corpus has none; metadata such as `source` is not
    promoted to an original by this function.
    """
    root = Path(root)
    dates = [date] if date else DATES
    paths: list[Path] = []
    for day in dates:
        for base in (root / "archive" / "originals" / day, root / "archive" / "source-text" / day):
            if base.is_dir():
                paths.extend(sorted(p for p in base.rglob("*") if p.is_file()))
    # Explicit original-English fields, if a future daily JSON contains one.
    for day in dates:
        p = root / "cumulative-2026" / "daily" / f"{day}.json"
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, list):
            for row in data:
                if not isinstance(row, dict):
                    continue
                for key, val in row.items():
                    if key.lower() in {"english_original", "original_english", "source_text"} and isinstance(val, str) and val.strip():
                        # The caller cannot compare a virtual string path, so
                        # materialize only in a temp-free deterministic cache.
                        cache = root / "tools" / "_oneoff" / ".english-original-cache"
                        cache.mkdir(parents=True, exist_ok=True)
                        q = cache / f"{day}-{row.get('code','row')}.txt"
                        q.write_text(val, encoding="utf-8")
                        paths.append(q)
    out: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _looks_like_english_original(p, raw):
            out.append(p)
    return out


def extract_arabic_events(text: str, date: str) -> list[dict[str, str]]:
    """Split a sectioned report into independent MN- event blocks."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if re.search(rf"MN-{re.escape(date)}-\d+", line)]
    events: list[dict[str, str]] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        for i in range(start + 1, end):
            if lines[i].startswith("## "):
                end = i
                break
        block = "\n".join(lines[start:end]).strip()
        m = re.search(rf"(MN-{re.escape(date)}-\d+)", block)
        if m and block:
            events.append({"code": m.group(1), "date": date, "text": block})
    return events


def load_records(date: str) -> dict[str, dict[str, Any]]:
    p = ROOT / "cumulative-2026" / "daily" / f"{date}.json"
    if not p.exists():
        return {}
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {r.get("code"): r for r in rows if isinstance(r, dict) and r.get("code")}


def load_events() -> list[Event]:
    events: list[Event] = []
    for date in DATES:
        p = ROOT / "reports" / f"{date}-sectioned.md"
        if not p.exists():
            continue
        records = load_records(date)
        for row in extract_arabic_events(p.read_text(encoding="utf-8"), date):
            events.append(Event(row["code"], date, row["text"], records.get(row["code"], {})))
    return events


def _refs(event: Event) -> list[str]:
    text = event.text + " " + json.dumps(event.record, ensure_ascii=False)
    refs = re.findall(r"(?<![A-Za-z0-9])\d{2,6}(?:[-/]\d{2,4})(?![A-Za-z0-9])", text)
    # IMO numbers and distinctive report numerals are useful only when present
    # in the English file as well; no Arabic-to-English translation is guessed.
    refs += re.findall(r"(?<![A-Za-z0-9])(?:IMO\s*)?\d{6,8}(?![A-Za-z0-9])", text, re.I)
    return list(dict.fromkeys(x.lower() for x in refs))


def _source_hints(event: Event) -> list[str]:
    hints = [event.record.get("source", "")]
    hints.append(event.record.get("title", ""))
    hints.extend(_refs(event))
    return [x.lower() for x in hints if x]


def focus_source(raw: str, refs: list[str]) -> str:
    """Keep the heading/paragraph/table row for the matching bulletin refs."""
    text = _latin_only(raw)
    lines = text.splitlines()
    if not refs:
        return text
    hit_indexes: list[int] = []
    for i, line in enumerate(lines):
        low = line.lower()
        for ref in refs:
            ref_low = ref.lower()
            if ref_low in low:
                hit_indexes.append(i)
                break
            # UKMTO headings commonly render 179-26 as #179; NAVAREA may use
            # a slash while the Arabic record uses a hyphen.
            m = re.match(r"(\d+)[-/](\d+)$", ref_low)
            if m and (re.search(rf"(?<!\d){re.escape(m.group(1))}(?:[-/]26)?(?!\d)", low)):
                hit_indexes.append(i)
                break
    if not hit_indexes:
        return text
    selected: list[str] = []
    for hit in sorted(set(hit_indexes)):
        start = hit
        end = hit + 1
        while end < len(lines) and not re.match(r"^#{1,4}\s", lines[end]):
            end += 1
        if end == hit + 1:
            end = min(len(lines), hit + 2)
        selected.extend(lines[start:end])
    return "\n".join(dict.fromkeys(x for x in selected if x.strip())).strip()


def choose_source(event: Event, candidates: list[Path]) -> tuple[Path | None, str, str]:
    """Pick only an explicit, high-overlap local original; otherwise abstain."""
    refs = _refs(event)
    hints = _source_hints(event)
    scored: list[tuple[int, Path, str]] = []
    for p in candidates:
        raw = p.read_text(encoding="utf-8", errors="ignore")
        text = _latin_only(raw)
        low = text.lower()
        score = 0
        reasons: list[str] = []
        ref_hits = [r for r in refs if r in low]
        if ref_hits:
            score += 10 * len(ref_hits)
            reasons.append("refs=" + ",".join(ref_hits))
        # Source labels are accepted only as corroboration, never alone.
        for h in hints[:2]:
            words = [w for w in re.findall(r"[a-z]{3,}|\d{2,6}[-/]\d{2,4}", h) if w not in {"the", "and", "source", "official"}]
            hits = sum(1 for w in words if w in low)
            score += min(hits, 4)
        # A file named for the bulletin is useful corroboration.
        fname = p.name.lower()
        if any(r in fname for r in refs):
            score += 40
            reasons.append("filename")
        if "ukmto" in fname and any("ukmto" in h for h in hints[:2]):
            score += 8
        if score >= 10:
            scored.append((score, p, "; ".join(reasons)))
    if not scored:
        return None, "", "لا يوجد أصل إنجليزي محلي ذو تطابق صريح؛ لم يُستخدم عنوان تغذية أو وصف عربي كبديل."
    scored.sort(key=lambda x: (-x[0], str(x[1])))
    score, path, reason = scored[0]
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return path, focus_source(raw, refs), f"score={score}; {reason}"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    # llm.mjs supports a JSON array and passes each string item verbatim. This
    # is safer than line-delimited JSON here because source excerpts contain
    # newlines, and it keeps the event id out of the prompt.
    path.write_text(json.dumps([x["input"] for x in rows], ensure_ascii=False), encoding="utf-8")


def run_batch(items: list[dict[str, Any]], system: str, tmpdir: Path, label: str, model: str, workers: int) -> tuple[dict[str, dict[str, Any]], str]:
    if not items:
        return {}, "لا عناصر"
    inp = tmpdir / f"{label}.input.jsonl"
    out = tmpdir / f"{label}.output.jsonl"
    schema = tmpdir / f"{label}.schema.json"
    _write_jsonl(inp, items)
    schema.write_text(json.dumps(SCHEMA, ensure_ascii=False), encoding="utf-8")
    cmd = [NODE, CLIENT, "batch", "--input", str(inp), "--out", str(out),
           "--template", "{input}", "--system", system, "--schema", str(schema),
           "--schema-name", "extract", "--model", model, "--workers", str(workers),
           "--max-tokens", "3000", "--reasoning-effort", "minimal"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    log = (proc.stdout + "\n" + proc.stderr).strip()
    if proc.returncode != 0 or not out.exists():
        return {}, f"exit={proc.returncode}\n{log[-2000:]}"
    rows: dict[str, dict[str, Any]] = {}
    for line in out.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        index = row.get("index")
        key = None
        if isinstance(index, int) and 0 <= index < len(items):
            key = str(items[index]["id"])
        if not key:
            key = row.get("id")
        if not key:
            continue
        if row.get("error"):
            rows[key] = {"_error": str(row.get("error"))}
            continue
        try:
            val = row.get("output")
            parsed = json.loads(val) if isinstance(val, str) else val
            if not isinstance(parsed, dict):
                raise ValueError("output is not an object")
            rows[key] = normalize(parsed)
        except Exception as exc:
            rows[key] = {"_error": f"parse: {exc}; raw={str(row.get('output',''))[:500]}"}
    return rows, log[-2000:]


def normalize(data: dict[str, Any]) -> dict[str, Any]:
    out = {
        "event_type": data.get("event_type", "other"),
        "certainty": data.get("certainty", "none"),
        "attribution": data.get("attribution", "none"),
        "attributed_to": data.get("attributed_to"),
        "numbers": [str(x) for x in (data.get("numbers") or [])],
        "names": [str(x) for x in (data.get("names") or [])],
        "location": str(data.get("location") or ""),
        "time": str(data.get("time") or ""),
    }
    return out


def compare(source: Path, arabic: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(COMPARE), str(source), str(arabic)], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def write_summary(out: Path, rows: list[dict[str, Any]], logs: dict[str, str], total_events: int, source_count: int) -> None:
    major = sum(r.get("code") is not None and r.get("result") == 2 for r in rows)
    minor = sum(r.get("code") is not None and r.get("result") == 1 for r in rows)
    same = sum(r.get("code") is not None and r.get("result") == 0 for r in rows)
    unavailable = sum(r.get("code") is not None and not r.get("available") for r in rows)
    lines = ["# فحص صحة المعنى بالترجمة العكسية — 17–23 أكتوبر 2026", "",
             "> الأصل الإنجليزي والعربي أُرسلا بنداءين منفصلين لا يرى أحدهما الآخر. لم تُستخدم عناوين التغذية أو أوصاف السجل كأصل إنجليزي.", "",
             f"- الوقائع في التقارير: **{total_events}**", f"- الوقائع المفحوصة فعليًا: **{same + major + minor}**",
             f"- أصول إنجليزية محلية مطابقة: **{source_count}**", f"- بلا أصل إنجليزي فعلي: **{unavailable}**", "",
             "## النتيجة", "", "| الواقعة | التاريخ | هل الأصل متاح | رمز المقارنة (0/1/2) | الفرق (إن وُجد) |", "|---|---|---:|---:|---|"]
    for r in rows:
        diff = r.get("compare", "")
        diff = diff.replace("\n", "<br>")
        if len(diff) > 1200:
            diff = diff[:1200] + "…"
        result = "—" if r.get("result") is None else str(r["result"])
        lines.append(f"| `{r['code']}` | {r['date']} | {'نعم' if r.get('available') else 'لا'} | {result} | {diff or '—'} |")
    lines += ["", "## المخرجات الخام", "", "- ملفات `*.source.json` و`*.arabic.json` هي ناتج الاستخراج المنفصل.", "- ملفات `*.comparison.raw.txt` تحفظ stdout/stderr الخام من `meaning_compare.py`.", ""]
    for k, v in logs.items():
        lines += [f"### {k}", "", "```text", v[-4000:], "```", ""]
    lines += ["## إحصاءات", "", f"- متطابق: **{same}**", f"- فرق جوهري: **{major}**", f"- فرق ثانوي: **{minor}**", f"- بلا أصل: **{unavailable}**"]
    out.joinpath("summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--model", default="gpt-5-mini")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    candidates = discover_english_sources(ROOT)
    events = load_events()
    for event in events:
        event.source_path, event.source_text, event.source_reason = choose_source(event, candidates)
    available = [e for e in events if e.source_path and e.source_text]
    arabic_items = [{"id": e.code, "input": e.text} for e in available]
    source_items = [{"id": e.code, "input": e.source_text or ""} for e in available]
    logs: dict[str, str] = {"corpus": f"events={len(events)}; available={len(available)}; candidate_files={len(candidates)}"}
    with tempfile.TemporaryDirectory(prefix="reverse-check-") as td:
        tmp = Path(td)
        source_rows, source_log = run_batch(source_items, SOURCE_SYSTEM, tmp, "source", args.model, args.workers)
        arabic_rows, arabic_log = run_batch(arabic_items, ARABIC_SYSTEM, tmp, "arabic", args.model, args.workers)
        logs["source batch"] = source_log
        logs["arabic batch"] = arabic_log
        results: list[dict[str, Any]] = []
        for event in events:
            base = {"code": event.code, "date": event.date, "available": bool(event.source_path and event.source_text), "source": str(event.source_path) if event.source_path else None, "reason": event.source_reason}
            if not base["available"]:
                results.append({**base, "result": None, "compare": event.source_reason})
                continue
            s = source_rows.get(event.code, {"_error": "لم يصل استخراج الأصل"})
            a = arabic_rows.get(event.code, {"_error": "لم يصل استخراج العربي"})
            source_file = out / f"{event.code}.source.json"
            arabic_file = out / f"{event.code}.arabic.json"
            source_file.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            arabic_file.write_text(json.dumps(a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if "_error" in s or "_error" in a:
                raw = "source=" + json.dumps(s, ensure_ascii=False) + "\narabic=" + json.dumps(a, ensure_ascii=False)
                result = None
            else:
                result, raw = compare(source_file, arabic_file)
            raw_file = out / f"{event.code}.comparison.raw.txt"
            raw_file.write_text(raw + "\n", encoding="utf-8")
            results.append({**base, "result": result, "compare": raw})
    write_summary(out, results, logs, len(events), len(available))
    print(json.dumps({"events": len(events), "available": len(available), "checked": sum(r.get("result") in (0,1,2) for r in results), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
