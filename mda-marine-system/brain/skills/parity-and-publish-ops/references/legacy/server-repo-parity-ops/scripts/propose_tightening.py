#!/usr/bin/env python3
"""استخرج أصناف ثغرات التماثل من السجلات واقترح اختبارات سلبية مانعة."""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

RULES = {
    "parity": (r"تماثل|مطابقة|انحراف|مستودع|شجرة محلية|مفقود من المستودع|زائد في المستودع", "assert parity_counts(local, repo, extras) == (local, repo, 0)"),
    "direction": (r"اتجاه|مصدر الحقيقة|GitHub|الخادم|تطبيق|مزامنة", "assert sync_plan(direction='server-to-repo').direct_main_push is False"),
    "exclusions": (r"استثناء|backup-repo|state/|سرّي|مخرجات مولّدة|لا تُنقل", "assert excluded_path('state/webhook-secret.txt').has_reason"),
    "portable-paths": (r"مسار مطلق|قابلية النقل|/home/ubuntu|__file__|BRAIN_DIR|SITE_DIR", "assert run_portable_gate(brain, site) == 0"),
    "git-flow": (r"فرع|طلب دمج|main|دفع مباشر|merge", "assert delivery_plan.push_target != 'main' and delivery_plan.pull_request is True"),
    "secret-scan": (r"تسرّب|سر|token|مفتاح|chat_id|env", "assert scan_repo_for_secrets(repo).count == 0"),
}


def _root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("BRAIN_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    here = Path(__file__).resolve()
    for base in (here.parent, *here.parents):
        for name in ("brain-marine-news", "brain"):
            candidate = base / name
            if (candidate / "audit").is_dir():
                return candidate
    return here.parents[2]


def _records(brain: Path) -> list[dict]:
    rows: list[dict] = []
    for path in (brain / "audit" / "faults-index.jsonl", brain / "audit" / "faults-raw.jsonl"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    markdown = brain / "audit" / "سجل-الأعطال-والثغرات.md"
    if markdown.is_file():
        for line in markdown.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.startswith("|") or re.match(r"\|\s*-", line):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 6 and re.match(r"^[كزعثم]-\d+", cells[0]):
                rows.append({"id": cells[0], "axis": cells[2], "symptom": cells[3], "cause": cells[4], "fix": cells[5], "barrier": cells[6] if len(cells) > 6 else ""})
    return rows


def _classify(record: dict) -> str:
    explicit = str(record.get("category") or record.get("cls") or record.get("axis") or "").lower()
    text = " ".join(str(record.get(key, "")) for key in ("surface", "area", "symptom", "cause", "fix", "barrier", "rule"))
    for name, (pattern, _) in RULES.items():
        if re.search(pattern, explicit, re.I) or re.search(pattern, text, re.I):
            return name
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    brain = _root(args.brain)
    records = _records(brain)
    counts = Counter(_classify(record) for record in records)
    samples: dict[str, list[str]] = defaultdict(list)
    for record in records:
        kind = _classify(record)
        ident = str(record.get("id") or record.get("code") or "سجل")
        if ident not in samples[kind] and len(samples[kind]) < 5:
            samples[kind].append(ident)
    proposals = []
    for kind, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        if kind == "other":
            test = "assert classify_fault(record) != 'other'"
            action = "أضف قاعدة تصنيف صريحة قبل إغلاق العطل"
        else:
            test = RULES[kind][1]
            action = f"ثبّت الاختبار السلبي المقترح لصنف {kind} ثم اكسره عمدًا للتأكد من المنع"
        proposals.append({"class": kind, "count": count, "sample": samples[kind], "negative_test": test, "tightening": action})
    payload = {"brain": str(brain), "records": len(records), "classes": dict(counts), "proposals": proposals}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"  السجلات المقروءة: {len(records)} · أصناف الثغرات: {len(counts)}")
    for proposal in proposals:
        print(f"  [{proposal['class']}] {proposal['count']} حالة · أمثلة: {', '.join(proposal['sample'])}")
        print(f"       التشديد: {proposal['tightening']}")
        print(f"       اختبار سلبي: {proposal['negative_test']}")
    print("  القاعدة: لا تُغلق الثغرة قبل تسجيل السبب الجذري والقاعدة والاختبار السلبي.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
