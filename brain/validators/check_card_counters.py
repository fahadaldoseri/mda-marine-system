#!/usr/bin/env python3
"""بوابة أمانة بطاقة أهم الأخبار: العدد والهدف والعنوان يجب أن يطابقوا الصفحة الهدف."""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class Node:
    def __init__(self, tag="root", attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []

    def text(self):
        return " ".join(c if isinstance(c, str) else c.text() for c in self.children).strip()


class TreeParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag.lower(), attrs, self.stack[-1])
        self.stack[-1].children.append(n)
        if n.tag not in self.VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack[-1].tag == tag.lower():
            self.stack.pop()

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].children.append(data)


def parse_document(source: str) -> Node:
    p = TreeParser()
    p.feed(source)
    p.close()
    return p.root


def _nodes(node: Node, tag: str | None = None):
    out = []
    for c in node.children:
        if isinstance(c, Node):
            if tag is None or c.tag == tag:
                out.append(c)
            out.extend(_nodes(c, tag))
    return out


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(value or "")).strip()


def _load_title_map(glossary_path: Path | None = None) -> dict[str, str]:
    """Load the approved Arabic→English title map without accepting fuzzy matches."""
    if glossary_path is None or not glossary_path.is_file():
        return {}
    try:
        entries = json.loads(glossary_path.read_text(encoding="utf-8")).get("entries", {})
    except (OSError, ValueError, TypeError):
        return {}
    return {_norm(str(k)): _norm(str(v)) for k, v in entries.items() if str(k).strip() and str(v).strip()}


def _same_title(left: str, right: str, lang: str = "ar",
                title_map: dict[str, str] | None = None) -> bool:
    left_n, right_n = _norm(left), _norm(right)
    if left_n == right_n or (lang == "en" and left_n.casefold() == right_n.casefold()):
        return True
    if lang != "en" or not title_map:
        return False
    # Compare only exact entries from the approved glossary; no substring matching.
    return (title_map.get(left_n, left_n).casefold() == right_n.casefold()
            or title_map.get(right_n, right_n).casefold() == left_n.casefold())


def _lang(root: Node) -> str:
    html_node = next(iter(_nodes(root, "html")), None)
    return (html_node.attrs.get("lang") if html_node else "") or "ar"


def _find_id(root: Node, ident: str) -> Node | None:
    return next((n for n in _nodes(root) if n.attrs.get("id") == ident), None)


def _find_heading(root: Node, title: str, tags=("h2", "h3", "h4"), lang: str = "ar",
                  title_map: dict[str, str] | None = None) -> Node | None:
    for tag in tags:
        for n in _nodes(root, tag):
            if _same_title(n.text(), title, lang, title_map):
                return n
    return None


def _count_list(node: Node) -> int:
    lists = _nodes(node, "ul") + _nodes(node, "ol")
    if not lists:
        return 0
    return sum(1 for li in _nodes(lists[0], "li"))


def _count_table_rows(node: Node) -> int:
    tables = _nodes(node, "table")
    if not tables:
        return 0
    table = tables[0]
    bodies = _nodes(table, "tbody")
    if bodies:
        return len(_nodes(bodies[0], "tr"))
    rows = _nodes(table, "tr")
    return max(0, len(rows) - 1)


def _count_heading_list(heading: Node) -> int:
    # The generator keeps a subheading and its list as siblings. Also support a
    # wrapper around both nodes, so a future layout change does not weaken this gate.
    direct_lists = _nodes(heading, "ul") + _nodes(heading, "ol")
    if direct_lists:
        return sum(1 for li in _nodes(direct_lists[0], "li"))
    parent = heading.parent
    if not parent:
        return 0
    children = parent.children
    try:
        start = children.index(heading) + 1
    except ValueError:
        return 0
    for c in children[start:]:
        if isinstance(c, str):
            continue
        if c.tag in {"h2", "h3", "h4"}:
            break
        lists = ([c] if c.tag in {"ul", "ol"} else []) + _nodes(c, "ul") + _nodes(c, "ol")
        if lists:
            return sum(1 for li in _nodes(lists[0], "li"))
    return 0


def _sections(root: Node):
    return _nodes(root, "section")


def _section_by_title(root: Node, title: str) -> Node | None:
    want = _norm(title)
    for sec in _sections(root):
        heads = _nodes(sec, "h2")
        if heads and _norm(heads[0].text()) == want:
            return sec
    return None


def _counter(text: str, lang: str) -> int | None:
    if lang == "en":
        m = re.search(r"\b(\d+)\s+(?:items?|rows?)\b", _norm(text), re.I)
    else:
        m = re.search(r"(?:^|\s)(\d+)\s+(?:بندًا|بنود|بند|صفًا|صفوف|صف)\b", _norm(text))
    return int(m.group(1)) if m else None


def _card_rows(root: Node):
    card = next((n for n in _nodes(root) if "sc-card" in n.attrs.get("class", "").split()), None)
    if not card:
        return []
    rows = []
    for row in _nodes(card):
        if "sc-row" not in row.attrs.get("class", "").split():
            continue
        labels = [n for n in _nodes(row) if "sc-l" in n.attrs.get("class", "").split()]
        more = [n for n in _nodes(row) if "sc-more" in n.attrs.get("class", "").split()]
        links = _nodes(more[0], "a") if more else []
        rows.append({
            "label": _norm(labels[0].text()) if labels else "",
            "more": _norm(more[0].text()) if more else "",
            "count": _counter(more[0].text() if more else "", _lang(root)),
            "href": (links[0].attrs.get("href") or "") if links else "",
            "goto": (links[0].attrs.get("data-goto") or "") if links else "",
        })
    return rows


def _target_for_href(href: str, ar_report: Node, ar_additions: Node, en_report: Node | None, en_additions: Node | None, lang: str) -> Node:
    path = href.split("#", 1)[0]
    if "additions" in path:
        return en_additions if lang == "en" and en_additions is not None else ar_additions
    return en_report if lang == "en" and en_report is not None else ar_report


def _expected(lang: str, title_map: dict[str, str] | None = None):
    arabic = {
        "changed": ("ما تغيّر", "ما تغيّر منذ التقرير السابق", "items"),
        "warnings": ("التحذيرات والنشرات الرسمية", "التحذيرات والنشرات الرسمية", "rows"),
        "watch": ("ما يُراقب خلال 24–72 ساعة", "علامات الإنذار المبكر 24–72 ساعة", "items"),
    }
    if lang != "en":
        return arabic
    fallback = {
        "changed": ("What changed", "What changed since the previous report", "items"),
        "warnings": ("Official warnings and advisories", "Official warnings and advisories", "rows"),
        "watch": ("What is monitored over the next 24–72 hours", "Early-warning indicators 24–72 hours", "items"),
    }
    title_map = title_map or {}
    expected = {}
    for key, (label, target, unit) in arabic.items():
        fallback_label, fallback_target, _ = fallback[key]
        expected[key] = (title_map.get(label, fallback_label), title_map.get(target, fallback_target), unit)
    return expected


def validate_one(report_html: str, additions_html: str, *, ar_report_html: str | None = None,
                 ar_additions_html: str | None = None,
                 title_map: dict[str, str] | None = None) -> list[str]:
    report = parse_document(report_html)
    additions = parse_document(additions_html)
    lang = _lang(report)
    expected = _expected(lang, title_map)
    ar_report = parse_document(ar_report_html) if ar_report_html else report
    ar_additions = parse_document(ar_additions_html) if ar_additions_html else additions
    errors = []
    rows = _card_rows(report)
    if len(rows) != 3:
        return [f"{lang}: بطاقة الفروع الثلاثة مفقودة أو زائدة: {len(rows)}"]
    seen = set()
    for key, (label, target_title, unit) in expected.items():
        matches = [r for r in rows if r["label"] == label]
        if len(matches) != 1:
            errors.append(f"{lang}: الفرع {label} غير موجود مرة واحدة")
            continue
        row = matches[0]
        seen.add(label)
        if row["count"] is None:
            errors.append(f"{lang}: عداد {label} غير مقروء")
        href = row["href"]
        if "#" not in href:
            errors.append(f"{lang}: رابط {label} بلا مرساة: {href}")
            continue
        frag = href.split("#", 1)[1]
        target = _target_for_href(href, ar_report, ar_additions, report if lang == "en" else None,
                                  additions if lang == "en" else None, lang)
        target_node = _find_id(target, frag)
        if target_node is None:
            errors.append(f"{lang}: مرساة {label} غير موجودة: #{frag}")
            continue
        target_heading = None
        if key == "changed":
            target_heading = next((n for n in _nodes(target_node, "h2")
                                   if _same_title(n.text(), target_title, lang, title_map)), None)
            measured = _count_list(target_node)
        elif key == "warnings":
            target_heading = _find_heading(target_node if target_node.tag == "section" else target,
                                           target_title, ("h2",), lang, title_map)
            measured = _count_table_rows(target_node)
            if not _nodes(target_node, "table"):
                errors.append(f"{lang}: قسم {target_title} ليس جدولًا")
        else:
            # A sub-anchor is the heading itself. Measure its sibling list until
            # the next heading; do not search only inside the heading node.
            if target_node.tag in {"h2", "h3", "h4"}:
                target_heading = target_node if _same_title(target_node.text(), target_title, lang, title_map) else None
            else:
                target_heading = _find_heading(target, target_title, ("h3", "h2"), lang, title_map)
            measured = _count_heading_list(target_heading) if target_heading else 0
            if target_heading is not target_node:
                errors.append(f"{lang}: مرساة {label} لا تهبط مباشرة على عنوان الهدف «{target_title}»: {frag}")
        if target_heading is None:
            errors.append(f"{lang}: عنوان الهدف لا يطابق {label}: {target_title}")
        if row["count"] != measured:
            errors.append(f"{lang}: {label} عداد البطاقة={row['count']} والهدف={measured}")
        goto = row["goto"]
        if goto and not _same_title(goto, target_title, lang, title_map):
            errors.append(f"{lang}: مرساة {label} بعنوان غير مطابق: {goto} ≠ {target_title}")
    if len(seen) != 3:
        errors.append(f"{lang}: فروع مفقودة في البطاقة")
    card_text = _norm(next((n.text() for n in _nodes(report) if "sc-card" in n.attrs.get("class", "").split()), ""))
    if "خلال 24 ساعة السابقة" in card_text or "over the previous 24 hours" in card_text:
        errors.append(f"{lang}: لفظ الفترة السابقة تسرب إلى بطاقة الفروع")
    if lang == "en" and re.search(r"[\u0600-\u06FF]", card_text):
        errors.append("en: نص عربي متسرب داخل بطاقة الفروع")
    return errors


def validate_card_documents(*, ar_report: str, ar_additions: str, en_report: str | None = None,
                             en_additions: str | None = None,
                             glossary_path: Path | None = None) -> list[str]:
    title_map = _load_title_map(glossary_path)
    errors = validate_one(ar_report, ar_additions, title_map=title_map)
    if en_report:
        errors.extend(validate_one(en_report, en_additions or ar_additions,
                                   ar_report_html=ar_report, ar_additions_html=ar_additions,
                                   title_map=title_map))
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--dist-root", required=True)
    args = ap.parse_args(argv)
    dist = Path(args.dist_root)
    ar_report_p = dist / "reports" / f"{args.date}.html"
    ar_additions_p = dist / "additions.html"
    en_report_p = dist / "reports" / "en" / f"{args.date}.html"
    en_additions_p = dist / "reports" / "en" / "additions.html"
    for p in (ar_report_p, ar_additions_p, en_report_p, en_additions_p):
        if not p.is_file():
            print(f"✘ ملف مطلوب مفقود: {p}")
            return 2
    errors = validate_card_documents(
        ar_report=ar_report_p.read_text(encoding="utf-8"),
        ar_additions=ar_additions_p.read_text(encoding="utf-8"),
        en_report=en_report_p.read_text(encoding="utf-8"),
        en_additions=en_additions_p.read_text(encoding="utf-8"),
        glossary_path=dist.parent / "sources" / "i18n" / "en" / "glossary.json",
    )
    if errors:
        for e in errors:
            print(f"✘ {e}")
        return 2
    print("✔ بطاقة الفروع الثلاثة: العناوين والعدادات والمراسي متطابقة عربيًا وإنجليزيًا")
    return 0


if __name__ == "__main__":
    sys.exit(main())
