#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بوابة نظافة أسطح صفحة الإصدار وصفحة الإضافات.

تمنع هذه البوابة تكرار عناوين الأقسام، وتسرب الرموز الداخلية أو النصوص
البديلة، وتجاوز طول قسم «مستوى التهديد»، وظهور «تتبع الوقائع»، كما تثبت
أن كتلة «أهم الأخبار المتعلقة بالأمن البحري» في الإضافات لا في الإصدار.

العقد: الخروج 0 عند المطابقة، والخروج 2 عند أي منع أو تعذر قياس.
"""
from __future__ import annotations

import os
import sys

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

GATE_NAME = "نظافة أسطح الإصدار والإضافات"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from site_root import resolve_site_root  # noqa: E402  (ك-590: مصدر واحد لجذر الموقع)

SEAWATCH_ROOT = resolve_site_root() or (Path(__file__).resolve().parents[2] / "seawatch")
REPORT_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.html$")
THREAT_TITLE = "مستوى التهديد"
NEWS_TITLE = "أهم الأخبار المتعلقة بالأمن البحري"
TRACKING_TITLE = "تتبع الوقائع"
BASE_THREAT_WORD_LIMIT = 110  # سقف المالك (2026-11-04) لثلاثة قطاعات معلنة
BASE_SECTORS = 3
PER_SECTOR_WORDS = 18  # كلفة قياسية للقطاع الواجب: سطر إعلان مستواه + صفّه في الجدول
THREAT_WORD_LIMIT = BASE_THREAT_WORD_LIMIT  # قيمة احتياطية عند تعذر قراءة عدد القطاعات

_TOKEN_START = r"(?<![A-Za-z0-9_])"
_TOKEN_END = r"(?![A-Za-z0-9_])"
INTERNAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("وسم قطاع Z1..Z5", re.compile(rf"{_TOKEN_START}Z[1-5]{_TOKEN_END}")),
    (
        "درجة إسناد رمزية",
        re.compile(rf"{_TOKEN_START}(?:A/1|B/2|C/3|D/4|E/5|F/6){_TOKEN_END}"),
    ),
)
# قياس 2026-11-04: أرقام سجل الوقائع (MN/BF/IMO) هي مُعرّف البطاقة المرئي بحسب تصميم
# المالك، ورموز التقدير EST تظهر في جدول رموز التقدير المعتمد داخل صفحة الإضافات.
# فيُمنع ظهورها داخل متن قسم «مستوى التهديد» وحده (موضع الاكتظاظ الذي شكا منه المالك)،
# ولا يُمنع ظهورها في موضعها المصمَّم.
THREAT_ONLY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "رقم سجل MN/BF/IMO",
        re.compile(rf"{_TOKEN_START}(?:MN|BF|IMO)-\d{{4}}(?:-[A-Za-z0-9]+)+{_TOKEN_END}"),
    ),
    (
        "رمز تقدير EST",
        re.compile(rf"{_TOKEN_START}EST-\d{{4}}(?:-[A-Za-z0-9]+)+{_TOKEN_END}"),
    ),
)
# قياس 2026-11-04: «غير متاح» و«غير متاحين» عبارات إفصاح مشروعة عن معلومة غائبة في
# المصدر (مثل «النصان الكاملان غير متاحين»)، فحُصر المنع في رسائل البديل التي طلب
# المالك حذفها صراحةً من سطح القارئ.
FORBIDDEN_PHRASES = (
    "الترجمة غير مدرجة في الدفتر",
    "الرابط الرسمي غير مدرج في الدفتر",
    "التوقيت غير مسجّل في المصدر",
    "لا تتوفر إحداثيات قابلة للرسم",
)
HIDDEN_TAGS = frozenset({"head", "script", "style", "template", "noscript"})
HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
)


class GateInputError(ValueError):
    """تعذر قياس مدخل؛ يجب تحويله إلى منع لا إلى نجاح صامت."""


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    parent: "Node | None" = None
    children: list["Node | str"] = field(default_factory=list)
    line: int = 0


class SurfaceParser(HTMLParser):
    """محلل HTML صغير يحتفظ بالبنية اللازمة للنص المرئي والأقسام."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self.stack: list[Node] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(
            tag.lower(),
            {key.lower(): (value or "") for key, value in attrs},
            parent=self.stack[-1],
            line=self.getpos()[0],
        )
        self.stack[-1].children.append(node)
        if node.tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(
            tag.lower(),
            {key.lower(): (value or "") for key, value in attrs},
            parent=self.stack[-1],
            line=self.getpos()[0],
        )
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        wanted = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == wanted:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _self_hidden(node: Node) -> bool:
    if node.tag in HIDDEN_TAGS:
        return True
    attrs = node.attrs
    if "hidden" in attrs or attrs.get("aria-hidden", "").strip().lower() == "true":
        return True
    style = attrs.get("style", "").lower()
    return bool(re.search(r"display\s*:\s*none|visibility\s*:\s*hidden", style))


def _visible_nodes(node: Node, hidden: bool = False):
    current_hidden = hidden or _self_hidden(node)
    if current_hidden:
        return
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from _visible_nodes(child, current_hidden)


def _text(node: Node, skip_tags: frozenset[str] = frozenset()) -> str:
    if _self_hidden(node) or node.tag in skip_tags:
        return ""
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, Node):
            child_text = _text(child, skip_tags)
            if child_text:
                parts.append(child_text)
        elif child.strip():
            parts.append(child)
    return _normalise(" ".join(parts))


def _parse(path: Path, label: str) -> Node:
    if not path.exists():
        raise GateInputError(f"{label}: الملف غير موجود: {path}")
    if not path.is_file():
        raise GateInputError(f"{label}: المسار ليس ملفًا قابلًا للقياس: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GateInputError(f"{label}: تعذرت قراءة الملف: {path} ({exc})") from exc
    if not raw.strip():
        raise GateInputError(f"{label}: الملف فارغ؛ تعذر القياس: {path}")
    parser = SurfaceParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:  # الفشل المغلق عند تعذر تحليل السطح
        raise GateInputError(f"{label}: تعذر تحليل HTML؛ فشل مغلق: {exc}") from exc
    return parser.root



def _zone_count(date: str | None) -> int | None:
    """عدد القطاعات المعلنة لذلك التاريخ من بطاقتها الحاكمة (مصدر واحد)."""
    if not date:
        return None
    brain = Path(__file__).resolve().parents[1]
    for path in (brain / "web" / "zones" / f"{date}.json", brain / "web" / "zone-registry.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        zones = data.get("zones")
        if isinstance(zones, list) and zones:
            return len(zones)
    return None


def _word_limit(date: str | None) -> tuple[int, int | None]:
    """السقف = سقف المالك + كلفة كل قطاع زائد عن ثلاثة (يمنع سقفًا غير قابل للتحقق عند التوسع)."""
    count = _zone_count(date)
    if count is None:
        return BASE_THREAT_WORD_LIMIT, None
    extra = max(0, count - BASE_SECTORS)
    return BASE_THREAT_WORD_LIMIT + PER_SECTOR_WORDS * extra, count

def _latest_report() -> Path:
    reports_dir = SEAWATCH_ROOT / "dist" / "reports"
    if not reports_dir.is_dir():
        raise GateInputError(f"صفحة الإصدار الافتراضية: مجلد التقارير غير موجود: {reports_dir}")
    candidates = sorted(
        path for path in reports_dir.iterdir() if path.is_file() and REPORT_NAME.fullmatch(path.name)
    )
    if not candidates:
        raise GateInputError(f"صفحة الإصدار الافتراضية: لا يوجد تقرير مؤرخ قابل للقياس داخل {reports_dir}")
    return candidates[-1]


def _resolve_report(value: str | None) -> Path:
    return Path(value).expanduser() if value else _latest_report()


def _resolve_additions(value: str | None) -> Path:
    return Path(value).expanduser() if value else SEAWATCH_ROOT / "dist" / "additions.html"


def _surface_text(root: Node) -> str:
    return _text(root)


def _surface_h2(root: Node) -> list[tuple[Node, str]]:
    return [
        (node, _text(node))
        for node in _visible_nodes(root)
        if node.tag == "h2" and _text(node)
    ]


def _threat_body(node: Node) -> str:
    ancestor = node.parent
    while ancestor is not None and ancestor.tag not in {"section", "article"}:
        ancestor = ancestor.parent
    if ancestor is not None:
        return _text(ancestor, HEADING_TAGS)

    # HTML مصغر أو قديم بلا section: خذ الأشقاء بعد h2 حتى h2 التالي.
    if node.parent is None:
        return ""
    parts: list[str] = []
    found = False
    for child in node.parent.children:
        if child is node:
            found = True
            continue
        if not found:
            continue
        if isinstance(child, Node):
            if child.tag == "h2":
                break
            if not _self_hidden(child):
                parts.append(_text(child, HEADING_TAGS))
        elif child.strip():
            parts.append(child)
    return _normalise(" ".join(parts))


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def violations(report: str | Path | None = None, additions: str | Path | None = None) -> list[str]:
    """أعد أسباب المنع فقط؛ لا تطبع ولا تغيّر الملفات، فتصلح للاختبار."""
    failures: list[str] = []
    try:
        report_path = _resolve_report(str(report) if report is not None else None)
        additions_path = _resolve_additions(str(additions) if additions is not None else None)
        report_root = _parse(report_path, "صفحة الإصدار")
        additions_root = _parse(additions_path, "صفحة الإضافات")
    except GateInputError as exc:
        return [str(exc)]

    surfaces = (
        ("صفحة الإصدار", report_root),
        ("صفحة الإضافات", additions_root),
    )
    surface_texts = [(label, _surface_text(root)) for label, root in surfaces]

    # 1) لا يتكرر عنوان h2 بالنص نفسه داخل الصفحة نفسها.
    for label, root in surfaces:
        headings = _surface_h2(root)
        counts = Counter(text for _, text in headings)
        for title, count in sorted(counts.items()):
            if count > 1:
                failures.append(f"{label}: عنوان قسم h2 مكرر {count} مرات: «{title}»")

    # 2) لا تظهر الرموز الداخلية في النص المرئي؛ style/script/head والمخفي مستثنون.
    for label, text in surface_texts:
        for description, pattern in INTERNAL_PATTERNS:
            matches = sorted(set(pattern.findall(text)))
            for match in matches:
                failures.append(f"{label}: رمز داخلي ظاهر ({description}): «{match}»")

    # 2-ب) رموز السجلات والتقدير ممنوعة داخل متن قسم «مستوى التهديد» وحده.
    for node, title in _surface_h2(report_root):
        if title != THREAT_TITLE:
            continue
        body = _threat_body(node)
        for description, pattern in THREAT_ONLY_PATTERNS:
            for match in sorted(set(pattern.findall(body))):
                failures.append(
                    f"صفحة الإصدار: رمز داخلي في متن «{THREAT_TITLE}» ({description}): «{match}»"
                )

    # 3) لا تظهر رسائل البديل الممنوعة.
    for label, text in surface_texts:
        for phrase in FORBIDDEN_PHRASES:
            if phrase in text:
                failures.append(f"{label}: نص بديل ممنوع ظاهر: «{phrase}»")

    # 4) قِس متن قسم مستوى التهديد في صفحة الإصدار دون عنوان h2 نفسه.
    threat_nodes = [node for node, title in _surface_h2(report_root) if title == THREAT_TITLE]
    if not threat_nodes:
        failures.append(f"صفحة الإصدار: قسم «{THREAT_TITLE}» غير موجود؛ تعذر قياس حد الكلمات")
    else:
        report_date = re.search(r"(\d{4}-\d{2}-\d{2})", report_path.name)
        date_value = report_date.group(1) if report_date else None
        limit, zones_count = _word_limit(date_value)
        for node in threat_nodes:
            count = _word_count(_threat_body(node))
            if count > limit:
                extra_note = (
                    f" · قطاعات معلنة: {zones_count}"
                    if zones_count is not None
                    else " · تعذر قراءة عدد القطاعات؛ حُسب السقف الأساسي"
                )
                failures.append(
                    f"صفحة الإصدار: متن قسم «{THREAT_TITLE}» يتجاوز السقف: {count} كلمة"
                    f" (الحد {limit} = {BASE_THREAT_WORD_LIMIT} + {PER_SECTOR_WORDS}×القطاعات الزائدة عن {BASE_SECTORS}{extra_note})"
                )

    # 5) عنوان تتبع الوقائع ممنوع على كلا السطحين.
    for label, text in surface_texts:
        if TRACKING_TITLE in text:
            failures.append(f"{label}: عنوان «{TRACKING_TITLE}» ممنوع على السطح المرئي")

    # 6) كتلة أهم الأخبار مكانها الإضافات فقط؛ الرابط المختصر في الإصدار مسموح.
    report_text = _normalise(_surface_text(report_root))
    additions_text = _normalise(_surface_text(additions_root))
    if NEWS_TITLE not in additions_text:
        failures.append(f"صفحة الإضافات: العنوان المطلوب غائب: «{NEWS_TITLE}»")
    if NEWS_TITLE in report_text:
        failures.append(
            f"صفحة الإصدار: العنوان «{NEWS_TITLE}» ظاهر؛ المسموح فقط رابط «أهم الأخبار»"
        )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="فحص نظافة الأسطح المرئية لصفحة الإصدار والإضافات")
    parser.add_argument("--report", default=None, help="مسار صفحة الإصدار HTML؛ الافتراضي أحدث تقرير مؤرخ في seawatch/dist/reports")
    parser.add_argument("--additions", default=None, help="مسار صفحة الإضافات HTML؛ الافتراضي seawatch/dist/additions.html")
    parser.add_argument("--json", action="store_true", help="إخراج الحكم بصيغة JSON")
    args = parser.parse_args()
    try:
        failures = violations(args.report, args.additions)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:  # لا نجاح عند تعذر القياس الداخلي.
        failures = [f"تعذر القياس الداخلي؛ فشل مغلق: {type(exc).__name__}: {exc}"]
    status = "مطابق" if not failures else "منع"
    if args.json:
        print(json.dumps({"gate": GATE_NAME, "status": status, "violations": failures}, ensure_ascii=False))
    elif failures:
        print(f"منع: {GATE_NAME}")
        for failure in failures:
            print(f"  ✗ {failure}")
    else:
        print(f"مطابق: {GATE_NAME}")
    if failures:
        return 2
    return 0


if __name__ == "__main__":
    import sys as _sys, pathlib as _pl
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
    from _guard import run
    run(main)
