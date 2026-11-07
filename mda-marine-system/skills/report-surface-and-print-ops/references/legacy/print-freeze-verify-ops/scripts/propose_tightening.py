#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""استخرج أصناف الثغرات من سجلات JSON/JSONL أو Markdown واقترح تشديدًا قابلًا للاختبار."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SUGGESTIONS = {
    "القياس والدليل": (
        "النجاح أُعلن من نص أو رمز عام دون مقياس مستقل.",
        "لا تصنّف ادعاءً مؤكدًا إلا مع أمر قابل لإعادة التشغيل ورمز خروج أو رقم.",
        "شغّل claims_table.py بصف confirmed بلا measurement؛ يجب أن يخرج 2.",
    ),
    "الطباعة والتقسيم": (
        "قواعد كسر الصفحة أو أبعاد كتلة الطباعة سمحت بقص عنصر أو ترك فراغ غير مقبول.",
        "قس عدد الصفحات وبوابتي PDF بعد كل تغيير، واحمِ الخريطة ومفتاحها من الانقسام.",
        "شغّل بوابتي PDF على نسخة ذات مفتاح خريطة مقسوم؛ يجب أن تفشلا برمز مانع.",
    ),
    "المسارات وقابلية النقل": (
        "الجذر كُتب نصًا أو استُنتج من موضع واحد ففشل التشغيل خارج البيئة الأصلية.",
        "استنتج الجذر من __file__ واسمح بـ --brain/--site، ثم اختبر التشغيل من مسار آخر.",
        "شغّل الأداة من نسخة مؤقتة مع --brain/--site؛ يجب ألا تعتمد على /home/ubuntu/.",
    ),
    "الأسطح والروابط": (
        "التحقق قاس مسارًا مشابهًا أو نسخة لم تنتشر، لا السطح المعلن الفعلي.",
        "اختبر الرابط/السطح المعلن نفسه، وسجّل رمز HTTP أو رمز خروج الانتشار قبل القبول.",
        "اطلب مسارًا غير منشور أو رابطًا 404؛ يجب أن توقف البوابة التسليم لا أن تمرره.",
    ),
    "التعديل والتحقق": (
        "التعديل الآلي أبلغ نجاحًا بلا قراءة قبلية أو تحقق من أثر الكتابة.",
        "اقرأ النمط الحقيقي، اكتب مرة، ثم تحقق من الأثر وشغّل الاختبار السلبي.",
        "مرّر نمطًا غير موجود؛ يجب أن يخرج السكربت غير صفري وألا يغيّر الملف.",
    ),
}

PATTERNS = [
    ("القياس والدليل", r"قياس|رمز خروج|exit|مقياس|دليل|نجاح.*0|غير متحقق|confirmed"),
    ("الطباعة والتقسيم", r"pdf|طباعة|صفحة|خريطة|مفتاح|فراغ|انقسام|قص|print"),
    ("المسارات وقابلية النقل", r"مسار|جذر|absolute|portable|/home/ubuntu|قابلية النقل"),
    ("الأسطح والروابط", r"رابط|404|http|انتشار|سطح|مسار معلن|ويب"),
    ("التعديل والتحقق", r"تعديل|كتابة|استبدال|import|استيراد|تحقق|أثر|نمط"),
]


def _default_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in (here, *here.parents):
        for candidate in (ancestor / "brain-marine-news", ancestor):
            if (candidate / "audit").is_dir():
                return candidate
    return here.parents[3] / "brain-marine-news"


def _records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".json", ".jsonl"}:
        if path.suffix.lower() == ".json":
            data = json.loads(text)
            if isinstance(data, list):
                return [x if isinstance(x, dict) else {"raw": x} for x in data]
            return [data] if isinstance(data, dict) else [{"raw": data}]
        out = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                out.append(item if isinstance(item, dict) else {"raw": item})
            except json.JSONDecodeError:
                out.append({"raw": line})
        return out
    return [{"raw": text}]


def _flatten(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True)


def _category(record: dict[str, Any]) -> str:
    explicit = " ".join(str(record.get(k, "")) for k in ("category", "fault_class", "kind", "axis", "area"))
    if explicit:
        for label, pattern in PATTERNS:
            if re.search(pattern, explicit, re.I):
                return label
    text = _flatten(record)
    for label, pattern in PATTERNS:
        if re.search(pattern, text, re.I):
            return label
    return "أخرى"


def _field(record: dict[str, Any], keys: tuple[str, ...], default: str) -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", "—", "-"):
            return " ".join(str(value).split())
    return default


def build_report(records: list[dict[str, Any]], source: Path) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(_category(record), []).append(record)
    lines = [f"# مقترحات تشديد مستخرجة من `{source}`", "", "هذه المقترحات لا تغلق العطل؛ يلزم تسجيل السبب الجذري والقاعدة والاختبار السلبي ثم تشغيل جولة تحقق ثانية.", ""]
    lines.append("| الصنف | عدد السجلات | السبب الجذري | القاعدة المشددة | الاختبار السلبي |")
    lines.append("|---|---:|---|---|---|")
    for category, items in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if category in SUGGESTIONS:
            cause, rule, negative = SUGGESTIONS[category]
        else:
            first = items[0]
            cause = _field(first, ("cause", "root_cause", "symptom"), "سبب جذري غير موثق في السجل")
            rule = _field(first, ("hardening_status", "fix_status", "fix"), "أضف قاعدة منع صريحة مرتبطة بهذا الصنف")
            negative = "أنشئ مدخلًا مصطنعًا يكرر الصنف وتحقق من أن البوابة ترفضه برمز غير صفري."
        lines.append(f"| {category} | {len(items)} | {cause} | {rule} | {negative} |")
    lines.extend(["", "## تتبع السجلات", ""])
    for category, items in sorted(grouped.items()):
        ids = [str(x.get("id")) for x in items if x.get("id") not in (None, "")]
        lines.append(f"- **{category}** — " + (", ".join(ids[:20]) if ids else f"{len(items)} سجل بلا معرّف"))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="اقتراح تشديدات من سجل ثغرات")
    parser.add_argument("--root", default="", help="جذر brain الذي يحوي audit/")
    parser.add_argument("--log", action="append", type=Path, help="سجل JSON/JSONL/Markdown؛ كرره لأكثر من سجل")
    parser.add_argument("--out", type=Path, default=None, help="ملف مخرج اختياري")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve() if args.root else _default_root()
    logs = args.log or [root / "audit" / "faults-raw.jsonl"]
    logs = [x.expanduser().resolve() for x in logs]
    existing = [x for x in logs if x.exists()]
    if not existing:
        print("لا يوجد سجل صالح للقراءة: " + ", ".join(map(str, logs)), file=sys.stderr)
        return 3
    all_lines = []
    for log in existing:
        try:
            all_lines.append(build_report(_records(log), log))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"تعذّر قراءة {log}: {exc}", file=sys.stderr)
            return 3
    output = "\n".join(all_lines)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
